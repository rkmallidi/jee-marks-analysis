from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import GradedResult, OmrResponse


class ResponseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def bulk_insert_responses(self, responses: list[OmrResponse]) -> None:
        self._s.add_all(responses)
        await self._s.flush()

    async def get_responses_for_exam(self, exam_id: int) -> list[OmrResponse]:
        r = await self._s.execute(
            select(OmrResponse).where(OmrResponse.exam_id == exam_id)
        )
        return list(r.scalars().all())

    async def delete_graded_results(self, exam_id: int, key_type: str) -> None:
        await self._s.execute(
            delete(GradedResult).where(
                GradedResult.exam_id  == exam_id,
                GradedResult.key_type == key_type,
            )
        )

    async def bulk_upsert_graded(self, results: list[GradedResult]) -> None:
        """
        PostgreSQL UPSERT: insert or update on (admission_no, question_id, key_type).
        Uses raw SQL for bulk efficiency rather than individual ORM flushes.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from app.models.orm import GradedResult as GRModel

        if not results:
            return

        # Deduplicate by constraint key — keeps last value for each unique tuple,
        # guarding against duplicate rows in omr_responses (e.g. re-uploaded CSVs).
        seen: dict[tuple, dict] = {}
        for r in results:
            key = (r.admission_no, r.question_id, r.key_type)
            seen[key] = {
                "admission_no":  r.admission_no,
                "question_id":   r.question_id,
                "exam_id":       r.exam_id,
                "key_type":      r.key_type,
                "marks_awarded": r.marks_awarded,
                "verdict":       r.verdict,
                "is_attempted":  r.is_attempted,
            }
        rows = list(seen.values())

        stmt = pg_insert(GRModel).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["admission_no", "question_id", "key_type"],
            set_={
                "marks_awarded": stmt.excluded.marks_awarded,
                "verdict":       stmt.excluded.verdict,
                "is_attempted":  stmt.excluded.is_attempted,
            },
        )
        await self._s.execute(stmt)

    async def get_graded_for_exam(self, exam_id: int) -> list[GradedResult]:
        r = await self._s.execute(
            select(GradedResult).where(GradedResult.exam_id == exam_id)
        )
        return list(r.scalars().all())
