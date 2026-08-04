"""Test configuration and shared fixtures.

asyncio_mode = auto is set in pytest.ini — no manual event_loop fixture needed.
Tests use an in-memory SQLite database that is created fresh before each test
and torn down after.
"""
import asyncio
import sys
from collections.abc import AsyncGenerator

# Scratch script (not a pytest test) that hits a live server at import time.
collect_ignore = ["fix_auth_test.py"]

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.taxonomy import Taxonomy, TaxonomyItem, TaxonomyNode
from app.models.user import User, UserRole
from app.services.auth_service import create_access_token, hash_password

TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    user = User(
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def superuser(db: AsyncSession) -> User:
    user = User(
        email="super@test.com",
        full_name="Test Superuser",
        hashed_password=hash_password("super123456"),
        role=UserRole.SUPERUSER,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def enterprise_user(db: AsyncSession) -> User:
    user = User(
        email="enterprise@test.com",
        full_name="Test Enterprise",
        hashed_password=hash_password("ent123456"),
        role=UserRole.ENTERPRISE,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user(db: AsyncSession) -> User:
    user = User(
        email="viewer@test.com",
        full_name="Test Viewer",
        hashed_password=hash_password("view123456"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(admin_user: User) -> str:
    return create_access_token({"sub": str(admin_user.id), "role": admin_user.role.value})


@pytest_asyncio.fixture
async def superuser_token(superuser: User) -> str:
    return create_access_token({"sub": str(superuser.id), "role": superuser.role.value})


@pytest_asyncio.fixture
async def enterprise_token(enterprise_user: User) -> str:
    return create_access_token({"sub": str(enterprise_user.id), "role": enterprise_user.role.value})


@pytest_asyncio.fixture
async def viewer_token(viewer_user: User) -> str:
    return create_access_token({"sub": str(viewer_user.id), "role": viewer_user.role.value})


@pytest_asyncio.fixture
async def taxonomy(db: AsyncSession) -> Taxonomy:
    t = Taxonomy(name="Test Taxonomy", description="Test")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


@pytest_asyncio.fixture
async def taxonomy_node(db: AsyncSession, taxonomy: Taxonomy) -> TaxonomyNode:
    n = TaxonomyNode(taxonomy_id=taxonomy.id, code="TEST-NODE", name="Test Node")
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return n


@pytest_asyncio.fixture
async def taxonomy_item(db: AsyncSession, taxonomy_node: TaxonomyNode) -> TaxonomyItem:
    item = TaxonomyItem(
        node_id=taxonomy_node.id,
        code="TEST-ITEM-001",
        common_name="Test Item",
        scientific_name="Testus itemus",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(admin_token: str) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {admin_token}"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def enterprise_client(enterprise_token: str) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {enterprise_token}"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def viewer_client(viewer_token: str) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {viewer_token}"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def anon_client() -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated client — for testing 401 boundaries."""
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
