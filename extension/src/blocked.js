// Blocked page: link to the dashboard, and match the heading to the blocking mode.
document.getElementById('dashboardLink').href = `${FOCUSFORGE_WEB_URL}/dashboard`;

chrome.storage.local.get(['focusSessionActive', 'blockingMode'], (state) => {
  if (!state.focusSessionActive && state.blockingMode === 'always') {
    document.querySelector('h2').textContent = 'This site is on your always-blocked list';
  }
});
