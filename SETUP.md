# FocusForge Setup Guide

How to run the full FocusForge stack (PostgreSQL, FastAPI, Next.js, Chrome extension) on your machine, plus how the production deployment is wired.

> Just want to try it? Use the **[live demo](https://focusforge-iota.vercel.app)** and the **[packaged extension](https://github.com/srinivasthomala/focusforge/releases/latest)**. No local setup needed.

## Prerequisites

- **Python 3.12** (API)
- **Node.js 18+** (web; CI uses Node 20)
- **Docker** (local PostgreSQL 16)
- **Chrome** (extension)
- A free **[Supabase](https://supabase.com) project**, used for dashboard authentication only (no Supabase database)
- *Optional:* an **Anthropic API key** for real Claude summaries. Without one, the API serves a deterministic fallback summary.

## Step 1: Configure Supabase auth

1. Create a Supabase project.
2. **Authentication → Providers:** enable **Email**. For frictionless local testing, turn off "Confirm email". Google is optional.
3. **Authentication → URL Configuration:** add `http://localhost:3000/auth/callback` to the redirect URLs.
4. Note the **project URL** (`https://<project-id>.supabase.co`) and the **publishable key** (`sb_publishable_...`).

## Step 2: Start PostgreSQL and the API

```bash
cd api
docker compose up -d          # Postgres 16 on localhost:5432
cp .env.example .env          # then edit .env (see below)

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In `api/.env`, the default `DATABASE_URL` already matches `docker-compose.yml`. Set:

```bash
SUPABASE_URL=https://<project-id>.supabase.co   # verifies dashboard logins via JWKS
# ANTHROPIC_API_KEY=sk-ant-...                  # optional: real Claude summaries
```

Tables are created automatically on startup. The API runs at `http://localhost:8000` with interactive docs at `/docs`.

## Step 3: Run the web dashboard

In a new terminal:

```bash
cd web
cp .env.local.example .env.local   # fill in the Supabase URL + publishable key
npm install
npm run dev
```

Open `http://localhost:3000`, sign up on the login page, and you'll land on the dashboard. The browser only ever calls `/api/*` on the web origin; Next.js proxies those requests server-side to `API_URL` (default `http://localhost:8000`).

## Step 4: Load and connect the Chrome extension

1. Go to `chrome://extensions/`, enable **Developer mode**, click **Load unpacked**, and select the `extension/` folder.
2. **Point it at your local API.** The extension targets the production API by default. On `chrome://extensions/`, open the FocusForge **service worker** inspector and run:
   ```js
   chrome.storage.local.set({ apiBaseUrl: 'http://localhost:8000' })
   ```
   (Run `chrome.storage.local.remove('apiBaseUrl')` to switch back to production.)
3. In the web app, go to **Settings → API Keys** and generate a key (starts with `ff_`).
4. Open the extension's **Options** page, paste the key, and save.

The extension authenticates with that API key. Dashboard users authenticate with Supabase. Both resolve to the same user on the backend.

## Step 5: Try the full flow

1. Open the extension popup and start a focus session.
2. Visit a blocked site (default blocklist: `youtube.com`, `twitter.com`, `reddit.com`). The tab is redirected to the blocked page.
3. End the session. Activity logs sync to the API and are stored in PostgreSQL.
4. Refresh the dashboard to see focus minutes, distractions, and the weekly chart. Click **Generate AI Summary** for the Claude-written insight.
5. Edit the blocklist or blocking mode in **Settings**. The extension picks up changes within about a minute (immediately when the popup opens).

## Architecture (local)

```
Chrome extension ──(API key)── POST /logs, GET /settings ──┐
                                                           ▼
Next.js :3000 ──(Supabase JWT)── /api/* proxy ──────► FastAPI :8000 ──► PostgreSQL :5432
                                                           │
                                                           └──► Anthropic Claude (optional)
```

See the [README](README.md#architecture) for the production diagram.

## Environment variables

**API (`api/.env`)**

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Yes | PostgreSQL connection string (plain `postgres://` URLs are normalized) |
| `SUPABASE_URL` | Yes | Supabase project URL; JWKS endpoint used to verify dashboard tokens |
| `SUPABASE_JWT_SECRET` | No | Legacy HS256 fallback for projects not using asymmetric keys |
| `ANTHROPIC_API_KEY` | No | Enables real Claude summaries (fallback summary when unset) |
| `ANTHROPIC_MODEL` | No | Defaults to `claude-opus-4-8` |
| `AI_DAILY_GENERATION_LIMIT`, `AI_RATE_LIMIT_PER_IP`, `AI_RATE_LIMIT_WINDOW_SECONDS` | No | Abuse guards on Claude calls (defaults: 50/day, 5 per IP per hour) |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated origins; defaults to `http://localhost:3000` |

**Web (`web/.env.local`)**

| Variable | Required | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase publishable key |
| `API_URL` | No | Server-side proxy target; defaults to `http://localhost:8000` |

## Tests and CI

```bash
# API: pytest against in-memory SQLite (no Postgres or Supabase needed)
cd api
pip install -r requirements-dev.txt
pytest

# Web: the same checks CI runs
cd web
npm run lint
npx tsc --noEmit
npm run build
```

GitHub Actions (`.github/workflows/ci.yml`) runs both jobs on every push and pull request to `main`.

`.github/workflows/deploy-api.yml` then deploys the API to Fly.io whenever a push to `main` touches `api/`, gated on the test suite passing. It needs a `FLY_API_TOKEN` repository secret:

```bash
fly tokens create deploy -a focusforge-api
# paste the output into GitHub → Settings → Secrets and variables → Actions
```

## Seeding demo data

`scripts/seed_demo_data.py` posts a realistic backdated week of activity through the same `/logs` endpoint the extension uses:

```bash
python scripts/seed_demo_data.py --api-key ff_xxx --base-url http://localhost:8000
python scripts/seed_demo_data.py --api-key ff_xxx --dry-run   # preview without posting
```

Omit `--base-url` to target the production API.

## Production deployment

| Component | Host | Notes |
| --- | --- | --- |
| Web | **Vercel** | Root directory `web`, framework preset Next.js. Env: Supabase URL + publishable key, `API_URL` = the Fly URL |
| API | **Fly.io** | `api/Dockerfile` + `api/fly.toml` (scale-to-zero, `/health` check). Deploys automatically when `api/` changes on `main`, after tests pass. Manual fallback: `fly deploy --remote-only` from `api/` |
| Database | **Neon** | PostgreSQL. Set as `DATABASE_URL` via `fly secrets set` |
| Auth | **Supabase** | Add the production `/auth/callback` URL to the redirect URLs |

Fly secrets: `DATABASE_URL`, `SUPABASE_URL`, `CORS_ALLOWED_ORIGINS` (the Vercel origin), and optionally `ANTHROPIC_API_KEY`.

A twice-daily workflow (`.github/workflows/keep-warm.yml`) runs a real SQL query and an auth request against Supabase (a public ping alone did not stop the free-tier pause), wakes the API, re-enables its own schedule, and opens a `keep-warm` issue on failure. It needs the `SUPABASE_DB_URL` secret (session pooler connection string) and the `SUPABASE_PUBLISHABLE_KEY` variable.

## Releasing the extension

Bump `version` in `extension/manifest.json`, then push a tag:

```bash
git tag v0.2.0 && git push origin v0.2.0
```

`.github/workflows/release-extension.yml` zips `extension/` and publishes it as a GitHub Release.

## Troubleshooting

**Dashboard redirects to the login page or shows auth errors**
- Check `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `web/.env.local` and restart `npm run dev`.
- Make sure `SUPABASE_URL` is set in `api/.env` so the API can verify tokens (401s otherwise).
- Supabase sessions are per-origin, so a login on one URL doesn't carry over to another.

**Dashboard is empty**
- New accounts have no activity yet. Connect the extension (Step 4) or run the seed script.

**Extension isn't syncing**
- Confirm the API key is saved on the Options page and hasn't been revoked in Settings.
- For local development, confirm `apiBaseUrl` points at `http://localhost:8000` (Step 4).
- Check the service worker console on `chrome://extensions/` for errors.

**Sites aren't being blocked**
- In "focus-only" mode, a focus session must be active. Switch to "always" in Settings to block at all times.

**API won't start**
- Make sure Postgres is up: `docker compose ps` in `api/`.
