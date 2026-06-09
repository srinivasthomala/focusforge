# Chrome Extension Notes

## Icon Files

The extension manifest references three icon sizes that need to be created:
- `icons/icon16.png` (16x16px)
- `icons/icon48.png` (48x48px)  
- `icons/icon128.png` (128x128px)

### Quick Fix for Development

You can ignore the missing icon warnings - the extension will still function. Chrome will just show a default puzzle piece icon.

### Creating Real Icons

If you want proper icons:

1. **Using an online tool**: Use a tool like Canva or Figma to create simple squares
2. **Color scheme**: Use teal (#14b8a6) as the main color
3. **Symbol**: Add "FF" text or a simple hammer/forge icon
4. **Export**: Save as PNG in the three required sizes

### Or use this command line approach (if you have ImageMagick):

```bash
cd extension/icons

# Create a simple teal square (requires ImageMagick)
convert -size 16x16 xc:#14b8a6 icon16.png
convert -size 48x48 xc:#14b8a6 icon48.png
convert -size 128x128 xc:#14b8a6 icon128.png
```

## How the Extension Works

### Blocking Mechanism

The extension uses a **tab redirection approach** rather than declarativeNetRequest rules for v1 simplicity:

1. Listen to `chrome.tabs.onUpdated` events
2. Check if the URL matches a blocked domain
3. If blocked and session is active, redirect to `blocked.html`
4. Log the distraction attempt

This approach is simpler but less strict than network-level blocking. It's appropriate for a personal productivity tool where the goal is awareness, not absolute enforcement.

### Activity Logging

- Logs are stored in-memory in the background service worker
- Every 5 minutes, logs are sent to the backend via `POST /logs`
- Logs are also sent immediately when a focus session ends

### State Management

State is maintained in the background service worker:
- `focusSessionActive`: boolean
- `sessionEndTime`: timestamp
- `blocklist`: array of domains
- `activityLogs`: array of log entries
- `distractionAttempts`: counter

### Communication

- **Popup ↔ Background**: Uses `chrome.runtime.sendMessage()`
- **Background → Backend**: Uses `fetch()` API calls
- **Storage**: Uses `chrome.storage.local` for persistent blocklist

## Known Limitations (v1)

1. **Service worker lifetime**: May be shut down by Chrome after inactivity. In production, you'd want to persist state.
2. **Blocking not foolproof**: Users can disable the extension or edit URLs directly. This is intentional - it's a focus aid, not a lockdown system.
3. **No cross-device sync**: Settings are local to each browser.

## Future Improvements

- Persist state to chrome.storage instead of just memory
- Add custom session durations
- Implement break timers (Pomodoro style)
- Add statistics directly in the extension popup
- Sync blocklist with backend API
- Add website categorization (productive vs distracting)


