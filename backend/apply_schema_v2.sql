-- =============================================================================
-- Schema update script  (equivalent to Alembic migration 0004)
-- Run this against the existing database when you cannot use Alembic.
--
-- Usage (Docker):
--   docker exec -i jee_postgres psql -U jee -d jeedb < apply_schema_v2.sql
--
-- Usage (local):
--   psql -U jee -d jeedb -f apply_schema_v2.sql
-- =============================================================================

-- ── 1. papers_master ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS papers_master (
    paper_code VARCHAR(10) PRIMARY KEY
);

INSERT INTO papers_master (paper_code) VALUES ('P1'), ('P2')
ON CONFLICT (paper_code) DO NOTHING;

-- ── 2. exam_papers ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS exam_papers (
    id         SERIAL PRIMARY KEY,
    exam_id    INTEGER     NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    paper_code VARCHAR(10) NOT NULL REFERENCES papers_master(paper_code),
    UNIQUE (exam_id, paper_code)
);

CREATE INDEX IF NOT EXISTS idx_exam_papers_exam ON exam_papers(exam_id);

-- ── 3. Back-fill exam_papers from existing papers table ───────────────────────
INSERT INTO exam_papers (exam_id, paper_code)
SELECT DISTINCT p.exam_id, p.paper_code
FROM   papers p
WHERE  p.paper_code IN ('P1', 'P2')
ON CONFLICT DO NOTHING;

-- Exams with no papers entry → default to P1
INSERT INTO exam_papers (exam_id, paper_code)
SELECT e.id, 'P1'
FROM   exams e
WHERE  NOT EXISTS (
    SELECT 1 FROM exam_papers ep WHERE ep.exam_id = e.id
)
ON CONFLICT DO NOTHING;

-- ── 4. questions: replace topic_id FK with topic VARCHAR ─────────────────────
ALTER TABLE questions ADD COLUMN IF NOT EXISTS topic VARCHAR(200);

-- Copy topic name from topics table where topic_id was set
UPDATE questions q
SET    topic = t.name
FROM   topics t
WHERE  q.topic_id = t.id
  AND  q.topic IS NULL;

-- Drop the FK constraint (PostgreSQL auto-names it)
ALTER TABLE questions DROP CONSTRAINT IF EXISTS questions_topic_id_fkey;

-- Drop the column
ALTER TABLE questions DROP COLUMN IF EXISTS topic_id;

-- ── 5. results table ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS results (
    id          SERIAL PRIMARY KEY,
    student_id  VARCHAR(15) NOT NULL REFERENCES students(admission_no) ON DELETE CASCADE,
    exam_id     INTEGER     NOT NULL REFERENCES exams(id)              ON DELETE CASCADE,
    paper_code  VARCHAR(10),          -- NULL for CONSOLIDATED rows
    score       FLOAT       NOT NULL,
    total_marks FLOAT       NOT NULL,
    result_type VARCHAR(20) NOT NULL  -- 'PAPER' | 'CONSOLIDATED'
);

CREATE INDEX IF NOT EXISTS idx_results_exam         ON results(exam_id);
CREATE INDEX IF NOT EXISTS idx_results_student      ON results(student_id);
CREATE INDEX IF NOT EXISTS idx_results_student_exam ON results(student_id, exam_id);

-- ── 6. questions: replace paper_id with exam_paper_id ────────────────────────
-- Only run if paper_id column still exists (idempotent guard)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'questions' AND column_name = 'paper_id'
    ) THEN
        -- Add new column
        ALTER TABLE questions ADD COLUMN IF NOT EXISTS exam_paper_id INTEGER;

        -- Back-fill from papers → exam_papers
        UPDATE questions q
        SET    exam_paper_id = ep.id
        FROM   papers p
        JOIN   exam_papers ep
               ON  ep.exam_id    = p.exam_id
               AND ep.paper_code = p.paper_code
        WHERE  q.paper_id = p.id;

        -- Add FK constraint
        ALTER TABLE questions
            ADD CONSTRAINT fk_questions_exam_paper_id
            FOREIGN KEY (exam_paper_id) REFERENCES exam_papers(id) ON DELETE CASCADE;

        -- Make NOT NULL
        ALTER TABLE questions ALTER COLUMN exam_paper_id SET NOT NULL;

        -- Drop old index, FK, column
        DROP INDEX IF EXISTS idx_questions_paper;
        ALTER TABLE questions DROP CONSTRAINT IF EXISTS questions_paper_id_fkey;
        ALTER TABLE questions DROP COLUMN IF EXISTS paper_id;

        -- Create new index
        CREATE INDEX IF NOT EXISTS idx_questions_exam_paper ON questions(exam_paper_id);

        -- Drop redundant papers table
        DROP TABLE IF EXISTS papers CASCADE;

        RAISE NOTICE '  Migration 0005: exam_paper_id back-fill complete.';
    ELSE
        RAISE NOTICE '  Migration 0005: already applied, skipping.';
    END IF;
END$$;

-- ── 7. Drop answer_keys; remove all numerical columns from questions ──────────
DROP TABLE IF EXISTS answer_keys CASCADE;

ALTER TABLE questions DROP COLUMN IF EXISTS numerical_answer;
ALTER TABLE questions DROP COLUMN IF EXISTS numerical_range_min;
ALTER TABLE questions DROP COLUMN IF EXISTS numerical_range_max;
ALTER TABLE questions DROP COLUMN IF EXISTS numerical_answer_2;
ALTER TABLE questions DROP COLUMN IF EXISTS numerical_range_min_2;
ALTER TABLE questions DROP COLUMN IF EXISTS numerical_range_max_2;

-- Widen correct_option to hold range strings like "9.95:10.05"
ALTER TABLE questions ALTER COLUMN correct_option TYPE VARCHAR(50);

-- ── 8. BKC/AKC answer columns on questions ───────────────────────────────────
DO $$
BEGIN
    -- Rename correct_option → correct_option_bkc (idempotent)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'questions' AND column_name = 'correct_option'
    ) THEN
        ALTER TABLE questions RENAME COLUMN correct_option TO correct_option_bkc;
        RAISE NOTICE '  Migration 0008: renamed correct_option → correct_option_bkc.';
    ELSE
        RAISE NOTICE '  Migration 0008: correct_option already renamed, skipping.';
    END IF;
END$$;

ALTER TABLE questions ADD COLUMN IF NOT EXISTS is_deleted_bkc     BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS correct_option_akc VARCHAR(50);
ALTER TABLE questions ADD COLUMN IF NOT EXISTS is_deleted_akc     BOOLEAN;

-- ── Done ──────────────────────────────────────────────────────────────────────
DO $$
BEGIN
    RAISE NOTICE '✅  Schema v2 applied successfully.';
END$$;
