# File: alembic/env.py | Version: 1.0 | Title: Alembic environment (autogenerate-ready)
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None:  # pragma: no cover
    fileConfig(config.config_file_name)

# Pull DB URL from env if provided
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Target metadata
from app.db.base_class import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():  # pragma: no cover
    run_migrations_offline()
else:
    run_migrations_online()
