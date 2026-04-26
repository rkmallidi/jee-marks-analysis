/**
 * Alerts feed — filter by severity / rule / acknowledged status
 * Acknowledge button fires PATCH and invalidates cache
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { alertsApi, examsApi, AlertOut } from "@/lib/api";
import { fmt } from "@/lib/utils";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import SeverityBadge from "@/components/ui/SeverityBadge";
import EmptyState from "@/components/ui/EmptyState";

const RULE_LABELS: Record<string, string> = {
  performance_drop: "Performance Drop",
  weak_topic:       "Weak Topic",
  below_branch_avg: "Below Branch Avg",
  consistently_low: "Consistently Low",
};

export default function AlertsPage() {
  const qc = useQueryClient();
  const [severity, setSeverity]     = useState<string>("");
  const [ruleKey, setRuleKey]       = useState<string>("");
  const [showAcked, setShowAcked]   = useState(false);
  const [examId, setExamId]         = useState<number | "">("");

  const { data: exams } = useQuery({
    queryKey: ["exams"],
    queryFn:  () => examsApi.list().then((r) => r.data),
  });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["alerts", severity, ruleKey, showAcked, examId],
    queryFn: () =>
      alertsApi
        .list({
          severity:     severity || undefined,
          rule_key:     ruleKey || undefined,
          acknowledged: showAcked || undefined,
          exam_id:      examId   || undefined,
        })
        .then((r) => r.data),
  });

  const ackMut = useMutation({
    mutationFn: (id: number) => alertsApi.ack(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  if (isLoading) return <PageLoader />;
  if (isError)   return <ErrorBanner onRetry={refetch} />;

  const alerts = data ?? [];
  const critical = alerts.filter((a) => a.severity === "critical").length;
  const warning  = alerts.filter((a) => a.severity === "warning").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">🔔 Alerts</h1>
          <p className="text-surface-500 text-sm mt-0.5">
            {critical > 0 && <span className="text-danger-dark font-medium">{critical} critical · </span>}
            {warning > 0  && <span className="text-warning-dark font-medium">{warning} warnings · </span>}
            {alerts.length} total
          </p>
        </div>
        <button onClick={() => refetch()} className="btn-secondary btn-sm">
          ↺ Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="card py-3 flex flex-wrap items-center gap-3">
        {/* Exam filter */}
        <select
          value={examId}
          onChange={(e) => setExamId(e.target.value ? Number(e.target.value) : "")}
          className="input w-auto py-1.5"
        >
          <option value="">All Tests</option>
          {(exams ?? []).map((ex) => (
            <option key={ex.id} value={ex.id}>
              {ex.exam_code}{ex.title ? ` — ${ex.title}` : ""}
            </option>
          ))}
        </select>

        {/* Severity filter */}
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="input w-auto py-1.5"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>

        {/* Rule filter */}
        <select
          value={ruleKey}
          onChange={(e) => setRuleKey(e.target.value)}
          className="input w-auto py-1.5"
        >
          <option value="">All Rules</option>
          {Object.entries(RULE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>

        {/* Acknowledged toggle */}
        <label className="flex items-center gap-2 text-sm text-surface-600 cursor-pointer">
          <input
            type="checkbox"
            checked={showAcked}
            onChange={(e) => setShowAcked(e.target.checked)}
            className="rounded border-surface-300 text-primary-600 focus:ring-primary-500"
          />
          Show acknowledged
        </label>

        {(examId || severity || ruleKey || showAcked) && (
          <button
            onClick={() => { setExamId(""); setSeverity(""); setRuleKey(""); setShowAcked(false); }}
            className="btn-ghost btn-sm text-surface-400"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Alert list */}
      {alerts.length === 0 ? (
        <EmptyState icon="🎉" title="No alerts" description="All students are on track!" />
      ) : (
        <div className="space-y-3">
          {alerts.map((a) => <AlertRow key={a.id} alert={a} onAck={ackMut.mutate} acking={ackMut.isPending} />)}
        </div>
      )}
    </div>
  );
}

function AlertRow({ alert: a, onAck, acking }: { alert: AlertOut; onAck: (id: number) => void; acking: boolean }) {
  const border = a.severity === "critical" ? "border-danger/40" : a.severity === "warning" ? "border-warning/40" : "border-info/40";

  return (
    <div className={`card border-l-4 ${border} flex flex-col sm:flex-row sm:items-start gap-4 ${a.is_acknowledged ? "opacity-60" : ""}`}>
      <div className="flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={a.severity} />
          <span className="text-xs bg-surface-100 text-surface-600 rounded-full px-2 py-0.5 font-medium">
            {RULE_LABELS[a.rule_key] ?? a.rule_key}
          </span>
          {a.is_acknowledged && (
            <span className="text-xs bg-success-light text-success-dark rounded-full px-2 py-0.5 font-medium">
              ✓ Acknowledged
            </span>
          )}
        </div>

        <p className="font-semibold text-surface-800">{a.message}</p>

        <div className="flex flex-wrap gap-3 text-sm text-surface-500">
          <Link to={`/students/${a.admission_no}`} className="hover:text-primary-600 font-medium">
            👤 {a.student_name}
          </Link>
          <span className="font-mono text-xs">{a.admission_no}</span>
          {a.exam_name && <span>📝 {a.exam_name}</span>}
          <span>🕐 {fmt(a.created_at, "dd MMM yyyy, HH:mm")}</span>
        </div>

        {/* Context details — skip nested objects/arrays, they're shown elsewhere */}
        {Object.keys(a.context).length > 0 && (
          <div className="flex flex-wrap gap-2 mt-1">
            {Object.entries(a.context)
              .filter(([, v]) => typeof v !== "object" || v === null)
              .map(([k, v]) => (
                <span key={k} className="text-xs bg-surface-100 text-surface-600 rounded-lg px-2 py-1 font-mono">
                  {k}: {String(v)}
                </span>
              ))}
          </div>
        )}
      </div>

      {!a.is_acknowledged && (
        <button
          onClick={() => onAck(a.id)}
          disabled={acking}
          className="btn-secondary btn-sm shrink-0 self-start"
        >
          ✓ Acknowledge
        </button>
      )}
    </div>
  );
}
