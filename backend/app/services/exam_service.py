from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Exam, ExamPaper
from app.repositories.exam_repo import ExamRepository
from app.schemas.api import ExamCreate, ExamOut, ExamUpdate

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
            program_name=data.program_name or None,
            student_class=data.student_class or None,
        )
        paper_codes = _PAPERS[data.exam_type]
        await self._repo.create_exam(exam, paper_codes)
        return ExamOut.model_validate(exam)

    async def update_exam(self, exam_id: int, data: ExamUpdate) -> ExamOut:
        exam = await self._repo.get_by_id_with_papers(exam_id)
        if not exam:
            raise ValueError(f"Exam {exam_id} not found")
        if data.title         is not None: exam.title         = data.title or None
        if data.exam_date     is not None: exam.exam_date     = data.exam_date
        if data.program_name  is not None: exam.program_name  = data.program_name or None
        if data.student_class is not None: exam.student_class = data.student_class or None
        if data.exam_type is not None and data.exam_type != exam.exam_type:
            exam.exam_type = data.exam_type
            existing = {ep.paper_code for ep in exam.exam_paper_links}
            for pc in _PAPERS[data.exam_type]:
                if pc not in existing:
                    self._repo._s.add(ExamPaper(exam_id=exam.id, paper_code=pc))
        await self._repo._s.flush()
        await self._repo._s.refresh(exam, attribute_names=["exam_paper_links"])
        return ExamOut.model_validate(exam)

    async def list_exams(self) -> list[ExamOut]:
        exams = await self._repo.list_exams()
        return [ExamOut.model_validate(e) for e in exams]

    async def get_exam_papers(self, exam_id: int) -> list[str]:
        papers = await self._repo.get_authorized_papers(exam_id)
        return sorted(papers)
