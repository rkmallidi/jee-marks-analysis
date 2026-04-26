from __future__ import annotations

import re

import pandas as pd

from app.validators.base import ValidationResult

_ADMISSION_RE = re.compile(r"^[A-Z0-9]{5,15}$")

REQUIRED_COLUMNS = {
    "admission_no", "name", "branch_name", "program_name",
    "student_class", "section", "dean",
}


class StudentValidator:
    def __init__(self, existing_admission_nos: set[str]) -> None:
        self._existing = existing_admission_nos

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        result = ValidationResult()

        missing_cols = REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            result.add(0, ",".join(sorted(missing_cols)), f"Missing required columns: {missing_cols}")
            return result

        seen_in_file: set[str] = set()

        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # type: ignore[arg-type]

            adm = str(row.get("admission_no", "")).strip().upper()
            if not adm:
                result.add(row_num, "admission_no", "Required field is blank")
            elif not _ADMISSION_RE.match(adm):
                result.add(row_num, "admission_no", f"Must be 5–15 alphanumeric characters, got {adm!r}")
            elif adm in seen_in_file:
                result.add(row_num, "admission_no", f"Duplicate within file: {adm}")
            else:
                seen_in_file.add(adm)

            name = str(row.get("name", "")).strip()
            if not name:
                result.add(row_num, "name", "Required field is blank")
            elif not (2 <= len(name) <= 150):
                result.add(row_num, "name", f"Length must be 2–150, got {len(name)}")

            branch_name = str(row.get("branch_name", "")).strip()
            if not branch_name:
                result.add(row_num, "branch_name", "Required field is blank")

            program_name = str(row.get("program_name", "")).strip()
            if not program_name:
                result.add(row_num, "program_name", "Required field is blank")

            student_class = str(row.get("student_class", "")).strip()
            if not student_class:
                result.add(row_num, "student_class", "Required field is blank")

            section = str(row.get("section", "")).strip()
            if not (1 <= len(section) <= 10):
                result.add(row_num, "section", "Must be 1–10 chars")

            dean = str(row.get("dean", "")).strip()
            if not dean:
                result.add(row_num, "dean", "Required field is blank")

        return result
