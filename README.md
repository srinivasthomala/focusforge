# FocusForge

**Forge your focus. Shape your day.**

FocusForge is a lightweight focus and productivity tool for developers and creators. It helps you maintain deep work by blocking distractions, tracking focus sessions, and providing AI-powered insights into your productivity patterns.

## Project Structure

This is a monorepo containing three main components:

```
focusforge/
├── web/          # Next.js frontend dashboard
├── api/          # FastAPI backend server
├── extension/    # Chrome extension (Manifest v3)
└── README.md
```

### `/web` - Web Dashboard

Next.js app router frontend built with TypeScript, Tailwind CSS, and shadcn/ui.

**Features:**
- Landing page with hero section
- Dashboard showing focus metrics, distractions, and AI summary
- Settings page for blocklist management
- Weekly focus chart visualization

### `/api` - Backend API

FastAPI backend that receives activity logs and serves dashboard data.

**Endpoints:**
- `POST /logs` - Receive activity logs from extension
- `GET /dashboard` - Fetch dashboard metrics and weekly data
- `POST /summary` - Generate AI summary from logs

### `/extension` - Chrome Extension

Manifest v3 Chrome extension for blocking distracting websites and tracking focus.

**Features:**
- Block websites during focus sessions
- Track time spent on sites
- Log distraction attempts
- Start/end focus sessions from popup
- Send activity logs to backend

## Development Setup

### Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.9+
- Chrome browser (for extension development)

### Running the Web App

```bash
cd web
npm install
npm run dev
```

The web app will be available at `http://localhost:3000`

### Running the API

**PostgreSQL:** Activity logs and dashboard metrics are stored in PostgreSQL. The easiest way to run a local database is Docker from the `api` folder:

```bash
cd api
docker compose up -d
cp .env.example .env   # uses defaults matching docker-compose; edit if needed
```

**API server:**

```bash
cd api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Set `DATABASE_URL` in `api/.env` if your Postgres user, password, host, or database name differ. The value can be a normal `postgresql://...` URL; the app maps it to SQLAlchemy’s `postgresql+psycopg2` driver.

The API will be available at `http://localhost:8000`
API documentation at `http://localhost:8000/docs`

### Loading the Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `extension/` folder from this repository
5. The FocusForge extension should now appear in your extensions list
6. Pin it to your toolbar for easy access

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **Backend**: FastAPI, Python, Pydantic, SQLAlchemy, PostgreSQL
- **Extension**: Chrome Manifest v3, JavaScript
- **Future**: OpenAI/Claude for summaries, hosted auth (e.g. Supabase)

## Current Status

This is v1 - a working skeleton with:
- ✅ Full UI/UX design
- ✅ PostgreSQL persistence for activity logs and dashboard
- ✅ Basic blocking in extension
- ⏳ Real AI summary generation (coming soon)
- ⏳ User authentication (coming soon)

## Contributing

This is an indie SaaS project. Feel free to fork and customize for your own use!

## License

MIT
