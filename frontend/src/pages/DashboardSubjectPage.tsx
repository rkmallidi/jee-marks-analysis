/**
 * D3 – Subject Analysis Dashboard
 * Per-subject bar chart + accuracy + top/bottom performers
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis,
} from "recharts";
import { dashboardApi, DimensionParams } from "@/lib/api";
import { fmtNum, fmtPct, subjectColor } from "@/lib/utils";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import ExamPicker from "@/components/ui/ExamPicker";
import DimensionFilter from "@/components/ui/DimensionFilter";
import { useExamSelector } from "@/hooks/useExamSelector";

export default function DashboardSubjectPage() {
  const { examId, resolvedExamId, setExamId } = useExamSelector();
  const [dims, setDims] = useState<DimensionParams>({});

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["subject-analysis", resolvedExamId, dims],
    queryFn: () => dashboardApi.subjectAnalysis(resolvedExamId!, dims).then((r) => r.data),
    enabled: resolvedExamId !== null,
  });

  if (isLoading) return <PageLoader />;
  if (isError || !data) return <ErrorBanner onRetry={refetch} />;

  const radarData = data.subjects.map((s) => ({
    subject: s.subject,
    accuracy: s.avg_accuracy_pct,
    marks: s.avg_marks,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">📐 Subject Analysis</h1>
          <p className="text-surface-500 text-sm mt-0.5">Average performance and accuracy per subject</p>
        </div>
        <ExamPicker examId={examId} onChange={setExamId} />
      </div>

      <DimensionFilter value={dims} onChange={setDims} />

      {/* KPI cards */}
      <div className="grid sm:grid-cols-3 gap-4">
        {data.subjects.map((s) => (
          <div
            key={s.subject}
            className="card border-l-4"
            style={{ borderLeftColor: subjectColor(s.subject) }}
          >
            <p className="stat-label">{s.subject}</p>
            <p className="stat-value" style={{ color: subjectColor(s.subject) }}>
              {fmtNum(s.avg_marks, 1)}
            </p>
            <p className="stat-sub">Avg accuracy {fmtPct(s.avg_accuracy_pct)}</p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Grouped bar */}
        <div className="card">
          <p className="section-title mb-4">Avg Marks by Subject</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.subjects} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="subject" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ borderRadius: 12 }} />
              <Bar dataKey="avg_marks" name="Avg Marks" radius={[6, 6, 0, 0]}>
                {data.subjects.map((s, i) => (
                  <Cell key={i} fill={subjectColor(s.subject)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Radar accuracy */}
        <div className="card">
          <p className="section-title mb-4">Accuracy Radar</p>
          <ResponsiveContainer width="100%" height={260}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
              <Radar name="Accuracy %" dataKey="accuracy" stroke="#6366f1" fill="#6366f1" fillOpacity={0.25} strokeWidth={2} />
              <Tooltip contentStyle={{ borderRadius: 12 }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top / Bottom performers per subject */}
      <div className="grid sm:grid-cols-3 gap-6">
        {data.subjects.map((s) => (
          <div key={s.subject} className="card overflow-hidden p-0">
            <div
              className="px-5 py-3 font-semibold text-sm text-white"
              style={{ backgroundColor: subjectColor(s.subject) }}
            >
              {s.subject}
            </div>

            <div className="p-4 space-y-4">
              <div>
                <p className="text-xs font-semibold text-success-dark mb-2">🟢 Top performers</p>
                {s.top_students.map((st, i) => (
                  <div key={i} className="flex justify-between items-center py-1 border-b border-surface-100 last:border-0">
                    <span className="text-sm text-surface-700 truncate">{st.name}</span>
                    <span className="text-sm font-semibold text-success-dark ml-2">{fmtNum(st.marks, 0)}</span>
                  </div>
                ))}
              </div>
              <div>
                <p className="text-xs font-semibold text-danger-dark mb-2">🔴 Needs support</p>
                {s.bottom_students.map((st, i) => (
                  <div key={i} className="flex justify-between items-center py-1 border-b border-surface-100 last:border-0">
                    <span className="text-sm text-surface-700 truncate">{st.name}</span>
                    <span className="text-sm font-semibold text-danger-dark ml-2">{fmtNum(st.marks, 0)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
