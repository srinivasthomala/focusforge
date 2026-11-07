// FocusForge setup: save and check the API key that connects this extension
// to the user's FocusForge account.

const input = document.getElementById('apiKey');
const status = document.getElementById('status');
const saveBtn = document.getElementById('save');

// Links to the web app (get a key, dashboard, privacy).
document.querySelectorAll('.web-link').forEach((link) => {
  link.href = `${FOCUSFORGE_WEB_URL}${link.dataset.path}`;
  link.target = '_blank';
  link.rel = 'noopener';
});

function showStatus(message, kind) {
  status.textContent = message;
  status.className = `status ${kind}`;
}

function getApiBaseUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiBaseUrl'], (result) => {
      const url = (result.apiBaseUrl || '').trim().replace(/\/+$/, '');
      resolve(url || 'https://focusforge-api.fly.dev');
    });
  });
}

// Ask the API whether the key works. Returns 'ok', 'invalid' or 'offline'.
async function checkKey(apiKey) {
  try {
    const response = await fetch(`${await getApiBaseUrl()}/settings`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    if (response.ok) return 'ok';
    if (response.status === 401 || response.status === 403) return 'invalid';
    return 'offline';
  } catch (error) {
    return 'offline';
  }
}

// Prefill with any saved key and show whether it is connected.
chrome.storage.local.get(['apiKey'], async (result) => {
  if (!result.apiKey) {
    showStatus('Not connected yet.', 'muted');
    return;
  }
  input.value = result.apiKey;
  showStatus('Checking connection...', 'muted');
  const state = await checkKey(result.apiKey);
  if (state === 'ok') showStatus('Connected to your FocusForge account.', 'ok');
  else if (state === 'invalid') showStatus('This key no longer works. Generate a new one and paste it here.', 'err');
  else showStatus('Saved, but the server could not be reached. It will retry automatically.', 'muted');
});

async function save() {
  const apiKey = input.value.trim();

  if (!apiKey) {
    chrome.storage.local.set({ apiKey: '' }, () => showStatus('Key removed. This extension is disconnected.', 'muted'));
    return;
  }
  if (!apiKey.startsWith('ff_')) {
    showStatus('That is not a FocusForge key. Keys start with "ff_".', 'err');
    return;
  }

  saveBtn.disabled = true;
  showStatus('Checking your key...', 'muted');
  const state = await checkKey(apiKey);
  saveBtn.disabled = false;

  if (state === 'invalid') {
    showStatus('That key was not accepted. Copy it again from the dashboard, or generate a new one.', 'err');
    return;
  }

  chrome.storage.local.set({ apiKey }, () => {
    // Pull settings and send any queued sessions right away.
    chrome.runtime.sendMessage({ action: 'syncNow' }, () => void chrome.runtime.lastError);
    if (state === 'ok') {
      showStatus('Connected. Your blocked sites and sessions now sync with your dashboard.', 'ok');
    } else {
      showStatus('Saved, but the server could not be reached right now. It will retry automatically.', 'muted');
    }
  });
}

saveBtn.addEventListener('click', save);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') save();
});
