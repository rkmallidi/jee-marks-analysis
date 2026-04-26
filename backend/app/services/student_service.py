from __future__ import annotations

import io
from typing import Literal

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Student
from app.repositories.student_repo import StudentRepository
from app.schemas.api import StudentCreate, StudentUpdate


class StudentService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = StudentRepository(session)

    async def list_students(
        self,
        branch_name:      str | None,
        program_name:     str | None,
        section:          str | None,
        status:           str | None,
        allowed_sections: list[str] | None,
        search:           str | None = None,
        page:             int = 1,
        page_size:        int = 50,
        student_class:    str | None = None,
        dean:             str | None = None,
    ) -> tuple[list[Student], int]:
        return await self._repo.list_students(
            branch_name, program_name, section, status,
            allowed_sections, search, page, page_size,
            student_class=student_class, dean=dean,
        )

    async def export_students(
        self,
        branch_name:      str | None,
        program_name:     str | None,
        section:          str | None,
        status:           str | None,
        allowed_sections: list[str] | None,
        search:           str | None = None,
        format:           Literal["csv", "xlsx"] = "csv",
    ) -> tuple[bytes, str, str]:
        students, _ = await self._repo.list_students(
            branch_name, program_name, section, status,
            allowed_sections, search, page=None, page_size=None,
        )
        df = pd.DataFrame([
            {
                "Admission No":  s.admission_no,
                "Name":          s.name,
                "Branch":        s.branch_name,
                "Program":       s.program_name,
                "Class":         s.student_class,
                "Section":       s.section,
                "Dean":          s.dean,
                "Status":        s.status,
            }
            for s in students
        ])
        buffer = io.BytesIO()
        if format == "csv":
            df.to_csv(buffer, index=False)
            mime = "text/csv"
            ext = "csv"
        else:
            df.to_excel(buffer, index=False, engine="openpyxl")
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        buffer.seek(0)
        return buffer.getvalue(), f"students.{ext}", mime

    async def get_student(self, admission_no: str) -> Student:
        student = await self._repo.get_by_admission_no(admission_no)
        if not student:
            raise KeyError(f"Student {admission_no!r} not found")
        return student

    async def create_student(self, data: StudentCreate) -> Student:
        if await self._repo.get_by_admission_no(data.admission_no):
            raise ValueError(f"admission_no {data.admission_no!r} already exists")
        student = Student(
            admission_no=data.admission_no,
            name=data.name,
            branch_name=data.branch_name,
            program_name=data.program_name,
            student_class=data.student_class,
            section=data.section,
            dean=data.dean,
            status=data.status,
        )
        self._repo._s.add(student)
        await self._repo._s.flush()
        return student

    async def update_student(self, admission_no: str, data: StudentUpdate) -> Student:
        student = await self.get_student(admission_no)
        return await self._repo.update(student, data.model_dump(exclude_none=True))

    async def delete_student(self, admission_no: str) -> None:
        student = await self.get_student(admission_no)
        await self._repo.soft_delete(student)

    async def get_allowed_sections_for_faculty(self, user_id: int) -> list[str]:
        fs_list = await self._repo.get_faculty_sections(user_id)
        return [fs.section for fs in fs_list]

    async def get_filter_options(self) -> dict:
        """Get distinct values for filter dropdowns"""
        return {
            "branches": await self._repo.get_distinct_branches(),
            "programs": await self._repo.get_distinct_programs(),
            "classes": await self._repo.get_distinct_classes(),
            "sections": await self._repo.get_distinct_sections(),
            "deans": await self._repo.get_distinct_deans(),
        }
