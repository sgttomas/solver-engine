"""
SOLVER Database Migrations - Alembic Environment

Requires PYTHONPATH=apps/api to import config.
Run via: PYTHONPATH=apps/api alembic -c infra/db/migrations/alembic.ini upgrade head
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

try:
    from config import settings
except ImportError as exc:
    raise RuntimeError(
        "Unable to import config. Run alembic with PYTHONPATH=apps/api"
    ) from exc

target_metadata = None  # Raw SQL migrations, no ORM metadata yet


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.postgres_url_sync
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        settings.postgres_url_sync,
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
