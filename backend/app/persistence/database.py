"""Async SQLAlchemy engine and session factory for PostgreSQL."""

from collections.abc import AsyncGenerator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


class Settings(BaseSettings):
    """Application settings loaded from environment and optional `.env` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "metamorphic-kb"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://metamorphic:metamorphic@localhost:5432/metamorphic_kb"

    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_story_points_field: str = "customfield_10016"


settings = Settings()

_engine_kwargs: dict = {
    "echo": settings.debug,
}

# NullPool avoids sharing connections across forks/tests; swap for production pool if needed.
if settings.debug:
    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.database_url, **_engine_kwargs)


async def _setup_pgvector_on_connect(conn: object) -> None:
    """Enable pgvector in the DB (if needed) and register the type with asyncpg."""
    from pgvector.asyncpg import register_vector

    try:
        await register_vector(conn)  # type: ignore[arg-type]
    except ValueError as exc:
        # QA/local DBs often skip `alembic upgrade head` → extension/type missing.
        if "vector" not in str(exc).lower():
            raise
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")  # type: ignore[union-attr]
        await register_vector(conn)  # type: ignore[arg-type]


@event.listens_for(engine.sync_engine, "connect")
def _register_pgvector(dbapi_connection: object, connection_record: object) -> None:
    """Register pgvector types with asyncpg (required for VECTOR columns)."""
    dbapi_connection.run_async(_setup_pgvector_on_connect)  # type: ignore[attr-defined]


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def dispose_engine() -> None:
    """Dispose of the connection pool (e.g. on application shutdown)."""
    await engine.dispose()
