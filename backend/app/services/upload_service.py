from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import OmrResponse, Question, Student, UploadJob
from app.repositories.exam_repo import ExamRepository
from app.repositories.response_repo import ResponseRepository
from app.repositories.student_repo import StudentRepository
from app.validators.answer_key_validator import AnswerKeyValidator, _parse_bool
from app.validators.base import ValidationResult
from app.validators.question_validator import QuestionValidator
from app.validators.response_validator import ResponseValidator, convert_option_answer
from app.validators.student_validator import StudentValidator

_SAFE_STR = lambda v: None if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v).strip() or None
_SAFE_FLT = lambda v, d=None: d if (v is None or (isinstance(v, float) and pd.isna(v))) else float(v)


def _read_df(data: bytes, filename: str) -> pd.DataFrame:
    """Read xlsx or csv bytes into a DataFrame, detected by filename extension."""
    if (filename or "").lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(data))
    return pd.read_csv(io.BytesIO(data))


class UploadService:
    """
    All uploads are atomic: validation failure → nothing written.
    Each method returns an UploadJob ORM row tracking outcome and errors.
    """

    def __init__(self, session: AsyncSession, uploaded_by: int) -> None:
        self._s            = session
        self._student_repo = StudentRepository(session)
        self._exam_repo    = ExamRepository(session)
        self._resp_repo    = ResponseRepository(session)
        self._uploaded_by  = uploaded_by

    async def _record_job(
        self,
        upload_type: str,
        filename:    str,
        result:      ValidationResult,
        total_rows:  int,
        accepted:    int,
    ) -> UploadJob:
        job = UploadJob(
            upload_type=upload_type,
            filename=filename,
            status="failed" if not result.is_valid else "completed",
            total_rows=total_rows,
            accepted_rows=accepted if result.is_valid else 0,
            rejected_rows=total_rows - accepted if result.is_valid else total_rows,
            error_json=result.as_dicts() if result.errors else None,
            uploaded_by=self._uploaded_by,
            completed_at=datetime.utcnow(),
        )
        self._s.add(job)
        await self._s.flush()
        return job

    async def _check_exam_paper(
        self, exam_id: int, paper_code: str, filename: str, upload_type: str
    ) -> tuple[ValidationResult, object | None, object | None]:
        """Validate exam + paper auth. Returns (vr, exam, exam_paper)."""
        exam = await self._exam_repo.get_by_id(exam_id)
        if not exam:
            vr = ValidationResult()
            vr.add(0, "exam_id", f"Exam ID {exam_id} not found")
            return vr, None, None

        authorized = await self._exam_repo.get_authorized_papers(exam_id)
        if paper_code not in authorized:
            vr = ValidationResult()
            vr.add(0, "paper_code",
                   f"Paper '{paper_code}' not authorized for exam '{exam.exam_code}'. "
                   f"Authorized: {sorted(authorized)}")
            return vr, None, None

        exam_paper = await self._exam_repo.get_exam_paper(exam_id, paper_code)
        return ValidationResult(), exam, exam_paper

    # ── Students ──────────────────────────────────────────────────────────────

    async def upload_students(self, file_bytes: bytes, filename: str) -> UploadJob:
        df           = pd.read_excel(io.BytesIO(file_bytes))
        existing_nos = await self._student_repo.get_existing_admission_nos()

        validator = StudentValidator(existing_nos)
        result    = validator.validate(df)
        job       = await self._record_job("students", filename, result, len(df), len(df))
        if not result.is_valid:
            return job

        students = []
        for _, row in df.iterrows():
            students.append(Student(
                admission_no=str(row["admission_no"]).strip().upper(),
                name=str(row["name"]).strip(),
                branch_name=str(row["branch_name"]).strip(),
                program_name=str(row["program_name"]).strip(),
                student_class=str(row["student_class"]).strip(),
                section=str(row["section"]).strip(),
                dean=str(row["dean"]).strip(),
                status=str(row.get("status", "active")).strip(),
            ))
        await self._student_repo.bulk_insert(students)
        return job

    # ── Questions (saves BKC answer) ──────────────────────────────────────────

    async def upload_questions(
        self, file_bytes: bytes, filename: str, exam_id: int, paper_code: str
    ) -> UploadJob:
        """Upload questions for a specific exam paper.

        exam_id and paper_code come from the HTTP form (not the Excel file).
        Excel columns: qno, subject, question_type, marks, negative_marks,
        correct_answer (→ correct_option_bkc), plus optional: topic, sub_topic, partial_marks.
        """
        df = pd.read_excel(io.BytesIO(file_bytes))

        auth_vr, exam, exam_paper = await self._check_exam_paper(exam_id, paper_code, filename, "questions")
        if not auth_vr.is_valid:
            return await self._record_job("questions", filename, auth_vr, 0, 0)

        validator = QuestionValidator()
        result    = validator.validate(df)
        job       = await self._record_job("questions", filename, result, len(df), len(df))
        if not result.is_valid:
            return job

        from sqlalchemy import select as sa_select

        # Build a map of existing questions for this paper keyed by question_no
        existing: dict[int, Question] = {
            q.question_no: q
            for q in (await self._s.execute(
                sa_select(Question).where(Question.exam_paper_id == exam_paper.id)
            )).scalars().all()
        }

        for _, row in df.iterrows():
            raw_del    = str(row.get("is_deleted", "")).strip().lower()
            q_no       = int(row["qno"])
            subject    = str(row["subject"]).strip()
            topic      = _SAFE_STR(row.get("topic"))
            sub_topic  = _SAFE_STR(row.get("sub_topic"))
            q_type     = str(row["question_type"]).strip()
            pos_marks  = float(row["marks"])
            neg_marks  = abs(float(row["negative_marks"]))  # accept -1 or 1
            part_marks = _SAFE_FLT(row.get("partial_marks"), 0.0)
            correct    = _SAFE_STR(row.get("correct_answer"))
            if correct:
                correct = convert_option_answer(correct, q_type)
            difficulty = _SAFE_STR(row.get("difficulty"))
            is_del     = raw_del in ("y", "yes", "true", "1")

            if q_no in existing:
                q = existing[q_no]
                q.subject            = subject
                q.topic              = topic
                q.sub_topic          = sub_topic
                q.question_type      = q_type
                q.positive_marks     = pos_marks
                q.negative_marks     = neg_marks
                q.partial_marks      = part_marks
                q.correct_option_bkc = correct
                q.is_deleted_bkc     = is_del
                q.difficulty         = difficulty
            else:
                self._s.add(Question(
                    exam_paper_id=exam_paper.id,
                    question_no=q_no,
                    subject=subject,
                    topic=topic,
                    sub_topic=sub_topic,
                    question_type=q_type,
                    positive_marks=pos_marks,
                    negative_marks=neg_marks,
                    partial_marks=part_marks,
                    correct_option_bkc=correct,
                    is_deleted_bkc=is_del,
                    difficulty=difficulty,
                ))

        await self._s.flush()
        return job

    # ── Answer Key (BKC or AKC correction) ───────────────────────────────────

    async def upload_answer_key(
        self, file_bytes: bytes, filename: str,
        exam_id: int, paper_code: str, key_type: str
    ) -> UploadJob:
        """Upload BKC or AKC answer corrections.

        exam_id, paper_code, key_type come from the HTTP form.
        CSV columns: qno (required), correct_answer (optional), is_deleted (optional).

        BKC upload → updates correct_option_bkc + is_deleted_bkc on existing questions.
        AKC upload → updates correct_option_akc + is_deleted_akc on existing questions.
        AKC evaluation falls back to BKC for any question not present in the AKC upload.
        """
        upload_type = f"answer_key_{key_type.lower()}"
        df = _read_df(file_bytes, filename)

        auth_vr, exam, exam_paper = await self._check_exam_paper(exam_id, paper_code, filename, upload_type)
        if not auth_vr.is_valid:
            return await self._record_job(upload_type, filename, auth_vr, 0, 0)

        # Collect valid question numbers for this exam paper
        valid_nos: set[int] = {
            q_no
            for (_, _, q_no) in await self._exam_repo.get_valid_question_keys(exam.exam_code)
        }

        validator = AnswerKeyValidator(valid_nos)
        result    = validator.validate(df)
        job       = await self._record_job(upload_type, filename, result, len(df), len(df))
        if not result.is_valid:
            return job

        has_answer_col  = "correct_answer" in df.columns
        has_deleted_col = "is_deleted"     in df.columns

        for _, row in df.iterrows():
            q_no       = int(row["qno"])
            correct_ans = _SAFE_STR(row.get("correct_answer")) if has_answer_col else None
            deleted     = _parse_bool(row.get("is_deleted"))   if has_deleted_col else False

            question = await self._exam_repo.get_question_by_key(
                exam.exam_code, paper_code, q_no
            )
            if not question:
                continue

            if correct_ans:
                correct_ans = convert_option_answer(correct_ans, question.question_type)

            if key_type == "BKC":
                question.correct_option_bkc = correct_ans
                question.is_deleted_bkc     = deleted
            else:  # AKC
                question.correct_option_akc = correct_ans
                question.is_deleted_akc     = deleted

        await self._s.flush()
        return job

    # ── Responses ─────────────────────────────────────────────────────────────

    async def upload_responses(
        self, file_bytes: bytes, filename: str, exam_id: int, paper_code: str
    ) -> UploadJob:
        """
        Wide-format CSV: one row per student, question numbers as column headers.

            admission_no | 1  | 2  | 3  | ...
            257003927    | B  | AC | 5  |

        exam_id and paper_code come from the HTTP form.
        Blank cells are silently skipped (student did not attempt that question).
        """
        auth_vr, exam, _ = await self._check_exam_paper(exam_id, paper_code, filename, "responses")
        if not auth_vr.is_valid:
            return await self._record_job("responses", filename, auth_vr, 0, 0)

        df = pd.read_csv(io.BytesIO(file_bytes), dtype=str)

        # Build question map: {qno: Question}
        questions = await self._exam_repo.get_questions_for_paper(exam_id, paper_code)
        question_map: dict[int, "Question"] = {q.question_no: q for q in questions}
        qtype_map:    dict[int, str]        = {q.question_no: q.question_type for q in questions}

        valid_admissions = await self._student_repo.get_existing_admission_nos()

        validator = ResponseValidator(valid_admissions, qtype_map)
        result    = validator.validate(df)
        job       = await self._record_job("responses", filename, result, len(df), len(df))
        if not result.is_valid:
            return job

        # Identify question columns
        q_cols = [int(c) for c in df.columns if c != "admission_no" and c.strip().lstrip("-").isdigit()]

        response_rows: list[dict] = []
        for _, row in df.iterrows():
            adm = str(row["admission_no"]).strip().upper()
            for qno in q_cols:
                raw = row.get(str(qno))
                if raw is None or (isinstance(raw, float) and pd.isna(raw)):
                    continue
                resp = str(raw).strip()
                if not resp or resp.lower() in ("nan", "none"):
                    continue

                q = question_map.get(qno)
                if q:
                    response_rows.append({
                        "admission_no": adm,
                        "question_id":  q.id,
                        "exam_id":      exam_id,
                        "response_raw": resp,
                    })

        if response_rows:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(OmrResponse).values(response_rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["admission_no", "question_id"],
                set_={"response_raw": stmt.excluded.response_raw,
                      "exam_id":      stmt.excluded.exam_id},
            )
            await self._s.execute(stmt)

        await self._s.flush()
        return job

    # ── OMR scanner responses ─────────────────────────────────────────────────

    async def upload_omr_scanner(
        self, file_bytes: bytes, filename: str, exam_id: int, paper_code: str
    ) -> UploadJob:
        """Parse OMR scanner text format and store responses.

        Line format:  x,<admission_no>,<v1>,<v2>,...
          -1000000  → blank / unattempted (skipped for all question types)
          0         → blank for option questions; valid answer "0" for numerical
          1-5       → A-E for option questions; literal integer for numerical
        """
        from app.validators.response_validator import OmrScannerValidator, omr_to_response

        auth_vr, exam, _ = await self._check_exam_paper(
            exam_id, paper_code, filename, "omr_responses"
        )
        if not auth_vr.is_valid:
            return await self._record_job("omr_responses", filename, auth_vr, 0, 0)

        questions = await self._exam_repo.get_questions_for_paper(exam_id, paper_code)
        if not questions:
            vr = ValidationResult()
            vr.add(0, "questions", "No questions found for this exam paper — upload questions first")
            return await self._record_job("omr_responses", filename, vr, 0, 0)

        # Positional order must match question_no ascending
        questions_sorted = sorted(questions, key=lambda q: q.question_no)
        ordered_qtypes   = [q.question_type for q in questions_sorted]

        valid_admissions = await self._student_repo.get_existing_admission_nos()

        lines = file_bytes.decode("utf-8", errors="replace").splitlines()

        # Count student lines for job tracking
        student_lines = [
            ln for ln in lines
            if ln.strip().split(",")[0].strip().lower() == "x"
        ]

        validator = OmrScannerValidator(valid_admissions, ordered_qtypes)
        result    = validator.validate(lines)
        job       = await self._record_job(
            "omr_responses", filename, result, len(student_lines), len(student_lines)
        )
        if not result.is_valid:
            return job

        response_rows: list[dict] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if parts and parts[-1] == "":
                parts = parts[:-1]
            if not parts or parts[0].lower() != "x":
                continue

            adm       = parts[1].upper()
            val_parts = parts[2:]

            for pos, raw in enumerate(val_parts):
                try:
                    val = int(raw)
                except ValueError:
                    continue

                q    = questions_sorted[pos]
                resp = omr_to_response(val, q.question_type)
                if resp is None:
                    continue

                response_rows.append({
                    "admission_no": adm,
                    "question_id":  q.id,
                    "exam_id":      exam_id,
                    "response_raw": resp,
                })

        if response_rows:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(OmrResponse).values(response_rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["admission_no", "question_id"],
                set_={"response_raw": stmt.excluded.response_raw,
                      "exam_id":      stmt.excluded.exam_id},
            )
            await self._s.execute(stmt)

        await self._s.flush()
        return job

    async def get_upload_job(self, upload_id: int) -> UploadJob | None:
        from sqlalchemy import select
        r = await self._s.execute(select(UploadJob).where(UploadJob.id == upload_id))
        return r.scalar_one_or_none()
