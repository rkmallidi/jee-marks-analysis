from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orm import FacultySection


class FacultySectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_all(self) -> list[FacultySection]:
        r = await self._s.execute(
            select(FacultySection)
            .options(selectinload(FacultySection.user), selectinload(FacultySection.branch))
            .order_by(FacultySection.id)
        )
        return list(r.scalars().all())

    async def get_by_id(self, fs_id: int) -> FacultySection | None:
        r = await self._s.execute(
            select(FacultySection)
            .options(selectinload(FacultySection.user), selectinload(FacultySection.branch))
            .where(FacultySection.id == fs_id)
        )
        return r.scalar_one_or_none()

    async def create(self, fs: FacultySection) -> FacultySection:
        self._s.add(fs)
        await self._s.flush()
        return fs

    async def delete(self, fs: FacultySection) -> None:
        await self._s.delete(fs)
        await self._s.flush()
