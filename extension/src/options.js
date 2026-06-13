// FocusForge options — save the API base URL + key used to authenticate log syncing.

const input = document.getElementById('apiKey');
const baseUrlInput = document.getElementById('apiBaseUrl');
const status = document.getElementById('status');

// Prefill with any saved values.
chrome.storage.local.get(['apiKey', 'apiBaseUrl'], (result) => {
  if (result.apiKey) {
    input.value = result.apiKey;
  }
  if (result.apiBaseUrl) {
    baseUrlInput.value = result.apiBaseUrl;
  }
});

function showStatus(message, ok) {
  status.textContent = message;
  status.className = `status ${ok ? 'ok' : 'err'}`;
}

document.getElementById('save').addEventListener('click', () => {
  const apiKey = input.value.trim();
  const apiBaseUrl = baseUrlInput.value.trim().replace(/\/+$/, '');

  if (apiBaseUrl && !/^https?:\/\//.test(apiBaseUrl)) {
    showStatus('API base URL should start with http:// or https://', false);
    return;
  }

  if (apiKey && !apiKey.startsWith('ff_')) {
    showStatus('That doesn’t look like a FocusForge key (should start with "ff_").', false);
    return;
  }

  chrome.storage.local.set({ apiKey, apiBaseUrl }, () => {
    showStatus(apiKey ? 'Saved. The extension will sync on the next interval.' : 'Saved.', true);
  });
});
