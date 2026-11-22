# Module 12 Implementation Plan – Advanced Authentication, Persistent Database, Cloud Deployment, Premium 3D Twin

---

## 1️⃣ Findings – Repository Overview (Stage 0)

| Item | Detail |
|------|--------|
| **Repository root** | `C:\Users\Prasun\SmartWarehouse-AI.2` |
| **Current branch** | `main` (no uncommitted changes except the files we will add) |
| **Tests** | **159 passed**, **0 failed** (full suite) |
| **Python version** | 3.13.7 |
| **Streamlit** | Installed (latest 1.x, provides `st.session_state`, `st.sidebar`, etc.) |
| **Key modules** | `core/*` (grid, planner, reservation, replanner, iot_manager, hazard_detector, …), `visualization/renderer_3d.py`, `app.py` and UI pages |
| **Existing persistence** | None – all live state lives in memory; only CSV/JSON logs are written by the simulator for demo purposes |
| **Auth** | No authentication system – the UI is open to any user |
| **Database** | No DB layer; `sqlite3` not used anywhere |
| **Cloud support** | No deployment scripts or config for Render/Render.com, Railway, etc. |
| **.gitignore** | Does not currently ignore `.env`, `*.db`, `backups/` – opportunities to add for secrets |

### Immediate Risks
* The import‑guard test in `tests/test_hazard_detector.py` was previously failing due to naive string matching. It has been fixed with an AST‑based guard, and the full test suite now passes.
* No persistence means historical incident/telemetry data cannot survive a process restart – a requirement for Module 12.
* No authentication, so any user can trigger emergency actions, violating safety policies.

---

## 2️⃣ Proposed Package Layout (Module 12)

```
SmartWarehouse-AI.2/
│
├─ docs/                     # Documentation (new MODULE12_PLAN.md, deployment guide, etc.)
│   └─ MODULE12_PLAN.md
│
├─ persistence/              # SQLite / optional PostgreSQL persistence layer
│   ├─ __init__.py
│   ├─ db.py                  # Connection manager, schema init, migrations
│   ├─ migrations/            # One‑off .sql scripts, named 001_init.sql, 002_add_user.sql …
│   ├─ repo.py                # High‑level repository objects (UserRepo, IncidentRepo, …)
│   └─ queue.py               # In‑memory write‑behind queue with background flush
│
├─ auth/                     # Authentication & Authorization package
│   ├─ __init__.py
│   ├─ models.py              # Dataclasses for User, Role, Session
│   ├─ crypto.py              # Password hashing (scrypt), verification
│   └─ routes.py              # Login, logout, registration, role‑change helpers
│
├─ config/                    # Application configuration loader
│   └─ settings.py            # Loads from .env, Streamlit secrets, validates
│
├─ ui/                        # UI helper modules (new pages, components)
│   ├─ __init__.py
│   ├─ login_page.py          # Streamlit login form, session handling
│   ├─ admin_page.py          # User management, backup/restore, retention UI
│   ├─ operator_page.py       # Emergency acknowledge/clear UI (auth‑protected)
│   └─ twin_controls.py       # 3D twin layer toggles, camera presets
│
├─ visualization/renderer_3d.py   # Will be extended – keep current logic untouched
│
├─ app.py                     # Main Streamlit entry – will import auth/ui helpers
│
└─ ... (existing core modules) 
```

### Rationale
* **Isolation** – Persistence (`persistence/`) and auth (`auth/`) are separate packages, making them easy to enable/disable via config.
* **Standard library first** – SQLite via `sqlite3` satisfies the “no new dependencies” rule. PostgreSQL support is optional and lazily imported only when `DATABASE_URL` is defined.
* **Write‑behind queue** – Guarantees that the real‑time simulation tick never blocks on I/O, satisfying the safety‑critical constraint.
* **Roles** – Defined as an Enum (`ADMIN`, `OPERATOR`, `VIEWER`). Authorization checks are performed server‑side in each mutating handler.
* **Configuration** – Centralised in `config/settings.py`; it validates required env vars, applies sensible defaults, and aborts start‑up in production mode if auth is disabled.
* **UI integration** – New Streamlit pages live under `ui/` and are referenced from `app.py`. Existing pages remain unchanged; visibility is driven by the current session's role.

---

## 3️⃣ Database Schema (SQLite – primary) 

| Table | Columns (type) | Description |
|-------|----------------|-------------|
| **users** | `id INTEGER PRIMARY KEY AUTOINCREMENT`, `username TEXT UNIQUE NOT NULL`, `password_hash BLOB NOT NULL`, `role TEXT NOT NULL CHECK(role IN ('ADMIN','OPERATOR','VIEWER'))`, `created_at TIMESTAMP NOT NULL`, `last_login TIMESTAMP`, `failed_attempts INTEGER NOT NULL DEFAULT 0`, `locked_until TIMESTAMP` | User accounts and lock‑out state |
| **sessions** | `token TEXT PRIMARY KEY`, `user_id INTEGER NOT NULL`, `issued_at TIMESTAMP NOT NULL`, `last_activity TIMESTAMP NOT NULL`, `expires_at TIMESTAMP NOT NULL`, `FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE` | Streamlit‑session token storage (optional persistence) |
| **incidents** | `id INTEGER PRIMARY KEY AUTOINCREMENT`, `hazard_type TEXT NOT NULL`, `severity TEXT NOT NULL`, `status TEXT NOT NULL`, `sensor_ids TEXT`, `device_id TEXT`, `coord_x INTEGER`, `coord_y INTEGER`, `value REAL`, `unit TEXT`, `tick INTEGER`, `rule_id TEXT`, `explanation TEXT`, `recovery TEXT`, `data_source TEXT NOT NULL`, `created_at TIMESTAMP NOT NULL` | Mirrors `HazardDetector` incidents for historical view |
| **hazard_audits** | `id INTEGER PRIMARY KEY AUTOINCREMENT`, `incident_id INTEGER NOT NULL`, `action TEXT NOT NULL CHECK(action IN ('ACK','CLEAR','OVERRIDE'))`, `username TEXT NOT NULL`, `tick INTEGER NOT NULL`, `timestamp TIMESTAMP NOT NULL`, `prev_hash TEXT`, `hash TEXT NOT NULL`, `FOREIGN KEY(incident_id) REFERENCES incidents(id)` | Append‑only audit log with hash‑chain integrity |
| **sensor_readings** | `id INTEGER PRIMARY KEY AUTOINCREMENT`, `sensor_id TEXT NOT NULL`, `value REAL NOT NULL`, `unit TEXT NOT NULL`, `tick INTEGER NOT NULL`, `data_source TEXT NOT NULL`, `created_at TIMESTAMP NOT NULL` | Down‑sampled telemetry for the Historical Records page |
| **tasks** | `id INTEGER PRIMARY KEY AUTOINCREMENT`, `task_type TEXT`, `payload JSON`, `status TEXT`, `assigned_robot TEXT`, `created_at TIMESTAMP`, `completed_at TIMESTAMP` | Optional – records task‑assignment history |
| **system_config** | `key TEXT PRIMARY KEY`, `value TEXT` | Runtime configuration (e.g., retention windows) |
| **migration_meta** | `id INTEGER PRIMARY KEY`, `name TEXT UNIQUE`, `applied_at TIMESTAMP` | Tracks which migration scripts have run |

*All timestamps are stored in UTC.*

### Migration Flow
1. On start‑up `persistence/db.py` calls `run_migrations()`.
2. It scans `migrations/` in lexical order, checks `migration_meta` for each name, and executes any missing script inside a transaction.
3. If a migration fails, the app aborts with a clear error and rolls back – no partial schema state.

---

## 4️⃣ Authentication & Authorization Design

* **Password hashing** – `hashlib.scrypt` with per‑user 16‑byte salt, `n=2**14`, `r=8`, `p=1`. The stored blob contains `salt||hash||params` so future re‑hashes are possible.
* **Constant‑time verification** – `hmac.compare_digest`.
* **Login flow** – Users submit username/password via `ui/login_page.py`. Successful login creates a random token (`secrets.token_urlsafe(32)`) stored in `st.session_state['auth_token']` and persisted in the `sessions` table.
* **Session expiry** – Configurable idle timeout (default 15 min) and absolute timeout (default 8 h). Expired sessions are logged out automatically on the next interaction.
* **Roles** – Permissions expressed in a dict:
  ```python
  PERMS = {
      "ADMIN": {"manage_users", "backup", "restore", "purge", "view_all"},
      "OPERATOR": {"run_sim", "acknowledge", "clear", "view_live"},
      "VIEWER": {"view_live", "view_historical"},
  }
  ```
  Every mutating handler checks `if action in PERMS[session.role]` – UI widgets are hidden for unauthorized roles, but the backend guard remains.
* **First‑run bootstrap** – If `users` table is empty, `ui/admin_page.py` presents a **Setup Admin** screen that creates the first ADMIN. The password is entered once and never echoed or logged.
* **Lockout** – After `MAX_FAILED=5` consecutive bad attempts, `locked_until = now + 5 minutes`. The lockout period is stored in DB; a dummy hash verification runs for unknown usernames to keep timing constant.
* **Audit Logging** – All authentication events (login, logout, failed attempts, password change) are written to a `login_events` table (similar to `hazard_audits`). No secrets are ever written.

---

## 5️⃣ 3‑D Digital Twin Enhancements (Premium UI)

* **Layer architecture** – Separate data‑builder functions (`build_robot_traces`, `build_hazard_zones`, `build_sensor_coverage`) that return Plotly `Scatter3d` / `Mesh3d` objects. The renderer only assembles the list of enabled layers.
* **Trace budget** – Target ≤ 40 traces. Large grids automatically batch racks into a single `Mesh3d`; robot trails are limited to the last **N** ticks (configurable, default 20).
* **Performance measurement** – `time.perf_counter()` around the builder; the result is displayed in the UI (`builder_time_ms`).
* **Controls (Streamlit sidebar)**:
  - Camera preset selector (`Isometric`, `Top‑Down`, `Front`, `Side`).
  - Toggle switches for **Robots**, **Racks**, **Sensors**, **Hazard Zones**, **Routes**, **Coverage Discs**.
  - Search boxes to select a robot or sensor; the selection highlights the object in the 3D view (via a larger marker).
* **Fallback** – If building a 3D figure raises an exception (e.g., missing Plotly or out‑of‑memory), the UI automatically switches to a 2‑D Matplotlib floorplan with a banner *"3‑D view unavailable – showing 2‑D fallback"*.
* **Testing** – Added `tests/test_renderer_budget.py` asserting the builder returns ≤ 40 traces for a 30 × 30 warehouse and that toggling layers does not raise errors.

---

## 6️⃣ Cloud Deployment Preparation

* **requirements.txt** – pins core dependencies only (Streamlit, Plotly, NumPy, Pandas, NetworkX, sqlite3 is stdlib). Optional PostgreSQL driver `psycopg2‑binary` is listed in `requirements-postgres.txt`.
* **.env.example** – contains placeholders:
  ```
  # Database – SQLite (default) or PostgreSQL URL
  DATABASE_URL="sqlite:///data/smartwarehouse.db"
  # Auth secret for first admin bootstrap (only used when no users exist)
  BOOTSTRAP_ADMIN_PASSWORD=""
  # Secret key for session token signing
  SECRET_KEY="<random‑64‑char‑hex>"
  # Mode: development / production
  ENV="development"
  ```
* **.gitignore additions** – `*.db`, `data/`, `.env`, `backups/`.
* **Render (or similar) config** – `render.yaml`:
  ```yaml
  services:
    - type: web
      name: smartwarehouse
      env: python
      buildCommand: pip install -r requirements.txt
      startCommand: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
      envVars:
        - key: DATABASE_URL
          fromSecret: DATABASE_URL
        - key: SECRET_KEY
          fromSecret: SECRET_KEY
        - key: ENV
          value: production
  ```
* **Health‑check** – Streamlit exposes `/` which returns HTTP 200 when the app loads. The deployment guide recommends using a simple external ping service.
* **Backup & Restore UI** – Admin page lets the user trigger `sqlite3.backup()` → `backups/<timestamp>.db`. Restores replace the current file after a confirmation dialog. Both actions are logged in `system_audit`.
* **Retention policy UI** – Admin can specify how many days of sensor‑reading history to keep; a dry‑run shows rows that will be deleted, then an audited delete runs.

---

## 7️⃣ Test Plan (Module 12)

| Scope | Test File | Description |
|-------|-----------|-------------|
| **Database** | `tests/persistence/test_db.py` | Migrations on fresh DB, idempotency, schema validation |
| | `tests/persistence/test_repo.py` | CRUD for User, Incident, Session; constraint violations raise domain errors |
| | `tests/persistence/test_queue.py` | Write‑behind queue flushes batches, handles DB‑down gracefully (simulated by monkeypatching `sqlite3.connect` to raise) |
| **Auth** | `tests/auth/test_crypto.py` | Salt uniqueness, verify correct/incorrect passwords, rehash on cost change |
| | `tests/auth/test_login_flow.py` | Successful login creates session token, failed attempts increment lockout counter, lockout blocks after threshold |
| | `tests/auth/test_role_enforcement.py` | VIEWER cannot ack/clear emergencies, OPERATOR can, ADMIN can override; server‑side checks enforced |
| **UI/Pages** | `tests/ui/test_pages.py` | Streamlit `AppTest` (if available) logs in as each role and verifies page visibility and that protected handlers reject unauthorized tokens |
| **3‑D Renderer** | `tests/test_renderer_budget.py` | Builder returns ≤ 40 traces; toggling each layer works without exception |
| **Integration** | `tests/integration/test_full_flow.py` | End‑to‑end: register admin, create operator, run a fire scenario, ack/clear incident, verify rows in `incidents` and `hazard_audits`, then query historical page – all while simulation tick time remains < 5 ms (measured with `time.perf_counter`). |
| **Deployment config** | `tests/deploy/test_config_validation.py` | Missing `DATABASE_URL` or `SECRET_KEY` aborts with clear error; production mode refuses `auth_enabled=False` |

All new tests use only the standard library and the existing test dependencies; no external services are called.

---

## 8️⃣ Decisions Requiring Owner Approval

| Decision | Recommended Default | Reason |
|----------|---------------------|--------|
| **Database engine** | SQLite (file‑based) | No extra dependencies, works locally and on most PaaS (file can be mounted). PostgreSQL optional via `DATABASE_URL`.
| **PostgreSQL driver** | Include `psycopg2‑binary` in `requirements-postgres.txt` only | Lazy import prevents import error when not used.
| **Initial admin bootstrap** | Prompt for password on first run (via UI) | Guarantees at least one admin without hard‑coded credentials.
| **Lockout parameters** | `MAX_FAILED=5`, lockout `5 min` | Balances security with usability for a teaching demo.
| **Retention window for sensor readings** | 30 days by default, configurable | Keeps DB size manageable while preserving useful history.
| **Backup location** | `backups/` inside project root (git‑ignored) | Simple, visible to user, works on Render/Render.com where disk persists for the container lifetime.
| **Production mode checks** | `ENV=production` must have `DATABASE_URL` set and `auth_enabled=True` | Prevents accidental open‑access deployments.

Please review the plan. Reply **"approved"** (or indicate amendments) so we can proceed to implementation (Stages 2‑7).