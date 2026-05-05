"""
One-shot data cleanup script — wipes all transactional data, keeps config/auth tables.

Preserved: users, branches, topics, papers_master, alert_config, faculty_sections, refresh_tokens
Cleared:   students + all exam/marks/analytics tables

Run from the backend directory:
    python -m app.clean_data
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.database import AsyncSessionLocal

TRUNCATE_SQL = """
TRUNCATE TABLE
    alerts,
    rank_audit,
    graded_results,
    omr_responses,
    student_topic_summary,
    student_subject_summary,
    student_exam_summary,
    rank_summary,
    aggregate_summary,
    results,
    rolling_averages,
    student_transfers,
    upload_jobs,
    questions,
    exam_papers,
    exams,
    students
RESTART IDENTITY CASCADE;
"""


async def clean() -> None:
    print("\nStarting data cleanup...\n")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(text(TRUNCATE_SQL))
    print("All transactional data cleared.\n")
    print("Preserved: users, branches, topics, papers_master, alert_config, faculty_sections\n")


if __name__ == "__main__":
    asyncio.run(clean())
