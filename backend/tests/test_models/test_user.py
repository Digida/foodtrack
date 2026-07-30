import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole


class TestUser:
    async def test_create_user(self, db: AsyncSession):
        user = User(
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_pw",
            role=UserRole.ENTERPRISE,
        )
        db.add(user)
        await db.commit()
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.is_active is True

    async def test_unique_email(self, db: AsyncSession):
        user1 = User(email="dup@test.com", full_name="A", hashed_password="pw", role=UserRole.VIEWER)
        db.add(user1)
        await db.commit()
        user2 = User(email="dup@test.com", full_name="B", hashed_password="pw", role=UserRole.VIEWER)
        db.add(user2)
        with pytest.raises(Exception):
            await db.commit()
        await db.rollback()

    async def test_default_role(self, db: AsyncSession):
        user = User(email="default@test.com", full_name="Default", hashed_password="pw")
        db.add(user)
        await db.commit()
        assert user.role == UserRole.VIEWER
