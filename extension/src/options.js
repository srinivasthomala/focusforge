// FocusForge options — save the API key used to authenticate log syncing.

const input = document.getElementById('apiKey');
const status = document.getElementById('status');

// Prefill with any saved key.
chrome.storage.local.get(['apiKey'], (result) => {
  if (result.apiKey) {
    input.value = result.apiKey;
  }
});

function showStatus(message, ok) {
  status.textContent = message;
  status.className = `status ${ok ? 'ok' : 'err'}`;
}

document.getElementById('save').addEventListener('click', () => {
  const apiKey = input.value.trim();

  if (apiKey && !apiKey.startsWith('ff_')) {
    showStatus('That doesn’t look like a FocusForge key (should start with "ff_").', false);
    return;
  }

  chrome.storage.local.set({ apiKey }, () => {
    showStatus(apiKey ? 'Saved. The extension will sync on the next interval.' : 'Key cleared.', true);
  });
});
