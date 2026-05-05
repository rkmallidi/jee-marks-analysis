from __future__ import annotations

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.analytics_engine import AnalyticsBundle
from app.models.orm import (
    AggregateSummary,
    Exam,
    RankAudit,
    RankSummary,
    Result,
    RollingAverage,
    StudentExamSummary,
    StudentSubjectSummary,
    StudentTopicSummary,
)


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def delete_exam_analytics(self, exam_id: int) -> None:
        for model in (
            StudentExamSummary,
            StudentSubjectSummary,
            StudentTopicSummary,
            RankSummary,
            AggregateSummary,
        ):
            await self._s.execute(
                delete(model).where(model.exam_id == exam_id)  # type: ignore[attr-defined]
            )

    async def insert_bundle(self, bundle: AnalyticsBundle) -> None:
        """Bulk-insert all analytics rows using PostgreSQL multi-row INSERT."""

        if bundle.exam_summaries:
            rows = [
                {k: v for k, v in r.__dict__.items() if not k.startswith("_")}
                for r in bundle.exam_summaries
            ]
            await self._s.execute(pg_insert(StudentExamSummary).values(rows))

        if bundle.subject_summaries:
            rows = [
                {k: v for k, v in r.__dict__.items() if not k.startswith("_")}
                for r in bundle.subject_summaries
            ]
            await self._s.execute(pg_insert(StudentSubjectSummary).values(rows))

        if bundle.topic_summaries:
            rows = [
                {k: v for k, v in r.__dict__.items() if not k.startswith("_")}
                for r in bundle.topic_summaries
            ]
            await self._s.execute(pg_insert(StudentTopicSummary).values(rows))

        if bundle.rank_summaries:
            rows = [
                {k: v for k, v in r.__dict__.items() if not k.startswith("_")}
                for r in bundle.rank_summaries
            ]
            await self._s.execute(pg_insert(RankSummary).values(rows))

        if bundle.agg_summaries:
            rows = [
                {k: v for k, v in r.__dict__.items() if not k.startswith("_")}
                for r in bundle.agg_summaries
            ]
            await self._s.execute(pg_insert(AggregateSummary).values(rows))

        await self._s.flush()

    async def get_exam_summaries(self, exam_id: int) -> list[StudentExamSummary]:
        r = await self._s.execute(
            select(StudentExamSummary).where(StudentExamSummary.exam_id == exam_id)
        )
        return list(r.scalars().all())

    async def get_student_exam_summary(
        self, admission_no: str, exam_id: int
    ) -> StudentExamSummary | None:
        r = await self._s.execute(
            select(StudentExamSummary).where(
                StudentExamSummary.admission_no == admission_no,
                StudentExamSummary.exam_id == exam_id,
            )
        )
        return r.scalar_one_or_none()

    async def get_student_history(
        self, admission_no: str, limit: int = 10
    ) -> list[StudentExamSummary]:
        r = await self._s.execute(
            select(StudentExamSummary)
            .where(StudentExamSummary.admission_no == admission_no)
            .order_by(StudentExamSummary.exam_id.desc())
            .limit(limit)
        )
        return list(r.scalars().all())

    async def get_student_history_by_type(
        self, admission_no: str, exam_type: str
    ) -> list[StudentExamSummary]:
        """All exam summaries for a student filtered to a specific exam type, oldest-first."""
        r = await self._s.execute(
            select(StudentExamSummary)
            .join(Exam, StudentExamSummary.exam_id == Exam.id)
            .where(
                StudentExamSummary.admission_no == admission_no,
                Exam.exam_type == exam_type,
            )
            .order_by(StudentExamSummary.exam_id.asc())
        )
        return list(r.scalars().all())

    async def get_rolling_averages(self, admission_no: str) -> list[RollingAverage]:
        r = await self._s.execute(
            select(RollingAverage).where(RollingAverage.admission_no == admission_no)
        )
        return list(r.scalars().all())

    async def get_aggregate_for_exam(
        self,
        exam_id:     int,
        scope:       str | None = None,
        scope_value: str | None = None,
    ) -> list[AggregateSummary]:
        q = select(AggregateSummary).where(AggregateSummary.exam_id == exam_id)
        if scope:
            q = q.where(AggregateSummary.scope == scope)
        if scope_value:
            q = q.where(AggregateSummary.scope_value == scope_value)
        r = await self._s.execute(q)
        return list(r.scalars().all())

    async def get_topic_summaries_for_exam(
        self,
        exam_id:       int,
        admission_nos: list[str] | None = None,
    ) -> list[StudentTopicSummary]:
        q = select(StudentTopicSummary).where(StudentTopicSummary.exam_id == exam_id)
        if admission_nos is not None:
            q = q.where(StudentTopicSummary.admission_no.in_(admission_nos))
        r = await self._s.execute(q)
        return list(r.scalars().all())

    async def get_student_topic_history(
        self, admission_no: str
    ) -> list[StudentTopicSummary]:
        r = await self._s.execute(
            select(StudentTopicSummary)
            .where(StudentTopicSummary.admission_no == admission_no)
            .order_by(StudentTopicSummary.exam_id.desc())
        )
        return list(r.scalars().all())

    async def get_subject_summaries_for_exam(
        self, exam_id: int, admission_nos: list[str] | None = None
    ) -> list[StudentSubjectSummary]:
        q = select(StudentSubjectSummary).where(StudentSubjectSummary.exam_id == exam_id)
        if admission_nos is not None:
            q = q.where(StudentSubjectSummary.admission_no.in_(admission_nos))
        r = await self._s.execute(q)
        return list(r.scalars().all())

    async def log_rank_audit(self, entries: list[RankAudit]) -> None:
        self._s.add_all(entries)
        await self._s.flush()

    async def get_exam_total_benchmarks(self, exam_id: int) -> dict:
        r = await self._s.execute(
            select(
                func.avg(StudentExamSummary.total_marks).label("avg_total"),
                func.max(StudentExamSummary.total_marks).label("max_total"),
            ).where(StudentExamSummary.exam_id == exam_id)
        )
        row = r.one_or_none()
        if not row or row.avg_total is None:
            return {"avg_total": None, "max_total": None}
        return {
            "avg_total": round(float(row.avg_total), 2),
            "max_total": float(row.max_total),
        }

    async def get_subject_toppers(self, exam_id: int) -> dict[str, float]:
        r = await self._s.execute(
            select(StudentSubjectSummary.subject, func.max(StudentSubjectSummary.marks).label("top"))
            .where(StudentSubjectSummary.exam_id == exam_id)
            .group_by(StudentSubjectSummary.subject)
        )
        return {row.subject: float(row.top) for row in r.all()}

    async def get_branch_aggregates(self, exam_id: int) -> dict[str, list[dict]]:
        """Return aggregate summary rows grouped by branch_name scope."""
        rows = await self.get_aggregate_for_exam(exam_id, scope="branch")
        result: dict[str, list[dict]] = {}
        for row in rows:
            result.setdefault(row.scope_value, []).append({
                "subject":    row.subject,
                "avg":        row.avg,
                "median":     row.median,
                "n_students": row.n_students,
            })
        return result

    # ── PostgreSQL CTE-powered leaderboard ─────────────────────────────────────
    async def get_leaderboard(
        self, exam_id: int, limit: int = 10, offset: int = 0,
        allowed_nos: list[str] | None = None,
    ) -> list[dict]:
        """
        Uses a PostgreSQL CTE with DENSE_RANK() window function to return
        the top-N students for a given exam with their rank computed in-DB.
        When allowed_nos is provided, ranks are recomputed within that set.
        """
        scope_filter = "AND ses.admission_no = ANY(:allowed_nos)" if allowed_nos is not None else ""
        sql = text(f"""
            WITH ranked AS (
                SELECT
                    ses.admission_no,
                    s.name,
                    s.branch_name,
                    s.program_name,
                    s.student_class,
                    s.section,
                    ses.total_marks,
                    ses.negative_marks,
                    ses.percentile_overall,
                    ROUND(
                        (ses.correct_count::float / NULLIF(ses.attempted_count, 0) * 100)::numeric,
                        2
                    )::float AS accuracy_pct,
                    DENSE_RANK() OVER (
                        ORDER BY ses.total_marks DESC,
                            (ses.correct_count::float / NULLIF(ses.attempted_count, 0)) DESC,
                            ses.negative_marks ASC
                    ) AS rank
                FROM student_exam_summary ses
                JOIN students s ON s.admission_no = ses.admission_no
                WHERE ses.exam_id = :exam_id {scope_filter}
            ),
            with_subjects AS (
                SELECT
                    ranked.admission_no,
                    ranked.name,
                    ranked.branch_name,
                    ranked.program_name,
                    ranked.student_class,
                    ranked.section,
                    ranked.total_marks,
                    ranked.negative_marks,
                    ranked.percentile_overall,
                    ranked.accuracy_pct,
                    ranked.rank,
                    COALESCE(
                        (SELECT marks FROM student_subject_summary sss2 
                         WHERE sss2.exam_id = :exam_id AND sss2.admission_no = ranked.admission_no 
                         AND sss2.subject = 'Physics'),
                        0.0
                    ) AS physics_marks,
                    COALESCE(
                        (SELECT marks FROM student_subject_summary sss2 
                         WHERE sss2.exam_id = :exam_id AND sss2.admission_no = ranked.admission_no 
                         AND sss2.subject = 'Chemistry'),
                        0.0
                    ) AS chemistry_marks,
                    COALESCE(
                        (SELECT marks FROM student_subject_summary sss2 
                         WHERE sss2.exam_id = :exam_id AND sss2.admission_no = ranked.admission_no 
                         AND sss2.subject = 'Maths'),
                        0.0
                    ) AS maths_marks
                FROM ranked
            )
            SELECT
                rank,
                admission_no,
                name,
                branch_name,
                program_name,
                student_class,
                section,
                total_marks,
                physics_marks,
                chemistry_marks,
                maths_marks,
                accuracy_pct,
                negative_marks,
                COALESCE(percentile_overall, 0.0) AS percentile
            FROM with_subjects
            ORDER BY rank
            LIMIT :limit OFFSET :offset
        """)
        params: dict = {"exam_id": exam_id, "limit": limit, "offset": offset}
        if allowed_nos is not None:
            params["allowed_nos"] = allowed_nos
        r = await self._s.execute(sql, params)
        return [dict(row._mapping) for row in r.all()]

    async def get_percentile_distribution(
        self, exam_id: int, allowed_nos: list[str] | None = None
    ) -> list[dict]:
        """Score distribution histogram. Scoped to allowed_nos when provided."""
        scope_filter = "AND admission_no = ANY(:allowed_nos)" if allowed_nos is not None else ""
        sql = text(f"""
            SELECT
                WIDTH_BUCKET(total_marks, min_s, max_s + 0.001, 10) AS bucket,
                MIN(total_marks) AS bucket_min,
                MAX(total_marks) AS bucket_max,
                COUNT(*) AS student_count
            FROM student_exam_summary,
                 (SELECT MIN(total_marks) AS min_s, MAX(total_marks) AS max_s
                  FROM student_exam_summary
                  WHERE exam_id = :exam_id {scope_filter}) bounds
            WHERE exam_id = :exam_id {scope_filter}
            GROUP BY bucket
            ORDER BY bucket
        """)
        params: dict = {"exam_id": exam_id}
        if allowed_nos is not None:
            params["allowed_nos"] = allowed_nos
        r = await self._s.execute(sql, params)
        return [dict(row._mapping) for row in r.all()]

    async def get_exam_overall_stats(self, exam_id: int) -> dict:
        sql = text("""
            SELECT
                MIN(total_marks)                                      AS min_total,
                MAX(total_marks)                                      AS max_total,
                COUNT(*)                                              AS total_students,
                COUNT(CASE WHEN percentage >= 35 THEN 1 END)         AS pass_count
            FROM student_exam_summary
            WHERE exam_id = :exam_id
        """)
        r   = await self._s.execute(sql, {"exam_id": exam_id})
        row = r.mappings().one_or_none()
        if not row or not row["total_students"]:
            return {"min_total": 0.0, "max_total": 0.0, "total_students": 0, "pass_rate_pct": 0.0}
        total = row["total_students"]
        return {
            "min_total":      float(row["min_total"] or 0),
            "max_total":      float(row["max_total"] or 0),
            "total_students": total,
            "pass_rate_pct":  round((row["pass_count"] or 0) / total * 100, 1),
        }

    async def get_exam_stats_scoped(
        self, exam_id: int, admission_nos: list[str] | None
    ) -> dict:
        """Compute live exam stats for a scoped set of students (or all if None)."""
        q = select(StudentExamSummary).where(StudentExamSummary.exam_id == exam_id)
        if admission_nos is not None:
            q = q.where(StudentExamSummary.admission_no.in_(admission_nos))
        r    = await self._s.execute(q)
        rows = list(r.scalars().all())
        if not rows:
            return {"avg_total": 0.0, "max_total": 0.0, "min_total": 0.0,
                    "total_students": 0, "pass_rate_pct": 0.0}
        total      = len(rows)
        marks_list = [row.total_marks for row in rows]
        pass_count = sum(1 for row in rows if (row.percentage or 0) >= 35)
        return {
            "avg_total":      round(sum(marks_list) / total, 2),
            "max_total":      float(max(marks_list)),
            "min_total":      float(min(marks_list)),
            "total_students": total,
            "pass_rate_pct":  round(pass_count / total * 100, 1),
        }

    async def get_paper_results_for_student(
        self, admission_no: str, exam_id: int
    ) -> dict[str, dict]:
        """Returns {paper_code: {score, total_marks}} for PAPER-type results only."""
        r = await self._s.execute(
            select(Result).where(
                Result.student_id == admission_no,
                Result.exam_id    == exam_id,
                Result.result_type == "PAPER",
            )
        )
        return {
            row.paper_code: {"score": row.score, "total_marks": row.total_marks}
            for row in r.scalars().all()
            if row.paper_code is not None
        }

    async def get_paper_subject_data_for_student(
        self, admission_no: str, exam_id: int, key_type: str = "BKC"
    ) -> dict[str, dict[str, dict]]:
        """Returns {paper_code: {subject: {marks, max_marks, correct, partial, wrong, blank, neg}}}

        marks and max_marks include bonus (deleted-question) contributions so that
        per-paper subject marks sum correctly to the paper total stored in the Result table.
        Correct/wrong/partial/blank counts exclude bonus rows.
        """
        sql = text("""
            WITH auth_max AS (
                -- Authoritative max marks per (paper, subject) from the question bank,
                -- independent of whether the student has response records for every question.
                SELECT ep.paper_code, q.subject, SUM(q.positive_marks) AS max_marks
                FROM   questions   q
                JOIN   exam_papers ep ON q.exam_paper_id = ep.id
                WHERE  ep.exam_id = :exam_id
                GROUP  BY ep.paper_code, q.subject
            ),
            student_data AS (
                -- Per-student (paper, subject) aggregates including bonus marks in the score.
                -- Correct/wrong/partial/blank counts exclude bonus rows.
                SELECT
                    ep.paper_code,
                    q.subject,
                    COALESCE(SUM(gr.marks_awarded), 0)                                                      AS marks,
                    COUNT(CASE WHEN gr.verdict = 'correct'                            THEN 1 END)            AS correct_count,
                    COUNT(CASE WHEN gr.verdict = 'partial'                            THEN 1 END)            AS partial_count,
                    COUNT(CASE WHEN gr.verdict = 'wrong'                              THEN 1 END)            AS wrong_count,
                    COUNT(CASE WHEN gr.is_attempted = FALSE AND gr.verdict != 'bonus' THEN 1 END)            AS blank_count,
                    COALESCE(SUM(CASE WHEN gr.marks_awarded < 0 THEN ABS(gr.marks_awarded) ELSE 0 END), 0)  AS negative_marks
                FROM graded_results gr
                JOIN questions   q  ON gr.question_id  = q.id
                JOIN exam_papers ep ON q.exam_paper_id = ep.id
                WHERE gr.admission_no = :admission_no
                  AND gr.exam_id      = :exam_id
                  AND gr.key_type     = :key_type
                GROUP BY ep.paper_code, q.subject
            )
            SELECT
                sd.paper_code,
                sd.subject,
                sd.marks,
                am.max_marks,
                sd.correct_count,
                sd.partial_count,
                sd.wrong_count,
                sd.blank_count,
                sd.negative_marks
            FROM student_data sd
            JOIN auth_max am ON am.paper_code = sd.paper_code AND am.subject = sd.subject
        """)
        r = await self._s.execute(sql, {
            "admission_no": admission_no,
            "exam_id":      exam_id,
            "key_type":     key_type,
        })
        result: dict[str, dict[str, dict]] = {}
        for row in r.mappings().all():
            paper   = row["paper_code"]
            subject = row["subject"]
            result.setdefault(paper, {})[subject] = {
                "marks":     float(row["marks"]         or 0),
                "max_marks": float(row["max_marks"]     or 0),
                "correct":   int(row["correct_count"]   or 0),
                "partial":   int(row["partial_count"]   or 0),
                "wrong":     int(row["wrong_count"]     or 0),
                "blank":     int(row["blank_count"]     or 0),
                "neg":       float(row["negative_marks"] or 0),
            }
        return result

    async def get_paper_subject_benchmarks(
        self, exam_id: int, key_type: str = "BKC"
    ) -> dict[str, dict[str, dict]]:
        """Returns {paper_code: {subject: {avg, top}, '_total': {avg, top}}} across all students.

        The special '_total' key holds the paper-level (all subjects combined) avg and top score.
        """
        sql = text("""
            WITH sps AS (
                SELECT
                    gr.admission_no,
                    ep.paper_code,
                    q.subject,
                    SUM(gr.marks_awarded) AS marks
                FROM graded_results gr
                JOIN questions   q  ON gr.question_id  = q.id
                JOIN exam_papers ep ON q.exam_paper_id = ep.id
                WHERE gr.exam_id  = :exam_id
                  AND gr.key_type = :key_type
                GROUP BY gr.admission_no, ep.paper_code, q.subject
            ),
            paper_totals AS (
                SELECT admission_no, paper_code, SUM(marks) AS marks
                FROM sps
                GROUP BY admission_no, paper_code
            )
            SELECT paper_code, subject,
                   ROUND(AVG(marks)::numeric, 2) AS avg_marks,
                   MAX(marks)                    AS top_marks
            FROM sps
            GROUP BY paper_code, subject
            UNION ALL
            SELECT paper_code, '_total',
                   ROUND(AVG(marks)::numeric, 2),
                   MAX(marks)
            FROM paper_totals
            GROUP BY paper_code
        """)
        r = await self._s.execute(sql, {"exam_id": exam_id, "key_type": key_type})
        result: dict[str, dict[str, dict]] = {}
        for row in r.mappings().all():
            paper   = row["paper_code"]
            subject = row["subject"]
            result.setdefault(paper, {})[subject] = {
                "avg": float(row["avg_marks"] or 0),
                "top": float(row["top_marks"] or 0),
            }
        return result

    async def get_paper_topic_data_for_student(
        self, admission_no: str, exam_id: int, key_type: str = "BKC"
    ) -> dict[str, list[dict]]:
        """Returns {paper_code: [{topic, subject, accuracy, attempted}]} for a student."""
        sql = text("""
            SELECT
                ep.paper_code,
                q.subject,
                q.topic,
                COUNT(CASE WHEN gr.is_attempted = TRUE AND gr.verdict != 'bonus' THEN 1 END) AS attempted,
                COUNT(CASE WHEN gr.verdict = 'correct'                           THEN 1 END) AS correct_count
            FROM graded_results gr
            JOIN questions   q  ON gr.question_id  = q.id
            JOIN exam_papers ep ON q.exam_paper_id = ep.id
            WHERE gr.admission_no = :admission_no
              AND gr.exam_id      = :exam_id
              AND gr.key_type     = :key_type
            GROUP BY ep.paper_code, q.subject, q.topic
        """)
        r = await self._s.execute(sql, {
            "admission_no": admission_no,
            "exam_id":      exam_id,
            "key_type":     key_type,
        })
        result: dict[str, list[dict]] = {}
        for row in r.mappings().all():
            paper = row["paper_code"]
            att   = int(row["attempted"]     or 0)
            corr  = int(row["correct_count"] or 0)
            result.setdefault(paper, []).append({
                "topic":    row["topic"],
                "subject":  row["subject"],
                "accuracy": corr / att if att > 0 else 0.0,
                "attempted": att,
            })
        return result

    async def get_student_exam_responses(
        self, admission_no: str, exam_id: int
    ) -> list[dict]:
        """Per-question response table: student answer + BKC/AKC grading side by side."""
        sql = text("""
            SELECT
                q.question_no,
                ep.paper_code,
                q.subject,
                q.topic,
                q.sub_topic,
                q.question_type,
                q.positive_marks,
                q.negative_marks,
                q.correct_option_bkc,
                q.is_deleted_bkc,
                q.correct_option_akc,
                q.is_deleted_akc,
                omr.response_raw,
                gr_bkc.verdict       AS verdict_bkc,
                gr_bkc.marks_awarded AS marks_bkc,
                gr_akc.verdict       AS verdict_akc,
                gr_akc.marks_awarded AS marks_akc
            FROM questions q
            JOIN exam_papers ep ON q.exam_paper_id = ep.id
            LEFT JOIN omr_responses omr
                ON omr.question_id   = q.id
               AND omr.admission_no  = :admission_no
            LEFT JOIN graded_results gr_bkc
                ON gr_bkc.question_id   = q.id
               AND gr_bkc.admission_no  = :admission_no
               AND gr_bkc.exam_id       = :exam_id
               AND gr_bkc.key_type      = 'BKC'
            LEFT JOIN graded_results gr_akc
                ON gr_akc.question_id   = q.id
               AND gr_akc.admission_no  = :admission_no
               AND gr_akc.exam_id       = :exam_id
               AND gr_akc.key_type      = 'AKC'
            WHERE ep.exam_id = :exam_id
            ORDER BY ep.paper_code, q.question_no
        """)
        r = await self._s.execute(sql, {"admission_no": admission_no, "exam_id": exam_id})
        return [
            {
                "question_no":    row["question_no"],
                "paper_code":     row["paper_code"],
                "subject":        row["subject"],
                "topic":          row["topic"],
                "sub_topic":      row["sub_topic"],
                "question_type":  row["question_type"],
                "positive_marks": float(row["positive_marks"] or 0),
                "negative_marks": float(row["negative_marks"] or 0),
                "correct_bkc":    row["correct_option_bkc"],
                "is_deleted_bkc": bool(row["is_deleted_bkc"]),
                "correct_akc":    row["correct_option_akc"],
                "is_deleted_akc": row["is_deleted_akc"],
                "response":       row["response_raw"] or "",
                "verdict_bkc":    row["verdict_bkc"] or "not_graded",
                "marks_bkc":      float(row["marks_bkc"]) if row["marks_bkc"] is not None else None,
                "verdict_akc":    row["verdict_akc"],
                "marks_akc":      float(row["marks_akc"]) if row["marks_akc"] is not None else None,
            }
            for row in r.mappings().all()
        ]
