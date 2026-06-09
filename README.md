# FocusForge

> **AI-powered focus and productivity SaaS for developers and creators.**
> Block distracting sites with a Chrome extension, track focus sessions, and get Claude-generated insights into your productivity patterns — all in one dashboard.

<p align="left">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue.svg" />
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" />
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" />
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" />
  <img alt="Postgres" src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" />
  <img alt="Chrome MV3" src="https://img.shields.io/badge/Chrome-MV3-4285F4?logo=googlechrome&logoColor=white" />
  <img alt="Claude" src="https://img.shields.io/badge/AI-Anthropic%20Claude-D97757" />
</p>

**🌐 Live demo:** _coming soon — see [Roadmap](#roadmap)_ &nbsp;·&nbsp; **🧩 Chrome extension:** _packaged release coming soon_ &nbsp;·&nbsp; **📚 API docs:** _coming soon_

---

## Screenshots

<p align="center">
  <img src="docs/screenshots/dashboard.png" alt="FocusForge dashboard" width="100%" />
</p>

<p align="center">
  <img src="docs/screenshots/extension-popup.png" alt="Extension popup with active focus session" width="32%" />
  &nbsp;
  <img src="docs/screenshots/blocked-page.png" alt="Site blocked page" width="32%" />
  &nbsp;
  <img src="docs/screenshots/settings.png" alt="Settings page" width="32%" />
</p>

> 🚧 Screenshots are placeholders until they're captured — see [`docs/screenshots/README.md`](docs/screenshots/README.md) for the shot list.

---

## What it does

- 🧱 **Block distractions on demand.** A Chrome (Manifest v3) extension intercepts navigation to user-defined domains while a focus session is active.
- 📊 **Track focus time.** Activity logs are streamed from the extension to a FastAPI backend, persisted in Postgres, and aggregated into daily / weekly metrics.
- 🤖 **AI-powered insights.** Anthropic Claude generates a personalized daily summary of your focus patterns, top distractions, and momentum trends.
- ⚙️ **Per-user settings.** Manage your blocklist, blocking mode, and session defaults from a Next.js dashboard.

---

## Architecture

```mermaid
flowchart LR
    subgraph Browser
      EXT["Chrome MV3 Extension<br/>(popup + service worker)"]
    end
    subgraph "Web (Vercel)"
      WEB["Next.js 14 Dashboard<br/>(TS · Tailwind · Recharts)"]
    end
    subgraph "API (Render / Fly)"
      API["FastAPI<br/>(SQLAlchemy · Pydantic)"]
      AI["Anthropic Claude<br/>summarizer"]
    end
    DB[("PostgreSQL<br/>(Neon)")]

    EXT -- "POST /logs (activity batch)" --> API
    WEB -- "GET /dashboard" --> API
    WEB -- "POST /summary" --> API
    API -- "read / write logs" --> DB
    API -- "summarize daily activity" --> AI
```

---

## Tech stack

| Layer | Stack |
| --- | --- |
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn-style components, Recharts |
| **Backend** | FastAPI, Pydantic v2, SQLAlchemy 2.0, Uvicorn |
| **Database** | PostgreSQL 16 (Docker locally, Neon in prod) |
| **AI** | Anthropic Claude (Sonnet) for summary generation |
| **Extension** | Chrome Manifest v3, vanilla JS service worker, `declarativeNetRequest` |
| **Deploy** | Vercel (web) · Render or Fly.io (api) · Neon (db) |
| **CI** | GitHub Actions — lint, typecheck, tests |

---

## Repository layout

```
focusforge/
├── web/          # Next.js dashboard
├── api/          # FastAPI backend + Postgres docker-compose
├── extension/    # Chrome Manifest v3 extension
├── scripts/      # One-off scripts (icon generation, seed data, ...)
├── docs/         # Screenshots, diagrams, longer-form docs
├── LICENSE
├── README.md     # ← you are here
└── SETUP.md      # Full local setup walkthrough
```

---

## Quick start

> Full step-by-step instructions live in [`SETUP.md`](SETUP.md). The condensed version:

```bash
# 1. Start Postgres
cd api && docker compose up -d && cp .env.example .env

# 2. Run the API
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Run the web app (new terminal)
cd web && npm install && npm run dev

# 4. Load the extension at chrome://extensions → "Load unpacked" → select extension/
```

Visit http://localhost:3000 for the dashboard and http://localhost:8000/docs for the API.

---

## Roadmap

- [x] Working monorepo (web + api + extension)
- [x] Persistent activity logs in PostgreSQL
- [x] Weekly focus chart + daily metrics
- [x] MV3 extension with on-the-fly blocking
- [ ] Real Anthropic Claude integration for the daily summary
- [ ] Per-user authentication (Supabase / Clerk magic link)
- [ ] Settings page persisted to backend + synced to extension
- [ ] Live demo deployed (Vercel + Render + Neon)
- [ ] Pytest + Vitest coverage with GitHub Actions CI badge
- [ ] Packaged extension `.zip` published as a GitHub Release

---

## About

Built by **[Srinivas Thomala](mailto:srinivas.1796@gmail.com)** — a senior full-stack engineer focused on **AI-integrated SaaS products**. Available for freelance work via Upwork.

## License

[MIT](LICENSE) — do whatever you want with it.
