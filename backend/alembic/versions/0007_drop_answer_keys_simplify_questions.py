"""Drop answer_keys table; remove all numerical answer columns from questions

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-24

Changes:
  - Drop answer_keys table entirely (all answer data lives in questions.correct_option)
  - Drop questions.numerical_answer
  - Drop questions.numerical_range_min
  - Drop questions.numerical_range_max
  - Drop questions.numerical_answer_2
  - Drop questions.numerical_range_min_2
  - Drop questions.numerical_range_max_2
  - Widen questions.correct_option to VARCHAR(50) to hold range strings like "9.95:10.05"

Numerical answer format in correct_option:
  Exact answer  →  "42"  or  "3.14"
  Range         →  "8.5:9.5"  (min:max, colon separator)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_Q_NUMERICAL_COLS = [
    "numerical_answer",
    "numerical_range_min",
    "numerical_range_max",
    "numerical_answer_2",
    "numerical_range_min_2",
    "numerical_range_max_2",
]


def upgrade() -> None:
    op.drop_table("answer_keys")
    for col in _Q_NUMERICAL_COLS:
        op.drop_column("questions", col)
    op.alter_column("questions", "correct_option", type_=sa.String(50))


def downgrade() -> None:
    op.alter_column("questions", "correct_option", type_=sa.String(20))
    for col in _Q_NUMERICAL_COLS:
        op.add_column("questions", sa.Column(col, sa.Float(), nullable=True))

    op.create_table(
        "answer_keys",
        sa.Column("id",                    sa.Integer(),              primary_key=True, autoincrement=True),
        sa.Column("question_id",           sa.Integer(),              sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_type",              sa.String(3),              nullable=False),
        sa.Column("correct_option",        sa.String(20)),
        sa.Column("numerical_answer",      sa.Float()),
        sa.Column("numerical_range_min",   sa.Float()),
        sa.Column("numerical_range_max",   sa.Float()),
        sa.Column("numerical_answer_2",    sa.Float()),
        sa.Column("numerical_range_min_2", sa.Float()),
        sa.Column("numerical_range_max_2", sa.Float()),
        sa.Column("marks_override",        sa.Float()),
        sa.Column("is_deleted",            sa.Boolean(),              nullable=False, server_default="false"),
        sa.Column("uploaded_at",           sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("uploaded_by",           sa.Integer(),              sa.ForeignKey("users.id")),
        sa.UniqueConstraint("question_id", "key_type"),
    )
