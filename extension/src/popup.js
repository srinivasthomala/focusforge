// FocusForge Popup Script

const $ = (id) => document.getElementById(id);

const idleView = $('idleView');
const activeView = $('activeView');
const doneView = $('doneView');
const startBtn = $('startBtn');
const customInput = $('customMinutes');
const durationError = $('durationError');
const timerDisplay = $('timerDisplay');
const timerSub = $('timerSub');
const progressBar = $('progressBar');
const sessionStatus = $('sessionStatus');
const distractionCount = $('distractionCount');
const blocklistContainer = $('blocklistContainer');

let timerInterval = null;
let selectedMinutes = 25;

function send(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => resolve(response || {}));
  });
}

async function refresh() {
  updateUI(await send({ action: 'getStatus' }));
}

function show(view) {
  for (const v of [idleView, activeView, doneView]) {
    v.classList.toggle('hidden', v !== view);
  }
}

function updateUI(status) {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }

  if (status.focusSessionActive) {
    show(activeView);
    sessionStatus.textContent = 'Focusing';
    startTimer(status.sessionStartTime, status.sessionEndTime);
  } else if (status.lastCompleted) {
    show(doneView);
    sessionStatus.textContent = 'Inactive';
    const mins = Math.round(status.lastCompleted.minutes);
    $('doneSub').textContent = mins >= 1
      ? `You focused for ${mins} minute${mins === 1 ? '' : 's'}.`
      : 'Ended before a full minute.';
  } else {
    show(idleView);
    sessionStatus.textContent = 'Inactive';
    selectMinutes(status.lastDuration || 25);
  }

  $('connectBanner').style.display = status.hasApiKey ? 'none' : 'block';
  distractionCount.textContent = status.distractionAttempts || 0;
  renderBlocklist(status.blocklist);
}

// ---- Choosing a length ---------------------------------------------------------

function selectMinutes(minutes) {
  selectedMinutes = minutes;
  let isPreset = false;
  document.querySelectorAll('.preset').forEach((btn) => {
    const match = Number(btn.dataset.min) === minutes;
    btn.classList.toggle('selected', match);
    isPreset = isPreset || match;
  });
  if (isPreset) {
    customInput.value = '';
  } else if (document.activeElement !== customInput) {
    customInput.value = minutes;
  }
  durationError.textContent = '';
  startBtn.textContent = `Start ${minutes}-min focus`;
  startBtn.disabled = false;
}

document.querySelectorAll('.preset').forEach((btn) => {
  btn.addEventListener('click', () => selectMinutes(Number(btn.dataset.min)));
});

customInput.addEventListener('input', () => {
  const value = Number(customInput.value);
  if (!customInput.value) {
    selectMinutes(selectedMinutes);
    return;
  }
  if (!Number.isInteger(value) || value < 1 || value > FOCUSFORGE_MAX_MINUTES) {
    document.querySelectorAll('.preset').forEach((b) => b.classList.remove('selected'));
    durationError.textContent = `Pick a whole number from 1 to ${FOCUSFORGE_MAX_MINUTES}.`;
    startBtn.disabled = true;
    return;
  }
  selectMinutes(value);
});

customInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !startBtn.disabled) startBtn.click();
});

// ---- Running timer -------------------------------------------------------------

function format(ms) {
  const total = Math.ceil(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const ss = s.toString().padStart(2, '0');
  return h > 0 ? `${h}:${m.toString().padStart(2, '0')}:${ss}` : `${m}:${ss}`;
}

function startTimer(startTime, endTime) {
  const planned = Math.max(1, endTime - startTime);
  timerSub.textContent = `of ${Math.round(planned / 60000)} min`;

  const render = () => {
    const remaining = Math.max(0, endTime - Date.now());
    timerDisplay.textContent = format(remaining);
    progressBar.style.width = `${Math.min(100, ((planned - remaining) / planned) * 100)}%`;
    if (remaining === 0) {
      clearInterval(timerInterval);
      timerInterval = null;
      setTimeout(refresh, 600); // let the background finish the session first
    }
  };

  render(); // paint immediately so reopening mid-session shows the real time
  timerInterval = setInterval(render, 1000);
}

// ---- Buttons -------------------------------------------------------------------

startBtn.addEventListener('click', async () => {
  const response = await send({ action: 'startSession', duration: selectedMinutes });
  if (response.success) {
    refresh();
  } else if (response.error) {
    durationError.textContent = response.error;
  }
});

$('endBtn').addEventListener('click', async () => {
  const response = await send({ action: 'endSession' });
  if (response.success) refresh();
});

$('extendBtn').addEventListener('click', async () => {
  const response = await send({ action: 'extendSession', minutes: 5 });
  if (response.success) refresh();
});

$('againBtn').addEventListener('click', async () => {
  await send({ action: 'dismissCompleted' });
  refresh();
});

$('dismissBtn').addEventListener('click', async () => {
  await send({ action: 'dismissCompleted' });
  window.close();
});

// ---- Links ---------------------------------------------------------------------

function openTab(url) {
  chrome.tabs.create({ url });
  window.close();
}

$('dashboardLink').addEventListener('click', (e) => {
  e.preventDefault();
  openTab(`${FOCUSFORGE_WEB_URL}/dashboard`);
});

$('optionsLink').addEventListener('click', (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
  window.close();
});

$('connectLink').addEventListener('click', (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
  window.close();
});

// ---- Blocklist -----------------------------------------------------------------

function renderBlocklist(list) {
  blocklistContainer.textContent = '';
  if (list && list.length > 0) {
    for (const domain of list) {
      const item = document.createElement('div');
      item.className = 'blocklist-item';
      item.textContent = domain;
      blocklistContainer.appendChild(item);
    }
    return;
  }
  const empty = document.createElement('div');
  empty.className = 'blocklist-empty';
  empty.append('No sites blocked yet. Add them in your ');
  const link = document.createElement('a');
  link.href = '#';
  link.textContent = 'dashboard settings';
  link.addEventListener('click', (e) => {
    e.preventDefault();
    openTab(`${FOCUSFORGE_WEB_URL}/settings`);
  });
  empty.append(link, '.');
  blocklistContainer.appendChild(empty);
}

// Live-update when the background syncs new settings from the dashboard, so the
// popup reflects changes without being reopened. Reads storage directly (no
// getStatus round-trip) to avoid re-triggering a settings fetch.
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local') return;
  if (changes.blocklist) {
    renderBlocklist(changes.blocklist.newValue || []);
  }
  if (changes.distractionAttempts) {
    distractionCount.textContent = changes.distractionAttempts.newValue || 0;
  }
  if (changes.apiKey) {
    $('connectBanner').style.display = changes.apiKey.newValue ? 'none' : 'block';
  }
});

refresh();
