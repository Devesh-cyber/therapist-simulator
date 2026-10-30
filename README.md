# Therapist Simulator — MVP

A casual simulation game: run the Quiet Room Clinic, talk to AI patients (Grok), uncover their hidden story on a live **Patient Case Board**, submit your understanding, and get scored.

```
React + Vite + TS (Vercel)  ──HTTPS REST──▶  FastAPI (Render)  ──▶  Grok API (xAI)
                                                   │
                                                   └──▶  Supabase PostgreSQL
```

## Project structure

```
therapist-simulator/
├── backend/                     FastAPI app (deploy to Render)
│   ├── app/
│   │   ├── main.py              app, CORS, routers
│   │   ├── config.py            env settings
│   │   ├── database.py          Database Service (SQLAlchemy models)
│   │   ├── auth.py              Authentication Service (signed guest tokens)
│   │   ├── schemas.py           Pydantic: LLM output contracts + API shapes
│   │   ├── routers/             auth, patients, sessions, game
│   │   └── services/
│   │       ├── llm.py               Grok client (OpenAI-compatible, retries, JSON validation)
│   │       ├── patient_generator.py Patient Generator
│   │       ├── patient_simulator.py Patient Simulator (+ context summarising)
│   │       ├── discovery.py         Discovery Evaluator (+ backend validation, states)
│   │       ├── session_evaluator.py Session Evaluator
│   │       ├── scoring.py           Scoring Engine (weighted formula in Python)
│   │       ├── session_manager.py   Session Manager (timer, message flow, rewards)
│   │       ├── progression.py       levels, difficulty tiers, XP
│   │       └── mock_engine.py       offline demo engine (used only when no Grok key)
│   ├── tests/                   pytest suite (18 tests)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    React app (deploy to Vercel)
│   ├── src/api/                 typed API client + types
│   ├── src/pages/               Main Menu, Clinic, Arrival, Consultation, Assessment,
│   │                            Results, Progress, History, Settings
│   ├── src/game/                room scene + character (scene.js), notebook, game styles
│   ├── src/components/          CaseBoard, Layout, UI kit
│   ├── vercel.json              SPA rewrites
│   └── .env.example
├── in-app-version/              single-file claude.ai version (template + build script)
├── supabase/migrations/001_initial_schema.sql
└── render.yaml                  Render blueprint for the backend
```

## The consultation room
The consultation is played inside an illustrated therapy room (`frontend/src/game/scene.js`, plain SVG, no assets):
- The patient is a procedurally drawn character (skin, hair, glasses, beard, outfit come from the generated patient's `look`) sitting in an armchair across from you.
- Every Grok reply is JSON `{line, emotion, comfort}`. The emotion drives their face and posture (neutral, warm, sad, anxious, guarded with crossed arms, tearful, relieved, frustrated); a thought bubble shows while they think; the mouth moves while their line types out.
- A **Comfort** meter shows how safe the patient feels with you (moves at most 15 points per turn).
- The wall clock and the light through the window follow the 10-minute timer (afternoon fades to dusk).
- Your case board is a handwritten notebook on the desk; new discoveries fly into it as notes.
- The patient walks in after you accept the intake form and leaves when the session ends.

`in-app-version/` holds the single-file version that runs inside claude.ai (Claude plays the patient there). Rebuild it with `python in-app-version/build.py` after editing `scene.js` or `template.html`.

## Run locally (5 minutes)

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # add GROK_API_KEY now or later
uvicorn app.main:app --reload --port 8000
```
With `DATABASE_URL` empty it uses a local SQLite file. With `GROK_API_KEY` empty it runs the **offline demo AI** (simple keyword engine, 3 built-in patients) so you can click through the whole game. The UI shows an "Offline demo AI" badge in that mode.

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_BASE_URL=http://localhost:8000
npm run dev                   # http://localhost:5173
```

## Grok configuration
1. Create a key at console.x.ai.
2. In `backend/.env` set:
   ```
   GROK_API_KEY=xai-...
   GROK_MODEL=grok-4            # use any chat model id listed in your xAI console
   GROK_BASE_URL=https://api.x.ai/v1
   ```
3. Restart the backend. `GET /api/health` shows `"llm_mode": "grok"`.

The key lives only on the backend. The frontend never sees it.

## Supabase configuration
1. Create a project → **SQL Editor** → paste `supabase/migrations/001_initial_schema.sql` → Run.
2. **Project Settings → Database → Connection string → URI** (use the *Session pooler* string on Render, since Render has no IPv6). Put it in `DATABASE_URL`, e.g.
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`
3. Security: RLS is enabled on every table with no anon/authenticated policies (except reading the achievements catalogue), so nothing — especially `patients.hidden_profile` — is readable with the public anon key. Only the backend, connecting with the database password, can read hidden profiles.

## Deploy
**Backend → Render**
- New → Blueprint → select the repo (uses `render.yaml`), or New → Web Service with:
  - Root directory `backend`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env vars: `GROK_API_KEY`, `GROK_MODEL`, `GROK_BASE_URL`, `DATABASE_URL`, `APP_SECRET` (long random string), `FRONTEND_URL` (your Vercel URL).
- Note: Render's free tier sleeps; the first request after idle can take ~30–60s.

**Frontend → Vercel**
- Import the repo, set **Root Directory = `frontend`** (framework: Vite).
- Env var: `VITE_API_BASE_URL=https://<your-render-service>.onrender.com`
- Deploy. `vercel.json` handles client-side routes. `*.vercel.app` preview URLs are already allowed by backend CORS.

## How it works
- **Hidden vs visible profile**: the generator creates a full profile with 5–14 *discovery facts* (category, importance 1–3, related facts, reveal hint). Only the arrival card is ever sent to the browser.
- **Message flow** (`POST /api/sessions/{id}/message`): validate session → verify server timer → store player message → patient context + recent history (older turns summarised) → Grok reply → validate/clean reply → store → Discovery Evaluator → backend validation (known key, not yet found, confidence ≥ 0.6, DB unique constraint) → return reply + only new board items. If Grok fails, the player's message is kept and an error is returned.
- **States**: Discovered → Important (importance 3) → Connected (a related fact is also discovered).
- **Timer**: `ends_at` stored on the server; client countdown is corrected with `server_now`; messages after expiry get `409`.
- **Scoring** (all in Python):
  - Overall `S = 0.20E + 0.20Q + 0.15L + 0.20U + 0.15C + 0.10N` from the six Grok category scores; conversational categories are capped when there were fewer than 3 player messages.
  - Satisfaction = mean of 6 patient-experience sub-scores.
  - Understanding = 35% importance-weighted discovery coverage + 30% assessment accuracy + 15% connections + 10% uncertainty recognition + 10% prioritisation.
  - XP = (0.5·overall + 0.25·understanding + 0.25·satisfaction [+10 full discovery]) × difficulty multiplier (1.0 → 2.0). Level n needs 50·(n−1)·n total XP.

## API
| Method | Endpoint |
|---|---|
| POST | /api/auth/guest · GET/PATCH /api/auth/me |
| POST | /api/patients/generate (returns waiting patient or generates one; `?force=true` for new) |
| GET | /api/patients/{id} |
| POST | /api/sessions/start |
| GET | /api/sessions/{id} |
| POST | /api/sessions/{id}/message |
| GET | /api/sessions/{id}/board |
| POST | /api/sessions/{id}/notes · /end · /assessment · /evaluate |
| GET | /api/sessions/{id}/results · /api/sessions/history · /api/game/progress |

Every endpoint except guest login requires `Authorization: Bearer <token>` and checks ownership (other players' patients/sessions return 404).

## Tests
```bash
cd backend && pytest -q
# against Postgres instead of SQLite:
TEST_DATABASE_URL=postgresql://user:pass@host:5432/db pytest -q
```
Covers: patient generation, hidden-profile protection, conversation, discovery detection, duplicate prevention, board updates/states, 10-minute timer, expiry rejection, manual end, assessment, weighted formula, satisfaction, understanding, XP/levels, persistence/history, idempotent evaluation (no double XP), auth + ownership, Grok client request shape/retries/JSON repair, reply cleanup.

## Known limitations
- Tests run against the offline engine; real Grok behaviour (patient consistency, discovery quality, score calibration) needs a manual playtest once your key is in. Prompts live in the `services/*.py` files and are easy to tune.
- Auth is a signed guest token stored in the browser — clearing storage loses the profile. Supabase Auth could replace it later.
- Grok calls are synchronous per request (no streaming); a patient reply typically takes a few seconds.
- No rate limiting on generation/messages.
- Patients are fictional and scenarios avoid crisis topics by design; this is a game, not clinical training.
