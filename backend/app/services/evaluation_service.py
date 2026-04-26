from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, func, select

from app.engines.analytics_engine import GradedRow, StudentMeta, compute_analytics
from app.engines.rule_engine import QuestionRow, grade_response
from app.models.orm import ExamPaper, GradedResult, Question, RankAudit, Result
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.alert_repo import AlertRepository
from app.repositories.exam_repo import ExamRepository
from app.repositories.response_repo import ResponseRepository
from app.repositories.student_repo import StudentRepository


def _resolve_question(q_orm: Question, key_type: str) -> QuestionRow:
    """
    Build a QuestionRow with the correct answer resolved for the given key_type.

    BKC: use correct_option_bkc / is_deleted_bkc
    AKC: use correct_option_akc if set, else fall back to BKC values
         use is_deleted_akc     if set, else fall back to is_deleted_bkc
    """
    if key_type == "AKC":
        correct_option = (
            q_orm.correct_option_akc
            if q_orm.correct_option_akc is not None
            else q_orm.correct_option_bkc
        )
        is_deleted = (
            q_orm.is_deleted_akc
            if q_orm.is_deleted_akc is not None
            else q_orm.is_deleted_bkc
        )
    else:  # BKC
        correct_option = q_orm.correct_option_bkc
        is_deleted     = q_orm.is_deleted_bkc

    effective_type = "DELETED" if is_deleted else q_orm.question_type

    return QuestionRow(
        question_type=effective_type,
        positive_marks=q_orm.positive_marks,
        negative_marks=q_orm.negative_marks,
        partial_marks=q_orm.partial_marks,
        correct_option=correct_option,
    )


class EvaluationService:
    """
    Grade responses → compute analytics → run alerts.
    Supports BKC and AKC key types; both results stored in graded_results.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._s              = session
        self._exam_repo      = ExamRepository(session)
        self._resp_repo      = ResponseRepository(session)
        self._student_repo   = StudentRepository(session)
        self._analytics_repo = AnalyticsRepository(session)
        self._alert_repo     = AlertRepository(session)

    async def evaluate(self, exam_id: int, key_type: str = "BKC") -> dict:
        t0 = time.monotonic()

        exam = await self._exam_repo.get_by_id(exam_id)
        if not exam:
            raise KeyError(f"Exam {exam_id} not found")

        if key_type not in ("BKC", "AKC"):
            raise ValueError(f"key_type must be BKC or AKC, got {key_type!r}")

        responses = await self._resp_repo.get_responses_for_exam(exam_id)
        if not responses:
            return {"exam_id": exam_id, "key_type": key_type,
                    "students_graded": 0, "questions_graded": 0, "duration_ms": 0}

        questions_map = {q.id: q for q in await self._exam_repo.get_questions_for_exam(exam_id)}

        # Snapshot ranks before re-grade (for audit log)
        pre_summaries = {
            s.admission_no: s
            for s in await self._analytics_repo.get_exam_summaries(exam_id)
        }

        await self._resp_repo.delete_graded_results(exam_id, key_type)

        graded: list[GradedResult] = []
        for resp in responses:
            q_orm = questions_map.get(resp.question_id)
            if not q_orm:
                continue

            question = _resolve_question(q_orm, key_type)
            result   = grade_response(resp.response_raw, question)

            graded.append(GradedResult(
                admission_no=resp.admission_no,
                question_id=resp.question_id,
                exam_id=exam_id,
                key_type=key_type,
                marks_awarded=result.marks_awarded,
                verdict=result.verdict,
                is_attempted=result.is_attempted,
            ))

        # Every student must receive bonus marks for deleted questions regardless
        # of whether they submitted a response for that question. Students who left
        # a deleted question blank would otherwise be penalised unfairly in ranking.
        deleted_q_ids = {
            q_id for q_id, q_orm in questions_map.items()
            if _resolve_question(q_orm, key_type).question_type == "DELETED"
        }
        if deleted_q_ids:
            responded_pairs = {(gr.admission_no, gr.question_id) for gr in graded}
            all_sids = {gr.admission_no for gr in graded}
            for sid in all_sids:
                for q_id in deleted_q_ids:
                    if (sid, q_id) not in responded_pairs:
                        q_orm = questions_map[q_id]
                        graded.append(GradedResult(
                            admission_no=sid,
                            question_id=q_id,
                            exam_id=exam_id,
                            key_type=key_type,
                            marks_awarded=q_orm.positive_marks,
                            verdict="bonus",
                            is_attempted=False,
                        ))

        await self._resp_repo.bulk_upsert_graded(graded)
        await self._recompute_analytics(exam_id, graded, key_type)
        await self._compute_paper_results(exam_id, key_type)

        # Audit log
        post_summaries = {
            s.admission_no: s
            for s in await self._analytics_repo.get_exam_summaries(exam_id)
        }
        audit = []
        for sid, post in post_summaries.items():
            pre = pre_summaries.get(sid)
            audit.append(RankAudit(
                admission_no=sid, exam_id=exam_id, key_type=key_type,
                rank_before=pre.rank_overall if pre else None,
                rank_after=post.rank_overall,
                marks_before=pre.total_marks if pre else None,
                marks_after=post.total_marks,
            ))
        await self._analytics_repo.log_rank_audit(audit)

        from app.services.alert_service import AlertService
        await AlertService(self._s).run_for_exam(exam_id)

        elapsed = int((time.monotonic() - t0) * 1000)
        return {
            "exam_id":          exam_id,
            "key_type":         key_type,
            "students_graded":  len({r.admission_no for r in graded}),
            "questions_graded": len(graded),
            "duration_ms":      elapsed,
        }

    async def _recompute_analytics(
        self, exam_id: int, graded: list[GradedResult], key_type: str
    ) -> None:
        questions_map = {q.id: q for q in await self._exam_repo.get_questions_for_exam(exam_id)}

        # Full paper totals — denominator is the whole paper, not just what each student attempted
        paper_max_marks: float = sum(q.positive_marks for q in questions_map.values())
        subject_max_marks: dict[str, float] = {}
        for q in questions_map.values():
            subject_max_marks[q.subject] = subject_max_marks.get(q.subject, 0.0) + q.positive_marks

        graded_rows: list[GradedRow] = []
        for gr in graded:
            q_orm = questions_map.get(gr.question_id)
            if not q_orm:
                continue
            graded_rows.append(GradedRow(
                admission_no=gr.admission_no,
                question_id=gr.question_id,
                subject=q_orm.subject,
                topic=q_orm.topic or "",
                marks_awarded=gr.marks_awarded,
                positive_marks=q_orm.positive_marks,
                verdict=gr.verdict,
                is_attempted=gr.is_attempted,
                submitted_at=0.0,
            ))

        all_sids = {gr.admission_no for gr in graded}
        meta: dict[str, StudentMeta] = {}
        for sid in all_sids:
            s = await self._student_repo.get_by_admission_no(sid)
            if s:
                meta[sid] = StudentMeta(
                    admission_no=sid, branch_name=s.branch_name,
                    program_name=s.program_name, section=s.section,
                )

        bundle = compute_analytics(exam_id, graded_rows, meta, paper_max_marks, subject_max_marks)
        await self._analytics_repo.delete_exam_analytics(exam_id)
        await self._analytics_repo.insert_bundle(bundle)

    async def _compute_paper_results(self, exam_id: int, key_type: str) -> None:
        exam = await self._exam_repo.get_by_id(exam_id)
        if not exam:
            return

        await self._s.execute(delete(Result).where(Result.exam_id == exam_id))

        # Authoritative max marks per paper — derived from the question bank, not graded rows
        paper_max: dict[str, float] = {}
        for q in await self._exam_repo.get_questions_for_exam(exam_id):
            ep = await self._s.get(ExamPaper, q.exam_paper_id)
            if ep:
                paper_max[ep.paper_code] = paper_max.get(ep.paper_code, 0.0) + q.positive_marks

        stmt = (
            select(
                GradedResult.admission_no,
                ExamPaper.paper_code,
                func.sum(GradedResult.marks_awarded).label("score"),
            )
            .join(Question,  GradedResult.question_id == Question.id)
            .join(ExamPaper, Question.exam_paper_id == ExamPaper.id)
            .where(
                GradedResult.exam_id  == exam_id,
                GradedResult.key_type == key_type,
            )
            .group_by(GradedResult.admission_no, ExamPaper.paper_code)
        )
        rows = (await self._s.execute(stmt)).all()

        paper_scores: dict[str, dict[str, tuple[float, float]]] = {}
        for admission_no, paper_code, score in rows:
            sc = float(score or 0.0)
            tm = paper_max.get(paper_code, 0.0)
            paper_scores.setdefault(admission_no, {})[paper_code] = (sc, tm)
            self._s.add(Result(
                student_id=admission_no,
                exam_id=exam_id,
                paper_code=paper_code,
                score=sc,
                total_marks=tm,
                result_type="PAPER",
            ))

        if exam.exam_type == "Advanced":
            for admission_no, papers in paper_scores.items():
                self._s.add(Result(
                    student_id=admission_no,
                    exam_id=exam_id,
                    paper_code=None,
                    score=sum(v[0] for v in papers.values()),
                    total_marks=sum(v[1] for v in papers.values()),
                    result_type="CONSOLIDATED",
                ))

        await self._s.flush()

    async def dry_run(self, exam_id: int) -> dict:
        pre   = {s.admission_no: s for s in await self._analytics_repo.get_exam_summaries(exam_id)}
        resps = await self._resp_repo.get_responses_for_exam(exam_id)
        sids  = {r.admission_no for r in resps}
        return {
            "exam_id":           exam_id,
            "students_affected": len(sids),
            "rank_changes": [
                {"admission_no": sid,
                 "current_rank": pre[sid].rank_overall if sid in pre else None}
                for sid in sids
            ],
        }
