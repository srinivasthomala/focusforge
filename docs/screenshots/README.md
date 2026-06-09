# Screenshots

This folder holds the marketing screenshots embedded in the top-level `README.md`.

## Captures needed

| File | What to capture | Recommended size |
| --- | --- | --- |
| `dashboard.png` | The `/dashboard` page with a few days of real activity so the bar chart, "Today's Focus" card, and AI summary all look populated. Dark theme. | 1440 × 900 (or 2× retina) |
| `extension-popup.png` | Chrome extension popup with an **active** focus session — green status, live timer, distractions counter, blocklist visible. | Native popup size (~360 wide) |
| `blocked-page.png` | The `src/blocked.html` page shown after attempting to visit `youtube.com` during a session. | 1440 × 900 |
| `settings.png` | The `/settings` page with the blocking-mode radios and a populated blocklist. | 1440 × 900 |
| `hero.gif` *(optional)* | 5–8 second screen recording: start session in popup → try to visit a blocked site → land on blocked page → dashboard updates. | Whatever ScreenToGif outputs, < 5 MB |

## How to capture cleanly

1. Run all three services locally (see `SETUP.md`).
2. Seed the database with a week of realistic-looking activity (a one-off `psql` insert script or just use the extension for a couple of days before capturing).
3. Use a clean Chrome profile (no other extension icons in the toolbar) and a 1440×900 browser window for parity across shots.
4. Crop tightly with whatever screenshot tool you prefer (Snipping Tool / ShareX / CleanShot). Save as PNG.
5. For GIFs, [ScreenToGif](https://www.screentogif.com/) is free and outputs reasonable sizes.

## Naming

Stick to the filenames in the table — the README links to them by exact name.
