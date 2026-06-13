// FocusForge Background Service Worker

// State management
const DEFAULT_BLOCKLIST = ['youtube.com', 'twitter.com', 'reddit.com'];

let focusSessionActive = false;
let sessionEndTime = null;
let sessionStartTime = null;
let blocklist = [...DEFAULT_BLOCKLIST];
let activityLogs = [];
let distractionAttempts = 0;
let stateLoaded = false;

// Production API endpoint. End users only provide their API key; the URL is
// fixed. For local development, set `apiBaseUrl` in chrome.storage to override.
const DEFAULT_API_BASE_URL = 'https://focusforge-api.fly.dev';

// Resolve the API base URL — the production default unless a dev override is set.
function getApiBaseUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiBaseUrl'], (result) => {
      const url = (result.apiBaseUrl || '').trim().replace(/\/+$/, '');
      resolve(url || DEFAULT_API_BASE_URL);
    });
  });
}

// Initialize extension
chrome.runtime.onInstalled.addListener(() => {
  console.log('FocusForge installed');

  loadState().then(updateBlockingRules);

  // Set up periodic log sending (every 5 minutes)
  chrome.alarms.create('sendLogs', { periodInMinutes: 5 });
});

chrome.runtime.onStartup.addListener(() => {
  loadState().then(updateBlockingRules);
});

// Listen for tab updates to detect blocked site access
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (!changeInfo.url) {
    return;
  }

  ensureStateLoaded().then(() => {
    if (!focusSessionActive) {
      return;
    }

    if (sessionEndTime && sessionEndTime <= Date.now()) {
      endFocusSession();
      return;
    }

    const domain = extractDomain(changeInfo.url);

    if (isBlockedDomain(domain)) {
      distractionAttempts++;
      
      // Log the distraction attempt
      logActivity({
        timestamp: new Date().toISOString(),
        url: changeInfo.url,
        domain: domain,
        minutesActive: 0,
        isFocusSession: true,
        isDistractionAttempt: true
      });
      
      // Redirect to blocked page
      chrome.tabs.update(tabId, { url: chrome.runtime.getURL('src/blocked.html') });
    }
  });
});

// Listen for alarms
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'sendLogs') {
    sendLogsToBackend();
  } else if (alarm.name === 'endSession') {
    endFocusSession().then(() => sendLogsToBackend());
  }
});

// Message handler for popup communication
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  handleMessage(request, sendResponse);
  return true;
});

async function handleMessage(request, sendResponse) {
  try {
    await ensureStateLoaded();

    if (sessionEndTime && sessionEndTime <= Date.now()) {
      await endFocusSession();
    }

    if (request.action === 'startSession') {
      await startFocusSession(request.duration);
      sendResponse({ success: true, focusSessionActive: true });
    } else if (request.action === 'endSession') {
      await endFocusSession();
      sendResponse({ success: true, focusSessionActive: false });
      // Flush logs after responding so the popup updates instantly; failures
      // are re-queued and retried by the periodic 'sendLogs' alarm.
      sendLogsToBackend();
    } else if (request.action === 'getStatus') {
      sendResponse({
        focusSessionActive,
        sessionEndTime,
        distractionAttempts,
        blocklist
      });
    } else if (request.action === 'updateBlocklist') {
      blocklist = normalizeBlocklist(request.blocklist);
      await saveState();
      updateBlockingRules();
      sendResponse({ success: true });
    }
  } catch (error) {
    sendResponse({ success: false, error: error.message });
  }
}

// Start a focus session
async function startFocusSession(duration = 25) {
  focusSessionActive = true;
  sessionStartTime = Date.now();
  sessionEndTime = sessionStartTime + (duration * 60 * 1000);

  // Set alarm to end session
  chrome.alarms.create('endSession', { when: sessionEndTime });

  // Update blocking rules
  updateBlockingRules();

  // Log session start as a marker (no minutes — actual focus time is recorded
  // when the session ends, so it reflects real elapsed time, not the plan).
  logActivity({
    timestamp: new Date().toISOString(),
    url: 'session-start',
    domain: 'system',
    minutesActive: 0,
    isFocusSession: true,
    isDistractionAttempt: false
  });

  await saveState();
  
  console.log(`Focus session started for ${duration} minutes`);
}

// End focus session
async function endFocusSession() {
  // Record the actual focused time (now − start), so a session ended early
  // counts only what was spent, not the planned duration. Guarded so repeat
  // calls (e.g. expiry + manual end) don't double-log.
  if (sessionStartTime) {
    logActivity({
      timestamp: new Date().toISOString(),
      url: 'session-end',
      domain: 'system',
      minutesActive: Math.max(0, (Date.now() - sessionStartTime) / 60000),
      isFocusSession: true,
      isDistractionAttempt: false
    });
    sessionStartTime = null;
  }

  focusSessionActive = false;
  sessionEndTime = null;

  // Clear the alarm if it exists
  chrome.alarms.clear('endSession');
  
  // Update blocking rules
  updateBlockingRules();

  await saveState();

  // Note: log flushing is intentionally NOT awaited here. Callers trigger the
  // network send after responding to the popup, so the UI never waits on it.
  console.log('Focus session ended');
}

// Log activity
function logActivity(entry) {
  activityLogs.push(entry);
  saveState();
}

// Send logs to backend
async function sendLogsToBackend() {
  await ensureStateLoaded();

  if (activityLogs.length === 0) {
    return;
  }

  const apiKey = await getApiKey();
  if (!apiKey) {
    // Keep logs queued until the user connects an account via the options page.
    console.warn('FocusForge: no API key set. Open the extension options to connect your account.');
    return;
  }

  const apiBaseUrl = await getApiBaseUrl();

  const logsToSend = activityLogs;
  activityLogs = [];
  await saveState();

  try {
    const response = await fetch(`${apiBaseUrl}/logs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({ logs: logsToSend })
    });

    if (response.ok) {
      console.log(`Sent ${logsToSend.length} logs to backend`);
    } else {
      console.error('Failed to send logs:', response.status, response.statusText);
      activityLogs = [...logsToSend, ...activityLogs];
      await saveState();
    }
  } catch (error) {
    console.error('Error sending logs:', error);
    activityLogs = [...logsToSend, ...activityLogs];
    await saveState();
  }
}

// Read the saved FocusForge API key (set via the options page).
function getApiKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiKey'], (result) => resolve(result.apiKey || ''));
  });
}

// Update declarativeNetRequest rules based on blocklist and session state
function updateBlockingRules() {
  // For simplicity in v1, we'll use tab redirection instead of declarativeNetRequest
  // The blocking is handled in the tabs.onUpdated listener
  console.log('Blocking rules updated. Session active:', focusSessionActive);
}

function ensureStateLoaded() {
  if (stateLoaded) {
    return Promise.resolve();
  }

  return loadState();
}

function loadState() {
  return new Promise((resolve) => {
    chrome.storage.local.get(
      ['blocklist', 'focusSessionActive', 'sessionEndTime', 'sessionStartTime', 'distractionAttempts', 'activityLogs'],
      (result) => {
        blocklist = normalizeBlocklist(result.blocklist || DEFAULT_BLOCKLIST);
        sessionEndTime = Number.isFinite(result.sessionEndTime) ? result.sessionEndTime : null;
        sessionStartTime = Number.isFinite(result.sessionStartTime) ? result.sessionStartTime : null;
        focusSessionActive = Boolean(result.focusSessionActive && sessionEndTime && sessionEndTime > Date.now());
        distractionAttempts = Number.isFinite(result.distractionAttempts) ? result.distractionAttempts : 0;
        activityLogs = Array.isArray(result.activityLogs) ? result.activityLogs : [];
        stateLoaded = true;

        if (!focusSessionActive) {
          sessionEndTime = null;
          sessionStartTime = null;
          chrome.alarms.clear('endSession');
        }

        saveState().then(resolve);
      }
    );
  });
}

function saveState() {
  return new Promise((resolve) => {
    chrome.storage.local.set({
      blocklist,
      focusSessionActive,
      sessionEndTime,
      sessionStartTime,
      distractionAttempts,
      activityLogs,
    }, resolve);
  });
}

function normalizeBlocklist(domains) {
  if (!Array.isArray(domains)) {
    return [...DEFAULT_BLOCKLIST];
  }

  return [...new Set(domains.map(normalizeDomain).filter(Boolean))];
}

function normalizeDomain(domain) {
  return String(domain || '')
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .split('/')[0]
    .replace(/^www\./, '');
}

function isBlockedDomain(domain) {
  return blocklist.some((blockedDomain) => (
    domain === blockedDomain || domain.endsWith(`.${blockedDomain}`)
  ));
}

// Extract domain from URL
function extractDomain(url) {
  try {
    const urlObj = new URL(url);
    return normalizeDomain(urlObj.hostname);
  } catch (e) {
    return '';
  }
}


