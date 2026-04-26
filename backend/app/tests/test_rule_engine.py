"""
Pytest suite for app.engines.rule_engine.

Run:
    pytest app/tests/test_rule_engine.py -v --tb=short
"""

from __future__ import annotations

import pytest

from app.engines.rule_engine import (
    EVALUATORS,
    DeletedEvaluator,
    GradeResult,
    MCQMultiEvaluator,
    NumericalDecimalEvaluator,
    NumericalIntEvaluator,
    NumericalRangeEvaluator,
    NoNegativeEvaluator,
    PartialMCQEvaluator,
    QuestionRow,
    SCQEvaluator,
    _parse_numerical,
    grade_response,
)


# ── shared fixture ────────────────────────────────────────────────────────────

def q(
    qtype: str,
    pos: float = 4.0,
    neg: float = 1.0,
    partial: float = 1.0,
    correct_option: str | None = None,
) -> QuestionRow:
    return QuestionRow(
        question_type=qtype,
        positive_marks=pos,
        negative_marks=neg,
        partial_marks=partial,
        correct_option=correct_option,
    )


# ── _parse_numerical ──────────────────────────────────────────────────────────

class TestParseNumerical:
    def test_exact_int(self):
        assert _parse_numerical("42") == (42.0, None, None)

    def test_exact_decimal(self):
        exact, _, _ = _parse_numerical("3.14")
        assert exact == pytest.approx(3.14)

    def test_range(self):
        exact, lo, hi = _parse_numerical("8.5:9.5")
        assert exact is None
        assert lo == pytest.approx(8.5)
        assert hi == pytest.approx(9.5)

    def test_negative_exact(self):
        exact, _, _ = _parse_numerical("-5")
        assert exact == pytest.approx(-5.0)

    def test_negative_range(self):
        _, lo, hi = _parse_numerical("-3.0:-2.0")
        assert lo == pytest.approx(-3.0)
        assert hi == pytest.approx(-2.0)

    def test_blank(self):
        assert _parse_numerical(None) == (None, None, None)
        assert _parse_numerical("") == (None, None, None)


# ── SCQ ──────────────────────────────────────────────────────────────────────

class TestSCQEvaluator:
    ev = SCQEvaluator()

    def _grade(self, resp: str, correct: str = "B", pos=4.0, neg=1.0) -> GradeResult:
        return self.ev.grade(resp, q("SCQ", pos=pos, neg=neg, correct_option=correct))

    def test_correct(self):
        r = self._grade("B")
        assert r.marks_awarded == pytest.approx(4.0)
        assert r.verdict == "correct"
        assert r.is_attempted is True

    def test_correct_lowercase_normalised(self):
        assert self._grade("b").verdict == "correct"

    def test_wrong(self):
        r = self._grade("A")
        assert r.marks_awarded == pytest.approx(-1.0)
        assert r.verdict == "wrong"

    def test_blank(self):
        r = self._grade("")
        assert r.marks_awarded == pytest.approx(0.0)
        assert r.verdict == "blank"
        assert r.is_attempted is False

    def test_null_string_as_blank(self):
        assert self._grade("null").verdict == "blank"

    def test_none_as_blank(self):
        assert self.ev.grade(None, q("SCQ", correct_option="B")).verdict == "blank"  # type: ignore[arg-type]

    def test_zero_negative_marks(self):
        r = self._grade("C", "B", neg=0.0)
        assert r.marks_awarded == pytest.approx(0.0)
        assert r.verdict == "wrong"

    def test_custom_marks(self):
        r = self._grade("A", "A", pos=3.0)
        assert r.marks_awarded == pytest.approx(3.0)


# ── MCQ / MCQ_MULTI ───────────────────────────────────────────────────────────

class TestMCQMultiEvaluator:
    ev = MCQMultiEvaluator()

    def _grade(self, resp: str, correct: str, pos=4.0, neg=1.0) -> GradeResult:
        return self.ev.grade(resp, q("MCQ", pos=pos, neg=neg, correct_option=correct))

    def test_full_correct_single(self):
        assert self._grade("A", "A").verdict == "correct"

    def test_full_correct_multi(self):
        assert self._grade("ABD", "ABD").marks_awarded == pytest.approx(4.0)

    def test_order_independent(self):
        assert self._grade("DBA", "ABD").verdict == "correct"

    def test_partial_one_of_three(self):
        r = self._grade("A", "ABD", pos=4.0)
        assert r.marks_awarded == pytest.approx(1.0)
        assert r.verdict == "partial"

    def test_partial_two_of_three(self):
        assert self._grade("AB", "ABD", pos=4.0).marks_awarded == pytest.approx(2.0)

    def test_partial_cap_at_pos_minus_1(self):
        assert self._grade("ABC", "ABCD", pos=3.0).marks_awarded == pytest.approx(2.0)

    def test_wrong_extra_option(self):
        r = self._grade("ABC", "AB")
        assert r.marks_awarded == pytest.approx(-1.0)
        assert r.verdict == "wrong"

    def test_blank(self):
        r = self._grade("", "AB")
        assert r.verdict == "blank"
        assert r.is_attempted is False

    def test_dedup_options(self):
        assert self._grade("AABB", "AB").verdict == "correct"

    def test_mcq_alias_same_as_mcq_multi(self):
        assert EVALUATORS["MCQ"] is EVALUATORS["MCQ_MULTI"]


# ── NUMERICAL_INT ─────────────────────────────────────────────────────────────

class TestNumericalIntEvaluator:
    ev = NumericalIntEvaluator()

    def test_exact_match(self):
        r = self.ev.grade("42", q("NUMERICAL_INT", neg=0.0, correct_option="42"))
        assert r.marks_awarded == pytest.approx(4.0)
        assert r.verdict == "correct"

    def test_float_input_equivalent(self):
        r = self.ev.grade("42.0", q("NUMERICAL_INT", neg=0.0, correct_option="42"))
        assert r.verdict == "correct"

    def test_wrong(self):
        r = self.ev.grade("43", q("NUMERICAL_INT", neg=0.0, correct_option="42"))
        assert r.marks_awarded == pytest.approx(0.0)
        assert r.verdict == "wrong"

    def test_no_negative_marks(self):
        r = self.ev.grade("0", q("NUMERICAL_INT", neg=1.0, correct_option="42"))
        assert r.marks_awarded == pytest.approx(0.0)

    def test_blank(self):
        assert self.ev.grade("", q("NUMERICAL_INT", correct_option="42")).verdict == "blank"

    def test_non_numeric(self):
        r = self.ev.grade("abc", q("NUMERICAL_INT", correct_option="42"))
        assert r.verdict == "wrong"

    def test_range_match(self):
        r = self.ev.grade("5", q("NUMERICAL_INT", neg=0.0, correct_option="3:7"))
        assert r.verdict == "correct"

    def test_out_of_range(self):
        r = self.ev.grade("8", q("NUMERICAL_INT", neg=0.0, correct_option="3:7"))
        assert r.verdict == "wrong"

    def test_negative_answer(self):
        r = self.ev.grade("-5", q("NUMERICAL_INT", correct_option="-5"))
        assert r.verdict == "correct"


# ── NUMERICAL_DECIMAL ─────────────────────────────────────────────────────────

class TestNumericalDecimalEvaluator:
    ev = NumericalDecimalEvaluator()

    def test_range_match(self):
        r = self.ev.grade("3.14", q("NUMERICAL_DECIMAL", correct_option="3.0:3.5"))
        assert r.verdict == "correct"
        assert r.marks_awarded == pytest.approx(4.0)

    def test_rounds_to_2dp(self):
        """3.145 rounds to 3.15, which is within [3.0, 3.5]."""
        r = self.ev.grade("3.145", q("NUMERICAL_DECIMAL", correct_option="3.0:3.5"))
        assert r.verdict == "correct"

    def test_exact_match(self):
        r = self.ev.grade("3.14", q("NUMERICAL_DECIMAL", correct_option="3.14"))
        assert r.verdict == "correct"

    def test_out_of_range(self):
        r = self.ev.grade("9.0", q("NUMERICAL_DECIMAL", correct_option="9.95:10.05"))
        assert r.verdict == "wrong"

    def test_blank(self):
        assert self.ev.grade("", q("NUMERICAL_DECIMAL", correct_option="1.0:2.0")).verdict == "blank"

    def test_non_numeric(self):
        assert self.ev.grade("abc", q("NUMERICAL_DECIMAL", correct_option="1.0:2.0")).verdict == "wrong"

    def test_no_negative_marks(self):
        r = self.ev.grade("100.0", q("NUMERICAL_DECIMAL", neg=2.0, correct_option="1.0:2.0"))
        assert r.marks_awarded == pytest.approx(0.0)


# ── NUMERICAL_RANGE ───────────────────────────────────────────────────────────

class TestNumericalRangeEvaluator:
    ev = NumericalRangeEvaluator()

    def _grade(self, resp: str, range_str: str) -> GradeResult:
        return self.ev.grade(resp, q("NUMERICAL_RANGE", neg=0.0, correct_option=range_str))

    def test_within_range(self):
        assert self._grade("3.14", "3.0:3.5").verdict == "correct"

    def test_on_lower_bound(self):
        assert self._grade("3.0", "3.0:3.5").verdict == "correct"

    def test_on_upper_bound(self):
        assert self._grade("3.5", "3.0:3.5").verdict == "correct"

    def test_below_range(self):
        assert self._grade("2.9", "3.0:3.5").verdict == "wrong"

    def test_above_range(self):
        assert self._grade("3.6", "3.0:3.5").verdict == "wrong"

    def test_blank(self):
        assert self._grade("", "3.0:3.5").verdict == "blank"

    def test_non_numeric(self):
        assert self._grade("xyz", "3.0:3.5").verdict == "wrong"

    def test_negative_range(self):
        assert self._grade("-2.5", "-3.0:-2.0").verdict == "correct"

    def test_no_option_wrong(self):
        r = self.ev.grade("3.14", q("NUMERICAL_RANGE"))
        assert r.verdict == "wrong"


# ── PARTIAL_MCQ ───────────────────────────────────────────────────────────────

class TestPartialMCQEvaluator:
    ev = PartialMCQEvaluator()

    def _grade(self, resp: str, correct: str = "B", pos=4.0, neg=1.0, partial=1.0) -> GradeResult:
        return self.ev.grade(resp, q("PARTIAL_MCQ", pos=pos, neg=neg, partial=partial, correct_option=correct))

    def test_correct(self):
        r = self._grade("B")
        assert r.marks_awarded == pytest.approx(4.0)
        assert r.verdict == "correct"

    def test_wrong(self):
        r = self._grade("A")
        assert r.marks_awarded == pytest.approx(-1.0)
        assert r.verdict == "wrong"

    def test_blank(self):
        assert self._grade("").verdict == "blank"

    def test_partial_flat(self):
        r = self._grade("A", correct="AB", partial=2.0)
        assert r.marks_awarded == pytest.approx(2.0)
        assert r.verdict == "partial"

    def test_extra_selection_is_wrong(self):
        assert self._grade("ABC", correct="AB").verdict == "wrong"


# ── NO_NEGATIVE ───────────────────────────────────────────────────────────────

class TestNoNegativeEvaluator:
    ev = NoNegativeEvaluator()

    def test_correct(self):
        r = self.ev.grade("C", q("NO_NEGATIVE", correct_option="C"))
        assert r.marks_awarded == pytest.approx(4.0)
        assert r.verdict == "correct"

    def test_wrong_no_deduction(self):
        r = self.ev.grade("A", q("NO_NEGATIVE", neg=2.0, correct_option="C"))
        assert r.marks_awarded == pytest.approx(0.0)
        assert r.verdict == "wrong"

    def test_blank(self):
        assert self.ev.grade("", q("NO_NEGATIVE", correct_option="C")).verdict == "blank"


# ── DELETED ───────────────────────────────────────────────────────────────────

class TestDeletedEvaluator:
    ev = DeletedEvaluator()

    def test_blank_gets_bonus(self):
        r = self.ev.grade("", q("DELETED", pos=4.0))
        assert r.marks_awarded == pytest.approx(4.0)
        assert r.verdict == "bonus"
        assert r.is_attempted is False

    def test_answered_gets_bonus(self):
        r = self.ev.grade("A", q("DELETED", pos=4.0))
        assert r.marks_awarded == pytest.approx(4.0)
        assert r.verdict == "bonus"
        assert r.is_attempted is True

    def test_wrong_still_gets_bonus(self):
        r = self.ev.grade("D", q("DELETED", pos=4.0))
        assert r.verdict == "bonus"
        assert r.marks_awarded == pytest.approx(4.0)


# ── Registry ──────────────────────────────────────────────────────────────────

class TestEvaluatorsRegistry:
    def test_all_types_present(self):
        expected = {
            "SCQ", "MCQ", "MCQ_MULTI",
            "NUMERICAL_INT", "NUMERICAL_DECIMAL", "NUMERICAL_RANGE",
            "PARTIAL_MCQ", "NO_NEGATIVE", "DELETED",
        }
        assert set(EVALUATORS.keys()) == expected

    def test_all_have_grade_method(self):
        for name, cls in EVALUATORS.items():
            assert hasattr(cls(), "grade"), f"{name} missing .grade()"

    def test_mcq_alias(self):
        assert EVALUATORS["MCQ"] is EVALUATORS["MCQ_MULTI"]


# ── grade_response dispatcher ─────────────────────────────────────────────────

class TestGradeResponseDispatcher:
    def test_scq(self):
        assert grade_response("A", q("SCQ", correct_option="A")).verdict == "correct"

    def test_mcq(self):
        assert grade_response("AB", q("MCQ", correct_option="AB")).verdict == "correct"

    def test_numerical_int_exact(self):
        assert grade_response("7", q("NUMERICAL_INT", correct_option="7")).verdict == "correct"

    def test_numerical_int_range(self):
        assert grade_response("5", q("NUMERICAL_INT", correct_option="3:7")).verdict == "correct"

    def test_numerical_decimal_exact(self):
        assert grade_response("3.14", q("NUMERICAL_DECIMAL", correct_option="3.14")).verdict == "correct"

    def test_numerical_decimal_range(self):
        assert grade_response("3.14", q("NUMERICAL_DECIMAL", correct_option="3.0:3.5")).verdict == "correct"

    def test_numerical_range(self):
        assert grade_response("1.5", q("NUMERICAL_RANGE", correct_option="1.0:2.0")).verdict == "correct"

    def test_deleted_gives_bonus(self):
        assert grade_response("B", q("DELETED", pos=4.0)).verdict == "bonus"

    def test_unknown_type_raises(self):
        with pytest.raises(KeyError):
            grade_response("A", q("BOGUS", correct_option="A"))


# ── Normalisation edge-cases ──────────────────────────────────────────────────

BLANK_INPUTS = ["", " ", "  ", None, "null", "NULL", "none", "NONE", "blank", "BLANK"]

@pytest.mark.parametrize("blank", BLANK_INPUTS)
def test_scq_blank_variants(blank):
    r = grade_response(blank, q("SCQ", correct_option="A"))  # type: ignore[arg-type]
    assert r.verdict == "blank"
    assert r.is_attempted is False

@pytest.mark.parametrize("blank", BLANK_INPUTS)
def test_numerical_int_blank_variants(blank):
    r = grade_response(blank, q("NUMERICAL_INT", correct_option="42"))  # type: ignore[arg-type]
    assert r.verdict == "blank"

@pytest.mark.parametrize("blank", BLANK_INPUTS)
def test_mcq_blank_variants(blank):
    r = grade_response(blank, q("MCQ", correct_option="A"))  # type: ignore[arg-type]
    assert r.verdict == "blank"


# ── GradeResult immutability ──────────────────────────────────────────────────

def test_grade_result_frozen():
    r = GradeResult(marks_awarded=4.0, verdict="correct", is_attempted=True)
    with pytest.raises((AttributeError, TypeError)):
        r.marks_awarded = 0.0  # type: ignore[misc]

def test_grade_result_fields():
    r = GradeResult(marks_awarded=-1.0, verdict="wrong", is_attempted=True)
    assert r.marks_awarded == -1.0
    assert r.verdict == "wrong"
    assert r.is_attempted is True
