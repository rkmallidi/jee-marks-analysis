from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


# ── Data contracts ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HistoricalSummary:
    exam_id:      int
    admission_no: str
    total_marks:  float
    percentage:   float
    rank_overall: int | None
    rank_branch:  int | None
    branch_name:  str
    section:      str


@dataclass(frozen=True)
class TopicHistory:
    admission_no: str
    exam_id:      int
    topic:        str
    subject:      str
    accuracy:     float
    attempted:    int
    correct:      int
    exam_type:    str | None = None   # "Mains" or "Advanced" — for type-segregated streak detection


@dataclass
class AlertContext:
    exam_id:           int
    exam_type:         str | None         # "Mains" or "Advanced"
    student_ids:       list[str]
    current_summaries: dict[str, HistoricalSummary]
    historical:        dict[str, list[HistoricalSummary]]  # newest-first
    topic_history:     dict[str, list[TopicHistory]]
    branch_stats:      dict[str, tuple[float, float]]       # branch_name → (avg, stdev)
    config:            dict[str, dict]                      # rule_key → config dict


@dataclass(frozen=True)
class AlertRecord:
    admission_no: str
    exam_id:      int
    rule_key:     str
    severity:     str
    title:        str
    message:      str
    context_json: dict  # stored as JSONB


# ── Protocol ───────────────────────────────────────────────────────────────────

@runtime_checkable
class AlertRule(Protocol):
    rule_key: str

    def evaluate(self, ctx: AlertContext) -> list[AlertRecord]: ...


# ── Rules ──────────────────────────────────────────────────────────────────────

class PerformanceDropRule:
    """
    Fires when a student's percentage is ≥ drop_pct_threshold points
    below their rolling average over the previous lookback_exams.
    severity: warning if 15–25 drop, critical if >25.
    """
    rule_key = "performance_drop"

    def evaluate(self, ctx: AlertContext) -> list[AlertRecord]:
        cfg       = ctx.config.get(self.rule_key, {})
        threshold = float(cfg.get("drop_pct_threshold", 15.0))
        lookback  = int(cfg.get("lookback_exams", 3))

        out: list[AlertRecord] = []
        for sid in ctx.student_ids:
            current = ctx.current_summaries.get(sid)
            if not current:
                continue
            history = ctx.historical.get(sid, [])[:lookback]
            if not history:
                continue

            rolling_avg = statistics.mean(h.percentage for h in history)
            drop = rolling_avg - current.percentage
            if drop < threshold:
                continue

            severity = "critical" if drop > 25 else "warning"
            out.append(AlertRecord(
                admission_no=sid, exam_id=ctx.exam_id,
                rule_key=self.rule_key, severity=severity,
                title="Performance drop detected",
                message=(
                    f"Score {current.percentage:.1f}% is {drop:.1f} pts below "
                    f"rolling avg {rolling_avg:.1f}% (last {len(history)} exams)."
                ),
                context_json={
                    "current_pct": round(current.percentage, 2),
                    "rolling_avg": round(rolling_avg, 2),
                    "drop":        round(drop, 2),
                    "lookback":    len(history),
                },
            ))
        return out


class WeakTopicRule:
    """
    Fires when a student has one or more topics below accuracy threshold.
    Emits a single alert per student listing all weak topics, because
    the Alert table enforces UniqueConstraint(admission_no, exam_id, rule_key).
    """
    rule_key = "weak_topic"

    def evaluate(self, ctx: AlertContext) -> list[AlertRecord]:
        cfg           = ctx.config.get(self.rule_key, {})
        acc_threshold = float(cfg.get("accuracy_threshold", 0.40))
        lookback      = int(cfg.get("lookback_exams", 3))
        min_attempts  = int(cfg.get("min_attempts", 5))

        out: list[AlertRecord] = []
        for sid in ctx.student_ids:
            by_topic: dict[str, list[TopicHistory]] = {}
            for tr in ctx.topic_history.get(sid, []):
                by_topic.setdefault(tr.topic, []).append(tr)

            weak: list[dict] = []
            for topic, rows in by_topic.items():
                recent    = sorted(rows, key=lambda r: r.exam_id, reverse=True)[:lookback]
                total_att  = sum(r.attempted for r in recent)
                total_corr = sum(r.correct for r in recent)
                if total_att < min_attempts:
                    continue
                accuracy = total_corr / total_att
                if accuracy >= acc_threshold:
                    continue
                weak.append({
                    "topic":          topic,
                    "subject":        recent[0].subject,
                    "accuracy":       round(accuracy, 4),
                    "total_attempted": total_att,
                    "total_correct":  total_corr,
                })

            if not weak:
                continue

            # Sort worst-first so the title shows the lowest-accuracy topic
            weak.sort(key=lambda w: w["accuracy"])
            worst    = weak[0]
            topic_list = ", ".join(
                f"{w['topic']} ({w['accuracy']:.0%})" for w in weak
            )
            out.append(AlertRecord(
                admission_no=sid, exam_id=ctx.exam_id,
                rule_key=self.rule_key, severity="warning",
                title=f"Weak topic: {worst['topic']} (+{len(weak) - 1} more)" if len(weak) > 1
                      else f"Weak topic: {worst['topic']}",
                message=f"Low accuracy in: {topic_list}.",
                context_json={
                    "weak_topics":  weak,
                    "topic_count":  len(weak),
                },
            ))
        return out


class BelowBranchAvgRule:
    """
    Fires when student total marks < branch_avg − N × branch_stdev.
    severity: info if within 1–1.5σ, warning if beyond 1.5σ.
    """
    rule_key = "below_branch_avg"

    def evaluate(self, ctx: AlertContext) -> list[AlertRecord]:
        cfg        = ctx.config.get(self.rule_key, {})
        multiplier = float(cfg.get("stdev_multiplier", 1.0))

        out: list[AlertRecord] = []
        for sid in ctx.student_ids:
            current = ctx.current_summaries.get(sid)
            if not current:
                continue
            branch_avg, branch_stdev = ctx.branch_stats.get(current.branch_name, (0.0, 0.0))
            cutoff_1   = branch_avg - multiplier * branch_stdev
            cutoff_1_5 = branch_avg - 1.5 * branch_stdev

            if current.total_marks < cutoff_1_5:
                severity, label = "warning", "1.5σ"
            elif current.total_marks < cutoff_1:
                severity, label = "info",    "1σ"
            else:
                continue

            out.append(AlertRecord(
                admission_no=sid, exam_id=ctx.exam_id,
                rule_key=self.rule_key, severity=severity,
                title=f"Below branch average ({label})",
                message=(
                    f"Score {current.total_marks:.1f} is below branch avg "
                    f"{branch_avg:.1f} by more than {label} (cutoff {cutoff_1:.1f})."
                ),
                context_json={
                    "total_marks":    round(current.total_marks, 2),
                    "branch_avg":     round(branch_avg, 2),
                    "branch_stdev":   round(branch_stdev, 2),
                    "cutoff_1sigma":  round(cutoff_1, 2),
                    "cutoff_15sigma": round(cutoff_1_5, 2),
                },
            ))
        return out


class ConsistentlyLowRule:
    """
    Fires when student was in the bottom quartile of their branch
    in ≥ N of the last M exams.
    """
    rule_key = "consistently_low"

    def evaluate(self, ctx: AlertContext) -> list[AlertRecord]:
        cfg       = ctx.config.get(self.rule_key, {})
        min_low   = int(cfg.get("min_low_count", 3))
        window    = int(cfg.get("window_exams", 4))

        # pre-compute bottom-quartile cutoff per (branch_name, exam_id)
        branch_exam_scores: dict[tuple[str, int], list[float]] = {}
        for sid, histories in ctx.historical.items():
            for h in histories:
                key = (h.branch_name, h.exam_id)
                branch_exam_scores.setdefault(key, []).append(h.total_marks)

        q25_map: dict[tuple[str, int], float] = {}
        for key, scores in branch_exam_scores.items():
            sorted_s      = sorted(scores)
            idx           = max(0, len(sorted_s) // 4 - 1)
            q25_map[key]  = sorted_s[idx]

        out: list[AlertRecord] = []
        for sid in ctx.student_ids:
            current = ctx.current_summaries.get(sid)
            if not current:
                continue
            history = ctx.historical.get(sid, [])[:window]
            if len(history) < window:
                continue

            low_count = sum(
                1 for h in history
                if h.total_marks <= q25_map.get((h.branch_name, h.exam_id), 0.0)
            )
            if low_count < min_low:
                continue

            out.append(AlertRecord(
                admission_no=sid, exam_id=ctx.exam_id,
                rule_key=self.rule_key, severity="critical",
                title="Consistently in bottom quartile",
                message=(
                    f"In bottom quartile (branch) in {low_count} of last {len(history)} exams."
                ),
                context_json={
                    "low_count": low_count,
                    "window":    len(history),
                    "threshold": min_low,
                },
            ))
        return out


class SubtopicConsecutiveWeaknessRule:
    """
    Fires when a student has been below accuracy_threshold in the same topic
    for min_streak or more consecutive exams of the same type (Mains / Advanced
    evaluated independently). Uses exam_type on TopicHistory.
    """
    rule_key = "subtopic_consecutive_weakness"

    def evaluate(self, ctx: AlertContext) -> list[AlertRecord]:
        cfg           = ctx.config.get(self.rule_key, {})
        acc_threshold = float(cfg.get("accuracy_threshold", 0.40))
        min_streak    = int(cfg.get("min_streak", 2))
        current_type  = ctx.exam_type

        out: list[AlertRecord] = []
        for sid in ctx.student_ids:
            by_topic: dict[str, list[TopicHistory]] = {}
            for tr in ctx.topic_history.get(sid, []):
                if current_type and tr.exam_type and tr.exam_type != current_type:
                    continue
                by_topic.setdefault(tr.topic, []).append(tr)

            weak_streaks: list[dict] = []
            for topic, rows in by_topic.items():
                # Sort newest-first
                sorted_rows = sorted(rows, key=lambda r: r.exam_id, reverse=True)
                streak = 0
                for r in sorted_rows:
                    if r.attempted == 0:
                        break
                    if r.correct / r.attempted < acc_threshold:
                        streak += 1
                    else:
                        break
                if streak >= min_streak:
                    latest   = sorted_rows[0]
                    accuracy = latest.correct / max(latest.attempted, 1)
                    weak_streaks.append({
                        "topic":    topic,
                        "subject":  latest.subject,
                        "streak":   streak,
                        "accuracy": round(accuracy, 4),
                    })

            if not weak_streaks:
                continue

            weak_streaks.sort(key=lambda w: w["accuracy"])
            worst = weak_streaks[0]
            out.append(AlertRecord(
                admission_no=sid, exam_id=ctx.exam_id,
                rule_key=self.rule_key, severity="warning",
                title=f"Consecutive topic weakness: {worst['topic']}",
                message=(
                    f"Weak in '{worst['topic']}' for {worst['streak']} consecutive "
                    f"{current_type or 'exam'} exams (accuracy {worst['accuracy']:.0%})."
                ),
                context_json={
                    "weak_streaks": weak_streaks,
                    "exam_type":    current_type,
                    "min_streak":   min_streak,
                },
            ))
        return out


# ── Runner ─────────────────────────────────────────────────────────────────────

ALERT_RULES: list[AlertRule] = [
    PerformanceDropRule(),
    WeakTopicRule(),
    BelowBranchAvgRule(),
    ConsistentlyLowRule(),
    SubtopicConsecutiveWeaknessRule(),
]


def run_alert_engine(ctx: AlertContext) -> list[AlertRecord]:
    """
    Run all rules, return flat list. Idempotency is enforced at the DB layer
    via PostgreSQL ON CONFLICT DO UPDATE on (admission_no, exam_id, rule_key).
    """
    results: list[AlertRecord] = []
    for rule in ALERT_RULES:
        results.extend(rule.evaluate(ctx))
    return results
