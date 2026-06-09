// FocusForge Background Service Worker

// State management
const DEFAULT_BLOCKLIST = ['youtube.com', 'twitter.com', 'reddit.com'];

let focusSessionActive = false;
let sessionEndTime = null;
let blocklist = [...DEFAULT_BLOCKLIST];
let activityLogs = [];
let distractionAttempts = 0;
let stateLoaded = false;

// API endpoint
const API_BASE_URL = 'http://localhost:8000';

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
        userId: 'default-user',
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
    endFocusSession();
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
  sessionEndTime = Date.now() + (duration * 60 * 1000);
  
  // Set alarm to end session
  chrome.alarms.create('endSession', { when: sessionEndTime });
  
  // Update blocking rules
  updateBlockingRules();
  
  // Log session start
  logActivity({
    userId: 'default-user',
    timestamp: new Date().toISOString(),
    url: 'session-start',
    domain: 'system',
    minutesActive: duration,
    isFocusSession: true,
    isDistractionAttempt: false
  });

  await saveState();
  
  console.log(`Focus session started for ${duration} minutes`);
}

// End focus session
async function endFocusSession() {
  focusSessionActive = false;
  sessionEndTime = null;
  
  // Clear the alarm if it exists
  chrome.alarms.clear('endSession');
  
  // Update blocking rules
  updateBlockingRules();

  await saveState();
  
  // Send logs immediately
  await sendLogsToBackend();
  
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

  const logsToSend = activityLogs;
  activityLogs = [];
  await saveState();
  
  try {
    const response = await fetch(`${API_BASE_URL}/logs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ logs: logsToSend })
    });
    
    if (response.ok) {
      console.log(`Sent ${logsToSend.length} logs to backend`);
    } else {
      console.error('Failed to send logs:', response.statusText);
      activityLogs = [...logsToSend, ...activityLogs];
      await saveState();
    }
  } catch (error) {
    console.error('Error sending logs:', error);
    activityLogs = [...logsToSend, ...activityLogs];
    await saveState();
  }
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
      ['blocklist', 'focusSessionActive', 'sessionEndTime', 'distractionAttempts', 'activityLogs'],
      (result) => {
        blocklist = normalizeBlocklist(result.blocklist || DEFAULT_BLOCKLIST);
        sessionEndTime = Number.isFinite(result.sessionEndTime) ? result.sessionEndTime : null;
        focusSessionActive = Boolean(result.focusSessionActive && sessionEndTime && sessionEndTime > Date.now());
        distractionAttempts = Number.isFinite(result.distractionAttempts) ? result.distractionAttempts : 0;
        activityLogs = Array.isArray(result.activityLogs) ? result.activityLogs : [];
        stateLoaded = true;

        if (!focusSessionActive) {
          sessionEndTime = null;
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


