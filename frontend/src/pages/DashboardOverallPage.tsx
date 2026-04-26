/**
 * D1 – Overall Performance Dashboard
 * Cards → Trend line chart → Branch comparison bar → Histogram → Top-10 table
 */
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell,
} from "recharts";
import { dashboardApi, ExamTrendPoint } from "@/lib/api";
import { fmtNum, fmtPct, fmt, SUBJECT_COLORS } from "@/lib/utils";
import StatCard from "@/components/ui/StatCard";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import EmptyState from "@/components/ui/EmptyState";
import ExamPicker from "@/components/ui/ExamPicker";
import { useExamSelector } from "@/hooks/useExamSelector";

export default function DashboardOverallPage() {
  const { examId, setExamId } = useExamSelector();

  const { data: exams, isLoading: examsLoading } = useQuery({
    queryKey: ["exams-list"],
    queryFn: () => dashboardApi.exams().then((r) => r.data),
  });

  // Resolve the actual exam id — fall back to the first available if the stored one is stale
  const resolvedExamId: number | null = (() => {
    if (!exams || exams.length === 0) return null;
    return exams.find((e) => e.id === examId) ? examId : exams[0].id;
  })();

  // Persist fallback so other pages pick it up too
  useEffect(() => {
    if (resolvedExamId !== null && resolvedExamId !== examId) setExamId(resolvedExamId);
  }, [resolvedExamId]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["dashboard-overall", resolvedExamId],
    queryFn: () => dashboardApi.overall(resolvedExamId!).then((r) => r.data),
    enabled: resolvedExamId !== null,
  });

  const { data: trend } = useQuery<ExamTrendPoint[]>({
    queryKey: ["exam-trend", resolvedExamId],
    queryFn: () => dashboardApi.examTrend(resolvedExamId!).then((r) => r.data),
    enabled: resolvedExamId !== null,
  });

  if (examsLoading) return <PageLoader />;

  if (!exams || exams.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="page-title">Dashboard</h1>
            <p className="text-surface-500 text-sm mt-0.5">Overall Performance</p>
          </div>
          <ExamPicker examId={examId} onChange={setExamId} />
        </div>
        <EmptyState
          icon="📋"
          title="No exams configured"
          description="Upload an exam to get started. Go to the Upload Console to upload question papers, responses, and answer keys."
        />
      </div>
    );
  }

  if (isLoading) return <PageLoader />;
  if (isError || !data) return <ErrorBanner onRetry={refetch} />;

  const BRANCH_COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#3b82f6", "#ec4899"];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">{data.exam_name}</h1>
          <p className="text-surface-500 text-sm mt-0.5">{fmt(data.exam_date)} · Overall Performance</p>
        </div>
        <ExamPicker examId={examId} onChange={setExamId} />
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="Total Students" value={data.total_students} icon="👥" color="primary" />
        <StatCard label="Avg Score"     value={fmtNum(data.avg_total)}     icon="📊" color="info" />
        <StatCard label="Avg Physics"   value={fmtNum(data.avg_physics)}   icon="⚡" color="primary"
          sub={`${fmtPct(data.avg_physics / data.avg_total * 100)} of total`} />
        <StatCard label="Avg Chemistry" value={fmtNum(data.avg_chemistry)} icon="🧪" color="success" />
        <StatCard label="Avg Maths"     value={fmtNum(data.avg_maths)}     icon="📐" color="warning" />
        <StatCard label="Pass Rate"     value={fmtPct(data.pass_rate_pct)} icon="✅" color="success"
          sub={`Top ${fmtNum(data.max_total, 0)} / Low ${fmtNum(data.min_total, 0)}`} />
      </div>

      {/* Row 2: Trend + Branch compare */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Exam trend line */}
        <div className="card">
          <p className="section-title mb-4">📈 Score Trend (last exams)</p>
          {trend && trend.length > 1 ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trend} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="exam_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0" }} />
                <Legend />
                <Line type="monotone" dataKey="avg_total"     name="Total"     stroke="#6366f1" strokeWidth={2} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="avg_physics"   name="Physics"   stroke={SUBJECT_COLORS.physics}   strokeWidth={2} dot={{ r: 3 }} strokeDasharray="4 2" />
                <Line type="monotone" dataKey="avg_chemistry" name="Chemistry" stroke={SUBJECT_COLORS.chemistry} strokeWidth={2} dot={{ r: 3 }} strokeDasharray="4 2" />
                <Line type="monotone" dataKey="avg_maths"     name="Maths"     stroke={SUBJECT_COLORS.maths}     strokeWidth={2} dot={{ r: 3 }} strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-surface-400 text-sm text-center py-16">Not enough exams yet for trend data.</p>
          )}
        </div>

        {/* Branch comparison */}
        <div className="card">
          <p className="section-title mb-4">🏫 Branch Comparison</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.branch_comparison} layout="vertical" margin={{ top: 4, right: 32, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis dataKey="branch" type="category" tick={{ fontSize: 11 }} width={120} />
              <Tooltip contentStyle={{ borderRadius: 12 }} />
              <Bar dataKey="avg_total" name="Avg Score" radius={[0, 6, 6, 0]}>
                {data.branch_comparison.map((_, i) => (
                  <Cell key={i} fill={BRANCH_COLORS[i % BRANCH_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 3: Histogram + Top students */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Score distribution histogram */}
        <div className="card">
          <p className="section-title mb-4">📊 Score Distribution</p>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart
              data={data.histogram.map((b) => ({
                name: `${b.bucket_start}–${b.bucket_end}`,
                count: b.count,
              }))}
              margin={{ top: 4, right: 16, bottom: 0, left: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ borderRadius: 12 }} />
              <Bar dataKey="count" name="Students" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Top students table */}
        <div className="card overflow-hidden p-0">
          <div className="px-6 py-4 border-b border-surface-100">
            <p className="section-title">🏆 Top Students</p>
          </div>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Admission No</th>
                  <th>Name</th>
                  <th className="text-right">Score</th>
                </tr>
              </thead>
              <tbody>
                {data.top_students.map((s) => (
                  <tr key={s.rank}>
                    <td>
                      <span className={`font-bold ${s.rank === 1 ? "text-yellow-500" : s.rank === 2 ? "text-surface-400" : s.rank === 3 ? "text-orange-400" : "text-surface-600"}`}>
                        #{s.rank}
                      </span>
                    </td>
                    <td className="font-mono text-xs text-surface-500">{s.admission_no}</td>
                    <td className="font-medium">{s.name}</td>
                    <td className="text-right font-semibold text-primary-700">{fmtNum(s.total, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
