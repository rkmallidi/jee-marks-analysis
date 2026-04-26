"""Add BKC/AKC answer columns to questions; rename correct_option → correct_option_bkc

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-24

Changes:
  - Rename questions.correct_option → correct_option_bkc (preserves existing data)
  - Add questions.is_deleted_bkc  BOOLEAN NOT NULL DEFAULT FALSE
  - Add questions.correct_option_akc  VARCHAR(50) NULL
  - Add questions.is_deleted_akc  BOOLEAN NULL  (NULL = inherit from BKC)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("questions", "correct_option", new_column_name="correct_option_bkc")
    op.add_column("questions", sa.Column("is_deleted_bkc",     sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("questions", sa.Column("correct_option_akc", sa.String(50), nullable=True))
    op.add_column("questions", sa.Column("is_deleted_akc",     sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "is_deleted_akc")
    op.drop_column("questions", "correct_option_akc")
    op.drop_column("questions", "is_deleted_bkc")
    op.alter_column("questions", "correct_option_bkc", new_column_name="correct_option")
