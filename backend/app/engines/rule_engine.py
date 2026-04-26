from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable


# ── Data contracts ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class QuestionRow:
    question_type:  str
    positive_marks: float
    negative_marks: float
    partial_marks:  float
    correct_option: str | None   # all answer data lives here


@dataclass(frozen=True)
class GradeResult:
    marks_awarded: float
    verdict:       Literal["correct", "wrong", "partial", "blank", "bonus"]
    is_attempted:  bool


# ── Protocol ───────────────────────────────────────────────────────────────────

@runtime_checkable
class Evaluator(Protocol):
    def grade(self, response_raw: str, question: QuestionRow) -> GradeResult: ...


# ── Normalisation helpers ──────────────────────────────────────────────────────

def _normalise(response_raw: str) -> str:
    """Strip whitespace; treat 'blank'/'none'/'null'/'' as empty."""
    cleaned = response_raw.strip().lower()
    if cleaned in ("", "blank", "none", "null"):
        return ""
    return cleaned


def _parse_options(raw: str) -> frozenset[str]:
    """
    Parse a student response into a set of option letters.
    Handles both comma-separated ('A,C') and concatenated ('AC') formats.
    """
    s = raw.strip().upper()
    if not s:
        return frozenset()
    if "," in s:
        return frozenset(p.strip() for p in s.split(",") if p.strip())
    # No comma — each character is a separate option letter
    return frozenset(c for c in s if c.strip())


def _correct_options(question: QuestionRow) -> frozenset[str]:
    """
    Parse the stored correct_option string into a set of option letters.
    Correct answers are stored concatenated ('ACD') or comma-separated ('A,C,D').
    """
    raw = (question.correct_option or "").strip().upper()
    if not raw:
        return frozenset()
    if "," in raw:
        return frozenset(p.strip() for p in raw.split(",") if p.strip())
    return frozenset(c for c in raw if c.strip())


def _parse_numerical(correct_option: str | None) -> tuple[float | None, float | None, float | None]:
    """
    Parse numerical answer stored as a string in correct_option.

    Formats accepted:
      "42"          → exact answer 42.0
      "3.14"        → exact answer 3.14
      "8.5:9.5"     → range [8.5, 9.5]
      "-3.0:-2.0"   → range [-3.0, -2.0]

    Returns (exact, range_min, range_max).  All three are None when input is blank.
    """
    if not correct_option or not correct_option.strip():
        return None, None, None

    s = correct_option.strip()
    # Range: contains ':' not as part of a negative sign
    # Split on first ':' that isn't the very start of the string
    colon_pos = s.find(":", 1)   # skip index 0 so "-5" isn't split
    if colon_pos != -1:
        try:
            lo = float(s[:colon_pos])
            hi = float(s[colon_pos + 1:])
            return None, lo, hi
        except ValueError:
            return None, None, None

    try:
        return float(s), None, None
    except ValueError:
        return None, None, None


# ── Evaluators ─────────────────────────────────────────────────────────────────

class SCQEvaluator:
    """Single-correct: +positive on match, −negative on wrong, 0 on blank."""

    def grade(self, response_raw: str, question: QuestionRow) -> GradeResult:
        norm = _normalise(response_raw)
        if not norm:
            return GradeResult(0.0, "blank", False)

        selected = _parse_options(norm)
        correct  = _correct_options(question)

        if selected == correct:
            return GradeResult(question.positive_marks, "correct", True)
        return GradeResult(-question.negative_marks, "wrong", True)


class MCQMultiEvaluator:
    """
    JEE Advanced multi-correct MCQ.

    • All correct options, no wrong  →  +positive_marks
    • Subset of correct, no wrong    →  +1 per correct selected, capped at (positive − 1)
    • Any wrong option               →  −negative_marks  (no partial credit)
    • Blank                          →  0
    """

    def grade(self, response_raw: str, question: QuestionRow) -> GradeResult:
        norm = _normalise(response_raw)
        if not norm:
            return GradeResult(0.0, "blank", False)

        selected = _parse_options(norm)
        correct  = _correct_options(question)
        pos      = question.positive_marks

        wrong_selected = selected - correct
        if wrong_selected:
            return GradeResult(-question.negative_marks, "wrong", True)

        if selected == correct:
            return GradeResult(pos, "correct", True)

        # Subset of correct options, no wrong → partial (+1 per correct, cap = pos−1)
        partial = min(float(len(selected)), pos - 1.0)
        return GradeResult(partial, "partial", True)


class NumericalIntEvaluator:
    """
    Integer numerical.  correct_option holds "42" (exact) or "3:7" (range).
    No negative marking.
    """

    def grade(self, response_raw: str, question: QuestionRow) -> GradeResult:
        norm = _normalise(response_raw)
        if not norm:
            return GradeResult(0.0, "blank", False)

        try:
            given = int(round(float(norm)))
        except ValueError:
            return GradeResult(0.0, "wrong", True)

        exact, rmin, rmax = _parse_numerical(question.correct_option)
        pos = question.positive_marks

        if exact is not None and given == int(round(exact)):
            return GradeResult(pos, "correct", True)
        if rmin is not None and rmax is not None and int(round(rmin)) <= given <= int(round(rmax)):
            return GradeResult(pos, "correct", True)

        return GradeResult(0.0, "wrong", True)


class NumericalDecimalEvaluator:
    """
    Decimal numerical: student answer rounded to 2 dp.
    correct_option holds "3.14" (exact) or "9.95:10.05" (range).
    No negative marking.
    """

    def grade(self, response_raw: str, question: QuestionRow) -> GradeResult:
        norm = _normalise(response_raw)
        if not norm:
            return GradeResult(0.0, "blank", False)

        try:
            given = round(float(norm), 2)
        except ValueError:
            return GradeResult(0.0, "wrong", True)

        exact, rmin, rmax = _parse_numerical(question.correct_option)
        pos = question.positive_marks

        if exact is not None and given == round(exact, 2):
            return GradeResult(pos, "correct", True)
        if rmin is not None and rmax is not None and rmin <= given <= rmax:
            return GradeResult(pos, "correct", True)

        return GradeResult(0.0, "wrong", True)


class NumericalRangeEvaluator:
    """
    Range numerical.  correct_option holds "8.5:9.5".
    """

    def grade(self, response_raw: str, question: QuestionRow) -> GradeResult:
        norm = _normalise(response_raw)
        if not norm:
            return GradeResult(0.0, "blank", False)

        try:
            given = float(norm)
        except ValueError:
            return GradeResult(0.0, "wrong", True)

        _, rmin, rmax = _parse_numerical(question.correct_option)
        pos = question.positive_marks

        if rmin is not None and rmax is not None and rmin <= given <= rmax:
            return GradeResult(pos, "correct", True)

        return GradeResult(0.0, "wrong", True)


class PartialMCQEvaluator:
    """
    Flat partial credit variant (used in some JEE Advanced sections).

    • All correct, no wrong     →  +positive_marks
    • Subset correct, no wrong  →  +partial_marks (flat, NOT per-option)
    • Any wrong                 →  −negative_marks
    • Blank                     →  0
    """

    def grade(self, response_raw: str, question: QuestionRow) -> GradeResult:
        norm = _normalise(response_raw)
        if not norm:
            return GradeResult(0.0, "blank", False)

        selected = _parse_options(norm)
        correct  = _correct_options(question)
        pos      = question.positive_marks

        wrong_selected = selected - correct
        if wrong_selected:
            return GradeResult(-question.negative_marks, "wrong", True)

        if selected == correct:
            return GradeResult(pos, "correct", True)

        return GradeResult(question.partial_marks, "partial", True)


class DeletedEvaluator:
    """
    Deleted question: always awards positive_marks as "bonus" to every student.
    Excluded from accuracy, attempt, and negative-mark metrics in analytics.
    is_attempted reflects whether the student actually filled a response.
    """

    def grade(self, response_raw: str, question: QuestionRow) -> GradeResult:
        norm         = _normalise(response_raw)
        is_attempted = bool(norm)
        return GradeResult(question.positive_marks, "bonus", is_attempted)


# ── Registry + dispatcher ──────────────────────────────────────────────────────

EVALUATORS: dict[str, type[Evaluator]] = {
    "SCQ":               SCQEvaluator,
    "MCQ":               MCQMultiEvaluator,   # preferred alias
    "MCQ_MULTI":         MCQMultiEvaluator,   # kept for backward compatibility
    "NUMERICAL_INT":     NumericalIntEvaluator,
    "NUMERICAL_DECIMAL": NumericalDecimalEvaluator,
    "NUMERICAL_RANGE":   NumericalRangeEvaluator,
    "PARTIAL_MCQ":       PartialMCQEvaluator,
    "DELETED":           DeletedEvaluator,
    # Legacy aliases — kept for backward compatibility with existing DB data
    "NO_NEGATIVE":       SCQEvaluator,        # equivalent to SCQ with negative_marks=0
}


def grade_response(response_raw: str, question: QuestionRow) -> GradeResult:
    """Dispatch to the correct evaluator. Returns a blank result for unknown types."""
    evaluator_cls = EVALUATORS.get(question.question_type)
    if evaluator_cls is None:
        return GradeResult(0.0, "blank", False)
    return evaluator_cls().grade(response_raw, question)
