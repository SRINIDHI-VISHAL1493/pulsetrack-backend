import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


DEFAULT_SQLITE_URL = "sqlite+aiosqlite:///./pulsetrack.db"
DEFAULT_POSTGRES_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/pulsetrack"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

if DATABASE_URL.startswith("postgresql"):
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
else:
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Provide one transaction and roll it back whenever the operation fails."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
