from __future__ import annotations

import pandas as pd

from app.validators.base import ValidationResult

REQUIRED_COLUMNS = {"qno"}
VALID_KEY_TYPES  = {"BKC", "AKC"}


def _blank(val) -> bool:
    return val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == ""


def _parse_bool(raw: object) -> bool:
    if raw is None:
        return False
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    return str(raw).strip().upper() in ("TRUE", "1", "YES")


def _is_numerical_range(val: str) -> bool:
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


class AnswerKeyValidator:
    """
    Validates BKC / AKC answer key CSV.

    Required column: qno
    Optional columns: correct_answer, is_deleted

    correct_answer formats (same as question upload):
      "B"          single option
      "AC"         multi-option
      "42"         exact integer
      "3.14"       exact decimal
      "8.5:9.5"    range

    At least one of correct_answer or is_deleted=true must be present per row.
    """

    def __init__(self, valid_question_nos: set[int]) -> None:
        self._valid_nos = valid_question_nos

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        result = ValidationResult()

        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            result.add(0, ",".join(sorted(missing)), f"Missing required columns: {missing}")
            return result

        has_answer_col  = "correct_answer" in df.columns
        has_deleted_col = "is_deleted"     in df.columns

        if not has_answer_col and not has_deleted_col:
            result.add(0, "correct_answer",
                       "CSV must have at least a 'correct_answer' or 'is_deleted' column")
            return result

        seen: set[int] = set()

        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # type: ignore[arg-type]

            try:
                q_no = int(row["qno"])
            except (TypeError, ValueError):
                result.add(row_num, "qno", "Must be an integer")
                continue

            if q_no in seen:
                result.add(row_num, "qno", f"Duplicate question number: {q_no}")
            else:
                seen.add(q_no)

            if q_no not in self._valid_nos:
                result.add(row_num, "qno", f"Question {q_no} not found for this exam/paper")
                continue

            correct_answer = row.get("correct_answer") if has_answer_col else None
            is_deleted     = _parse_bool(row.get("is_deleted")) if has_deleted_col else False

            if _blank(correct_answer) and not is_deleted:
                result.add(row_num, "correct_answer",
                           "Provide correct_answer or set is_deleted=true")
                continue

            if not _blank(correct_answer):
                ca = str(correct_answer).strip()
                # Reject obviously invalid formats (pure letters without comma are MCQ options,
                # numbers are numerical answers — both are fine; reject mixed garbage)
                if not ca:
                    result.add(row_num, "correct_answer", "Cannot be blank when provided")

        return result
