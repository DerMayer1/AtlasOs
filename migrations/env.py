from alembic import context
from sqlalchemy import engine_from_config, pool

from atlas.platform.db.models import Base
from atlas.platform.db.session import normalize_database_url
from atlas.platform.runtime.settings import get_settings

config = context.config
target_metadata = Base.metadata

# Same driver normalization the app uses, so `alembic upgrade head` connects
# with psycopg3 against managed-host DSNs instead of failing on psycopg2.
config.set_main_option("sqlalchemy.url", normalize_database_url(get_settings().database_url))


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
