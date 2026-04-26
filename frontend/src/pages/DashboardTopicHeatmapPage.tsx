/**
 * D4 – Topic Heatmap Dashboard
 * Color-coded grid: green=strong, yellow=average, red=weak
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi, TopicHeatEntry } from "@/lib/api";
import { fmtPct, pctToHeatColor, pctToTextColor, subjectColor } from "@/lib/utils";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import ExamPicker from "@/components/ui/ExamPicker";
import EmptyState from "@/components/ui/EmptyState";
import { useExamSelector } from "@/hooks/useExamSelector";

const SUBJECTS = ["Physics", "Chemistry", "Maths"];

export default function DashboardTopicHeatmapPage() {
  const { examId, resolvedExamId, setExamId } = useExamSelector();
  const [subject, setSubject] = useState<string>("all");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["topic-heatmap", resolvedExamId],
    queryFn: () => dashboardApi.topicHeatmap(resolvedExamId!).then((r) => r.data),
    enabled: resolvedExamId !== null,
  });

  if (isLoading) return <PageLoader />;
  if (isError || !data) return <ErrorBanner onRetry={refetch} />;

  const topics: TopicHeatEntry[] = subject === "all"
    ? data.topics
    : data.topics.filter((t) => t.subject === subject);

  // Group for section display
  const grouped = SUBJECTS.reduce<Record<string, TopicHeatEntry[]>>((acc, sub) => {
    acc[sub] = topics.filter((t) => t.subject === sub);
    return acc;
  }, {});

  const weakTopics  = data.topics.filter((t) => t.avg_accuracy_pct < 40).length;
  const strongTopics= data.topics.filter((t) => t.avg_accuracy_pct >= 80).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">🔥 Topic Heatmap</h1>
          <p className="text-surface-500 text-sm mt-0.5">Accuracy across all topics — darker red = needs attention</p>
        </div>
        <ExamPicker examId={examId} onChange={setExamId} />
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="card text-center">
          <p className="stat-label">Topics Tracked</p>
          <p className="stat-value">{data.topics.length}</p>
        </div>
        <div className="card text-center border-l-4 border-danger">
          <p className="stat-label">Weak ({"<"}40%)</p>
          <p className="stat-value text-danger">{weakTopics}</p>
        </div>
        <div className="card text-center border-l-4 border-success">
          <p className="stat-label">Strong (≥80%)</p>
          <p className="stat-value text-success-dark">{strongTopics}</p>
        </div>
        <div className="card text-center">
          <p className="stat-label">Avg Accuracy</p>
          <p className="stat-value">
            {fmtPct(data.topics.reduce((s, t) => s + t.avg_accuracy_pct, 0) / (data.topics.length || 1))}
          </p>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-surface-600">
        <span className="font-medium">Accuracy key:</span>
        {[
          { label: "< 40%   Critical", bg: "#fee2e2", fg: "#b91c1c" },
          { label: "40–60%  Average",  bg: "#fef3c7", fg: "#b45309" },
          { label: "60–80%  Good",     bg: "#ccfbf1", fg: "#0f766e" },
          { label: "≥ 80%   Strong",   bg: "#dcfce7", fg: "#15803d" },
        ].map(({ label, bg, fg }) => (
          <span
            key={label}
            className="px-2.5 py-1 rounded-lg font-semibold text-[11px]"
            style={{ backgroundColor: bg, color: fg }}
          >
            {label}
          </span>
        ))}
      </div>

      {/* Subject filter */}
      <div className="flex flex-wrap gap-2">
        {["all", ...SUBJECTS].map((sub) => (
          <button
            key={sub}
            onClick={() => setSubject(sub)}
            className={`btn btn-sm capitalize ${subject === sub ? "btn-primary" : "btn-secondary"}`}
            style={
              sub !== "all" && subject !== sub
                ? { borderColor: subjectColor(sub), color: subjectColor(sub) }
                : {}
            }
          >
            {sub === "all" ? "All Subjects" : sub}
          </button>
        ))}
      </div>

      {/* Heatmap grid */}
      {topics.length === 0 ? (
        <EmptyState icon="🔥" title="No topic data yet" description="Run an evaluation first." />
      ) : (
        <div className="space-y-6">
          {SUBJECTS.filter((s) => subject === "all" || s === subject).map((sub) => (
            grouped[sub]?.length ? (
              <div key={sub}>
                <div
                  className="flex items-center gap-2 mb-3"
                >
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: subjectColor(sub) }}
                  />
                  <h2 className="font-semibold text-surface-700">{sub}</h2>
                  <span className="text-surface-400 text-sm">({grouped[sub].length} topics)</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                  {grouped[sub].map((topic) => (
                    <TopicCell key={topic.topic_name} topic={topic} />
                  ))}
                </div>
              </div>
            ) : null
          ))}
        </div>
      )}
    </div>
  );
}

function TopicCell({ topic: t }: { topic: TopicHeatEntry }) {
  const bg  = pctToHeatColor(t.avg_accuracy_pct);
  const fg  = pctToTextColor(t.avg_accuracy_pct);

  return (
    <div
      className="rounded-xl p-4 flex flex-col gap-2 border transition-transform duration-150 hover:scale-105 cursor-default"
      style={{ backgroundColor: bg, borderColor: fg + "40" }}
    >
      <p className="text-sm font-semibold leading-tight" style={{ color: fg }}>
        {t.topic_name}
      </p>
      <p className="text-2xl font-bold" style={{ color: fg }}>
        {fmtPct(t.avg_accuracy_pct)}
      </p>
      <p className="text-xs opacity-75" style={{ color: fg }}>
        {t.attempt_rate_pct.toFixed(0)}% attempted · {t.student_count} students
      </p>
    </div>
  );
}
