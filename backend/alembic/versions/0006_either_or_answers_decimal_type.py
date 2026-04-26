"""Add either-or answer columns; support NUMERICAL_DECIMAL question type

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-24

Changes:
questions table:
  + numerical_answer_2    FLOAT  — second valid exact answer (either-or)
  + numerical_range_min_2 FLOAT  — second valid range lower bound
  + numerical_range_max_2 FLOAT  — second valid range upper bound

answer_keys table:
  + numerical_answer_2    FLOAT
  + numerical_range_min_2 FLOAT
  + numerical_range_max_2 FLOAT

New question types (no DB change — stored as VARCHAR):
  NUMERICAL_DECIMAL  — decimal answer rounded to 2dp, range-based eval
  MCQ                — alias for MCQ_MULTI (preferred going forward)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_NEW_COLS = [
    "numerical_answer_2",
    "numerical_range_min_2",
    "numerical_range_max_2",
]


def upgrade() -> None:
    for table in ("questions", "answer_keys"):
        for col in _NEW_COLS:
            op.add_column(table, sa.Column(col, sa.Float(), nullable=True))


def downgrade() -> None:
    for table in ("questions", "answer_keys"):
        for col in _NEW_COLS:
            op.drop_column(table, col)
