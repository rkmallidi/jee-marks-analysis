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


def _is_valid_scq_option(seg: str) -> bool:
    """A valid SCQ option segment is a single letter (A-Z) or a positive integer (1, 2, 3…)."""
    s = seg.strip().upper()
    if len(s) == 1 and s.isalpha():
        return True
    try:
        return int(s) > 0
    except ValueError:
        return False


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
      SCQ               →  single option letter "B" or number "1", or OR "A|C" / "1|3"
      MCQ / MCQ_MULTI   →  option letters, e.g. "ABD"
      PARTIAL_MCQ       →  option letters + partial_marks column
      NUMERICAL_INT     →  exact integer "42", range "3:7", or OR "8|10"
      NUMERICAL_DECIMAL →  exact decimal "3.14", range "9.95:10.05", or OR "1.5|2.5"
      NUMERICAL_RANGE   →  range "8.5:9.5", or OR "8.5:9.5|11.0:12.0"
      DELETED           →  no answer required
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
                neg = abs(float(row["negative_marks"]))  # accept -1 or 1; stored as positive
                if pos < 0:
                    result.add(row_num, "marks", "Must be ≥ 0")
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

                if qtype == "SCQ":
                    for seg in ca_str.split("|"):
                        if not _is_valid_scq_option(seg):
                            result.add(row_num, "correct_answer",
                                       'SCQ: use a single option "A" or number "1", or OR "A|C"')
                            break

                elif qtype == "NUMERICAL_INT":
                    for seg in ca_str.split("|"):
                        seg = seg.strip()
                        if not seg:
                            result.add(row_num, "correct_answer",
                                       'NUMERICAL_INT: empty segment in OR expression')
                            break
                        if not _is_numerical_range(seg):
                            try:
                                int(round(float(seg)))
                            except ValueError:
                                result.add(row_num, "correct_answer",
                                           'NUMERICAL_INT: use integer "42", range "3:7", or OR "8|10"')
                                break

                elif qtype == "NUMERICAL_DECIMAL":
                    for seg in ca_str.split("|"):
                        seg = seg.strip()
                        if not seg:
                            result.add(row_num, "correct_answer",
                                       'NUMERICAL_DECIMAL: empty segment in OR expression')
                            break
                        if not _is_numerical_range(seg):
                            try:
                                float(seg)
                            except ValueError:
                                result.add(row_num, "correct_answer",
                                           'NUMERICAL_DECIMAL: use decimal "3.14", range "9.95:10.05", or OR "1.5|2.5"')
                                break

                elif qtype == "NUMERICAL_RANGE":
                    for seg in ca_str.split("|"):
                        seg = seg.strip()
                        if not seg or not _is_numerical_range(seg):
                            result.add(row_num, "correct_answer",
                                       'NUMERICAL_RANGE: use range "min:max" or OR "8.5:9.5|11.0:12.0"')
                            break

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
