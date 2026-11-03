// FocusForge Background Service Worker

// State management
// Empty on purpose: nothing is blocked until the user adds sites in the
// dashboard (or asks the Focus Coach). Mirrors the API DEFAULT_BLOCKLIST.
const DEFAULT_BLOCKLIST = [];

let focusSessionActive = false;
let sessionEndTime = null;
let sessionStartTime = null;
let blocklist = [...DEFAULT_BLOCKLIST];
let blockingMode = 'focus-only'; // 'focus-only' | 'always' — synced from the dashboard
let lastSettingsSync = 0;
let activityLogs = [];
let distractionAttempts = 0;
let stateLoaded = false;

// How stale settings may get before an opportunistic (on-navigation) refresh.
const SETTINGS_STALE_MS = 30000;

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

  loadState().then(() => {
    updateBlockingRules();
    fetchSettings();
  });

  // Periodic log sending (every 5 min) + settings sync (every 1 min — Chrome's floor).
  chrome.alarms.create('sendLogs', { periodInMinutes: 5 });
  chrome.alarms.create('syncSettings', { periodInMinutes: 1 });
});

chrome.runtime.onStartup.addListener(() => {
  loadState().then(() => {
    updateBlockingRules();
    fetchSettings();
  });
  chrome.alarms.create('syncSettings', { periodInMinutes: 1 });
});

// Listen for tab updates to detect blocked site access
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (!changeInfo.url) {
    return;
  }

  ensureStateLoaded().then(() => {
    // Keep the blocklist/mode fresh as the user browses (throttled, non-blocking).
    maybeRefreshSettings();

    // End an expired session before deciding whether to block.
    if (focusSessionActive && sessionEndTime && sessionEndTime <= Date.now()) {
      endFocusSession();
    }

    // Block during a focus session, or always when "block always" is on.
    const blockingActive = focusSessionActive || blockingMode === 'always';
    if (!blockingActive) {
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
        isFocusSession: focusSessionActive,
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
  } else if (alarm.name === 'syncSettings') {
    fetchSettings();
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
        blocklist,
        blockingMode
      });
      // Opportunistically refresh settings when the popup opens (non-blocking).
      fetchSettings();
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

const LOG_BATCH_SIZE = 500;

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

  // The API accepts at most 1000 logs per request; stay well under it so a
  // long offline queue drains in chunks instead of failing as one big batch.
  while (activityLogs.length > 0) {
    const logsToSend = activityLogs.slice(0, LOG_BATCH_SIZE);
    activityLogs = activityLogs.slice(LOG_BATCH_SIZE);
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
        continue;
      }
      if (response.status === 400 || response.status === 422) {
        // The server rejected the data itself; retrying the same batch would
        // fail forever and block everything queued behind it.
        console.error(`Dropping ${logsToSend.length} logs the server rejected:`, response.status);
        continue;
      }
      console.error('Failed to send logs:', response.status, response.statusText);
    } catch (error) {
      console.error('Error sending logs:', error);
    }
    // Transient failure (network, 401, 429, 5xx): requeue and retry later.
    activityLogs = [...logsToSend, ...activityLogs];
    await saveState();
    return;
  }
}

// Read the saved FocusForge API key (set via the options page).
function getApiKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiKey'], (result) => resolve(result.apiKey || ''));
  });
}

// Pull the user's blocklist + blocking mode from the backend (the dashboard is
// the source of truth). No-ops without an API key.
async function fetchSettings() {
  const apiKey = await getApiKey();
  if (!apiKey) {
    return;
  }

  const apiBaseUrl = await getApiBaseUrl();

  try {
    const response = await fetch(`${apiBaseUrl}/settings`, {
      headers: { 'Authorization': `Bearer ${apiKey}` },
    });
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    if (Array.isArray(data.blocklist)) {
      blocklist = normalizeBlocklist(data.blocklist);
    }
    if (data.blockingMode === 'always' || data.blockingMode === 'focus-only') {
      blockingMode = data.blockingMode;
    }
    lastSettingsSync = Date.now();
    await saveState();
    updateBlockingRules();
  } catch (error) {
    console.error('Error fetching settings:', error);
  }
}

// Refresh settings if they're older than the throttle window. Non-blocking, so
// it never delays navigation; the fresh values apply to subsequent page loads.
function maybeRefreshSettings() {
  if (Date.now() - lastSettingsSync > SETTINGS_STALE_MS) {
    fetchSettings();
  }
}

// Hook invoked whenever session/blocklist state changes. Blocking itself is
// handled in the tabs.onUpdated listener, which redirects navigations to a
// blocked domain over to blocked.html.
function updateBlockingRules() {
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
      ['blocklist', 'blockingMode', 'lastSettingsSync', 'focusSessionActive', 'sessionEndTime', 'sessionStartTime', 'distractionAttempts', 'activityLogs'],
      (result) => {
        blocklist = normalizeBlocklist(result.blocklist || DEFAULT_BLOCKLIST);
        blockingMode = result.blockingMode === 'always' ? 'always' : 'focus-only';
        lastSettingsSync = Number.isFinite(result.lastSettingsSync) ? result.lastSettingsSync : 0;
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
      blockingMode,
      lastSettingsSync,
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


