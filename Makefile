# File: Makefile | Version: 1.0 | Title: Dev convenience targets
.PHONY: install dev fmt lint test cov migrate makemigration precommit

install:
\tpython -m pip install --upgrade pip && pip install -r requirements.txt

dev:
\tpip install -r requirements-dev.txt

fmt:
\tblack . && ruff check . --fix && isort .

lint:
\truff check . && black --check . && isort . --check-only

test:
\tpytest -q

cov:
\tpytest --cov=app --cov-report=term-missing

migrate:
\talembic upgrade head

makemigration:
\talembic revision --autogenerate -m "update"

precommit:
\tpre-commit run --all-files
