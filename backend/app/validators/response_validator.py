from __future__ import annotations

import pandas as pd

from app.validators.base import ValidationResult

_VALID_OPTIONS = set("ABCDE")

# ── OMR scanner constants ─────────────────────────────────────────────────────
OMR_BLANK   = -1_000_000          # sentinel emitted by scanner for unattempted
_OPTION_MAP = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
_OPTION_TYPES = {"SCQ", "MCQ", "MCQ_MULTI", "PARTIAL_MCQ", "NO_NEGATIVE"}


def omr_to_response(val: int, qtype: str) -> str | None:
    """Convert a raw OMR integer to a response string, or None if blank.

    Option questions (SCQ/MCQ…): 1→A … 5→E; 0 or OMR_BLANK → blank
    Numerical questions:         OMR_BLANK → blank; any other int (incl. 0) → str
    """
    if val == OMR_BLANK:
        return None
    if qtype in _OPTION_TYPES:
        return _OPTION_MAP.get(val)   # None for 0 or out-of-range
    return str(val)                   # 0 is a valid numerical answer


def convert_option_answer(raw: str, qtype: str) -> str:
    """Normalise a correct_answer value using the OMR option map.

    For option questions (SCQ / MCQ / PARTIAL_MCQ …):
      Digit characters are mapped through _OPTION_MAP (1→A … 5→E).
      Letter characters A-E are upper-cased and kept as-is.
      Everything else (0, 6+, commas, spaces) is dropped.

    Examples:
      "2"    SCQ          → "B"
      "24"   MCQ_MULTI    → "BD"
      "B"    SCQ          → "B"   (already a letter — unchanged)
      "ABD"  MCQ_MULTI    → "ABD" (already letters — unchanged)

    For numerical questions the value is returned unchanged.
    """
    if not raw or qtype not in _OPTION_TYPES:
        return raw

    result: list[str] = []
    for ch in raw:
        if ch.isdigit():
            letter = _OPTION_MAP.get(int(ch))
            if letter:
                result.append(letter)
        elif ch.upper() in "ABCDE":
            result.append(ch.upper())
        # commas, spaces, 0, 6+ → dropped
    return "".join(result) if result else raw


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


# ── OMR scanner validator ─────────────────────────────────────────────────────

class OmrScannerValidator:
    """
    Validates OMR scanner text format.

    Each student line:
        x,<admission_no>,<v1>,<v2>,<v3>,...

    • First field must be 'x' (case-insensitive); other rows are silently skipped.
    • admission_no must exist in the student master.
    • Remaining fields are positional responses for Q1, Q2, … Qn in question-number order.
    • Number of response values must match the number of questions in the paper.
    • Every value must be a plain integer (-1000000 = blank sentinel).
    """

    def __init__(
        self,
        valid_admission_nos: set[str],
        ordered_qtypes: list[str],   # question_type in question_no order (1, 2, 3, …)
    ) -> None:
        self._valid_admissions = valid_admission_nos
        self._ordered_qtypes   = ordered_qtypes

    def validate(self, lines: list[str]) -> ValidationResult:
        result   = ValidationResult()
        expected = len(self._ordered_qtypes)
        seen:    set[str] = set()

        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split(",")]
            # drop trailing empty field from trailing comma
            if parts and parts[-1] == "":
                parts = parts[:-1]

            if not parts or parts[0].lower() != "x":
                continue  # header / summary rows — skip silently

            if len(parts) < 2:
                result.add(line_no, "admission_no", "Missing admission number")
                continue

            adm = parts[1].upper()
            if not adm:
                result.add(line_no, "admission_no", "Blank admission number")
                continue
            if adm not in self._valid_admissions:
                result.add(line_no, "admission_no", f"Student not found: {adm!r}")
                continue
            if adm in seen:
                result.add(line_no, "admission_no", f"Duplicate row for student {adm!r}")
                continue
            seen.add(adm)

            val_parts = parts[2:]
            if len(val_parts) != expected:
                result.add(line_no, "columns",
                           f"Expected {expected} response values, got {len(val_parts)}")
                continue

            for pos, raw in enumerate(val_parts):
                try:
                    int(raw)
                except ValueError:
                    result.add(line_no, f"Q{pos + 1}",
                               f"Non-integer value {raw!r} at position {pos + 1}")

        return result
