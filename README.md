# PhysIQ — Adaptive Physics I Learning

A Duolingo-style adaptive learning application for freshman Physics I.
Students progress through 7 topics and their subtopics via a tier-based
question system that adjusts difficulty in real time.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Browser  (React + Vite · port 3000)                    │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS / REST+JSON
┌────────────────────────▼────────────────────────────────┐
│  Relay  (Flask · port 5000)                             │
│  Auth · session cache · route validation                │
└──────────┬──────────────────────────┬───────────────────┘
           │ Internal HTTP            │ SQLAlchemy
┌──────────▼──────────┐   ┌──────────▼──────────────────┐
│  Engine             │   │  MySQL 8 (Cloud SQL)         │
│  (Flask · port 5001)│   │  All persistent data         │
│  Adaptive logic     │   └─────────────────────────────┘
│  Scoring · Unlocks  │
└─────────────────────┘
```

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 4.x+
- Git

No local Python or Node installation required — everything runs in containers.

## Quick Start

```bash
# 1. Clone
git clone <your-repo-url> physiq-app
cd physiq-app

# 2. Configure environment
cp .env.example .env
# Edit .env and set a strong JWT_SECRET before doing anything else

# 3. Build and start all services
docker compose up --build

# 4. Wait for the db health check to pass (about 20 seconds on first run),
#    then open http://localhost:3000
```

The database schema and seed data (topics + subtopics) are loaded
automatically on first start via the Docker entrypoint mount in
`docker-compose.yml`.

## Project Structure

```
physiq-app/
├── frontend/               React SPA (Vite)
│   ├── src/
│   │   ├── api/            API client, token refresh, endpoint modules
│   │   ├── context/        AuthContext, SessionContext
│   │   ├── hooks/          useDashboard, useTopics, useSubtopics
│   │   ├── components/     Nav, UI primitives (Button, Card, TierIndicator…)
│   │   └── pages/          AuthPage, DashboardPage, TopicsPage, SessionPage
│   ├── package.json
│   └── vite.config.js      Dev proxy → relay on port 5000
│
├── relay/                  Flask relay server (public-facing)
│   ├── app.py              App factory, CORS, blueprint registration
│   ├── auth.py             JWT generation, bcrypt, @jwt_required
│   ├── cache.py            Session state cache (Redis / in-memory)
│   ├── db.py               SQLAlchemy helpers
│   ├── engine_client.py    HTTP wrapper for engine calls
│   ├── guards.py           Subtopic access validation
│   ├── routes/
│   │   ├── auth.py         POST /auth/register|login|refresh|logout
│   │   ├── sessions.py     POST /sessions/start|answer|close
│   │   ├── dashboard.py    GET  /dashboard
│   │   ├── topics.py       GET  /topics, /topics/:id/subtopics
│   │   └── progress.py     GET  /progress/subtopics|review-history
│   ├── requirements.txt
│   └── Dockerfile
│
├── engine/                 Flask background engine (internal only)
│   ├── app.py              App factory + IP allowlist guard
│   ├── answer_checker.py   Multiple choice / numeric / free-response validators
│   ├── db.py               SQLAlchemy helpers
│   ├── routes/
│   │   ├── sessions.py     POST /engine/sessions/build|evaluate|close
│   │   ├── questions.py    POST /engine/questions/select-review|next
│   │   ├── progress.py     POST /engine/progress/unlock|update-score
│   │   └── users.py        POST /engine/users/initialize
│   ├── requirements.txt
│   └── Dockerfile
│
├── database/
│   └── schema.sql          Full DDL + Physics I seed data
│
├── docker-compose.yml
├── .env.example
└── README.md
```

## Adding Questions

Questions live in the `question` and `question_option` tables.
Insert them directly via SQL or build an admin interface later.

**Multiple choice example:**
```sql
INSERT INTO question (subtopic_id, tier, prompt, correct_answer, hint_text, question_type)
VALUES (1, 1,
  'A car accelerates from 0 to 30 m/s in 6 seconds. What is its acceleration?',
  'B',
  'Acceleration = change in velocity ÷ time elapsed.',
  'multiple_choice');

-- Get the new question_id, then insert options:
INSERT INTO question_option (question_id, option_key, option_text) VALUES
  (LAST_INSERT_ID(), 'A', '3 m/s²'),
  (LAST_INSERT_ID(), 'B', '5 m/s²'),
  (LAST_INSERT_ID(), 'C', '6 m/s²'),
  (LAST_INSERT_ID(), 'D', '10 m/s²');
```

**Numeric example** (2% relative tolerance by default):
```sql
INSERT INTO question (subtopic_id, tier, prompt, correct_answer, hint_text, question_type)
VALUES (1, 2,
  'A ball is dropped from rest. What is its speed (m/s) after 3 seconds? (g = 9.81 m/s²)',
  '29.43',
  'v = u + at, where u = 0, a = 9.81, t = 3.',
  'numeric');
```

**Numeric with custom tolerance** (exact to ±0.5):
```sql
-- correct_answer format: 'value|tolerance'
INSERT INTO question (..., correct_answer, ...) VALUES (..., '29.43|0.5', ...);
```

**Free response** (all keywords must appear):
```sql
INSERT INTO question (subtopic_id, tier, prompt, correct_answer, hint_text, question_type)
VALUES (7, 1,
  'State Newton\'s Second Law in your own words.',
  'force|mass|acceleration',
  'Think about how force, mass, and motion relate to each other.',
  'free_response');
```

## Development Tips

**Viewing logs for a single service:**
```bash
docker compose logs -f relay
docker compose logs -f engine
```

**Connecting to the database directly:**
```bash
docker compose exec db mysql -u physiq -pphysiq physiq
```

**Rebuilding after code changes:**
```bash
docker compose up --build relay    # relay only
docker compose up --build engine   # engine only
# Frontend hot-reloads automatically via Vite
```

**Running without Docker (relay example):**
```bash
cd relay
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=mysql+pymysql://physiq:physiq@localhost:3306/physiq \
ENGINE_BASE_URL=http://localhost:5001 \
JWT_SECRET=dev-secret \
flask --app app:create_app run --port 5000 --debug
```

## Production Deployment (Google Cloud)

1. **Cloud SQL** — Create a MySQL 8 instance. Note the connection string.
2. **Cloud Run** — Deploy `relay/` and `engine/` as separate services.
   - Set `DATABASE_URL` to the Cloud SQL socket format (see `.env.example`).
   - Set `ENGINE_BASE_URL` to the internal Cloud Run URL of the engine service.
   - Set `ALLOWED_RELAY_HOSTS` on the engine to the relay service's egress IP.
   - Set `JWT_SECRET` from Secret Manager.
3. **Frontend** — Run `npm run build` and deploy `frontend/dist/` to
   Cloud Storage + Cloud CDN, or Cloud Run with an nginx container.
   Set `VITE_API_URL` to the relay's Cloud Run URL at build time.

## Session Flow Summary

```
start_session  →  engine builds pool (12 T1 / 10 T2 / 8 T3 / 6 T4 questions)
                  + 2 weighted review questions

Each answer:
  Wrong (first try)  →  hint served, question held, slot NOT consumed
  Any resolving answer (correct OR hint-retry) →  slot consumed
    Correct  →  tier_correct[tier]++  (2 correct = advance tier)
    Wrong    →  no tier credit

Pass condition:    tier_correct[3] >= 2  within 12 slots
Skip condition:    tier_correct[4] >= 2  within 12 slots
                   → next subtopic T3 probe (1 correct needed)
                   → next subtopic T4 probe (1 correct = skip granted)
```

## License

MIT
