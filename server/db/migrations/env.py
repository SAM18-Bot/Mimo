"""
Alembic migration environment.
Configured for:
  - Online mode (direct DB connection)
  - Offline mode (generate SQL scripts)
  - Autogenerate support (reads SQLAlchemy models)
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from server import config as app_config
from server.db import models  # noqa: F401 — registers all models with Base.metadata
from server.db.database import Base

config = context.config

# ── logging setup ─────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── metadata for autogenerate ─────────────────────────────────────────────
target_metadata = Base.metadata

# ── override URL from environment if set ──────────────────────────────────
db_url = app_config.DATABASE_URL.replace("%", "%%")
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (generate SQL without a live connection).
    Useful for generating migration scripts to review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url                  = url,
        target_metadata      = target_metadata,
        literal_binds        = True,
        dialect_opts         = {"paramstyle": "named"},
        compare_type         = True,
        compare_server_default = True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (with a live DB connection).
    This is the normal mode used by `alembic upgrade head`.
    """
    existing = config.attributes.get("connection")
    if existing is not None:
        context.configure(connection=existing, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix      = "sqlalchemy.",
        poolclass   = pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection           = connection,
            target_metadata      = target_metadata,
            compare_type         = True,
            compare_server_default = True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
