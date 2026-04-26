

# JEE Student Performance Intelligence Platform

> *"When the Dean walks into the Monday review meeting, she can answer which 10 students need intervention this week — and why — without calling anyone."*

A full-stack platform for JEE/NEET coaching institutes: OMR upload in under a minute, auto-regrading on key corrections, topic-level weakness analysis, and proactive student alerts.

---

## ✨ Feature highlights

| Area | What it does |
|------|-------------|
| **Upload Console** | Drag-and-drop Questions, OMR Responses, BKC / AKC answer keys with real-time progress bars and row-level error reports |
| **Auto Grading** | 7 question types (SCQ, MCQ_MULTI, NUMERICAL_INT, NUMERICAL_RANGE, PARTIAL_MCQ, NO_NEGATIVE, DELETED) with JEE marking rules. AKC always overrides BKC. Deleted questions give full bonus to everyone |
| **Analytics Engine** | Dense ranking (ties broken by accuracy then negative marks), subject/topic summaries, percentile distribution via PostgreSQL `WIDTH_BUCKET` |
| **Dashboard D1** | Overall stats, branch comparison bar chart, score histogram, top-10 table, multi-exam trend line |
| **Dashboard D2** | Weak-students feed sorted by severity (critical → warning → info), one-click profile link |
| **Dashboard D3** | Per-subject radar + bar charts, top/bottom performer lists |
| **Dashboard D4** | Topic heatmap — color-coded tiles (red = critical, green = strong), filterable by subject |
| **Dashboard D5** | Student deep-dive: rank trajectory, subject trends, weak-topic mini-heatmap, recent alerts |
| **Leaderboard** | Podium podium + full sortable table with score bars |
| **Alerts** | 4 rules: performance drop, weak topic, below-branch-avg, consistently low — with acknowledge workflow |
| **Auth** | JWT (15 min access + 7-day refresh), bcrypt-12, role-based (admin / dean / faculty) |
| **Faculty scoping** | Faculty only sees their assigned sections' students |

---

## 🗂️ Project structure

```
JEE Marks Analysis/
├── backend/
│   ├── app/
│   │   ├── config.py          # Pydantic settings
│   │   ├── database.py        # AsyncSession factory
│   │   ├── main.py            # FastAPI app factory
│   │   ├── dependencies.py    # CurrentUser, require_role
│   │   ├── models/orm.py      # 20 SQLAlchemy ORM models
│   │   ├── schemas/api.py     # Pydantic v2 schemas
│   │   ├── repositories/      # Data access layer (PostgreSQL upserts, CTEs)
│   │   ├── services/          # Business logic
│   │   ├── engines/           # rule_engine, analytics_engine, alert_engine
│   │   ├── validators/        # Row-level CSV/XLSX validators
│   │   ├── routers/           # FastAPI routers (auth, students, uploads, …)
│   │   ├── utils/security.py  # JWT + bcrypt helpers
│   │   ├── seed.py            # Idempotent seed script
│   │   └── tests/             # pytest suite (rule engine, 100 % branch coverage)
│   ├── alembic/               # Async Alembic migrations
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Router setup
│   │   ├── context/           # AuthContext (JWT + refresh)
│   │   ├── lib/api.ts         # Typed Axios client
│   │   ├── lib/utils.ts       # Color helpers, formatters
│   │   ├── components/        # Layout (Sidebar, Topbar) + UI atoms
│   │   ├── pages/             # All 9 page components
│   │   └── hooks/             # useExamSelector
│   ├── tailwind.config.js     # Custom design tokens
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 5-command bootstrap

### Prerequisites
- Docker Desktop ≥ 4.x  **or**  PostgreSQL 15+, Python 3.12+, Node 20+

### Option A — Docker (recommended)

```bash
# 1. Clone / enter the project directory
cd "E:\JEE Marks Analysis"

# 2. Copy environment file
cp .env.example .env          # edit SECRET_KEY at minimum

# 3. Start all services (PostgreSQL + API + React frontend)
docker compose up --build -d

# 4. Seed demo data (users, branches, topics, alert configs)
docker compose exec api python -m app.seed

# 5. Open the app
start http://localhost         # Windows
# or visit http://localhost in your browser
```

Log in with:  `admin / admin123`  ·  `dean / dean123`  ·  `faculty1 / faculty123`

---

### Option B — Local development (no Docker)

```bash
# ─── Backend ────────────────────────────────────────────────
cd "E:\JEE Marks Analysis\backend"

# Create & activate virtualenv
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # macOS/Linux

# Install dependencies
pip install -e .

# Set environment variables (or create a .env file)
copy .env.example .env
# Edit .env: set DATABASE_URL, SECRET_KEY

# Run migrations
alembic upgrade head

# Seed demo data
python -m app.seed

# Start API server  →  http://localhost:8000
uvicorn app.main:app --reload

# ─── Frontend ───────────────────────────────────────────────
cd "E:\JEE Marks Analysis\frontend"
npm install
npm run dev                    # → http://localhost:5173
```

---

## 🧪 Running tests

```bash
cd "E:\JEE Marks Analysis\backend"
pytest app/tests/ -v --tb=short
```

Tests cover all 7 evaluator classes, 36 branches, blank/null/malformed normalisation, and the dispatcher.

---

## 📂 Sample upload files

See `samples/` for ready-to-use templates:

| File | Purpose |
|------|---------|
| `students_sample.csv`         | 5 sample students for bulk upload |
| `questions_sample.xlsx`       | 30-question paper (mixed types) |
| `omr_responses_sample.csv`    | OMR responses for those students |
| `answer_key_bkc_sample.xlsx`  | Base Key Correction |
| `answer_key_akc_sample.xlsx`  | Amendment Key (overrides BKC for 2 questions) |

---

## 🔑 API quick-reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/login` | Get access + refresh tokens |
| `POST` | `/auth/refresh` | Rotate refresh token |
| `GET`  | `/students` | Paginated student list (FTS search) |
| `POST` | `/uploads/questions` | Upload question paper XLSX |
| `POST` | `/uploads/responses` | Upload OMR responses CSV |
| `POST` | `/uploads/answer-key` | Upload BKC or AKC XLSX |
| `POST` | `/evaluation/trigger/{exam_id}` | Grade exam + compute analytics |
| `GET`  | `/dashboards/overall/{exam_id}` | D1 data |
| `GET`  | `/dashboards/weak-students/{exam_id}` | D2 data |
| `GET`  | `/dashboards/subject-analysis/{exam_id}` | D3 data |
| `GET`  | `/dashboards/topic-heatmap/{exam_id}` | D4 data |
| `GET`  | `/dashboards/student/{student_id}` | D5 deep-dive |
| `GET`  | `/dashboards/leaderboard/{exam_id}` | Top-N ranked students |
| `GET`  | `/alerts` | Alert feed (filterable) |
| `PATCH`| `/alerts/{id}/acknowledge` | Acknowledge an alert |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🏗️ PostgreSQL capabilities used

- **JSONB** — alert context, alert config, upload error payloads (GIN indexed)
- **TSVECTOR + trigger** — full-text search on student name / admission no
- **pg_trgm** — fuzzy name matching extension (ready for future use)
- **ON CONFLICT DO UPDATE** — idempotent bulk upserts for graded_results and alerts
- **DENSE_RANK() OVER (…)** — window function for leaderboard CTE
- **WIDTH_BUCKET** — server-side score histogram
- **DateTime(timezone=True)** — all timestamps are timezone-aware

---

## 📄 License

MIT — use freely in coaching institutes.
