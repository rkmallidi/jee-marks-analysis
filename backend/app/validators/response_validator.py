from __future__ import annotations

import pandas as pd

from app.validators.base import ValidationResult

_VALID_OPTIONS = set("ABCDE")


class ResponseValidator:
    """
    Validates wide-format OMR response CSV.

    Expected layout:
        admission_no | 1  | 2  | 3  | ...
        257003927    | B  | AC | 5  |
        257003925    | A  |    | 3  |

    Column names after 'admission_no' are question numbers (integers).
    Blank cells = not attempted (valid, skipped during import).
    exam_id and paper_code come from the HTTP form — not the file.
    """

    def __init__(
        self,
        valid_admission_nos: set[str],
        question_map: dict[int, str],   # qno → question_type
    ) -> None:
        self._valid_admissions = valid_admission_nos
        self._question_map     = question_map

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        result = ValidationResult()

        if "admission_no" not in df.columns:
            result.add(0, "admission_no", "Missing required column: admission_no")
            return result

        # Identify question columns (all columns except admission_no)
        q_cols: list[int] = []
        for col in df.columns:
            if col == "admission_no":
                continue
            try:
                q_cols.append(int(col))
            except (TypeError, ValueError):
                result.add(0, str(col), f"Column name {col!r} is not a valid question number")

        unknown_qs = set(q_cols) - set(self._question_map.keys())
        if unknown_qs:
            result.add(0, "columns",
                       f"Question numbers not found in this paper: {sorted(unknown_qs)}")
            return result

        seen_admissions: set[str] = set()

        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # type: ignore[arg-type]
            adm = str(row.get("admission_no", "")).strip().upper()

            if not adm:
                result.add(row_num, "admission_no", "Admission number is blank")
                continue

            if adm not in self._valid_admissions:
                result.add(row_num, "admission_no", f"Student not found: {adm!r}")
                continue

            if adm in seen_admissions:
                result.add(row_num, "admission_no", f"Duplicate row for student {adm!r}")
                continue
            seen_admissions.add(adm)

            for qno in q_cols:
                raw = row.get(str(qno))
                if raw is None or (isinstance(raw, float) and pd.isna(raw)):
                    continue  # blank = not attempted, always valid
                resp = str(raw).strip()
                if not resp:
                    continue

                qtype = self._question_map[qno]
                self._validate_cell(result, row_num, qno, resp, qtype)

        return result

    def _validate_cell(
        self, result: ValidationResult, row_num: int, qno: int, resp: str, qtype: str
    ) -> None:
        if qtype in ("SCQ", "MCQ", "MCQ_MULTI", "PARTIAL_MCQ"):
            for letter in resp.replace(",", ""):
                if letter.strip().upper() not in _VALID_OPTIONS:
                    result.add(row_num, str(qno),
                               f"Invalid option {letter!r} for {qtype} (expected A-E)")
                    return

        elif qtype == "NUMERICAL_INT":
            try:
                int(resp)
            except ValueError:
                result.add(row_num, str(qno),
                           f"Must be an integer for NUMERICAL_INT, got {resp!r}")

        elif qtype in ("NUMERICAL_DECIMAL", "NUMERICAL_RANGE"):
            try:
                float(resp)
            except ValueError:
                result.add(row_num, str(qno),
                           f"Must be numeric for {qtype}, got {resp!r}")
