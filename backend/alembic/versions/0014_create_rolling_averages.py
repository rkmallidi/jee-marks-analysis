"""create rolling_averages table for per-student per-exam-type averages

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS rolling_averages (
            id           SERIAL PRIMARY KEY,
            admission_no VARCHAR(15) NOT NULL REFERENCES students(admission_no),
            exam_type    VARCHAR(20) NOT NULL,
            avg_score    FLOAT       NOT NULL,
            exam_count   INTEGER     NOT NULL DEFAULT 0,
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_ra_student_type UNIQUE (admission_no, exam_type)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ra_student ON rolling_averages (admission_no)
    """)


def downgrade() -> None:
    op.drop_index("idx_ra_student", table_name="rolling_averages")
    op.drop_table("rolling_averages")
