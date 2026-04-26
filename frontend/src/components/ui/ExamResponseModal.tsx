import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import { fmtNum } from "@/lib/utils";
import { PageLoader } from "@/components/ui/LoadingSpinner";

interface Props {
  admissionNo: string;
  examId:      number;
  examLabel:   string;
  onClose:     () => void;
}

const VERDICT_STYLE: Record<string, string> = {
  correct:     "bg-green-100  text-green-700  border-green-200",
  partial:     "bg-yellow-100 text-yellow-700 border-yellow-200",
  wrong:       "bg-red-100    text-red-700    border-red-200",
  blank:       "bg-surface-100 text-surface-500 border-surface-200",
  bonus:       "bg-blue-100   text-blue-600   border-blue-200",
  not_graded:  "bg-surface-50  text-surface-400 border-surface-200",
};

const VERDICT_LABEL: Record<string, string> = {
  correct: "✓ Correct", partial: "◑ Partial", wrong: "✗ Wrong",
  blank: "○ Blank", bonus: "★ Bonus", not_graded: "— N/A",
};

const SUBJECT_COLOR: Record<string, string> = {
  Physics:     "bg-blue-50   text-blue-700",
  Chemistry:   "bg-emerald-50 text-emerald-700",
  Mathematics: "bg-amber-50  text-amber-700",
  Maths:       "bg-amber-50  text-amber-700",
};

function VerdictBadge({ verdict }: { verdict: string | null }) {
  if (!verdict) return <span className="text-surface-300 text-xs">—</span>;
  return (
    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${VERDICT_STYLE[verdict] ?? VERDICT_STYLE.not_graded}`}>
      {VERDICT_LABEL[verdict] ?? verdict}
    </span>
  );
}

export default function ExamResponseModal({ admissionNo, examId, examLabel, onClose }: Props) {
  const [paperFilter,   setPaperFilter]   = useState("all");
  const [subjectFilter, setSubjectFilter] = useState("all");
  const [verdictFilter, setVerdictFilter] = useState("all");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["exam-responses", admissionNo, examId],
    queryFn:  () => dashboardApi.studentExamResponses(admissionNo, examId).then((r) => r.data),
  });

  const rows = data ?? [];

  const papers   = useMemo(() => ["all", ...Array.from(new Set(rows.map((r) => r.paper_code))).sort()], [rows]);
  const subjects = useMemo(() => ["all", ...Array.from(new Set(rows.map((r) => r.subject))).sort()], [rows]);

  const filtered = useMemo(() => rows.filter((r) => {
    if (paperFilter   !== "all" && r.paper_code !== paperFilter)   return false;
    if (subjectFilter !== "all" && r.subject    !== subjectFilter)  return false;
    if (verdictFilter !== "all" && r.verdict_bkc !== verdictFilter) return false;
    return true;
  }), [rows, paperFilter, subjectFilter, verdictFilter]);

  // Summary counts
  const summary = useMemo(() => ({
    correct: rows.filter((r) => r.verdict_bkc === "correct").length,
    partial: rows.filter((r) => r.verdict_bkc === "partial").length,
    wrong:   rows.filter((r) => r.verdict_bkc === "wrong").length,
    blank:   rows.filter((r) => r.verdict_bkc === "blank").length,
    totalBkc: rows.reduce((s, r) => s + (r.marks_bkc ?? 0), 0),
    totalAkc: rows.reduce((s, r) => s + (r.marks_akc ?? 0), 0),
    hasAkc:  rows.some((r) => r.verdict_akc !== null),
  }), [rows]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div
        className="relative bg-white flex flex-col m-4 rounded-2xl shadow-2xl overflow-hidden"
        style={{ maxHeight: "calc(100vh - 2rem)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-primary-600 to-primary-800 text-white shrink-0">
          <div>
            <h2 className="text-base font-bold">📋 Exam Result — {examLabel}</h2>
            <p className="text-primary-200 text-xs mt-0.5 font-mono">{admissionNo}</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-full bg-white/20 hover:bg-white/30 flex items-center justify-center text-lg leading-none transition-colors">
            ×
          </button>
        </div>

        {isLoading && <div className="flex-1 flex items-center justify-center"><PageLoader /></div>}
        {isError   && <div className="flex-1 flex items-center justify-center text-surface-400 text-sm">Failed to load responses.</div>}

        {!isLoading && !isError && (
          <>
            {/* Summary strip */}
            <div className="flex flex-wrap items-center gap-4 px-6 py-3 bg-surface-50 border-b border-surface-100 shrink-0 text-sm">
              <span className="text-green-600 font-semibold">✓ {summary.correct} Correct</span>
              <span className="text-yellow-600 font-semibold">◑ {summary.partial} Partial</span>
              <span className="text-red-600 font-semibold">✗ {summary.wrong} Wrong</span>
              <span className="text-surface-400">○ {summary.blank} Blank</span>
              <span className="text-surface-300">|</span>
              <span className="font-semibold text-primary-700">BKC: {fmtNum(summary.totalBkc, 1)} marks</span>
              {summary.hasAkc && (
                <span className="font-semibold text-purple-700">AKC: {fmtNum(summary.totalAkc, 1)} marks</span>
              )}
              <span className="ml-auto text-surface-400 text-xs">{filtered.length} of {rows.length} questions</span>
            </div>

            {/* Paper tabs (shown only when multiple papers exist) */}
            {papers.length > 2 && (
              <div className="flex items-center gap-1 px-6 py-2 border-b border-surface-100 bg-surface-50/60 shrink-0">
                {papers.map((p) => (
                  <button
                    key={p}
                    onClick={() => setPaperFilter(p)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
                      paperFilter === p
                        ? "bg-primary-600 text-white border-primary-600"
                        : "bg-white text-surface-600 border-surface-200 hover:bg-surface-50"
                    }`}
                  >
                    {p === "all" ? "All Papers" : p}
                  </button>
                ))}
              </div>
            )}

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3 px-6 py-2.5 border-b border-surface-100 shrink-0">
              <select value={subjectFilter} onChange={(e) => setSubjectFilter(e.target.value)} className="input w-auto py-1 text-sm">
                {subjects.map((s) => <option key={s} value={s}>{s === "all" ? "All Subjects" : s}</option>)}
              </select>
              <select value={verdictFilter} onChange={(e) => setVerdictFilter(e.target.value)} className="input w-auto py-1 text-sm">
                <option value="all">All Verdicts</option>
                <option value="correct">Correct</option>
                <option value="partial">Partial</option>
                <option value="wrong">Wrong</option>
                <option value="blank">Blank</option>
                <option value="bonus">Bonus</option>
              </select>
              {(paperFilter !== "all" || subjectFilter !== "all" || verdictFilter !== "all") && (
                <button onClick={() => { setPaperFilter("all"); setSubjectFilter("all"); setVerdictFilter("all"); }}
                  className="text-xs text-surface-400 hover:text-surface-600">
                  Clear
                </button>
              )}
            </div>

            {/* Table */}
            <div className="flex-1 overflow-auto">
              <table className="w-full text-sm border-collapse">
                <thead className="sticky top-0 bg-surface-50 z-10">
                  <tr className="text-xs font-semibold text-surface-500 uppercase tracking-wide border-b border-surface-200">
                    <th className="px-3 py-2 text-left w-10">Q#</th>
                    {papers.length > 2 && <th className="px-3 py-2 text-left w-14">Paper</th>}
                    <th className="px-3 py-2 text-left w-24">Subject</th>
                    <th className="px-3 py-2 text-left">Topic</th>
                    <th className="px-3 py-2 text-left w-20">Type</th>
                    <th className="px-3 py-2 text-center w-20">Response</th>
                    <th className="px-3 py-2 text-center w-20">BKC Ans</th>
                    {summary.hasAkc && <th className="px-3 py-2 text-center w-20">AKC Ans</th>}
                    <th className="px-3 py-2 text-center w-28">BKC Verdict</th>
                    <th className="px-3 py-2 text-center w-20">BKC Marks</th>
                    {summary.hasAkc && <th className="px-3 py-2 text-center w-28">AKC Verdict</th>}
                    {summary.hasAkc && <th className="px-3 py-2 text-center w-20">AKC Marks</th>}
                    <th className="px-3 py-2 text-center w-20">+/−</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={20} className="text-center py-12 text-surface-400 text-sm">No questions match the current filters.</td>
                    </tr>
                  ) : filtered.map((q, idx) => {
                    const rowBg = q.verdict_bkc === "correct" ? "bg-green-50/40"
                      : q.verdict_bkc === "wrong"   ? "bg-red-50/40"
                      : q.verdict_bkc === "partial"  ? "bg-yellow-50/40"
                      : "";
                    const isDeleted = q.is_deleted_bkc || q.is_deleted_akc;
                    return (
                      <tr key={idx} className={`border-b border-surface-100 hover:bg-surface-50 ${rowBg} ${isDeleted ? "opacity-60" : ""}`}>
                        <td className="px-3 py-2 font-mono text-xs text-surface-600 font-bold">
                          {q.question_no}
                          {isDeleted && <span className="ml-1 text-[9px] text-blue-500 font-semibold">DEL</span>}
                        </td>
                        {papers.length > 2 && (
                          <td className="px-3 py-2 text-xs font-mono text-surface-500">{q.paper_code}</td>
                        )}
                        <td className="px-3 py-2">
                          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${SUBJECT_COLOR[q.subject] ?? "bg-surface-100 text-surface-600"}`}>
                            {q.subject}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-xs text-surface-600 max-w-[180px]">
                          <p className="truncate" title={q.topic ?? ""}>{q.topic ?? "—"}</p>
                          {q.sub_topic && <p className="text-surface-400 truncate text-[10px]">{q.sub_topic}</p>}
                        </td>
                        <td className="px-3 py-2 text-xs text-surface-500">{q.question_type}</td>
                        <td className="px-3 py-2 text-center">
                          <span className={`font-mono font-bold text-sm px-2 py-0.5 rounded ${q.response ? "bg-primary-50 text-primary-700" : "text-surface-300"}`}>
                            {q.response || "—"}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span className="font-mono font-bold text-sm text-green-700 bg-green-50 px-2 py-0.5 rounded">
                            {q.correct_bkc ?? "—"}
                          </span>
                        </td>
                        {summary.hasAkc && (
                          <td className="px-3 py-2 text-center">
                            <span className={`font-mono font-bold text-sm px-2 py-0.5 rounded ${q.correct_akc ? "text-purple-700 bg-purple-50" : "text-surface-300"}`}>
                              {q.correct_akc ?? "—"}
                            </span>
                          </td>
                        )}
                        <td className="px-3 py-2 text-center"><VerdictBadge verdict={q.verdict_bkc} /></td>
                        <td className="px-3 py-2 text-center">
                          <span className={`font-semibold text-sm ${(q.marks_bkc ?? 0) > 0 ? "text-green-600" : (q.marks_bkc ?? 0) < 0 ? "text-red-600" : "text-surface-400"}`}>
                            {q.marks_bkc !== null ? fmtNum(q.marks_bkc, 1) : "—"}
                          </span>
                        </td>
                        {summary.hasAkc && <td className="px-3 py-2 text-center"><VerdictBadge verdict={q.verdict_akc} /></td>}
                        {summary.hasAkc && (
                          <td className="px-3 py-2 text-center">
                            <span className={`font-semibold text-sm ${(q.marks_akc ?? 0) > 0 ? "text-green-600" : (q.marks_akc ?? 0) < 0 ? "text-red-600" : "text-surface-400"}`}>
                              {q.marks_akc !== null ? fmtNum(q.marks_akc, 1) : "—"}
                            </span>
                          </td>
                        )}
                        <td className="px-3 py-2 text-center text-[11px] text-surface-400 whitespace-nowrap">
                          +{q.positive_marks} / −{q.negative_marks}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
