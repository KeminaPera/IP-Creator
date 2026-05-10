"""
Database configuration and session management.

Provides SQLAlchemy engine setup and async session factory
for database operations throughout the application.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config.settings import settings


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
