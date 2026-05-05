/**
 * D2 – Weak Students Dashboard
 * Severity summary → filterable cards with alert details
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi, WeakStudentEntry, DimensionParams } from "@/lib/api";
import { fmtNum } from "@/lib/utils";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import SeverityBadge from "@/components/ui/SeverityBadge";
import ExamPicker from "@/components/ui/ExamPicker";
import EmptyState from "@/components/ui/EmptyState";
import DimensionFilter from "@/components/ui/DimensionFilter";
import { useExamSelector } from "@/hooks/useExamSelector";

type FilterSeverity = "all" | "critical" | "warning" | "info";

const RULE_LABEL: Record<string, string> = {
  performance_drop:  "📉 Performance Drop",
  weak_topic:        "⚠️ Weak Topic",
  below_branch_avg:  "📊 Below Branch Avg",
  consistently_low:  "🔴 Consistently Low",
};

export default function DashboardWeakStudentsPage() {
  const { examId, resolvedExamId, setExamId } = useExamSelector();
  const [filter, setFilter] = useState<FilterSeverity>("all");
  const [dims, setDims]     = useState<DimensionParams>({});

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["weak-students", resolvedExamId, dims],
    queryFn: () => dashboardApi.weakStudents(resolvedExamId!, dims).then((r) => r.data),
    enabled: resolvedExamId !== null,
  });

  if (isLoading) return <PageLoader />;
  if (isError || !data) return <ErrorBanner onRetry={refetch} />;

  const filtered: WeakStudentEntry[] = filter === "all"
    ? data.students
    : data.students.filter((s) => s.severity === filter);

  const FILTER_BTNS: { label: string; key: FilterSeverity; count: number; cls: string }[] = [
    { label: "All",      key: "all",      count: data.students.length,  cls: "btn-secondary" },
    { label: "Critical", key: "critical", count: data.critical_count,   cls: "border border-danger text-danger-dark hover:bg-danger-light" },
    { label: "Warning",  key: "warning",  count: data.warning_count,    cls: "border border-warning text-warning-dark hover:bg-warning-light" },
    { label: "Info",     key: "info",     count: data.info_count,       cls: "border border-info text-info-dark hover:bg-info-light" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">🚨 Weak Students</h1>
          <p className="text-surface-500 text-sm mt-0.5">Students requiring intervention this week</p>
        </div>
        <ExamPicker examId={examId} onChange={setExamId} />
      </div>

      <DimensionFilter value={dims} onChange={setDims} />

      {/* Summary KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card border-l-4 border-danger">
          <p className="stat-label">Critical</p>
          <p className="stat-value text-danger">{data.critical_count}</p>
          <p className="stat-sub">Immediate action needed</p>
        </div>
        <div className="card border-l-4 border-warning">
          <p className="stat-label">Warning</p>
          <p className="stat-value text-warning">{data.warning_count}</p>
          <p className="stat-sub">Monitor closely</p>
        </div>
        <div className="card border-l-4 border-info">
          <p className="stat-label">Info</p>
          <p className="stat-value text-info">{data.info_count}</p>
          <p className="stat-sub">Watch list</p>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2">
        {FILTER_BTNS.map(({ label, key, count, cls }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`btn btn-sm gap-1.5 ${filter === key ? "ring-2 ring-offset-1 ring-primary-400" : cls}`}
          >
            {label}
            <span className="bg-black/10 rounded-full px-1.5 py-0.5 text-[10px] font-bold">{count}</span>
          </button>
        ))}
      </div>

      {/* Student cards grid */}
      {filtered.length === 0 ? (
        <EmptyState icon="🎉" title="No students in this category" description="All students are performing well!" />
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((s) => (
            <StudentAlertCard key={s.admission_no} student={s} />
          ))}
        </div>
      )}
    </div>
  );
}

function StudentAlertCard({ student: s }: { student: WeakStudentEntry }) {
  const borderMap = { critical: "border-danger/50", warning: "border-warning/50", info: "border-info/50" };

  return (
    <div className={`card border-l-4 ${borderMap[s.severity]} hover:shadow-card-hover transition-shadow`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <Link to={`/students/${s.admission_no}`} className="font-semibold text-surface-900 hover:text-primary-600 transition-colors">
            {s.name}
          </Link>
          <p className="text-xs text-surface-400 font-mono mt-0.5">{s.admission_no}</p>
        </div>
        <SeverityBadge severity={s.severity} />
      </div>

      <div className="flex gap-3 text-sm text-surface-600 mb-3">
        <span>🏫 {s.branch_name}</span>
        {s.latest_rank && <span>🏆 Rank #{s.latest_rank}</span>}
        {s.latest_total !== undefined && <span>📊 {fmtNum(s.latest_total, 0)} pts</span>}
      </div>

      <div className="space-y-1.5">
        {s.alerts.map((a, i) => (
          <div key={i} className="flex items-start gap-2 text-xs bg-surface-50 rounded-lg px-3 py-2">
            <span className="shrink-0">{RULE_LABEL[a.rule_key] ?? a.rule_key}</span>
            <span className="text-surface-500 leading-tight">{a.message}</span>
          </div>
        ))}
      </div>

      <div className="mt-3 pt-3 border-t border-surface-100">
        <Link to={`/students/${s.admission_no}`} className="text-xs text-primary-600 hover:text-primary-700 font-medium">
          View full profile →
        </Link>
      </div>
    </div>
  );
}
