# File: CONTRIBUTING.md | Version: 1.0 | Title: Contributing guidelines
# Contributing

Thanks for helping improve Task Manager!

## Dev setup
- Python 3.12+ (3.13 works)
- `pip install -r requirements.txt`
- For tooling: `pip install -r requirements-dev.txt`
- Copy `.env.example` to `.env` and adjust secrets.

## Commands
- `make fmt` – auto-format (Black, Ruff, isort)
- `make test` – run unit tests
- `make cov` – tests with coverage (≥85% gate)
- `make makemigration` then `make migrate` – DB changes

## PR checklist
- Tests pass in CI, coverage ≥85%
- If schema changed: include an Alembic migration
- Update docs/CHANGELOG when user-facing behavior changes

## Code style
- Black (line length 100), Ruff for lint
- Prefer type hints; keep functions small
