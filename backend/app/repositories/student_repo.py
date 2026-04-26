from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import FacultySection, Student


class StudentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_admission_no(self, admission_no: str) -> Student | None:
        r = await self._s.execute(
            select(Student).where(Student.admission_no == admission_no)
        )
        return r.scalar_one_or_none()

    async def list_students(
        self,
        branch_name:      str | None = None,
        program_name:     str | None = None,
        section:          str | None = None,
        status:           str | None = None,
        allowed_sections: list[str] | None = None,
        search:           str | None = None,
        page:             int | None = 1,
        page_size:        int | None = 50,
    ) -> tuple[list[Student], int]:
        q = select(Student)
        if branch_name:
            q = q.where(Student.branch_name == branch_name)
        if program_name:
            q = q.where(Student.program_name == program_name)
        if section:
            q = q.where(Student.section == section)
        if status:
            q = q.where(Student.status == status)
        if allowed_sections is not None:
            q = q.where(Student.section.in_(allowed_sections))
        if search:
            q = q.where(
                Student.search_vector.op("@@")(
                    text("plainto_tsquery('english', :q)")
                ).bindparams(q=search)
            )

        count_q = select(func.count()).select_from(q.subquery())
        total_r = await self._s.execute(count_q)
        total   = total_r.scalar_one()

        if page is not None and page_size is not None:
            q = q.offset((page - 1) * page_size).limit(page_size)
        r = await self._s.execute(q)
        return list(r.scalars().all()), total

    async def get_existing_admission_nos(self) -> set[str]:
        r = await self._s.execute(select(Student.admission_no))
        return set(r.scalars().all())

    async def bulk_insert(self, students: list[Student]) -> None:
        self._s.add_all(students)
        await self._s.flush()

    async def update(self, student: Student, data: dict) -> Student:
        for k, v in data.items():
            setattr(student, k, v)
        await self._s.flush()
        return student

    async def soft_delete(self, student: Student) -> None:
        student.status = "inactive"
        await self._s.flush()

    async def get_faculty_sections(self, user_id: int) -> list[FacultySection]:
        r = await self._s.execute(
            select(FacultySection).where(FacultySection.user_id == user_id)
        )
        return list(r.scalars().all())
