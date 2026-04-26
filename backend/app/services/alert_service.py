from __future__ import annotations

import statistics

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.alert_engine import (
    AlertContext,
    HistoricalSummary,
    TopicHistory,
    run_alert_engine,
)
from app.repositories.alert_repo import AlertRepository
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.student_repo import StudentRepository


class AlertService:
    def __init__(self, session: AsyncSession) -> None:
        self._alert_repo    = AlertRepository(session)
        self._analytics     = AnalyticsRepository(session)
        self._student_repo  = StudentRepository(session)

    async def run_for_exam(self, exam_id: int) -> int:
        """Run all alert rules. Returns number of alert records upserted."""
        config      = await self._alert_repo.get_config_dict()
        current_db  = await self._analytics.get_exam_summaries(exam_id)
        if not current_db:
            return 0

        all_sids = [s.admission_no for s in current_db]

        current_summaries: dict[str, HistoricalSummary] = {}
        for s in current_db:
            student = await self._student_repo.get_by_admission_no(s.admission_no)
            if student:
                current_summaries[s.admission_no] = HistoricalSummary(
                    exam_id=exam_id, admission_no=s.admission_no,
                    total_marks=s.total_marks, percentage=s.percentage,
                    rank_overall=s.rank_overall, rank_branch=s.rank_branch,
                    branch_name=student.branch_name, section=student.section,
                )

        historical: dict[str, list[HistoricalSummary]] = {}
        for sid in all_sids:
            hist_db = await self._analytics.get_student_history(sid, limit=5)
            rows = []
            for h in hist_db:
                if h.exam_id == exam_id:
                    continue
                student = await self._student_repo.get_by_admission_no(sid)
                if student:
                    rows.append(HistoricalSummary(
                        exam_id=h.exam_id, admission_no=sid,
                        total_marks=h.total_marks, percentage=h.percentage,
                        rank_overall=h.rank_overall, rank_branch=h.rank_branch,
                        branch_name=student.branch_name, section=student.section,
                    ))
            historical[sid] = rows

        topic_history: dict[str, list[TopicHistory]] = {}
        for sid in all_sids:
            topic_db = await self._analytics.get_student_topic_history(sid)
            topic_history[sid] = [
                TopicHistory(
                    admission_no=t.admission_no, exam_id=t.exam_id,
                    topic=t.topic, subject=t.subject,
                    accuracy=t.accuracy, attempted=t.attempted, correct=t.correct,
                )
                for t in topic_db
            ]

        branch_groups: dict[str, list[float]] = {}
        for s in current_db:
            student = await self._student_repo.get_by_admission_no(s.admission_no)
            if student:
                branch_groups.setdefault(student.branch_name, []).append(s.total_marks)

        branch_stats: dict[str, tuple[float, float]] = {
            bname: (
                statistics.mean(scores),
                statistics.stdev(scores) if len(scores) > 1 else 0.0,
            )
            for bname, scores in branch_groups.items()
        }

        ctx = AlertContext(
            exam_id=exam_id, student_ids=all_sids,
            current_summaries=current_summaries,
            historical=historical, topic_history=topic_history,
            branch_stats=branch_stats, config=config,
        )

        records = run_alert_engine(ctx)
        await self._alert_repo.upsert_alerts(records)
        return len(records)

    async def list_alerts(
        self,
        admission_no:          str | None,
        exam_id:               int | None,
        severity:              str | None,
        rule_key:              str | None,
        acknowledged:          bool | None,
        allowed_admission_nos: list[str] | None,
    ) -> list:
        return await self._alert_repo.list_alerts(
            admission_no, exam_id, severity, rule_key, acknowledged, allowed_admission_nos
        )

    async def acknowledge(self, alert_id: int, user_id: int) -> None:
        alert = await self._alert_repo.get_by_id(alert_id)
        if not alert:
            raise KeyError(f"Alert {alert_id} not found")
        await self._alert_repo.acknowledge(alert, user_id)

    async def get_configs(self) -> list:
        return await self._alert_repo.get_all_configs()

    async def update_config(self, rule_key: str, config: dict, user_id: int) -> None:
        await self._alert_repo.upsert_config(rule_key, config, user_id)
