"""Add difficulty column to questions

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-25

Changes:
  - Add questions.difficulty  VARCHAR(20) NULL
    Valid values: Easy | Medium | Hard | Very Hard (enforced at application layer)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("difficulty", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "difficulty")
