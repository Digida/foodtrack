from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database.

    For SQLite (development/test): create all tables directly via SQLAlchemy.
    For PostgreSQL (production): tables are managed exclusively via Alembic migrations.
    create_all is intentionally skipped for PostgreSQL to prevent schema drift.
    """
    is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    if is_sqlite:
        async with engine.begin() as conn:
            from app.models import (  # noqa: F401
                user, product, certificate, traceability, taxonomy, tracking,
                cargo, tenant, enrichment, events, telemetry, api_key,
                retention, esg, recall, supplier, insurance,
            )
            await conn.run_sync(Base.metadata.create_all)
