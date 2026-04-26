"""questions: replace paper_id FK (→papers) with exam_paper_id FK (→exam_papers); drop papers table

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-24

Changes:
- questions.paper_id (→ papers.id) removed
- questions.exam_paper_id (→ exam_papers.id) added
- papers table dropped (redundant — exam_papers already tracks exam/paper mapping)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new nullable column with FK to exam_papers
    op.add_column(
        "questions",
        sa.Column("exam_paper_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_questions_exam_paper_id",
        "questions", "exam_papers",
        ["exam_paper_id"], ["id"],
        ondelete="CASCADE",
    )

    # 2. Back-fill: match via papers → exam_papers on (exam_id, paper_code)
    op.execute("""
        UPDATE questions q
        SET    exam_paper_id = ep.id
        FROM   papers p
        JOIN   exam_papers ep
               ON  ep.exam_id    = p.exam_id
               AND ep.paper_code = p.paper_code
        WHERE  q.paper_id = p.id
    """)

    # 3. Make NOT NULL (all rows must be filled before this)
    op.alter_column("questions", "exam_paper_id", nullable=False)

    # 4. Drop old index, FK constraint, and column
    op.drop_index("idx_questions_paper", table_name="questions")
    op.drop_constraint("questions_paper_id_fkey", "questions", type_="foreignkey")
    op.drop_column("questions", "paper_id")

    # 5. Create new index
    op.create_index("idx_questions_exam_paper", "questions", ["exam_paper_id"])

    # 6. Drop the now-redundant papers table (questions no longer reference it)
    op.drop_table("papers")


def downgrade() -> None:
    # Recreate papers from exam_papers
    op.create_table(
        "papers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "exam_id", sa.Integer(),
            sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("paper_code", sa.VARCHAR(10), nullable=False),
        sa.UniqueConstraint("exam_id", "paper_code"),
    )
    op.execute("""
        INSERT INTO papers (exam_id, paper_code)
        SELECT exam_id, paper_code FROM exam_papers
        ON CONFLICT DO NOTHING
    """)

    # Restore paper_id on questions
    op.add_column("questions", sa.Column("paper_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "questions_paper_id_fkey", "questions", "papers",
        ["paper_id"], ["id"], ondelete="CASCADE",
    )
    op.execute("""
        UPDATE questions q
        SET    paper_id = p.id
        FROM   exam_papers ep
        JOIN   papers p
               ON  p.exam_id    = ep.exam_id
               AND p.paper_code = ep.paper_code
        WHERE  q.exam_paper_id = ep.id
    """)
    op.alter_column("questions", "paper_id", nullable=False)

    # Drop exam_paper_id
    op.drop_index("idx_questions_exam_paper", table_name="questions")
    op.drop_constraint("fk_questions_exam_paper_id", "questions", type_="foreignkey")
    op.drop_column("questions", "exam_paper_id")

    # Restore old index
    op.create_index("idx_questions_paper", "questions", ["paper_id"])
