"""Add papers_master, exam_papers, results tables; migrate topic to string

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-24

Changes:
- papers_master (P1, P2 seed)
- exam_papers  (exam ↔ authorized papers)
- questions.topic_id FK removed; replaced by questions.topic VARCHAR
- results table (paper-wise + consolidated scores)
- Backward compatibility: existing exams default to P1 (or mirror existing papers)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision      = "0004"
down_revision = "0003"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── 1. papers_master ──────────────────────────────────────────────────────
    op.create_table(
        "papers_master",
        sa.Column("paper_code", sa.String(10), primary_key=True),
    )
    op.execute("INSERT INTO papers_master (paper_code) VALUES ('P1'), ('P2')")

    # ── 2. exam_papers ────────────────────────────────────────────────────────
    op.create_table(
        "exam_papers",
        sa.Column("id",         sa.Integer,    primary_key=True, autoincrement=True),
        sa.Column("exam_id",    sa.Integer,    sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_code", sa.String(10), sa.ForeignKey("papers_master.paper_code"),    nullable=False),
        sa.UniqueConstraint("exam_id", "paper_code"),
    )
    op.create_index("idx_exam_papers_exam", "exam_papers", ["exam_id"])

    # ── 3. Back-fill exam_papers from existing papers table ───────────────────
    # Insert one row per distinct (exam_id, paper_code) already in the papers table
    # that corresponds to a valid papers_master entry.
    op.execute("""
        INSERT INTO exam_papers (exam_id, paper_code)
        SELECT DISTINCT p.exam_id, p.paper_code
        FROM papers p
        WHERE p.paper_code IN ('P1', 'P2')
        ON CONFLICT DO NOTHING
    """)

    # Exams that still have no exam_papers row get a default P1 entry
    op.execute("""
        INSERT INTO exam_papers (exam_id, paper_code)
        SELECT e.id, 'P1'
        FROM exams e
        WHERE NOT EXISTS (
            SELECT 1 FROM exam_papers ep WHERE ep.exam_id = e.id
        )
        ON CONFLICT DO NOTHING
    """)

    # ── 4. questions: replace topic_id FK with topic string ───────────────────
    op.add_column("questions", sa.Column("topic", sa.String(200)))

    # Migrate existing topic names (topic_id → name string)
    op.execute("""
        UPDATE questions q
        SET    topic = t.name
        FROM   topics t
        WHERE  q.topic_id = t.id
    """)

    # Drop the FK constraint (name may vary; use IF EXISTS on the column)
    op.execute("ALTER TABLE questions DROP CONSTRAINT IF EXISTS questions_topic_id_fkey")
    op.drop_column("questions", "topic_id")

    # ── 5. results table ──────────────────────────────────────────────────────
    op.create_table(
        "results",
        sa.Column("id",          sa.Integer,   primary_key=True, autoincrement=True),
        sa.Column("student_id",  sa.String(15), sa.ForeignKey("students.admission_no", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_id",     sa.Integer,   sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_code",  sa.String(10)),  # NULL for CONSOLIDATED
        sa.Column("score",       sa.Float,     nullable=False),
        sa.Column("total_marks", sa.Float,     nullable=False),
        sa.Column("result_type", sa.String(20), nullable=False),  # "PAPER" | "CONSOLIDATED"
    )
    op.create_index("idx_results_exam",         "results", ["exam_id"])
    op.create_index("idx_results_student",      "results", ["student_id"])
    op.create_index("idx_results_student_exam", "results", ["student_id", "exam_id"])


def downgrade() -> None:
    # ── Reverse results ───────────────────────────────────────────────────────
    op.drop_index("idx_results_student_exam", table_name="results")
    op.drop_index("idx_results_student",      table_name="results")
    op.drop_index("idx_results_exam",         table_name="results")
    op.drop_table("results")

    # ── Reverse topic migration ───────────────────────────────────────────────
    op.add_column(
        "questions",
        sa.Column("topic_id", sa.Integer, sa.ForeignKey("topics.id"))
    )
    # Best-effort: restore topic_id where topic name still matches topics table
    op.execute("""
        UPDATE questions q
        SET    topic_id = t.id
        FROM   topics t
        WHERE  q.topic = t.name
    """)
    op.drop_column("questions", "topic")

    # ── Reverse exam_papers ───────────────────────────────────────────────────
    op.drop_index("idx_exam_papers_exam", table_name="exam_papers")
    op.drop_table("exam_papers")

    # ── Reverse papers_master ─────────────────────────────────────────────────
    op.drop_table("papers_master")
