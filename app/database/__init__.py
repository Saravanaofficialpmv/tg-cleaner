"""
Database setup and session management.
Async SQLite via aiosqlite + SQLAlchemy.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.models import Base

# Detect if running in Vercel serverless environment (read-only filesystem except /tmp)
if os.getenv("VERCEL"):
    DATABASE_URL = "sqlite+aiosqlite:////tmp/telegram_cleaner.db"
else:
    try:
        os.makedirs("database", exist_ok=True)
        # Test write permissions
        test_file = "database/.write_test"
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        DATABASE_URL = "sqlite+aiosqlite:///database/telegram_cleaner.db"
    except Exception:
        DATABASE_URL = "sqlite+aiosqlite:////tmp/telegram_cleaner.db"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


_db_initialized = False


async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency: yield a database session, close it after request."""
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
