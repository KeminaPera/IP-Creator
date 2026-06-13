"""
Database configuration and session management.

Provides SQLAlchemy engine setup and async session factory
for database operations throughout the application.
"""
from contextlib import asynccontextmanager, contextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.config.settings import settings


# ============================================================
# Async Engine (for FastAPI)
# ============================================================

# Create async database engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # SQL logging in debug mode
    pool_pre_ping=True,   # Verify connections before use
    pool_recycle=3600,    # Recycle connections after 1 hour
)

# Async session factory for database operations
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ============================================================
# Sync Engine (for Celery)
# ============================================================

# Convert async URL to sync URL (sqlite+aiosqlite -> sqlite)
sync_database_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")

# Create sync database engine with connection pooling
sync_engine = create_engine(
    sync_database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,        # Max permanent connections
    max_overflow=10,    # Max temporary connections during spikes
)

# Sync session factory for Celery tasks
sync_session_factory = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
)


def get_sync_session() -> Session:
    """
    Get a sync database session (for Celery tasks).
    
    Returns:
        Session: SQLAlchemy sync session
    """
    return sync_session_factory()


@contextmanager
def get_sync_session_safe():
    """
    Sync session context manager with automatic commit/rollback (for Celery tasks).
    
    Usage:
        with get_sync_session_safe() as session:
            session.execute(...)
            # auto commit on success, rollback on exception
    """
    session = sync_session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ============================================================
# Base and Helpers
# ============================================================

# Base class for all SQLAlchemy models
class Base(DeclarativeBase):
    pass


async def get_db_session() -> AsyncSession:
    """
    FastAPI dependency that provides database session.
    Ensures proper session lifecycle management.
    
    Yields:
        AsyncSession: Database session for the request
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session_standalone():
    """
    Async session context manager with automatic commit/rollback.
    
    Use this for async code OUTSIDE FastAPI request context
    (e.g., service classes, background tasks, quality assessor).
    
    Usage:
        async with get_db_session_standalone() as session:
            result = await session.execute(select(...))
            # auto commit on success, rollback on exception
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """
    Initialize database by creating all tables.
    Called during application startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Close database connections.
    Called during application shutdown.
    """
    await engine.dispose()
