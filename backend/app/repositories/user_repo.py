from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_users(self) -> list[User]:
        r = await self._s.execute(select(User).order_by(User.id))
        return list(r.scalars().all())

    async def get_by_id(self, user_id: int) -> User | None:
        r = await self._s.execute(select(User).where(User.id == user_id))
        return r.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        r = await self._s.execute(select(User).where(User.username == username))
        return r.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self._s.add(user)
        await self._s.flush()
        return user

    async def update(self, user: User, data: dict) -> User:
        for k, v in data.items():
            setattr(user, k, v)
        await self._s.flush()
        return user

    async def delete(self, user: User) -> None:
        await self._s.delete(user)
        await self._s.flush()
