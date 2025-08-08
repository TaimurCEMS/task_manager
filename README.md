# Task Manager (FastAPI)

A ClickUp-style backend built with **FastAPI**, **SQLAlchemy**, and **SQLite**.  
Current scope covers **Phase 1–3** of the plan: authentication, core entities (Workspace/Space/Folder/List), **Tasks** + **Task Dependencies**, and role checks.

---

## What’s here (Phases 1–3)

- 🔐 **JWT auth**: register, login (OAuth2 password flow), current user
- 🧱 **Core entities**: Workspace, Space, Folder, List (CRUD)
- ✅ **Tasks**: create/read/update/delete (soft-delete), by-list querying
- 🔗 **Dependencies**: create and fetch task dependencies
- 👤 **Role checks**: membership & role validation at workspace level (Owner/Admin/Member)
- 🧪 **Tests**: `pytest` (2 tests passing)

---

## Requirements

- Python **3.11+**
- Windows (PowerShell examples) or macOS/Linux (adjust venv activate command)

---

## Quickstart

### 1) Create & activate a virtual env

**Windows (PowerShell):**
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

If you already have a `requirements.txt`:
```bash
pip install -r requirements.txt
```

Or install the essentials:
```bash
pip install fastapi "uvicorn[standard]" sqlalchemy pydantic passlib[bcrypt] python-jose pytest httpx
```

### 3) Run the app

```bash
uvicorn app.main:app --reload
```
Open the interactive docs at: **http://127.0.0.1:8000/docs**

### 4) Run tests

```bash
python -m pytest -q
```

---

## API: common flow

### Register → Login → Call protected endpoints

**Register:** `POST /auth/register`  
Example JSON body:
```json
{
  "email": "demo@example.com",
  "password": "changeme123",
  "full_name": "Demo User"
}
```

**Login (token):** `POST /auth/token` (form-encoded: `username`, `password`)  
Example (PowerShell line continuation uses backtick ^; remove for Bash):
```bash
curl -X POST http://127.0.0.1:8000/auth/token ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  -d "username=demo@example.com&password=changeme123"
```
Response includes `access_token`. Use it as: `Authorization: Bearer <token>`.

**Example protected call** (varies by your routes; e.g., get a task):
```bash
curl http://127.0.0.1:8000/tasks/<task_id> -H "Authorization: Bearer <token>"
```

---

## Project structure (high level)

```
.
├─ app/
│  ├─ main.py                # FastAPI app, routers include
│  ├─ security.py            # JWT creation, password hashing, get_current_user
│  ├─ core/
│  │  └─ permissions.py      # role resolution & permission checks
│  ├─ db/
│  │  ├─ base.py
│  │  └─ session.py          # get_db, engine, SessionLocal (SQLite)
│  ├─ models/                # SQLAlchemy models (User, Workspace, Space, Folder, List, Task, TaskDependency,…)
│  ├─ schemas/               # Pydantic models
│  ├─ crud/                  # DB access functions
│  └─ routers/
│     ├─ auth.py             # /auth/register, /auth/token, (and possibly /auth/me)
│     ├─ core_entities.py    # Workspace/Space/Folder/List endpoints
│     └─ task.py             # Tasks + Dependencies endpoints
├─ tests/
│  ├─ conftest.py
│  ├─ test_auth.py
│  └─ test_protected.py
└─ .gitignore
```

**Database:** default SQLite (likely `sqlite:///./app.db`). The `.gitignore` excludes `*.db` already.

---

## Configuration notes

- **Secret key:** `app/security.py` uses a dev `SECRET_KEY`. For production, read it from env vars (e.g., `os.getenv("SECRET_KEY")`) and rotate regularly.
- **Time & JWT:** tokens use timezone-aware UTC (`datetime.now(UTC)`) to avoid deprecation warnings.
- **Env files:** keep secrets in `.env` (already ignored).

---

## Roadmap (next phases)

- **Phase 4:** Comments, mentions, notification triggers
- **Phase 5:** Tags, filtering/grouping, custom fields
- **Phase 6:** Time tracking, saved views
- **Phase 7:** Tests, seed data, polish

---

## Dev tips

- Interactive docs live at **/docs** (Swagger) and **/redoc**.
- When adding endpoints, keep **schemas → crud → routers** layers tidy.
- Keep role checks centralized (`app/core/permissions.py`) so it’s easy to reason about who can do what.
