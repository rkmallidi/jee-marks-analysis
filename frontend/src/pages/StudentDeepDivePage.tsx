import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { dashboardApi } from "@/lib/api";
import { fmtNum, fmtPct, SUBJECT_COLORS, pctToHeatColor, pctToTextColor } from "@/lib/utils";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import SeverityBadge from "@/components/ui/SeverityBadge";
import ExamResponseModal from "@/components/ui/ExamResponseModal";

export default function StudentDeepDivePage() {
  const { admission_no } = useParams<{ admission_no: string }>();
  const [expandedExamId, setExpandedExamId] = useState<number | null>(null);
  const [advView, setAdvView]               = useState<'p1' | 'p2' | 'consolidated'>('consolidated');
  const [examPaperTab, setExamPaperTab]     = useState<Record<number, string>>({});
  const [responseExam, setResponseExam]     = useState<{ examId: number; examLabel: string } | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["student-deep-dive", admission_no],
    queryFn: () => dashboardApi.studentDeepDive(admission_no!).then((r) => r.data),
    enabled: !!admission_no,
  });

  if (isLoading) return <PageLoader />;
  if (isError || !data) return <ErrorBanner onRetry={refetch} />;

  const { student: s } = data;
  const history      = data.exam_history    ?? [];
  const rankTraj     = data.rank_trajectory ?? [];
  const subjTrends   = data.subject_trends  ?? [];
  const weakTopics   = data.weak_topics     ?? [];
  const alerts       = data.active_alerts   ?? [];
  const rollingAvgs  = data.rolling_averages ?? [];

  // ── Compute summary stats from available data ──────────────────────────────
  const latest     = history[history.length - 1];
  const latestRank = rankTraj[rankTraj.length - 1]?.rank ?? null;
  const latestPct  = rankTraj[rankTraj.length - 1]?.percentile ?? null;
  const avgTotal   = history.length
    ? history.reduce((s, r) => s + r.total_marks, 0) / history.length
    : null;

  const subjectAvg = Object.fromEntries(
    subjTrends.map((st) => [
      st.subject,
      st.data.length ? st.data.reduce((s, d) => s + d.marks, 0) / st.data.length : 0,
    ])
  );
  const sortedSubjects = Object.entries(subjectAvg).sort((a, b) => b[1] - a[1]);
  const bestSubject  = sortedSubjects[0]?.[0] ?? "—";
  const worstSubject = sortedSubjects[sortedSubjects.length - 1]?.[0] ?? "—";

  // ── Transform subject trends to flat chart format ──────────────────────────
  // Collect all exam_ids in order from the first subject's data
  const examIds: number[] = [];
  const seen = new Set<number>();
  for (const st of subjTrends) {
    for (const d of st.data) {
      if (!seen.has(d.exam_id)) { seen.add(d.exam_id); examIds.push(d.exam_id); }
    }
  }
  const flatSubjectTrend = examIds.map((eid) => {
    const row: Record<string, number | string> = { exam_id: eid };
    for (const st of subjTrends) {
      const d = st.data.find((x) => x.exam_id === eid);
      if (d) row[st.subject] = d.marks;
    }
    return row;
  });

  const noExamData = history.length === 0;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="text-sm text-surface-400">
        <Link to="/students" className="hover:text-primary-600">Students</Link>
        <span className="mx-2">›</span>
        <span className="text-surface-700 font-medium">{s.name}</span>
      </nav>

      {/* Profile header */}
      <div className="card bg-gradient-to-r from-primary-600 to-primary-800 text-white p-6">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-white/20 flex items-center justify-center text-2xl font-bold">
            {s.name.charAt(0)}
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-bold">{s.name}</h1>
            <p className="text-primary-200 text-sm font-mono">{s.admission_no}</p>
            <div className="flex flex-wrap gap-3 mt-2 text-sm text-primary-100">
              <span>🏫 {s.branch_name}</span>
              <span>📚 {s.program_name}</span>
              <span>🎓 {s.student_class}</span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                s.status === "active" ? "bg-green-400/30 text-green-100" : "bg-red-400/30 text-red-100"
              }`}>
                {s.status}
              </span>
            </div>
          </div>

          {/* Summary stats */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-center">
            {[
              { label: "Latest Rank",   value: latestRank != null ? `#${latestRank}` : "—" },
              { label: "Latest Score",  value: latest ? fmtNum(latest.total_marks, 0) : "—" },
              { label: "Percentile",    value: latestPct != null ? `P${fmtNum(latestPct, 0)}` : "—" },
              { label: "Avg Score",     value: avgTotal != null ? fmtNum(avgTotal, 1) : "—" },
              { label: "Best Subject",  value: bestSubject },
              { label: "Weak Subject",  value: worstSubject },
            ].map(({ label, value }) => (
              <div key={label} className="bg-white/10 rounded-xl px-3 py-2">
                <p className="text-xs text-primary-200">{label}</p>
                <p className="font-bold text-sm mt-0.5">{value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* No data notice */}
      {noExamData && (
        <div className="card text-center py-12 text-surface-400">
          <p className="text-3xl mb-3">📭</p>
          <p className="font-medium text-surface-600">No exam data yet for this student.</p>
          <p className="text-sm mt-1">Upload responses and run evaluation to see performance data.</p>
        </div>
      )}

      {/* Charts row */}
      {!noExamData && (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Rank trajectory */}
          <div className="card">
            <p className="section-title mb-4">📈 Rank Trajectory</p>
            {rankTraj.length > 1 ? (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={rankTraj} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="exam_id" tick={{ fontSize: 10 }} label={{ value: "Exam", position: "insideBottom", offset: -2, style: { fontSize: 10 } }} />
                  <YAxis reversed tick={{ fontSize: 11 }} label={{ value: "Rank", angle: -90, position: "insideLeft", offset: 10, style: { fontSize: 11 } }} />
                  <Tooltip contentStyle={{ borderRadius: 12 }} formatter={(v) => [`#${v}`, "Rank"]} />
                  <Line type="monotone" dataKey="rank" stroke="#6366f1" strokeWidth={2} dot={{ r: 4, fill: "#6366f1" }} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-surface-400 py-16 text-sm">Need at least 2 exams for trend.</p>
            )}
          </div>

          {/* Subject score trend */}
          <div className="card">
            <p className="section-title mb-4">📊 Subject Score Trend</p>
            {flatSubjectTrend.length > 1 ? (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={flatSubjectTrend} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="exam_id" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ borderRadius: 12 }} />
                  <Legend />
                  {subjTrends.map((st) => (
                    <Line
                      key={st.subject}
                      type="monotone"
                      dataKey={st.subject}
                      stroke={(SUBJECT_COLORS as Record<string, string>)[st.subject.toLowerCase()] ?? "#94a3b8"}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-surface-400 py-16 text-sm">Need at least 2 exams for trend.</p>
            )}
          </div>
        </div>
      )}

      {/* Rolling averages */}
      {rollingAvgs.length > 0 && (
        <div className="card">
          <p className="section-title mb-4">Rolling Averages</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {rollingAvgs.map((ra) => (
              <div
                key={ra.exam_type}
                className={`rounded-xl p-4 border text-center ${
                  ra.exam_type === "Advanced"
                    ? "bg-purple-50 border-purple-200"
                    : "bg-sky-50 border-sky-200"
                }`}
              >
                <p className={`text-[10px] font-extrabold uppercase tracking-widest mb-1 ${
                  ra.exam_type === "Advanced" ? "text-purple-500" : "text-sky-500"
                }`}>
                  {ra.exam_type === "Advanced" ? "JEE Advanced" : "JEE Mains"}
                </p>
                <p className="text-2xl font-extrabold text-surface-900">
                  {fmtNum(ra.avg_score, 1)}
                </p>
                <p className="text-xs text-surface-400 mt-1">
                  avg over {ra.exam_count} exam{ra.exam_count !== 1 ? "s" : ""}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Weak topics + alerts */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Weak topics */}
        <div className="card">
          <p className="section-title mb-4">⚠️ Weak Topics</p>
          {weakTopics.length === 0 ? (
            <p className="text-center text-surface-400 py-8 text-sm">
              {noExamData ? "No exam data yet." : "No weak topics — keep it up! 🎉"}
            </p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart
                  data={weakTopics.slice(0, 8).map((t) => ({ ...t, accuracy_pct: +(t.accuracy * 100).toFixed(1) }))}
                  layout="vertical"
                  margin={{ top: 0, right: 24, bottom: 0, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" />
                  <YAxis dataKey="topic" type="category" tick={{ fontSize: 10 }} width={110} />
                  <Tooltip contentStyle={{ borderRadius: 12 }} formatter={(v) => [`${v}%`, "Accuracy"]} />
                  <Bar dataKey="accuracy_pct" name="Accuracy" radius={[0, 4, 4, 0]}>
                    {weakTopics.slice(0, 8).map((t, i) => (
                      <Cell key={i} fill={pctToTextColor(+(t.accuracy * 100).toFixed(1))} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {weakTopics.map((t) => {
                  const pct = +(t.accuracy * 100).toFixed(1);
                  return (
                    <div
                      key={`${t.topic}-${t.exam_id}`}
                      className="rounded-lg px-3 py-2 text-xs font-medium"
                      style={{ backgroundColor: pctToHeatColor(pct), color: pctToTextColor(pct) }}
                    >
                      <p className="font-semibold truncate">{t.topic}</p>
                      <p className="opacity-80">{fmtPct(pct)} · {t.attempted} attempts</p>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* Active alerts */}
        <div className="card">
          <p className="section-title mb-4">🔔 Active Alerts</p>
          {alerts.length === 0 ? (
            <p className="text-center text-surface-400 py-8 text-sm">No active alerts.</p>
          ) : (
            <div className="space-y-3">
              {alerts.map((a) => (
                <div key={a.alert_id} className="flex items-start gap-3 p-3 bg-surface-50 rounded-xl">
                  <SeverityBadge severity={a.severity} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-surface-800">{a.title}</p>
                    <p className="text-xs text-surface-600 mt-0.5 leading-relaxed">{a.message}</p>
                    <p className="text-xs text-surface-400 mt-1">Exam #{a.exam_id}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Exam type trend: Mains vs Mains, Adv vs Adv */}
      {(() => {
        const trendTypes = [
          { key: "Main",     label: "JEE Main",     color: { bg: "from-sky-600 to-sky-800",     cell: "bg-sky-50 border-sky-200",     cellHl: "bg-sky-100",     text: "text-sky-700",     bar: "#0ea5e9" } },
          { key: "Advanced", label: "JEE Advanced", color: { bg: "from-purple-600 to-purple-800", cell: "bg-purple-50 border-purple-200", cellHl: "bg-purple-100", text: "text-purple-700", bar: "#a855f7" } },
        ];

        // paperKey maps advView to the key used in h.paper_results
        const paperKey = advView === "p1" ? "P1" : advView === "p2" ? "P2" : null;

        const advancedAll = [...history].filter((h) => h.exam_type === "Advanced").sort((a, b) => a.exam_id - b.exam_id);

        const sections = trendTypes
          .map(({ key, label, color }) => {
            let exams = [...history].filter((h) => h.exam_type === key).sort((a, b) => a.exam_id - b.exam_id);
            // For Advanced P1/P2 views, keep only exams that actually have that paper's results
            if (key === "Advanced" && paperKey) {
              exams = exams.filter((h) => h.paper_results[paperKey] != null);
            }
            return { label, color, key, exams };
          })
          .filter((s) => (s.key === "Advanced" ? advancedAll.length >= 2 : s.exams.length >= 2));

        if (sections.length === 0) return null;

        return (
          <div className="card space-y-4">
            <p className="section-title">📊 Trend Analysis</p>
            {sections.map(({ label, color, key, exams }) => (
              <div key={label}>
                {/* Section label + Advanced tabs */}
                <div className="flex items-center gap-3 mb-3 flex-wrap">
                  <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gradient-to-r ${color.bg} text-white text-[11px] font-bold`}>
                    {label} · {key === "Advanced" ? advancedAll.length : exams.length} exams
                  </div>
                  {key === "Advanced" && (
                    <div className="flex gap-1">
                      {(["consolidated", "p1", "p2"] as const).map((v) => (
                        <button
                          key={v}
                          onClick={() => setAdvView(v)}
                          className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border transition-colors ${
                            advView === v
                              ? "bg-purple-600 text-white border-purple-600"
                              : "bg-white text-purple-600 border-purple-200 hover:bg-purple-50"
                          }`}
                        >
                          {v === "consolidated" ? "Consolidated" : v === "p1" ? "Paper 1" : "Paper 2"}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Empty state when filter yields no exams */}
                {exams.length === 0 && (
                  <p className="text-sm text-surface-400 py-4 text-center">
                    No {advView === "p1" ? "Paper 1" : "Paper 2"} results found for Advanced exams.
                  </p>
                )}

                {/* Horizontal timeline */}
                {exams.length > 0 && (
                <div className="overflow-x-auto pb-1">
                  <div className="flex items-stretch gap-0 min-w-max">
                    {exams.map((h, idx) => {
                      const prev = idx > 0 ? exams[idx - 1] : null;

                      // Per-paper score when a paper tab is selected, otherwise consolidated
                      const pr      = key === "Advanced" && paperKey ? h.paper_results[paperKey] : null;
                      const prevPr  = key === "Advanced" && paperKey && prev ? prev.paper_results[paperKey] : null;

                      const dispScore = pr     ? pr.score          : h.total_marks;
                      const dispMax   = pr     ? pr.total_marks    : h.max_marks;
                      const dispPct   = dispMax > 0 ? (dispScore / dispMax) * 100 : 0;

                      const prevDispScore = prevPr ? prevPr.score : prev?.total_marks ?? null;
                      const scoreDelta    = prevDispScore != null ? dispScore - prevDispScore : null;

                      // Rank + subject deltas only meaningful for consolidated view
                      const rankDelta  = !pr && prev != null && h.rank_overall != null && prev.rank_overall != null
                        ? prev.rank_overall - h.rank_overall : null;
                      const mathsDelta = !pr && prev != null && h.marks_mathematics != null && prev.marks_mathematics != null ? h.marks_mathematics - prev.marks_mathematics : null;
                      const physDelta  = !pr && prev != null && h.marks_physics     != null && prev.marks_physics     != null ? h.marks_physics     - prev.marks_physics     : null;
                      const chemDelta  = !pr && prev != null && h.marks_chemistry   != null && prev.marks_chemistry   != null ? h.marks_chemistry   - prev.marks_chemistry   : null;

                      const improved = scoreDelta != null && scoreDelta > 0;
                      const declined = scoreDelta != null && scoreDelta < 0;

                      const Delta = ({ v, invert = false }: { v: number | null; invert?: boolean }) => {
                        if (v == null) return null;
                        const pos = invert ? v < 0 : v > 0;
                        const neg = invert ? v > 0 : v < 0;
                        return (
                          <span className={`text-[9px] font-bold ml-0.5 ${pos ? "text-green-600" : neg ? "text-red-500" : "text-surface-400"}`}>
                            {v > 0 ? "+" : ""}{fmtNum(v, 0)}{pos ? "↑" : neg ? "↓" : ""}
                          </span>
                        );
                      };

                      return (
                        <div key={h.exam_id} className="flex items-center">
                          {idx > 0 && (
                            <div className="px-1.5 text-surface-300 text-base select-none">→</div>
                          )}

                          <div className={`rounded-xl border px-3 py-2.5 min-w-[108px] text-center space-y-1.5 ${
                            improved ? "border-green-200 bg-green-50"
                            : declined ? "border-red-200 bg-red-50"
                            : color.cell
                          }`}>
                            {/* Exam code + paper badge */}
                            <p className="text-[10px] font-semibold text-surface-500 truncate max-w-[96px]" title={h.exam_code ?? ""}>
                              {h.exam_code ?? `Exam #${h.exam_id}`}
                            </p>
                            {pr && (
                              <span className="inline-block px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 text-[9px] font-bold">
                                {paperKey}
                              </span>
                            )}
                            {h.exam_date && (
                              <p className="text-[9px] text-surface-400">
                                {new Date(h.exam_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                              </p>
                            )}

                            {/* Score */}
                            <div className="flex items-baseline justify-center gap-0.5">
                              <span className="text-lg font-extrabold text-surface-900 leading-none">{fmtNum(dispScore, 0)}</span>
                              <span className="text-[10px] text-surface-400">/{fmtNum(dispMax, 0)}</span>
                              <Delta v={scoreDelta} />
                            </div>

                            {/* % badge */}
                            <div>
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                                dispPct >= 60 ? "bg-green-100 text-green-700"
                                : dispPct >= 35 ? "bg-yellow-100 text-yellow-700"
                                : "bg-red-100 text-red-600"
                              }`}>{dispPct.toFixed(1)}%</span>
                            </div>

                            {/* Rank — consolidated only */}
                            {!pr && h.rank_overall != null && (
                              <div className="flex items-center justify-center text-[10px] text-surface-600">
                                <span className="font-bold">#{h.rank_overall}</span>
                                <Delta v={rankDelta} invert />
                              </div>
                            )}

                            {/* Subject scores — consolidated only */}
                            <div className="border-t border-surface-200 pt-1.5 space-y-0.5">
                              {!pr ? (
                                [
                                  { label: "M", marks: h.marks_mathematics, delta: mathsDelta, cls: "text-amber-600" },
                                  { label: "P", marks: h.marks_physics,      delta: physDelta,  cls: "text-blue-600"  },
                                  { label: "C", marks: h.marks_chemistry,    delta: chemDelta,  cls: "text-emerald-600" },
                                ].map(({ label, marks, delta, cls }) => (
                                  <div key={label} className="flex items-center justify-between text-[10px]">
                                    <span className={`font-extrabold ${cls}`}>{label}</span>
                                    <div className="flex items-center">
                                      <span className="font-semibold text-surface-800">{marks != null ? fmtNum(marks, 0) : "—"}</span>
                                      <Delta v={delta} />
                                    </div>
                                  </div>
                                ))
                              ) : (
                                <p className="text-[9px] text-surface-400 italic">Subject breakdown<br/>in Consolidated</p>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
                )}
              </div>
            ))}
          </div>
        );
      })()}

      {/* Exam history cards */}
      {history.length > 0 && (
        <div className="space-y-1">
          <p className="section-title px-1">📋 Exam History</p>
          <div className="space-y-2">
            {[...history].reverse().map((h) => {
              const isExpanded = expandedExamId === h.exam_id;

              // Per-subject authoritative max marks from question bank (via StudentSubjectSummary)
              const maxPhysics  = h.max_marks_physics     ?? h.max_marks / 3;
              const maxChem     = h.max_marks_chemistry   ?? h.max_marks / 3;
              const maxMaths    = h.max_marks_mathematics ?? h.max_marks / 3;

              // ── Paper tab state (computed early so insights can use it) ──────
              const hasPapers = h.exam_type === "Advanced" && Object.keys(h.paper_results).length > 0;
              const activeTab = examPaperTab[h.exam_id] ?? 'consolidated';
              const isPaperView = hasPapers && activeTab !== 'consolidated';

              const paperSubjects   = isPaperView ? (h.paper_subjects?.[activeTab]   ?? null) : null;
              const paperBenchmarks = isPaperView ? (h.paper_benchmarks?.[activeTab] ?? null) : null;

              const getPaperSubj  = (label: string) => paperSubjects
                ? (paperSubjects[label] ?? (label === 'Maths' ? paperSubjects['Mathematics'] : null) ?? null)
                : null;
              const getPaperBench = (label: string) => paperBenchmarks
                ? (paperBenchmarks[label] ?? (label === 'Maths' ? paperBenchmarks['Mathematics'] : null) ?? null)
                : null;

              // Paper-level total benchmark (avg/top for the whole paper across all students)
              const paperTotalBench = isPaperView ? (paperBenchmarks?.['_total'] ?? null) : null;
              // Per-paper result row (score/total_marks for this student)
              const pr = isPaperView ? (h.paper_results[activeTab] ?? null) : null;

              // Aggregate counts from paperSubjects (or fall back to consolidated)
              const viewCounts = paperSubjects
                ? Object.values(paperSubjects).reduce(
                    (acc, s) => ({
                      correct: acc.correct + s.correct,
                      partial: acc.partial + s.partial,
                      wrong:   acc.wrong   + s.wrong,
                      blank:   acc.blank   + s.blank,
                      neg:     acc.neg     + s.neg,
                    }),
                    { correct: 0, partial: 0, wrong: 0, blank: 0, neg: 0 }
                  )
                : { correct: h.correct_count, partial: h.partial_count ?? 0,
                    wrong: h.wrong_count, blank: h.blank_count, neg: h.negative_marks };

              // Effective score/max/avg/top for current view
              const viewScore       = pr ? pr.score       : h.total_marks;
              const viewMax         = pr ? pr.total_marks  : h.max_marks;
              const viewAvgTotal    = pr ? (paperTotalBench?.avg ?? null) : h.avg_total;
              const viewTopperTotal = pr ? (paperTotalBench?.top ?? null) : h.topper_total;

              // Subject detail rows — maxM uses authoritative per-subject max
              const subjectCols = [
                { key: 'phy',  label: 'Physics',   labelCls: 'text-blue-600 bg-blue-50',       barColor: 'bg-blue-500',
                  marks: h.marks_physics,     maxM: maxPhysics, rank: h.rank_physics,
                  avg: h.avg_physics,     topper: h.topper_physics,
                  correct: h.correct_physics,     partial: h.partial_physics,
                  wrong: h.wrong_physics,     blank: h.blank_physics,     neg: h.negative_physics },
                { key: 'chem', label: 'Chemistry', labelCls: 'text-emerald-600 bg-emerald-50', barColor: 'bg-emerald-500',
                  marks: h.marks_chemistry,   maxM: maxChem,    rank: h.rank_chemistry,
                  avg: h.avg_chemistry,   topper: h.topper_chemistry,
                  correct: h.correct_chemistry,   partial: h.partial_chemistry,
                  wrong: h.wrong_chemistry,   blank: h.blank_chemistry,   neg: h.negative_chemistry },
                { key: 'math', label: 'Maths',     labelCls: 'text-amber-600 bg-amber-50',     barColor: 'bg-amber-500',
                  marks: h.marks_mathematics, maxM: maxMaths,   rank: h.rank_mathematics,
                  avg: h.avg_mathematics, topper: h.topper_mathematics,
                  correct: h.correct_mathematics, partial: h.partial_mathematics,
                  wrong: h.wrong_mathematics, blank: h.blank_mathematics, neg: h.negative_mathematics },
              ];

              const effectiveSubjectCols = paperSubjects
                ? subjectCols.map((col) => {
                    const ps = getPaperSubj(col.label);
                    const pb = getPaperBench(col.label);
                    if (!ps) return col;
                    return { ...col,
                      marks:   ps.marks,
                      maxM:    ps.max_marks > 0 ? ps.max_marks : col.maxM,
                      rank:    null,
                      avg:     pb ? pb.avg : null,
                      topper:  pb ? pb.top : null,
                      correct: ps.correct, partial: ps.partial, wrong: ps.wrong, blank: ps.blank, neg: ps.neg };
                  })
                : subjectCols;

              // ── Insights (reactive to active tab) ───────────────────────────
              type Insight = { kind: 'success' | 'warning' | 'danger' | 'info'; icon: string; text: string };
              const insights: Insight[] = [];
              const totalQ   = viewCounts.correct + viewCounts.partial + viewCounts.wrong + viewCounts.blank;
              const att      = viewCounts.correct + viewCounts.partial + viewCounts.wrong;
              const accuracy = att > 0 ? (viewCounts.correct / att) * 100 : null;

              if (viewAvgTotal != null) {
                const d = viewScore - viewAvgTotal;
                if (d >= 10)       insights.push({ kind: 'success', icon: '📈', text: `${fmtNum(d, 1)} marks above class average` });
                else if (d <= -10) insights.push({ kind: 'warning', icon: '📉', text: `${fmtNum(Math.abs(d), 1)} marks below class average` });
              }
              if (viewTopperTotal != null) {
                const gap = viewTopperTotal - viewScore;
                if (gap === 0)     insights.push({ kind: 'success', icon: '👑', text: 'Top scorer this exam!' });
                else if (gap <= 5) insights.push({ kind: 'success', icon: '🔥', text: `Only ${fmtNum(gap, 0)} marks from top score` });
              }
              for (const col of effectiveSubjectCols) {
                if (col.marks != null && col.avg != null && col.maxM > 0) {
                  const d = col.marks - col.avg;
                  const pct = (d / col.maxM) * 100;
                  if (pct >= 15 && d >= 3)       insights.push({ kind: 'success', icon: '💪', text: `Strong in ${col.label} (+${fmtNum(d, 1)} vs avg)` });
                  else if (pct <= -15 && d <= -3) insights.push({ kind: 'danger',  icon: '⚠️',  text: `Needs focus: ${col.label} (${fmtNum(d, 1)} vs avg)` });
                }
                if (col.correct != null && col.wrong != null && col.wrong > col.correct && col.wrong >= 3)
                  insights.push({ kind: 'warning', icon: '🔄', text: `More wrong than correct in ${col.label}` });
              }
              if (viewCounts.neg > 0 && viewMax > 0) {
                const np = (viewCounts.neg / viewMax) * 100;
                if (np >= 10)     insights.push({ kind: 'danger',  icon: '📛', text: `Heavy negative marking: −${fmtNum(viewCounts.neg, 1)} marks lost` });
                else if (np >= 5) insights.push({ kind: 'warning', icon: '⚡', text: `Negative marking cost ${fmtNum(viewCounts.neg, 1)} marks` });
              }
              if (accuracy != null && att >= 5) {
                if (accuracy < 50)       insights.push({ kind: 'danger',  icon: '🎯', text: `Low accuracy (${accuracy.toFixed(0)}%) — ${viewCounts.wrong} wrong of ${att} attempted` });
                else if (accuracy >= 85) insights.push({ kind: 'success', icon: '🎯', text: `Excellent accuracy: ${accuracy.toFixed(0)}%` });
              }
              if (totalQ > 0 && viewCounts.blank / totalQ > 0.25)
                insights.push({ kind: 'info', icon: '📝', text: `${viewCounts.blank} questions left unattempted (${((viewCounts.blank / totalQ) * 100).toFixed(0)}%)` });

              const insightCls: Record<Insight['kind'], string> = {
                success: 'bg-green-50 text-green-700 border-green-200',
                warning: 'bg-amber-50 text-amber-700 border-amber-200',
                danger:  'bg-red-50   text-red-700   border-red-200',
                info:    'bg-blue-50  text-blue-700  border-blue-200',
              };

              // Topics for current view — per-paper when a paper tab is active
              const allExamTopics = weakTopics.filter((t) => t.exam_id === h.exam_id);
              const paperTopicList = isPaperView ? (h.paper_topics?.[activeTab] ?? null) : null;
              const examTopics = paperTopicList
                ? paperTopicList.filter((t) => t.attempted > 0 && t.accuracy < 0.7)
                    .sort((a, b) => a.accuracy - b.accuracy)
                : allExamTopics;

              return (
                <div key={h.exam_id} className="rounded-2xl border border-surface-200 bg-white shadow-sm overflow-hidden">

                  {/* ── Compact header (always visible, always consolidated) ── */}
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => setExpandedExamId(isExpanded ? null : h.exam_id)}
                    onKeyDown={(e) => e.key === "Enter" && setExpandedExamId(isExpanded ? null : h.exam_id)}
                    className="w-full text-left bg-gradient-to-r from-primary-600 to-primary-800 text-white hover:from-primary-700 hover:to-primary-900 transition-colors cursor-pointer"
                  >
                    {/* Row 1: Identity */}
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 pt-3 pb-2">
                      <span className="font-extrabold text-sm tracking-tight">{h.exam_code ?? `Exam #${h.exam_id}`}</span>
                      {h.exam_type && (
                        <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${h.exam_type === "Advanced" ? "bg-purple-400/30 text-purple-100" : "bg-sky-400/30 text-sky-100"}`}>
                          {h.exam_type}
                        </span>
                      )}
                      {h.is_absent && (
                        <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-red-500/40 text-red-100 border border-red-400/30">
                          ABSENT
                        </span>
                      )}
                      {h.papers.map((p) => (
                        <span key={p} className="px-1.5 py-0.5 rounded bg-white/15 text-white/80 text-[10px] font-mono">{p}</span>
                      ))}
                      {h.exam_date && (
                        <span className="text-[11px] text-primary-200">
                          📅 {new Date(h.exam_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                        </span>
                      )}
                      <button
                        onClick={(e) => { e.stopPropagation(); setResponseExam({ examId: h.exam_id, examLabel: h.exam_code ?? `Exam #${h.exam_id}` }); }}
                        className="ml-auto px-2.5 py-1 rounded-lg bg-white/15 hover:bg-white/30 text-white text-[11px] font-semibold transition-colors border border-white/20 shrink-0"
                      >
                        📋 Exam Result
                      </button>
                      <span className="text-white/40 text-xs select-none">{isExpanded ? '▲ collapse' : '▼ view analysis'}</span>
                    </div>

                    {/* Divider */}
                    <div className="border-t border-white/10 mx-4" />

                    {/* Row 2: Data overview (always consolidated) */}
                    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3">

                      {/* Subject mini scores */}
                      {[
                        { label: 'MATH', marks: h.marks_mathematics, maxM: maxMaths,   accentText: 'text-amber-200',  bar: 'bg-amber-300' },
                        { label: 'PHY',  marks: h.marks_physics,     maxM: maxPhysics, accentText: 'text-blue-200',    bar: 'bg-blue-300' },
                        { label: 'CHEM', marks: h.marks_chemistry,   maxM: maxChem,    accentText: 'text-emerald-200', bar: 'bg-emerald-300' },
                      ].map(({ label, marks, maxM, accentText, bar }) => {
                        const pct = marks != null && maxM > 0 ? Math.min((marks / maxM) * 100, 100) : 0;
                        return (
                          <div key={label} className="flex flex-col gap-1 min-w-[60px]">
                            <div className="flex items-baseline gap-1">
                              <span className={`text-[9px] font-extrabold uppercase tracking-widest ${accentText}`}>{label}</span>
                              <span className="font-bold text-sm leading-none">{marks != null ? fmtNum(marks, 0) : '—'}</span>
                              <span className="text-primary-300 text-[10px]">/{fmtNum(maxM, 0)}</span>
                            </div>
                            <div className="w-full h-1 rounded-full bg-white/20">
                              <div className={`h-full rounded-full ${bar} opacity-80`} style={{ width: `${pct}%` }} />
                            </div>
                          </div>
                        );
                      })}

                      <span className="text-white/20 text-lg hidden sm:block">|</span>

                      {/* Score — always consolidated */}
                      <div className="flex items-baseline gap-1.5">
                        <span className="text-2xl font-extrabold leading-none">{fmtNum(h.total_marks, 0)}</span>
                        <span className="text-primary-300 text-sm">/ {fmtNum(h.max_marks, 0)}</span>
                        <span className={`ml-1 text-[11px] font-bold px-2 py-0.5 rounded-full ${
                          h.percentage >= 60 ? "bg-green-400/25 text-green-200"
                          : h.percentage >= 35 ? "bg-yellow-400/25 text-yellow-200"
                          : "bg-red-400/25 text-red-200"
                        }`}>{h.percentage.toFixed(1)}%</span>
                      </div>

                      <span className="text-white/20 text-lg hidden sm:block">|</span>
                      <div className="flex items-center gap-2 flex-wrap">
                        {h.rank_overall != null && (
                          <div className="flex flex-col items-center bg-white/20 px-3 py-1 rounded-xl">
                            <span className="text-[9px] font-extrabold uppercase tracking-widest text-primary-200 leading-none">Overall Rank</span>
                            <span className="text-base font-extrabold leading-tight">#{h.rank_overall}</span>
                          </div>
                        )}
                        {h.rank_section != null && (
                          <div className="flex flex-col items-center bg-white/10 px-3 py-1 rounded-xl">
                            <span className="text-[9px] font-extrabold uppercase tracking-widest text-primary-300 leading-none">Section Rank</span>
                            <span className="text-base font-extrabold leading-tight text-primary-100">#{h.rank_section}</span>
                          </div>
                        )}
                      </div>

                      <span className="text-white/20 text-lg hidden sm:block">|</span>

                      <div className="flex items-center gap-3 text-[11px]">
                        <span className="flex items-center gap-1 text-primary-200">
                          <svg width="11" height="7" viewBox="0 0 14 10" fill="none" className="opacity-70">
                            <line x1="1" y1="5" x2="5.5" y2="5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="1.5 1.5"/>
                            <circle cx="7" cy="5" r="2" fill="currentColor"/>
                            <line x1="8.5" y1="5" x2="13" y2="5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="1.5 1.5"/>
                          </svg>
                          Avg <b className="text-white ml-0.5">{h.avg_total != null ? fmtNum(h.avg_total, 1) : "—"}</b>
                        </span>
                        <span className="flex items-center gap-1 text-primary-200">
                          👑 <b className="text-white ml-0.5">{h.topper_total != null ? fmtNum(h.topper_total, 0) : "—"}</b>
                        </span>
                        {h.negative_marks > 0 && (
                          <span className="flex items-center gap-0.5 text-orange-300">
                            <span className="font-bold">−{fmtNum(h.negative_marks, 1)}</span>
                            <span className="opacity-70 text-[10px]">neg</span>
                          </span>
                        )}
                      </div>

                    </div>
                  </div>

                  {/* ── Expanded detail panel ── */}
                  {isExpanded && (
                    <div className="border-t border-surface-100">

                      {/* Per-paper score summary + tab switcher for Advanced exams */}
                      {hasPapers && (
                        <div className="px-4 py-3 bg-purple-50 border-b border-purple-100">
                          <div className="flex items-center gap-4 flex-wrap">
                            <span className="text-[10px] font-extrabold uppercase tracking-widest text-purple-400">Paper Scores</span>
                            {Object.entries(h.paper_results).sort(([a],[b]) => a.localeCompare(b)).map(([paper, res]) => {
                              const pct = res.total_marks > 0 ? (res.score / res.total_marks) * 100 : 0;
                              return (
                                <div key={paper} className="flex items-center gap-1.5">
                                  <span className="px-1.5 py-0.5 rounded bg-purple-200 text-purple-800 text-[10px] font-bold">{paper}</span>
                                  <span className="font-extrabold text-sm text-surface-900">{fmtNum(res.score, 0)}</span>
                                  <span className="text-[10px] text-surface-400">/ {fmtNum(res.total_marks, 0)}</span>
                                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                                    pct >= 60 ? "bg-green-100 text-green-700"
                                    : pct >= 35 ? "bg-yellow-100 text-yellow-700"
                                    : "bg-red-50 text-red-600"
                                  }`}>{pct.toFixed(1)}%</span>
                                </div>
                              );
                            })}
                            <div className="ml-auto flex items-center gap-2">
                              <span className="text-[10px] text-purple-400 font-semibold">View:</span>
                              {(['consolidated', ...Object.keys(h.paper_results).sort()] as string[]).map((tab) => (
                                <button
                                  key={tab}
                                  onClick={() => setExamPaperTab((prev) => ({ ...prev, [h.exam_id]: tab }))}
                                  className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-colors ${
                                    activeTab === tab
                                      ? "bg-purple-600 text-white border-purple-600"
                                      : "bg-white text-purple-600 border-purple-200 hover:bg-purple-50"
                                  }`}
                                >
                                  {tab === 'consolidated' ? 'Combined' : tab}
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Subject 3-column grid */}
                      <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-surface-100">
                        {effectiveSubjectCols.map(({ key, label, labelCls, barColor, marks, maxM, rank, avg, topper, correct, partial, wrong, blank, neg }) => {
                          const sp = marks != null && maxM > 0 ? Math.min((marks / maxM) * 100, 100) : 0;
                          const ap = avg    != null && maxM > 0 ? Math.min((avg    / maxM) * 100, 100) : null;
                          const tp = topper != null && maxM > 0 ? Math.min((topper / maxM) * 100, 100) : null;
                          const subjectPct = marks != null && maxM > 0 ? (marks / maxM) * 100 : 0;
                          return (
                            <div key={key} className="p-4 space-y-3">
                              {/* Subject header */}
                              <div className="flex items-center justify-between">
                                <span className={`text-[11px] font-extrabold uppercase tracking-wide px-2.5 py-0.5 rounded-full ${labelCls}`}>{label}</span>
                                {rank != null && (
                                  <span className="text-[10px] font-semibold text-surface-500 bg-surface-100 px-2 py-0.5 rounded-full">Rank #{rank}</span>
                                )}
                              </div>
                              {/* Score */}
                              <div className="flex items-baseline gap-1.5">
                                <span className="text-2xl font-extrabold text-surface-900 leading-none">
                                  {marks != null ? fmtNum(marks, 0) : "—"}
                                </span>
                                <span className="text-sm text-surface-400">/ {fmtNum(maxM, 0)}</span>
                                <span className={`ml-1 text-[11px] font-bold px-1.5 py-0.5 rounded-full ${
                                  subjectPct >= 60 ? "bg-green-100 text-green-700"
                                  : subjectPct >= 35 ? "bg-yellow-100 text-yellow-700"
                                  : "bg-red-50 text-red-600"
                                }`}>{subjectPct.toFixed(0)}%</span>
                              </div>
                              {/* Bar */}
                              <div className="relative h-2 rounded-full bg-surface-100">
                                <div className={`h-full rounded-full ${barColor}`} style={{ width: `${sp}%` }} />
                                {ap != null && (
                                  <>
                                    <div className="absolute -top-1 pointer-events-none" style={{ left: `${ap}%`, transform: "translateX(-50%)" }}>
                                      <span className="text-[7px] text-slate-400 leading-none">▾</span>
                                    </div>
                                    <div className="absolute -top-1.5 -bottom-1.5 w-[2px] bg-slate-300 rounded-full" style={{ left: `${ap}%`, transform: "translateX(-50%)" }} />
                                  </>
                                )}
                                {tp != null && (
                                  <>
                                    <div className="absolute -top-1.5 pointer-events-none" style={{ left: `${tp}%`, transform: "translateX(-50%)" }}>
                                      <svg width="9" height="8" viewBox="0 0 13 11" fill="none" className="text-slate-400">
                                        <path d="M1.5 9.5V6L4 7.5L6.5 1.5L9 7.5L11.5 6V9.5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" fill="currentColor" fillOpacity="0.25"/>
                                        <line x1="1.5" y1="9.5" x2="11.5" y2="9.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
                                      </svg>
                                    </div>
                                    <div className={`absolute -top-1.5 -bottom-1.5 w-[2px] ${barColor} opacity-50 rounded-full`} style={{ left: `${tp}%`, transform: "translateX(-50%)" }} />
                                  </>
                                )}
                              </div>
                              {/* Benchmarks + response stats — single compact row */}
                              <div className="flex items-center gap-2 text-[10px] pt-1 border-t border-surface-100 flex-wrap">
                                <span className="text-green-600 font-semibold">✓ {correct ?? 0}</span>
                                <span className="text-violet-500">◑ {partial ?? 0}</span>
                                <span className="text-red-500 font-semibold">✗ {wrong ?? 0}</span>
                                <span className="text-surface-400">○ {blank ?? 0}</span>
                                <span className="text-orange-400 font-semibold">− {fmtNum(neg ?? 0, 1)}</span>
                                {(avg != null || topper != null) && (
                                  <span className="ml-auto flex items-center gap-2 text-slate-400">
                                    {avg != null && (
                                      <span className="flex items-center gap-0.5">
                                        <svg width="9" height="6" viewBox="0 0 14 10" fill="none"><line x1="1" y1="5" x2="5.5" y2="5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="1.5 1.5"/><circle cx="7" cy="5" r="2" fill="currentColor"/><line x1="8.5" y1="5" x2="13" y2="5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="1.5 1.5"/></svg>
                                        Avg <b className="text-slate-600">{fmtNum(avg, 1)}</b>
                                      </span>
                                    )}
                                    {topper != null && (
                                      <span className="flex items-center gap-0.5">
                                        <svg width="8" height="7" viewBox="0 0 13 11" fill="none"><path d="M1.5 9.5V6L4 7.5L6.5 1.5L9 7.5L11.5 6V9.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" fill="currentColor" fillOpacity="0.2"/><line x1="1.5" y1="9.5" x2="11.5" y2="9.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>
                                        Top <b className="text-slate-600">{fmtNum(topper, 0)}</b>
                                      </span>
                                    )}
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Performance insights */}
                      {insights.length > 0 && (
                        <div className="px-4 py-3 border-t border-surface-100 bg-surface-50/60">
                          <p className="text-[9px] font-extrabold uppercase tracking-widest text-surface-400 mb-2">💡 Performance Insights</p>
                          <div className="flex flex-wrap gap-1.5">
                            {insights.map((ins, i) => (
                              <span key={i} className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[11px] font-medium ${insightCls[ins.kind]}`}>
                                <span>{ins.icon}</span><span>{ins.text}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Weak topics for this exam — grouped by subject */}
                      {examTopics.length > 0 && (
                        <div className="px-4 py-3 border-t border-surface-100">
                          <p className="text-[9px] font-extrabold uppercase tracking-widest text-surface-400 mb-2">
                            📚 Weak Topics — {isPaperView ? activeTab : 'All Papers'}
                          </p>
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-x-4 gap-y-3">
                            {(["Maths", "Physics", "Chemistry"] as const).map((subjectName) => {
                              const topics = examTopics.filter((t) => t.subject === subjectName || (subjectName === "Maths" && t.subject === "Mathematics"));
                              if (topics.length === 0) return null;
                              const subjStyle =
                                subjectName === "Physics"   ? { header: "text-blue-600 border-blue-200 bg-blue-50",      bar: "#3b82f6" }
                                : subjectName === "Chemistry" ? { header: "text-emerald-600 border-emerald-200 bg-emerald-50", bar: "#10b981" }
                                : { header: "text-amber-600 border-amber-200 bg-amber-50", bar: "#f59e0b" };
                              return (
                                <div key={subjectName}>
                                  {/* Subject group header */}
                                  <div className={`text-[10px] font-extrabold uppercase tracking-widest px-2 py-1 rounded-lg border mb-1.5 ${subjStyle.header}`}>
                                    {subjectName}
                                  </div>
                                  {/* Topic rows */}
                                  <div className="space-y-1">
                                    {topics.map((t) => {
                                      const pct     = +(t.accuracy * 100).toFixed(1);
                                      const correct = Math.round(t.accuracy * t.attempted);
                                      const wrong   = t.attempted - correct;
                                      return (
                                        <div key={t.topic} className="flex items-center gap-2 px-1.5 py-1 rounded-lg hover:bg-surface-50">
                                          {/* Topic name */}
                                          <span className="text-[11px] font-medium text-surface-800 flex-1 min-w-0 truncate" title={t.topic}>{t.topic}</span>
                                          {/* Mini bar + % */}
                                          <div className="w-14 shrink-0">
                                            <div className="h-1.5 rounded-full bg-surface-100">
                                              <div className="h-full rounded-full" style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: subjStyle.bar, opacity: 0.7 }} />
                                            </div>
                                          </div>
                                          <span className="text-[11px] font-extrabold w-9 text-right shrink-0" style={{ color: pctToTextColor(pct) }}>{fmtPct(pct)}</span>
                                          {/* ✓ ✗ att */}
                                          <div className="flex items-center gap-1 text-[10px] shrink-0">
                                            <span className="text-green-600 font-semibold">✓{correct}</span>
                                            <span className="text-red-500 font-semibold">✗{wrong}</span>
                                            <span className="text-surface-400 text-[9px]">{t.attempted}q</span>
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Overall footer — reactive to active tab */}
                      <div className="flex items-center gap-3 px-4 py-2.5 bg-surface-50 border-t border-surface-100 text-[11px] flex-wrap">
                        <span className="text-[9px] font-extrabold uppercase tracking-widest text-surface-400 mr-1">
                          {isPaperView ? activeTab : 'Overall'}
                        </span>
                        <span className="text-green-600 font-semibold">✓ {viewCounts.correct} Correct</span>
                        <span className="text-violet-500 font-semibold">◑ {viewCounts.partial} Partial</span>
                        <span className="text-red-500 font-semibold">✗ {viewCounts.wrong} Wrong</span>
                        <span className="text-surface-400">○ {viewCounts.blank} Blank</span>
                        <span className="text-surface-500 ml-2">|</span>
                        <span className="text-primary-600 font-semibold">
                          Avg {viewAvgTotal != null ? fmtNum(viewAvgTotal, 1) : "—"}
                        </span>
                        <span className="text-primary-700 font-semibold">
                          👑 {viewTopperTotal != null ? fmtNum(viewTopperTotal, 0) : "—"}
                        </span>
                        <span className="text-orange-500 ml-auto font-semibold">− {fmtNum(viewCounts.neg, 1)} Neg. Marks</span>
                      </div>
                    </div>
                  )}

                </div>
              );
            })}
          </div>
        </div>
      )}

      {responseExam && (
        <ExamResponseModal
          admissionNo={s.admission_no}
          examId={responseExam.examId}
          examLabel={responseExam.examLabel}
          onClose={() => setResponseExam(null)}
        />
      )}
    </div>
  );
}
