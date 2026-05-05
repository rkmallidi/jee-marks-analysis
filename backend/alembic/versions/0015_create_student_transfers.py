"""create student_transfers table to track program/branch/section changes

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS student_transfers (
            id               SERIAL PRIMARY KEY,
            admission_no     VARCHAR(15)  NOT NULL REFERENCES students(admission_no),
            changed_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
            old_program_name VARCHAR(50)  NOT NULL,
            new_program_name VARCHAR(50)  NOT NULL,
            old_branch_name  VARCHAR(100) NOT NULL,
            new_branch_name  VARCHAR(100) NOT NULL,
            old_section      VARCHAR(10)  NOT NULL,
            new_section      VARCHAR(10)  NOT NULL,
            old_class        VARCHAR(30)  NOT NULL,
            new_class        VARCHAR(30)  NOT NULL
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_transfers_student    ON student_transfers (admission_no)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_transfers_changed_at ON student_transfers (changed_at)
    """)


def downgrade() -> None:
    op.drop_index("idx_transfers_changed_at", table_name="student_transfers")
    op.drop_index("idx_transfers_student",    table_name="student_transfers")
    op.drop_table("student_transfers")
