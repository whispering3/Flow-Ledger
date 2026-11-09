from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from apps.api.config import get_settings
from apps.api.database import Base
from apps.modules.destinations import models as destination_models  # noqa: F401
from apps.modules.executions import models as execution_models  # noqa: F401
from apps.modules.identity import models as identity_models  # noqa: F401
from apps.modules.organizations import models as organization_models  # noqa: F401
from apps.modules.projects import models as project_models  # noqa: F401
from apps.modules.webhooks import models as webhook_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata)
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
