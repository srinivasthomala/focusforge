// FocusForge Popup Script

const startBtn = document.getElementById('startBtn');
const endBtn = document.getElementById('endBtn');
const sessionStatus = document.getElementById('sessionStatus');
const distractionCount = document.getElementById('distractionCount');
const blocklistContainer = document.getElementById('blocklistContainer');
const timerDisplay = document.getElementById('timerDisplay');

let timerInterval = null;

// Initialize popup
async function init() {
  const status = await getStatus();
  updateUI(status);
}

// Get current status from background
function getStatus() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ action: 'getStatus' }, (response) => {
      resolve(response);
    });
  });
}

// Update UI based on status
function updateUI(status) {
  if (status.focusSessionActive) {
    sessionStatus.textContent = 'Active';
    sessionStatus.className = 'status-value status-active';
    startBtn.style.display = 'none';
    endBtn.style.display = 'block';
    timerDisplay.style.display = 'block';
    
    // Start timer countdown
    startTimer(status.sessionEndTime);
  } else {
    sessionStatus.textContent = 'Inactive';
    sessionStatus.className = 'status-value status-inactive';
    startBtn.style.display = 'block';
    endBtn.style.display = 'none';
    timerDisplay.style.display = 'none';
    
    // Stop timer
    if (timerInterval) {
      clearInterval(timerInterval);
    }
  }
  
  distractionCount.textContent = status.distractionAttempts || 0;
  
  // Display blocklist
  if (status.blocklist && status.blocklist.length > 0) {
    blocklistContainer.innerHTML = status.blocklist
      .map(domain => `<div class="blocklist-item">${domain}</div>`)
      .join('');
  } else {
    blocklistContainer.innerHTML = '<div class="blocklist-item">No sites blocked</div>';
  }
}

// Start timer countdown
function startTimer(endTime) {
  if (timerInterval) {
    clearInterval(timerInterval);
  }
  
  timerInterval = setInterval(() => {
    const now = Date.now();
    const remaining = Math.max(0, endTime - now);
    
    const minutes = Math.floor(remaining / 60000);
    const seconds = Math.floor((remaining % 60000) / 1000);
    
    timerDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    
    if (remaining === 0) {
      clearInterval(timerInterval);
      init(); // Refresh UI
    }
  }, 1000);
}

// Start focus session
startBtn.addEventListener('click', async () => {
  chrome.runtime.sendMessage(
    { action: 'startSession', duration: 25 },
    async (response) => {
      if (response.success) {
        const status = await getStatus();
        updateUI(status);
      }
    }
  );
});

// End focus session
endBtn.addEventListener('click', async () => {
  chrome.runtime.sendMessage({ action: 'endSession' }, async (response) => {
    if (response.success) {
      const status = await getStatus();
      updateUI(status);
    }
  });
});

// Initialize on load
init();


