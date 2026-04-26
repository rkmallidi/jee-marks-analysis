from __future__ import annotations

import pandas as pd

from app.validators.base import ValidationResult

VALID_SUBJECTS       = {"Physics", "Chemistry", "Mathematics"}
VALID_DIFFICULTIES   = {"Easy", "Medium", "Hard", "Very Hard"}
VALID_QUESTION_TYPES = {
    "SCQ",
    "MCQ", "MCQ_MULTI",          # MCQ_MULTI kept for backward compat
    "NUMERICAL_INT",
    "NUMERICAL_DECIMAL",
    "NUMERICAL_RANGE",
    "PARTIAL_MCQ",
}
REQUIRE_CORRECT_OPTION = {
    "SCQ", "MCQ", "MCQ_MULTI", "PARTIAL_MCQ",
    "NUMERICAL_INT", "NUMERICAL_DECIMAL", "NUMERICAL_RANGE",
}
_TRUTHY = {"y", "yes", "true", "1"}

# exam_code and paper_code come from HTTP form params — not the Excel file.
REQUIRED_COLUMNS = {"qno", "subject", "question_type", "marks", "negative_marks"}


def _blank(val) -> bool:
    return val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == ""


def _is_numerical_range(val: str) -> bool:
    """Check if value is a valid range string like '8.5:9.5' or '-3.0:-2.0'."""
    s = val.strip()
    colon_pos = s.find(":", 1)
    if colon_pos == -1:
        return False
    try:
        lo = float(s[:colon_pos])
        hi = float(s[colon_pos + 1:])
        return lo <= hi
    except ValueError:
        return False


class QuestionValidator:
    """
    Validates question upload Excel.

    All answer data is stored in the correct_answer column:
      SCQ / NO_NEGATIVE     →  single option letter, e.g. "B"
      MCQ / MCQ_MULTI       →  option letters, e.g. "ABD"
      PARTIAL_MCQ           →  option letters + partial_marks column
      NUMERICAL_INT         →  exact integer "42"  OR  range "3:7"
      NUMERICAL_DECIMAL     →  exact decimal "3.14"  OR  range "9.95:10.05"
      NUMERICAL_RANGE       →  range "8.5:9.5"
      DELETED               →  no answer required
    """

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        result = ValidationResult()

        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            result.add(0, ",".join(sorted(missing)), f"Missing required columns: {missing}")
            return result

        seen: set[int] = set()

        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # type: ignore[arg-type]

            # ── qno ───────────────────────────────────────────────────────────
            try:
                q_no = int(row["qno"])
            except (TypeError, ValueError):
                result.add(row_num, "qno", "Must be an integer")
                continue

            if q_no in seen:
                result.add(row_num, "qno", f"Duplicate question number: {q_no}")
            else:
                seen.add(q_no)

            # ── subject ───────────────────────────────────────────────────────
            subject = str(row.get("subject", "")).strip()
            if subject not in VALID_SUBJECTS:
                result.add(row_num, "subject", f"Must be one of {sorted(VALID_SUBJECTS)}")

            # ── question_type ─────────────────────────────────────────────────
            qtype = str(row.get("question_type", "")).strip()
            if qtype not in VALID_QUESTION_TYPES:
                result.add(row_num, "question_type",
                           f"Must be one of {sorted(VALID_QUESTION_TYPES)}")
                continue

            # ── marks ─────────────────────────────────────────────────────────
            try:
                pos = float(row["marks"])
                neg = float(row["negative_marks"])
                if pos < 0:
                    result.add(row_num, "marks", "Must be ≥ 0")
                if neg < 0:
                    result.add(row_num, "negative_marks",
                               "Must be ≥ 0 (stored positive, applied as penalty)")
                if neg > pos:
                    result.add(row_num, "negative_marks",
                               f"negative_marks ({neg}) > marks ({pos}) — please review")
            except (TypeError, ValueError):
                result.add(row_num, "marks", "Must be numeric")

            # ── difficulty (optional) ─────────────────────────────────────────
            diff_raw = str(row.get("difficulty", "")).strip()
            if diff_raw and diff_raw not in VALID_DIFFICULTIES:
                result.add(row_num, "difficulty",
                           f"Must be one of {sorted(VALID_DIFFICULTIES)} or blank")

            # ── is_deleted flag ───────────────────────────────────────────────
            is_del_raw = str(row.get("is_deleted", "")).strip().lower()
            if is_del_raw not in ("", "y", "yes", "true", "1", "n", "no", "false", "0"):
                result.add(row_num, "is_deleted", 'Must be Y or N (or blank for N)')
            is_deleted = is_del_raw in _TRUTHY

            # Deleted questions don't need a correct answer
            if is_deleted:
                continue

            if qtype in REQUIRE_CORRECT_OPTION:
                ca = row.get("correct_answer")
                if _blank(ca):
                    result.add(row_num, "correct_answer", f"Required for {qtype}")
                    continue
                ca_str = str(ca).strip()

                if qtype == "NUMERICAL_INT":
                    if not _is_numerical_range(ca_str):
                        try:
                            int(round(float(ca_str)))
                        except ValueError:
                            result.add(row_num, "correct_answer",
                                       'NUMERICAL_INT: use an integer "42" or range "3:7"')

                elif qtype == "NUMERICAL_DECIMAL":
                    if not _is_numerical_range(ca_str):
                        try:
                            float(ca_str)
                        except ValueError:
                            result.add(row_num, "correct_answer",
                                       'NUMERICAL_DECIMAL: use a decimal "3.14" or range "9.95:10.05"')

                elif qtype == "NUMERICAL_RANGE":
                    if not _is_numerical_range(ca_str):
                        result.add(row_num, "correct_answer",
                                   'NUMERICAL_RANGE: use range format "min:max", e.g. "8.5:9.5"')

            if qtype == "PARTIAL_MCQ":
                pm_raw = row.get("partial_marks")
                if _blank(pm_raw):
                    result.add(row_num, "partial_marks", "Required for PARTIAL_MCQ")
                else:
                    try:
                        if float(pm_raw) < 0:
                            result.add(row_num, "partial_marks", "Must be ≥ 0")
                    except (TypeError, ValueError):
                        result.add(row_num, "partial_marks", "Must be numeric")

        return result
