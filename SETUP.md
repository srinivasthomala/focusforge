# FocusForge Setup Guide

Quick setup instructions for running the FocusForge monorepo in development.

## Prerequisites

- Node.js 18+ (for the web frontend)
- Python 3.9+ (for the API backend)
- Chrome browser (for the extension)

## Step 1: Run the Backend API

```bash
cd api
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be running at `http://localhost:8000`

API documentation available at `http://localhost:8000/docs`

## Step 2: Run the Web Frontend

Open a new terminal:

```bash
cd web
npm install
npm run dev
```

The web app will be running at `http://localhost:3000`

Visit the landing page, then click "Go to Dashboard" to see the dashboard with mock data.

## Step 3: Load the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in the top right corner)
3. Click "Load unpacked"
4. Navigate to and select the `extension/` folder
5. The extension should now appear in your list

**Note about icons**: The extension requires icon files. For now, you can:
- Ignore the warnings about missing icons (extension will still work)
- Or create simple PNG files in `extension/icons/` named `icon16.png`, `icon48.png`, and `icon128.png`

## Step 4: Test the Full Flow

1. **Open the extension popup**: Click the FocusForge icon in your Chrome toolbar
2. **Start a focus session**: Click "Start 25-min Focus Session"
3. **Try visiting a blocked site**: Open a new tab and try to visit `youtube.com` - you should be redirected to the blocked page
4. **Check the dashboard**: Visit `http://localhost:3000/dashboard` to see your mock metrics
5. **Manage settings**: Visit `http://localhost:3000/settings` to manage your blocklist

## Architecture Overview

```
┌─────────────────┐
│ Chrome Extension│
│  (Manifest v3)  │
└────────┬────────┘
         │ POST /logs
         ↓
┌─────────────────┐      ┌─────────────────┐
│   Next.js Web   │─────→│  FastAPI Backend│
│   Frontend      │ proxy │  (Python)       │
└─────────────────┘      └─────────────────┘
  localhost:3000           localhost:8000
```

- The extension sends activity logs to the backend via `POST /logs`
- The web frontend fetches dashboard data via `GET /api/dashboard` (proxied to backend)
- The backend currently uses in-memory storage (no database yet)

## Troubleshooting

**Extension not blocking sites?**
- Make sure a focus session is active (green status in popup)
- Check that the site is in the default blocklist (youtube.com, twitter.com, reddit.com)

**Frontend not loading data?**
- Make sure the backend is running on port 8000
- Check the browser console for CORS errors
- Verify the API is accessible at `http://localhost:8000/docs`

**Can't load extension?**
- Missing icon warnings can be ignored for development
- Make sure you selected the `extension/` folder, not a subfolder
- Check `chrome://extensions/` for any error messages

## Next Steps

Once the skeleton is working:

1. Add real database integration (Supabase)
2. Implement actual AI summaries (Claude/OpenAI)
3. Add user authentication
4. Enhance the extension with more features
5. Deploy to production

Happy hacking! 🔨


