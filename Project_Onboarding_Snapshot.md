# 🧭 Project Onboarding Snapshot: Task Manager App

This document serves as the starting point for building your ClickUp-style task management platform using Python and FastAPI. It summarizes the key decisions, phases, conventions, and responsibilities for smooth development.

---

## ✅ Tech Stack

- **Language**: Python 3.11+
- **Backend Framework**: FastAPI
- **Database**: SQLite for local development (PostgreSQL-ready)
- **Auth**: JWT-based authentication
- **Frontend**: (Optional at MVP stage)
- **Environment**: VS Code on Windows (local setup)

---

## 📁 Initial Source Document

A single combined document contains:
- Functional and Behavioral Specification
- Full ERD (Rev03)
- Role matrices, scenarios, and acceptance criteria

This document will remain the **source of truth** for all development.

---

## 🏗️ Development Plan (Phases)

| Phase | Scope |
|-------|-------|
| Phase 1 | Backend project scaffold, database models, user auth, roles |
| Phase 2 | Workspace/Space/Folder/List CRUD with permission logic |
| Phase 3 | Task & Subtask logic, assignment, dependencies |
| Phase 4 | Comments, mentions, and notification triggers |
| Phase 5 | Tags, Filtering, Grouping, Custom Fields |
| Phase 6 | Time Tracking, Saved Views |
| Phase 7 | Testing setup, seed data, final polish |

Each phase will be confirmed and validated before moving to the next.

---

## 🔐 Naming Conventions

- **Models**: `PascalCase` (e.g., `User`, `Task`)
- **Tables**: `snake_case` (e.g., `task_dependencies`, `workspace_members`)
- **API endpoints**: RESTful (e.g., `/tasks`, `/workspaces/{id}/lists`)
- **Files/folders**: lowercase with underscores (e.g., `models/user.py`, `routers/task.py`)
- **Code shared in Chat**:
  - Every file will begin with a label on the first line like:
    ```
    # File: app/models/user.py | Version: 1.0 | Path: /app/models/user.py
    ```
  - This makes it easier to track, organize, and apply updates correctly in VS Code.

---

## 🧾 Commitments

- All features will strictly follow the ERD + Spec
- No field, permission, or behavior will be added without confirmation
- Development will be modular and traceable
- Every phase includes working code, testing examples, and your review
- All code will be consistently versioned and file-labeled for clarity

---

## 🧳 Ready to Begin?

Create a new ChatGPT project, upload your combined spec, and say:

> “Let’s begin Phase 1: Backend scaffold with FastAPI.”

We’ll take it from there — one layer at a time.
