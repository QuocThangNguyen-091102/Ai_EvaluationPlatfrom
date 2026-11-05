from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.database.base import Base

# Import các module model ở đây khi có model (M3 trở đi) để Alembic thấy bảng của chúng.

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL lấy từ cấu hình ứng dụng, không ghi cứng trong alembic.ini (tránh lộ mật khẩu).
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
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
