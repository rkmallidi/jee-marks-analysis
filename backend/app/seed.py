"""
Seed script – idempotent.

Run from the backend directory:
    python -m app.seed

Creates:
  • 3 users  : admin / dean / faculty1
  • 2 branches: Hyderabad-Kukatpally, Hyderabad-Madhapur
  • 3 programs: JEE-Main, JEE-Advanced, NEET
  • 13 topics : 4 Physics, 5 Chemistry, 4 Maths
  • 4 alert-config rows (defaults for every rule key)
  • faculty_sections assignment  (faculty1 → Section-A of both branches)
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.models.orm import (
    AlertConfig,
    Branch,
    FacultySection,
    PapersMaster,
    Topic,
    User,
)
from app.utils.security import hash_password

# ── credentials ─────────────────────────────────────────────────────────────
USERS = [
    {"username": "admin",    "full_name": "Admin User",   "role": "admin",   "password": "admin123"},
    {"username": "dean",     "full_name": "Dean Sharma",  "role": "dean",    "password": "dean123"},
    {"username": "faculty1", "full_name": "Prof. Rao",    "role": "faculty", "password": "faculty123"},
]

BRANCHES = [
    {"name": "Hyderabad-Kukatpally", "code": "HYD-KKP"},
    {"name": "Hyderabad-Madhapur",   "code": "HYD-MDH"},
]

TOPICS = [
    # Physics
    {"name": "Mechanics",              "subject": "Physics",   "description": "Kinematics, Laws of Motion, Work-Energy"},
    {"name": "Electrostatics",         "subject": "Physics",   "description": "Coulomb's law, Capacitance"},
    {"name": "Optics",                 "subject": "Physics",   "description": "Ray and Wave Optics"},
    {"name": "Modern Physics",         "subject": "Physics",   "description": "Photoelectric Effect, Nuclear Physics"},
    # Chemistry
    {"name": "Physical Chemistry",     "subject": "Chemistry", "description": "Thermodynamics, Equilibrium, Electrochemistry"},
    {"name": "Organic Chemistry",      "subject": "Chemistry", "description": "IUPAC, Reactions, Named Reactions"},
    {"name": "Inorganic Chemistry",    "subject": "Chemistry", "description": "Periodicity, s/p/d blocks"},
    {"name": "Chemical Bonding",       "subject": "Chemistry", "description": "VSEPR, Hybridisation, MO Theory"},
    {"name": "Coordination Compounds", "subject": "Chemistry", "description": "Nomenclature, Isomerism, Crystal Field"},
    # Maths
    {"name": "Algebra",                "subject": "Maths",     "description": "Quadratics, Sequences, Matrices, Complex Numbers"},
    {"name": "Calculus",               "subject": "Maths",     "description": "Limits, Derivatives, Integrals, Differential Equations"},
    {"name": "Coordinate Geometry",    "subject": "Maths",     "description": "Straight Lines, Conics"},
    {"name": "Trigonometry",           "subject": "Maths",     "description": "Identities, Inverse Trig, Solutions of Triangles"},
]

# Default thresholds – all tunable via PATCH /alerts/config
ALERT_CONFIGS = [
    {
        "rule_key": "performance_drop",
        "config_json": {
            "drop_threshold_pct": 15,
            "lookback_exams": 3,
            "severity": "warning",
            "description": "Alert when a student's score drops ≥15 % vs the previous 3-exam average",
        },
    },
    {
        "rule_key": "weak_topic",
        "config_json": {
            "accuracy_threshold_pct": 40,
            "min_attempts": 3,
            "severity": "info",
            "description": "Alert when topic accuracy falls below 40 % over ≥3 attempts",
        },
    },
    {
        "rule_key": "below_branch_avg",
        "config_json": {
            "deviation_pct": 20,
            "min_exams": 2,
            "severity": "warning",
            "description": "Alert when student is ≥20 % below branch average for ≥2 exams",
        },
    },
    {
        "rule_key": "consistently_low",
        "config_json": {
            "percentile_threshold": 20,
            "consecutive_exams": 3,
            "severity": "critical",
            "description": "Alert when student stays in the bottom 20th percentile for 3 consecutive exams",
        },
    },
]


# ── helpers ──────────────────────────────────────────────────────────────────

async def _upsert_user(session, row: dict) -> User:
    result = await session.execute(select(User).where(User.username == row["username"]))
    user = result.scalar_one_or_none()
    if user:
        print(f"  user '{row['username']}' already exists — skipping")
        return user
    user = User(
        username=row["username"],
        full_name=row["full_name"],
        role=row["role"],
        hashed_password=hash_password(row["password"]),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    print(f"  created user '{row['username']}'  ({row['role']})")
    return user


async def _upsert_branch(session, row: dict) -> Branch:
    result = await session.execute(select(Branch).where(Branch.name == row["name"]))
    branch = result.scalar_one_or_none()
    if branch:
        print(f"  branch '{row['name']}' already exists — skipping")
        return branch
    branch = Branch(name=row["name"], city=row.get("code"))
    session.add(branch)
    await session.flush()
    print(f"  created branch '{row['name']}'")
    return branch


async def _upsert_topic(session, row: dict) -> Topic:
    result = await session.execute(select(Topic).where(Topic.name == row["name"]))
    topic = result.scalar_one_or_none()
    if topic:
        print(f"  topic '{row['name']}' already exists — skipping")
        return topic
    topic = Topic(name=row["name"], subject=row["subject"])
    session.add(topic)
    await session.flush()
    print(f"  created topic '{row['name']}'  ({row['subject']})")
    return topic


async def _seed_papers_master(session) -> None:
    stmt = (
        pg_insert(PapersMaster)
        .values([{"paper_code": "P1"}, {"paper_code": "P2"}])
        .on_conflict_do_nothing(index_elements=["paper_code"])
    )
    await session.execute(stmt)
    print("  papers_master: P1, P2 ensured")


async def _upsert_alert_config(session, row: dict) -> None:
    stmt = (
        pg_insert(AlertConfig)
        .values(rule_key=row["rule_key"], config_json=row["config_json"])
        .on_conflict_do_nothing(index_elements=["rule_key"])
    )
    await session.execute(stmt)
    print(f"  alert config '{row['rule_key']}' ensured")


async def _upsert_faculty_section(session, faculty: User, branch: Branch, section: str) -> None:
    result = await session.execute(
        select(FacultySection).where(
            FacultySection.user_id == faculty.id,
            FacultySection.branch_id == branch.id,
            FacultySection.section == section,
        )
    )
    if result.scalar_one_or_none():
        print(f"  faculty section {branch.name}/{section} already assigned — skipping")
        return
    session.add(FacultySection(user_id=faculty.id, branch_id=branch.id, section=section))
    await session.flush()
    print(f"  assigned faculty1 → {branch.name} / {section}")


# ── main ─────────────────────────────────────────────────────────────────────

async def seed() -> None:
    print("\n🌱  Starting seed…\n")

    async with AsyncSessionLocal() as session:
        async with session.begin():

            print("── Papers Master ─────────────────────────────────")
            await _seed_papers_master(session)

            print("\n── Users ─────────────────────────────────────────")
            users: dict[str, User] = {}
            for u in USERS:
                users[u["username"]] = await _upsert_user(session, u)

            print("\n── Branches ──────────────────────────────────────")
            branches: list[Branch] = []
            for b in BRANCHES:
                branches.append(await _upsert_branch(session, b))

            print("\n── Topics ────────────────────────────────────────")
            for t in TOPICS:
                await _upsert_topic(session, t)

            print("\n── Alert Configs ─────────────────────────────────")
            for ac in ALERT_CONFIGS:
                await _upsert_alert_config(session, ac)

            print("\n── Faculty Sections ──────────────────────────────")
            faculty = users["faculty1"]
            for branch in branches:
                await _upsert_faculty_section(session, faculty, branch, "Section-A")

    print("\n✅  Seed complete.\n")


if __name__ == "__main__":
    asyncio.run(seed())
