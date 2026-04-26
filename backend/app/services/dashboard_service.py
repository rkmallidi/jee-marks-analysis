from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.alert_repo import AlertRepository
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.exam_repo import ExamRepository
from app.repositories.student_repo import StudentRepository


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._analytics     = AnalyticsRepository(session)
        self._exam_repo     = ExamRepository(session)
        self._student_repo  = StudentRepository(session)
        self._alert_repo    = AlertRepository(session)

    # ── D1 Overall ─────────────────────────────────────────────────────────────

    async def get_overall(self, exam_id: int) -> dict | None:
        exam = await self._exam_repo.get_by_id(exam_id)
        if not exam:
            return None

        agg           = await self._analytics.get_aggregate_for_exam(exam_id, "overall", "all")
        physics_avg   = next((a.avg for a in agg if a.subject == "Physics"),     0.0) or 0.0
        chemistry_avg = next((a.avg for a in agg if a.subject == "Chemistry"),   0.0) or 0.0
        math_avg      = next((a.avg for a in agg if a.subject == "Mathematics"), 0.0) or 0.0
        total_avg     = round(sum(a.avg or 0 for a in agg), 2)

        stats = await self._analytics.get_exam_overall_stats(exam_id)

        branch_agg        = await self._analytics.get_branch_aggregates(exam_id)
        branch_comparison = [
            {
                "branch":        bname,
                "avg_total":     round(sum(r["avg"] or 0 for r in rows), 2),
                "student_count": max((r["n_students"] or 0 for r in rows), default=0),
            }
            for bname, rows in branch_agg.items()
        ]

        leaderboard  = await self._analytics.get_leaderboard(exam_id, limit=10)
        top_students = [
            {
                "rank":         r["rank"],
                "name":         r["name"],
                "admission_no": r["admission_no"],
                "total":        r["total_marks"],
            }
            for r in leaderboard
        ]

        dist      = await self._analytics.get_percentile_distribution(exam_id)
        histogram = [
            {
                "bucket_start": r["bucket_min"],
                "bucket_end":   r["bucket_max"],
                "count":        r["student_count"],
            }
            for r in dist
        ]

        return {
            "exam_name":         exam.exam_code,
            "exam_date":         exam.exam_date.isoformat() if exam.exam_date else None,
            "total_students":    stats["total_students"],
            "avg_total":         total_avg,
            "avg_physics":       round(physics_avg, 2),
            "avg_chemistry":     round(chemistry_avg, 2),
            "avg_maths":         round(math_avg, 2),
            "max_total":         stats["max_total"],
            "min_total":         stats["min_total"],
            "pass_rate_pct":     stats["pass_rate_pct"],
            "branch_comparison": branch_comparison,
            "top_students":      top_students,
            "histogram":         histogram,
        }

    async def get_exam_trend(self, exam_id: int) -> list[dict]:
        all_exams    = await self._exam_repo.list_exams()  # desc by date
        chronological = list(reversed(all_exams))
        idx           = next((i for i, e in enumerate(chronological) if e.id == exam_id), None)
        subset        = chronological[: (idx + 1) if idx is not None else len(chronological)]

        trend = []
        for exam in subset:
            agg = await self._analytics.get_aggregate_for_exam(exam.id, "overall", "all")
            if not agg:
                continue
            physics_avg   = next((a.avg for a in agg if a.subject == "Physics"),     0.0) or 0.0
            chemistry_avg = next((a.avg for a in agg if a.subject == "Chemistry"),   0.0) or 0.0
            math_avg      = next((a.avg for a in agg if a.subject == "Mathematics"), 0.0) or 0.0
            n_students    = max((a.n_students or 0 for a in agg), default=0)
            trend.append({
                "exam_id":       exam.id,
                "exam_name":     exam.exam_code,
                "exam_date":     exam.exam_date.isoformat() if exam.exam_date else None,
                "avg_total":     round(sum(a.avg or 0 for a in agg), 2),
                "avg_physics":   round(physics_avg, 2),
                "avg_chemistry": round(chemistry_avg, 2),
                "avg_maths":     round(math_avg, 2),
                "total_students": n_students,
            })
        return trend

    # ── D2 Weak Students ────────────────────────────────────────────────────────

    async def get_weak_students(
        self,
        exam_id:               int,
        severity:              str | None,
        rule_key:              str | None,
        allowed_admission_nos: list[str] | None,
    ) -> dict:
        alerts = await self._alert_repo.list_alerts(
            exam_id=exam_id, severity=severity, rule_key=rule_key,
            acknowledged=False, allowed_admission_nos=allowed_admission_nos,
        )

        # Sort so the worst severity for each student comes first
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 9))

        # Group by student — one entry per student, worst severity wins
        student_map: dict[str, dict] = {}
        for alert in alerts:
            if alert.admission_no not in student_map:
                summary = await self._analytics.get_student_exam_summary(alert.admission_no, exam_id)
                student = await self._student_repo.get_by_admission_no(alert.admission_no)
                if not student or not summary:
                    continue
                student_map[alert.admission_no] = {
                    "admission_no": alert.admission_no,
                    "name":         student.name,
                    "section":      student.section,
                    "branch_name":  student.branch_name,
                    "latest_total": summary.total_marks,
                    "latest_rank":  summary.rank_overall,
                    "severity":     alert.severity,
                    "alerts":       [],
                }
            if alert.admission_no in student_map:
                student_map[alert.admission_no]["alerts"].append({
                    "rule_key": alert.rule_key,
                    "message":  alert.message,
                    "context":  alert.context_json,
                })

        rows = list(student_map.values())
        counts = {"critical": 0, "warning": 0, "info": 0}
        for r in rows:
            counts[r["severity"]] = counts.get(r["severity"], 0) + 1

        return {
            "exam_id":        exam_id,
            "total_flagged":  len(rows),
            "critical_count": counts["critical"],
            "warning_count":  counts["warning"],
            "info_count":     counts["info"],
            "students":       rows,
        }

    # ── D3 Subject Analysis ─────────────────────────────────────────────────────

    async def get_subjects(
        self, exam_id: int, scope: str, scope_value: str
    ) -> dict:
        agg = await self._analytics.get_aggregate_for_exam(exam_id, scope, scope_value)
        subjects = []
        for row in agg:
            all_subs = await self._analytics.get_subject_summaries_for_exam(exam_id)
            subj_rows = [s for s in all_subs if s.subject == row.subject]
            sorted_s  = sorted(subj_rows, key=lambda x: -x.marks)

            top = []
            for sr in sorted_s[:3]:
                student = await self._student_repo.get_by_admission_no(sr.admission_no)
                if student:
                    top.append({"name": student.name, "marks": sr.marks, "accuracy": sr.accuracy})

            bot = []
            for sr in sorted_s[-3:]:
                student = await self._student_repo.get_by_admission_no(sr.admission_no)
                if student:
                    bot.append({"name": student.name, "marks": sr.marks, "accuracy": sr.accuracy})

            avg_accuracy_pct = (
                round(sum(s.accuracy for s in subj_rows) / len(subj_rows) * 100, 2)
                if subj_rows else 0.0
            )
            subjects.append({
                "subject":           row.subject,
                "avg_marks":         row.avg,
                "avg_accuracy_pct":  avg_accuracy_pct,
                "median":            row.median,
                "stdev":             row.stdev,
                "min_score":         row.min_score,
                "max_score":         row.max_score,
                "n_students":        row.n_students,
                "top_students":      top,
                "bottom_students":   bot,
            })

        return {"exam_id": exam_id, "scope": scope, "scope_value": scope_value, "subjects": subjects}

    # ── D4 Topic Heatmap ────────────────────────────────────────────────────────

    async def get_topic_heatmap(
        self,
        exam_id:       int,
        section:       str | None,
        admission_nos: list[str] | None,
    ) -> dict:
        topic_rows = await self._analytics.get_topic_summaries_for_exam(exam_id, admission_nos)

        topics = sorted({t.topic for t in topic_rows})
        student_map: dict[str, dict] = {}
        cells = []

        for row in topic_rows:
            if row.admission_no not in student_map:
                s = await self._student_repo.get_by_admission_no(row.admission_no)
                if s:
                    student_map[row.admission_no] = {
                        "admission_no": s.admission_no,
                        "name":         s.name,
                        "section":      s.section,
                        "topics":       {},
                    }
            if row.admission_no in student_map:
                student_map[row.admission_no]["topics"][row.topic] = round(row.accuracy, 4)

            cells.append({
                "admission_no": row.admission_no,
                "name":         student_map.get(row.admission_no, {}).get("name", ""),
                "topic":        row.topic,
                "subject":      row.subject,
                "accuracy":     round(row.accuracy, 4),
                "attempted":    row.attempted,
                "correct":      row.correct,
            })

        return {
            "exam_id":  exam_id,
            "section":  section,
            "topics":   topics,
            "students": list(student_map.values()),
            "cells":    cells,
        }

    # ── D5 Student Deep Dive ────────────────────────────────────────────────────

    async def get_student_deep_dive(self, admission_no: str) -> dict:
        student = await self._student_repo.get_by_admission_no(admission_no)
        if not student:
            raise KeyError(f"Student '{admission_no}' not found")

        history_db = await self._analytics.get_student_history(student.admission_no, limit=20) or []
        topic_db   = await self._analytics.get_student_topic_history(student.admission_no) or []
        alerts_db  = await self._alert_repo.list_alerts(admission_no=student.admission_no) or []

        # Fetch exam metadata for all exam_ids in one pass
        exam_meta: dict[int, dict] = {}
        for s in history_db:
            if s.exam_id not in exam_meta:
                exam = await self._exam_repo.get_by_id_with_papers(s.exam_id)
                if exam:
                    exam_meta[s.exam_id] = {
                        "exam_code": exam.exam_code,
                        "exam_type": exam.exam_type,
                        "exam_date": exam.exam_date.isoformat() if exam.exam_date else None,
                        "papers":    sorted(ep.paper_code for ep in (exam.exam_paper_links or [])),
                    }

        # Fetch per-paper results (totals + subject breakdown from graded_results)
        paper_results_map:     dict[int, dict[str, dict]]            = {}
        paper_subjects_map:    dict[int, dict[str, dict[str, dict]]] = {}
        paper_benchmarks_map:  dict[int, dict[str, dict[str, dict]]] = {}
        paper_topics_map:      dict[int, dict[str, list[dict]]]       = {}
        for s in history_db:
            if s.exam_id not in paper_results_map:
                paper_results_map[s.exam_id] = await self._analytics.get_paper_results_for_student(
                    student.admission_no, s.exam_id
                )
                paper_subjects_map[s.exam_id] = await self._analytics.get_paper_subject_data_for_student(
                    student.admission_no, s.exam_id
                )
                paper_benchmarks_map[s.exam_id] = await self._analytics.get_paper_subject_benchmarks(
                    s.exam_id
                )
                paper_topics_map[s.exam_id] = await self._analytics.get_paper_topic_data_for_student(
                    student.admission_no, s.exam_id
                )

        # Fetch subject summaries (marks + ranks), toppers, class averages, and total benchmarks for each exam
        subject_data: dict[int, dict[str, dict]] = {}
        subject_toppers: dict[int, dict[str, float]] = {}
        subject_avgs: dict[int, dict[str, float]] = {}
        total_benchmarks: dict[int, dict] = {}
        for s in history_db:
            if s.exam_id not in subject_data:
                subs = await self._analytics.get_subject_summaries_for_exam(s.exam_id, [student.admission_no])
                subject_data[s.exam_id] = {
                    sub.subject: {
                        "marks":          sub.marks,
                        "max_marks":      sub.max_marks,
                        "accuracy":       sub.accuracy,
                        "rank":           sub.rank_subject,
                        "correct":        sub.correct,
                        "partial":        sub.partial_count,
                        "wrong":          sub.wrong,
                        "blank":          sub.blank,
                        "negative_marks": sub.negative_marks,
                    }
                    for sub in subs
                }
                subject_toppers[s.exam_id] = await self._analytics.get_subject_toppers(s.exam_id)
                agg = await self._analytics.get_aggregate_for_exam(s.exam_id, "overall", "all")
                subject_avgs[s.exam_id] = {a.subject: float(a.avg or 0) for a in agg}
                total_benchmarks[s.exam_id] = await self._analytics.get_exam_total_benchmarks(s.exam_id)

        exam_history = [
            {
                "exam_id":          s.exam_id,
                "exam_code":        exam_meta.get(s.exam_id, {}).get("exam_code"),
                "exam_type":        exam_meta.get(s.exam_id, {}).get("exam_type"),
                "exam_date":        exam_meta.get(s.exam_id, {}).get("exam_date"),
                "papers":           exam_meta.get(s.exam_id, {}).get("papers", []),
                "total_marks":      s.total_marks,
                "max_marks":        s.max_marks,
                "percentage":       s.percentage,
                "rank_overall":      s.rank_overall,
                "rank_section":      s.rank_section,
                "marks_physics":          subject_data.get(s.exam_id, {}).get("Physics",     {}).get("marks"),
                "max_marks_physics":      subject_data.get(s.exam_id, {}).get("Physics",     {}).get("max_marks"),
                "rank_physics":           subject_data.get(s.exam_id, {}).get("Physics",     {}).get("rank"),
                "correct_physics":        subject_data.get(s.exam_id, {}).get("Physics",     {}).get("correct"),
                "partial_physics":        subject_data.get(s.exam_id, {}).get("Physics",     {}).get("partial"),
                "wrong_physics":          subject_data.get(s.exam_id, {}).get("Physics",     {}).get("wrong"),
                "blank_physics":          subject_data.get(s.exam_id, {}).get("Physics",     {}).get("blank"),
                "negative_physics":       subject_data.get(s.exam_id, {}).get("Physics",     {}).get("negative_marks"),
                "marks_chemistry":        subject_data.get(s.exam_id, {}).get("Chemistry",   {}).get("marks"),
                "max_marks_chemistry":    subject_data.get(s.exam_id, {}).get("Chemistry",   {}).get("max_marks"),
                "rank_chemistry":         subject_data.get(s.exam_id, {}).get("Chemistry",   {}).get("rank"),
                "correct_chemistry":      subject_data.get(s.exam_id, {}).get("Chemistry",   {}).get("correct"),
                "partial_chemistry":      subject_data.get(s.exam_id, {}).get("Chemistry",   {}).get("partial"),
                "wrong_chemistry":        subject_data.get(s.exam_id, {}).get("Chemistry",   {}).get("wrong"),
                "blank_chemistry":        subject_data.get(s.exam_id, {}).get("Chemistry",   {}).get("blank"),
                "negative_chemistry":     subject_data.get(s.exam_id, {}).get("Chemistry",   {}).get("negative_marks"),
                "marks_mathematics":      subject_data.get(s.exam_id, {}).get("Mathematics", {}).get("marks"),
                "max_marks_mathematics":  subject_data.get(s.exam_id, {}).get("Mathematics", {}).get("max_marks"),
                "rank_mathematics":       subject_data.get(s.exam_id, {}).get("Mathematics", {}).get("rank"),
                "correct_mathematics":    subject_data.get(s.exam_id, {}).get("Mathematics", {}).get("correct"),
                "partial_mathematics":    subject_data.get(s.exam_id, {}).get("Mathematics", {}).get("partial"),
                "wrong_mathematics":      subject_data.get(s.exam_id, {}).get("Mathematics", {}).get("wrong"),
                "blank_mathematics":      subject_data.get(s.exam_id, {}).get("Mathematics", {}).get("blank"),
                "negative_mathematics":   subject_data.get(s.exam_id, {}).get("Mathematics", {}).get("negative_marks"),
                "correct_count":    s.correct_count,
                "partial_count":    s.partial_count,
                "wrong_count":      s.wrong_count,
                "blank_count":      s.blank_count,
                "negative_marks":   s.negative_marks,
                "topper_physics":     subject_toppers.get(s.exam_id, {}).get("Physics"),
                "topper_chemistry":   subject_toppers.get(s.exam_id, {}).get("Chemistry"),
                "topper_mathematics": subject_toppers.get(s.exam_id, {}).get("Mathematics"),
                "avg_physics":        subject_avgs.get(s.exam_id, {}).get("Physics"),
                "avg_chemistry":      subject_avgs.get(s.exam_id, {}).get("Chemistry"),
                "avg_mathematics":    subject_avgs.get(s.exam_id, {}).get("Mathematics"),
                "avg_total":          total_benchmarks.get(s.exam_id, {}).get("avg_total"),
                "topper_total":       total_benchmarks.get(s.exam_id, {}).get("max_total"),
                "paper_results":      paper_results_map.get(s.exam_id, {}),
                "paper_subjects":     paper_subjects_map.get(s.exam_id, {}),
                "paper_benchmarks":   paper_benchmarks_map.get(s.exam_id, {}),
                "paper_topics":       paper_topics_map.get(s.exam_id, {}),
            }
            for s in reversed(history_db)
        ]

        subject_trend_map: dict[str, list[dict]] = {}
        for eid, subj_map in subject_data.items():
            for subj, d in subj_map.items():
                subject_trend_map.setdefault(subj, []).append({
                    "exam_id":  eid,
                    "marks":    d["marks"],
                    "accuracy": d["accuracy"],
                    "rank":     d["rank"],
                })

        exam_id_order = [s.exam_id for s in reversed(history_db)]
        subject_trends = [
            {"subject": subj, "data": sorted(data, key=lambda d: exam_id_order.index(d["exam_id"]) if d["exam_id"] in exam_id_order else 0)}
            for subj, data in subject_trend_map.items()
        ]

        weak_topics = [
            {
                "topic":    t.topic,
                "subject":  t.subject,
                "accuracy": t.accuracy,
                "attempted": t.attempted,
                "exam_id":  t.exam_id,
            }
            for t in topic_db
            if t.accuracy < 0.5 and t.attempted >= 2
        ]

        rank_trajectory = [
            {"exam_id": s.exam_id, "rank": s.rank_overall, "percentile": s.percentile_overall}
            for s in reversed(history_db)
        ]

        active_alerts = [
            {
                "alert_id": a.id,
                "rule_key": a.rule_key,
                "severity": a.severity,
                "title":    a.title,
                "message":  a.message,
                "exam_id":  a.exam_id,
                "context":  a.context_json,
            }
            for a in alerts_db
        ]

        return {
            "student": {
                "admission_no":  student.admission_no,
                "name":          student.name,
                "branch_name":   student.branch_name,
                "program_name":  student.program_name,
                "student_class": student.student_class,
                "section":       student.section,
                "dean":          student.dean,
                "status":        student.status,
                "created_at":    student.created_at.isoformat(),
            },
            "exam_history":    exam_history,
            "subject_trends":  subject_trends,
            "weak_topics":     weak_topics,
            "rank_trajectory": rank_trajectory,
            "active_alerts":   active_alerts,
        }
