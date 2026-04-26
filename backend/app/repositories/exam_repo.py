from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orm import Exam, ExamPaper, Question, Topic


class ExamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── Exam lookups ──────────────────────────────────────────────────────────

    async def get_by_code(self, exam_code: str) -> Exam | None:
        r = await self._s.execute(select(Exam).where(Exam.exam_code == exam_code))
        return r.scalar_one_or_none()

    async def get_by_id(self, exam_id: int) -> Exam | None:
        r = await self._s.execute(select(Exam).where(Exam.id == exam_id))
        return r.scalar_one_or_none()

    async def get_by_id_with_papers(self, exam_id: int) -> Exam | None:
        r = await self._s.execute(
            select(Exam)
            .options(selectinload(Exam.exam_paper_links))
            .where(Exam.id == exam_id)
        )
        return r.scalar_one_or_none()

    async def list_exams(self) -> list[Exam]:
        r = await self._s.execute(
            select(Exam)
            .options(selectinload(Exam.exam_paper_links))
            .order_by(Exam.exam_date.desc().nulls_last())
        )
        return list(r.scalars().all())

    # ── Exam creation (with exam_papers) ──────────────────────────────────────

    async def create_exam(self, exam: Exam, paper_codes: list[str]) -> Exam:
        """Persist exam + its authorized paper links atomically."""
        self._s.add(exam)
        await self._s.flush()
        for pc in paper_codes:
            self._s.add(ExamPaper(exam_id=exam.id, paper_code=pc))
        await self._s.flush()
        await self._s.refresh(exam, attribute_names=["exam_paper_links"])
        return exam

    # ── Authorized papers ─────────────────────────────────────────────────────

    async def get_authorized_papers(self, exam_id: int) -> set[str]:
        """Returns the set of paper codes authorized for an exam (from exam_papers)."""
        r = await self._s.execute(
            select(ExamPaper.paper_code).where(ExamPaper.exam_id == exam_id)
        )
        return set(r.scalars().all())

    # ── get_or_create (used by legacy paths & response uploads) ───────────────

    async def get_or_create_exam(self, exam_code: str) -> Exam:
        exam = await self.get_by_code(exam_code)
        if not exam:
            exam = Exam(exam_code=exam_code)
            self._s.add(exam)
            await self._s.flush()
        return exam

    async def get_exam_paper(self, exam_id: int, paper_code: str) -> ExamPaper | None:
        r = await self._s.execute(
            select(ExamPaper).where(
                ExamPaper.exam_id == exam_id,
                ExamPaper.paper_code == paper_code,
            )
        )
        return r.scalar_one_or_none()

    # ── Question helpers ──────────────────────────────────────────────────────

    async def get_questions_for_paper(
        self, exam_id: int, paper_code: str
    ) -> list[Question]:
        r = await self._s.execute(
            select(Question)
            .join(ExamPaper, Question.exam_paper_id == ExamPaper.id)
            .where(ExamPaper.exam_id == exam_id, ExamPaper.paper_code == paper_code)
        )
        return list(r.scalars().all())

    async def get_questions_for_exam(self, exam_id: int) -> list[Question]:
        r = await self._s.execute(
            select(Question)
            .join(ExamPaper, Question.exam_paper_id == ExamPaper.id)
            .where(ExamPaper.exam_id == exam_id)
        )
        return list(r.scalars().all())

    async def get_question_by_key(
        self, exam_code: str, paper_code: str, question_no: int
    ) -> Question | None:
        r = await self._s.execute(
            select(Question)
            .join(ExamPaper, Question.exam_paper_id == ExamPaper.id)
            .join(Exam, ExamPaper.exam_id == Exam.id)
            .where(
                Exam.exam_code == exam_code,
                ExamPaper.paper_code == paper_code,
                Question.question_no == question_no,
            )
        )
        return r.scalar_one_or_none()

    async def get_valid_question_keys(
        self, exam_code: str
    ) -> set[tuple[str, str, int]]:
        r = await self._s.execute(
            select(Exam.exam_code, ExamPaper.paper_code, Question.question_no)
            .join(ExamPaper, Question.exam_paper_id == ExamPaper.id)
            .join(Exam, ExamPaper.exam_id == Exam.id)
            .where(Exam.exam_code == exam_code)
        )
        return {(row[0], row[1], row[2]) for row in r.all()}

    async def get_question_types(
        self, exam_code: str
    ) -> dict[tuple[str, str, int], str]:
        r = await self._s.execute(
            select(Exam.exam_code, ExamPaper.paper_code, Question.question_no, Question.question_type)
            .join(ExamPaper, Question.exam_paper_id == ExamPaper.id)
            .join(Exam, ExamPaper.exam_id == Exam.id)
            .where(Exam.exam_code == exam_code)
        )
        return {(row[0], row[1], row[2]): row[3] for row in r.all()}

    async def get_valid_topics(self) -> set[str]:
        r = await self._s.execute(select(Topic.name))
        return set(r.scalars().all())

    async def get_topic_by_name(self, name: str, subject: str) -> Topic | None:
        r = await self._s.execute(
            select(Topic).where(Topic.name == name, Topic.subject == subject)
        )
        return r.scalar_one_or_none()
