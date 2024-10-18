from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine import Connection
from app.database import Base

# Чтение конфигурации из alembic.ini
config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata


# Функция для оффлайн-миграций
def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# Функция для онлайн-миграций
async def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Создаем асинхронный движок
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Настраиваем контекст для миграций
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# Обертка для миграций (работает как синхронная в контексте)
def do_run_migrations(connection: Connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


# Определяем режим выполнения (онлайн или оффлайн)
if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
