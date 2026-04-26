from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Exam
from app.repositories.exam_repo import ExamRepository
from app.schemas.api import ExamCreate, ExamOut

_PAPERS: dict[str, list[str]] = {
    "Mains":    ["P1"],
    "Advanced": ["P1", "P2"],
}


class ExamService:
    def __init__(self, session: AsyncSession) -> None:
        self._s    = session
        self._repo = ExamRepository(session)

    async def create_exam(self, data: ExamCreate) -> ExamOut:
        existing = await self._repo.get_by_code(data.exam_code)
        if existing:
            raise ValueError(f"Exam code '{data.exam_code}' already exists")

        exam = Exam(
            exam_code=data.exam_code,
            title=data.title,
            exam_date=data.exam_date,
            exam_type=data.exam_type,
        )
        paper_codes = _PAPERS[data.exam_type]
        await self._repo.create_exam(exam, paper_codes)
        return ExamOut.model_validate(exam)

    async def list_exams(self) -> list[ExamOut]:
        exams = await self._repo.list_exams()
        return [ExamOut.model_validate(e) for e in exams]

    async def get_exam_papers(self, exam_id: int) -> list[str]:
        papers = await self._repo.get_authorized_papers(exam_id)
        return sorted(papers)
