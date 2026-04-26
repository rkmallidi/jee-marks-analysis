from __future__ import annotations

"""
Analytics engine — pure computation, no I/O.

PostgreSQL does the heavy lifting for ranking and percentile calculations
via window functions pushed down through the repository layer.
This module handles the Python-side aggregation that feeds those queries,
and provides the dataclasses the repository maps results into.
"""

import statistics
from dataclasses import dataclass, field
from typing import Any


# ── Input contracts ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GradedRow:
    admission_no:  str
    question_id:   int
    subject:       str
    topic:         str
    marks_awarded: float
    positive_marks: float
    verdict:       str
    is_attempted:  bool
    submitted_at:  float  # unix timestamp for tie-breaking


@dataclass(frozen=True)
class StudentMeta:
    admission_no: str
    branch_name:  str
    program_name: str
    section:      str


# ── Output contracts ───────────────────────────────────────────────────────────

@dataclass
class StudentExamRow:
    admission_no:    str
    exam_id:         int
    total_marks:     float
    max_marks:       float
    percentage:      float
    attempted_count: int
    correct_count:   int
    partial_count:   int
    wrong_count:     int
    blank_count:     int
    negative_marks:  float
    rank_overall:    int | None = None
    rank_branch:     int | None = None
    rank_program:    int | None = None
    rank_section:    int | None = None
    percentile_overall: float | None = None


@dataclass
class StudentSubjectRow:
    admission_no:   str
    exam_id:        int
    subject:        str
    marks:          float
    max_marks:      float
    accuracy:       float
    attempted:      int
    correct:        int
    partial_count:  int = 0
    wrong:          int = 0
    blank:          int = 0
    negative_marks: float = 0.0
    rank_subject:   int | None = None


@dataclass
class StudentTopicRow:
    admission_no: str
    exam_id:      int
    subject:    str
    topic:      str
    marks:      float
    max_marks:  float
    attempted:  int
    correct:    int
    accuracy:   float


@dataclass
class RankSummaryRow:
    exam_id:         int
    scope:           str
    scope_value:     str
    cutoff_top1pct:  float | None
    cutoff_top5pct:  float | None
    cutoff_top10pct: float | None
    cutoff_top25pct: float | None
    cutoff_median:   float | None


@dataclass
class AggregateSummaryRow:
    exam_id:     int
    scope:       str
    scope_value: str
    subject:     str
    avg:         float | None
    median:      float | None
    stdev:       float | None
    min_score:   float | None
    max_score:   float | None
    n_students:  int


@dataclass
class AnalyticsBundle:
    exam_summaries:    list[StudentExamRow]
    subject_summaries: list[StudentSubjectRow]
    topic_summaries:   list[StudentTopicRow]
    rank_summaries:    list[RankSummaryRow]
    agg_summaries:     list[AggregateSummaryRow]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _percentile(scores: list[float], pct: float) -> float | None:
    """Top-N% cutoff. pct=1 means top 1%."""
    if not scores:
        return None
    sorted_s = sorted(scores, reverse=True)
    idx = max(0, int(len(sorted_s) * pct / 100) - 1)
    return sorted_s[idx]


def _dense_rank_rows(rows: list[StudentExamRow]) -> list[tuple[StudentExamRow, int]]:
    """
    Dense ranking with three-level tie-breaker:
      1. total_marks  (desc)
      2. accuracy = correct / attempted  (desc)
      3. negative_marks  (asc — less negative is better)
    """
    if not rows:
        return []

    def sort_key(r: StudentExamRow) -> tuple[float, float, float]:
        acc = r.correct_count / max(r.attempted_count, 1)
        return (-r.total_marks, -acc, r.negative_marks)

    sorted_rows = sorted(rows, key=sort_key)
    ranked: list[tuple[StudentExamRow, int]] = []
    for i, row in enumerate(sorted_rows):
        if i == 0:
            ranked.append((row, 1))
        else:
            prev = sorted_rows[i - 1]
            same = (
                row.total_marks == prev.total_marks
                and (row.correct_count / max(row.attempted_count, 1))
                   == (prev.correct_count / max(prev.attempted_count, 1))
                and row.negative_marks == prev.negative_marks
            )
            ranked.append((row, ranked[-1][1] if same else i + 1))
    return ranked


# ── Core computation ───────────────────────────────────────────────────────────

def compute_analytics(
    exam_id:           int,
    graded_rows:       list[GradedRow],
    student_meta:      dict[str, StudentMeta],
    paper_max_marks:   float = 0.0,
    subject_max_marks: dict[str, float] | None = None,
) -> AnalyticsBundle:
    """
    Pure Python aggregation. No I/O.
    PostgreSQL window functions (DENSE_RANK, PERCENTILE_CONT) are used for
    the final ranking/percentile writes; this function prepares the per-student
    raw aggregates that feed those queries.
    """

    # ── Aggregate per student ──────────────────────────────────────────────────
    totals:   dict[str, float] = {}
    max_m:    dict[str, float] = {}
    attempted: dict[str, int]  = {}
    correct:  dict[str, int]   = {}
    partial:  dict[str, int]   = {}
    wrong:    dict[str, int]   = {}
    blank:    dict[str, int]   = {}
    neg_m:    dict[str, float] = {}

    subj_marks:    dict[tuple[str, str], float] = {}
    subj_max:      dict[tuple[str, str], float] = {}
    subj_att:      dict[tuple[str, str], int]   = {}
    subj_corr:     dict[tuple[str, str], int]   = {}
    subj_partial:  dict[tuple[str, str], int]   = {}
    subj_wrong:    dict[tuple[str, str], int]   = {}
    subj_blank:    dict[tuple[str, str], int]   = {}
    subj_neg:      dict[tuple[str, str], float] = {}

    topic_marks:   dict[tuple[str, str, str], float] = {}
    topic_max:     dict[tuple[str, str, str], float] = {}
    topic_att:     dict[tuple[str, str, str], int]   = {}
    topic_corr:    dict[tuple[str, str, str], int]   = {}
    topic_subject: dict[tuple[str, str], str]        = {}

    for r in graded_rows:
        sid      = r.admission_no
        sk       = (sid, r.subject)
        tk       = (sid, r.subject, r.topic)
        is_bonus = r.verdict == "bonus"  # deleted question — marks awarded but excluded from metrics

        totals[sid] = totals.get(sid, 0.0) + r.marks_awarded
        max_m[sid]  = max_m.get(sid, 0.0)  + r.positive_marks

        if not is_bonus:
            if r.is_attempted:
                attempted[sid] = attempted.get(sid, 0) + 1
            if r.verdict == "correct":
                correct[sid] = correct.get(sid, 0) + 1
            if r.verdict == "partial":
                partial[sid] = partial.get(sid, 0) + 1
            if r.verdict == "wrong":
                wrong[sid] = wrong.get(sid, 0) + 1
                if r.marks_awarded < 0:
                    neg_m[sid] = neg_m.get(sid, 0.0) + abs(r.marks_awarded)
            if not r.is_attempted:
                blank[sid] = blank.get(sid, 0) + 1

        subj_marks[sk] = subj_marks.get(sk, 0.0) + r.marks_awarded
        subj_max[sk]   = subj_max.get(sk, 0.0)   + r.positive_marks
        if not is_bonus:
            if r.is_attempted:
                subj_att[sk] = subj_att.get(sk, 0) + 1
            if r.verdict == "correct":
                subj_corr[sk] = subj_corr.get(sk, 0) + 1
            if r.verdict == "partial":
                subj_partial[sk] = subj_partial.get(sk, 0) + 1
            if r.verdict == "wrong":
                subj_wrong[sk] = subj_wrong.get(sk, 0) + 1
                if r.marks_awarded < 0:
                    subj_neg[sk] = subj_neg.get(sk, 0.0) + abs(r.marks_awarded)
            if not r.is_attempted:
                subj_blank[sk] = subj_blank.get(sk, 0) + 1

        topic_marks[tk] = topic_marks.get(tk, 0.0) + r.marks_awarded
        topic_max[tk]   = topic_max.get(tk, 0.0)   + r.positive_marks
        if not is_bonus:
            if r.is_attempted:
                topic_att[tk] = topic_att.get(tk, 0) + 1
            if r.verdict == "correct":
                topic_corr[tk] = topic_corr.get(tk, 0) + 1
        topic_subject[(r.subject, r.topic)] = r.subject

    # ── Build exam summary rows ────────────────────────────────────────────────
    exam_rows: list[StudentExamRow] = []
    for sid in student_meta:
        t  = totals.get(sid, 0.0)
        # Use the authoritative paper total if supplied; fall back to accumulated per-student max
        mx = paper_max_marks if paper_max_marks > 0 else max_m.get(sid, 0.0)
        exam_rows.append(StudentExamRow(
            admission_no=sid, exam_id=exam_id,
            total_marks=t,  max_marks=mx,
            percentage=round(t / mx * 100, 4) if mx else 0.0,
            attempted_count=attempted.get(sid, 0),
            correct_count=correct.get(sid, 0),
            partial_count=partial.get(sid, 0),
            wrong_count=wrong.get(sid, 0),
            blank_count=blank.get(sid, 0),
            negative_marks=neg_m.get(sid, 0.0),
        ))

    # ── Ranking (Python-side; repository will also push via PG window funcs) ──
    ranked_overall = _dense_rank_rows(exam_rows)
    rank_map: dict[str, int] = {r.admission_no: rk for r, rk in ranked_overall}

    branch_groups:  dict[str, list[StudentExamRow]] = {}
    program_groups: dict[str, list[StudentExamRow]] = {}
    section_groups: dict[str, list[StudentExamRow]] = {}

    for row in exam_rows:
        meta = student_meta[row.admission_no]
        branch_groups.setdefault(meta.branch_name, []).append(row)
        program_groups.setdefault(meta.program_name, []).append(row)
        section_groups.setdefault(meta.section, []).append(row)

    rank_branch:   dict[str, int] = {}
    rank_program:  dict[str, int] = {}
    rank_section:  dict[str, int] = {}

    for group in branch_groups.values():
        for r, rk in _dense_rank_rows(group):
            rank_branch[r.admission_no] = rk
    for group in program_groups.values():
        for r, rk in _dense_rank_rows(group):
            rank_program[r.admission_no] = rk
    for group in section_groups.values():
        for r, rk in _dense_rank_rows(group):
            rank_section[r.admission_no] = rk

    all_scores = sorted(r.total_marks for r in exam_rows)
    n = len(all_scores)
    for row in exam_rows:
        row.rank_overall = rank_map.get(row.admission_no)
        row.rank_branch  = rank_branch.get(row.admission_no)
        row.rank_program = rank_program.get(row.admission_no)
        row.rank_section = rank_section.get(row.admission_no)
        if n:
            below = sum(1 for s in all_scores if s < row.total_marks)
            row.percentile_overall = round(below / n * 100, 2)

    # ── Subject summaries ──────────────────────────────────────────────────────
    subject_rows: list[StudentSubjectRow] = []
    for (sid, subj), marks in subj_marks.items():
        att  = subj_att.get((sid, subj), 0)
        corr = subj_corr.get((sid, subj), 0)
        # Use paper-level per-subject max if supplied; fall back to per-student accumulated max
        s_max = (subject_max_marks or {}).get(subj) or subj_max.get((sid, subj), 0.0)
        subject_rows.append(StudentSubjectRow(
            admission_no=sid, exam_id=exam_id, subject=subj,
            marks=marks, max_marks=s_max,
            accuracy=corr / att if att else 0.0,
            attempted=att, correct=corr,
            partial_count=subj_partial.get((sid, subj), 0),
            wrong=subj_wrong.get((sid, subj), 0),
            blank=subj_blank.get((sid, subj), 0),
            negative_marks=subj_neg.get((sid, subj), 0.0),
        ))

    subj_groups: dict[str, list[StudentSubjectRow]] = {}
    for sr in subject_rows:
        subj_groups.setdefault(sr.subject, []).append(sr)
    for group in subj_groups.values():
        sorted_group = sorted(group, key=lambda x: (-x.marks, -(x.correct / max(x.attempted, 1))))
        for i, sr in enumerate(sorted_group):
            if i == 0:
                sr.rank_subject = 1
            else:
                prev = sorted_group[i - 1]
                same = (sr.marks == prev.marks and
                        (sr.correct / max(sr.attempted, 1)) == (prev.correct / max(prev.attempted, 1)))
                sr.rank_subject = sorted_group[i - 1].rank_subject if same else i + 1  # type: ignore[assignment]

    # ── Topic summaries ────────────────────────────────────────────────────────
    topic_rows: list[StudentTopicRow] = []
    for (sid, subj, topic), marks in topic_marks.items():
        att  = topic_att.get((sid, subj, topic), 0)
        corr = topic_corr.get((sid, subj, topic), 0)
        topic_rows.append(StudentTopicRow(
            admission_no=sid, exam_id=exam_id, subject=subj, topic=topic,
            marks=marks, max_marks=topic_max.get((sid, subj, topic), 0.0),
            attempted=att, correct=corr,
            accuracy=corr / att if att else 0.0,
        ))

    # ── Rank summaries (cutoff percentiles) ────────────────────────────────────
    rank_summaries: list[RankSummaryRow] = []

    def _mk_rank(scope: str, val: str, scores: list[float]) -> RankSummaryRow:
        return RankSummaryRow(
            exam_id=exam_id, scope=scope, scope_value=val,
            cutoff_top1pct=_percentile(scores, 1),
            cutoff_top5pct=_percentile(scores, 5),
            cutoff_top10pct=_percentile(scores, 10),
            cutoff_top25pct=_percentile(scores, 25),
            cutoff_median=statistics.median(scores) if scores else None,
        )

    rank_summaries.append(_mk_rank("overall", "all", [r.total_marks for r in exam_rows]))
    for bname, grp in branch_groups.items():
        rank_summaries.append(_mk_rank("branch", bname, [r.total_marks for r in grp]))
    for prog, grp in program_groups.items():
        rank_summaries.append(_mk_rank("program", prog, [r.total_marks for r in grp]))
    for sect, grp in section_groups.items():
        rank_summaries.append(_mk_rank("section", sect, [r.total_marks for r in grp]))

    # ── Aggregate summaries ────────────────────────────────────────────────────
    agg_summaries: list[AggregateSummaryRow] = []

    def _mk_agg(scope: str, val: str, subj: str, scores: list[float]) -> AggregateSummaryRow:
        n2 = len(scores)
        return AggregateSummaryRow(
            exam_id=exam_id, scope=scope, scope_value=val, subject=subj,
            avg=statistics.mean(scores) if n2 else None,
            median=statistics.median(scores) if n2 else None,
            stdev=statistics.stdev(scores) if n2 > 1 else 0.0,
            min_score=min(scores) if n2 else None,
            max_score=max(scores) if n2 else None,
            n_students=n2,
        )

    subjects = {sr.subject for sr in subject_rows}
    for subj in subjects:
        all_s  = [sr.marks for sr in subject_rows if sr.subject == subj]
        agg_summaries.append(_mk_agg("overall", "all", subj, all_s))

        for bname, grp in branch_groups.items():
            sids = {r.admission_no for r in grp}
            agg_summaries.append(_mk_agg("branch", bname, subj,
                [sr.marks for sr in subject_rows if sr.subject == subj and sr.admission_no in sids]))
        for prog, grp in program_groups.items():
            sids = {r.admission_no for r in grp}
            agg_summaries.append(_mk_agg("program", prog, subj,
                [sr.marks for sr in subject_rows if sr.subject == subj and sr.admission_no in sids]))
        for sect, grp in section_groups.items():
            sids = {r.admission_no for r in grp}
            agg_summaries.append(_mk_agg("section", sect, subj,
                [sr.marks for sr in subject_rows if sr.subject == subj and sr.admission_no in sids]))

    return AnalyticsBundle(
        exam_summaries=exam_rows,
        subject_summaries=subject_rows,
        topic_summaries=topic_rows,
        rank_summaries=rank_summaries,
        agg_summaries=agg_summaries,
    )
