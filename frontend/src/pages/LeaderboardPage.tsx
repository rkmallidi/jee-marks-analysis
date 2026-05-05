/**
 * D5a – Leaderboard
 * Full ranking table with medal icons, score bars, accuracy
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi, DimensionParams } from "@/lib/api";
import { fmtNum, fmtPct, SUBJECT_COLORS } from "@/lib/utils";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import ExamPicker from "@/components/ui/ExamPicker";
import DimensionFilter from "@/components/ui/DimensionFilter";
import { useExamSelector } from "@/hooks/useExamSelector";
import { Link } from "react-router-dom";

const MEDAL = (r: number) =>
  r === 1 ? "🥇" : r === 2 ? "🥈" : r === 3 ? "🥉" : `#${r}`;

export default function LeaderboardPage() {
  const { examId, resolvedExamId, setExamId } = useExamSelector();
  const [dims, setDims] = useState<DimensionParams>({});

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["leaderboard", resolvedExamId, dims],
    queryFn: () => dashboardApi.leaderboard(resolvedExamId!, 50, dims).then((r) => r.data),
    enabled: resolvedExamId !== null,
  });

  if (isLoading) return <PageLoader />;
  if (isError || !data) return <ErrorBanner onRetry={refetch} />;

  const maxTotal = data[0]?.total_marks ?? 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">🏆 Leaderboard</h1>
          <p className="text-surface-500 text-sm mt-0.5">Top 50 students ranked by total marks</p>
        </div>
        <ExamPicker examId={examId} onChange={setExamId} />
      </div>

      <DimensionFilter value={dims} onChange={setDims} />

      {/* Top 3 podium cards */}
      {data.length >= 3 && (
        <div className="grid grid-cols-3 gap-4">
          {[data[1], data[0], data[2]].map((s, idx) => {
            if (!s) return null;
            const heights = ["h-28", "h-36", "h-28"];
            const golds   = ["from-surface-200", "from-yellow-200", "from-orange-200"];
            return (
              <div
                key={s.admission_no}
                className={`card flex flex-col items-center justify-end ${heights[idx]} bg-gradient-to-b ${golds[idx]} to-white`}
              >
                <p className="text-3xl mb-1">{MEDAL(s.rank)}</p>
                <Link to={`/students/${s.admission_no}`} className="font-semibold text-sm text-center hover:text-primary-600 truncate max-w-full px-2">
                  {s.name}
                </Link>
                <p className="text-xs text-surface-500">{s.branch_name}</p>
                <p className="text-lg font-bold text-surface-900 mt-1">{fmtNum(s.total_marks, 0)}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Full table */}
      <div className="card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="tbl">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Student</th>
                <th>Branch</th>
                <th className="text-right">Total</th>
                <th className="text-right" style={{ color: SUBJECT_COLORS.physics }}>Physics</th>
                <th className="text-right" style={{ color: SUBJECT_COLORS.chemistry }}>Chem</th>
                <th className="text-right" style={{ color: SUBJECT_COLORS.maths }}>Maths</th>
                <th className="text-right">Accuracy</th>
                <th className="text-right">Percentile</th>
                <th className="w-32">Score Bar</th>
              </tr>
            </thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.admission_no}>
                  <td>
                    <span className={`font-bold text-sm ${s.rank <= 3 ? "text-yellow-500" : "text-surface-500"}`}>
                      {MEDAL(s.rank)}
                    </span>
                  </td>
                  <td>
                    <Link to={`/students/${s.admission_no}`} className="font-medium text-surface-800 hover:text-primary-600">
                      {s.name}
                    </Link>
                    <p className="text-xs text-surface-400 font-mono">{s.admission_no}</p>
                  </td>
                  <td className="text-surface-600 text-sm">{s.branch_name}</td>
                  <td className="text-right font-bold text-surface-900">{fmtNum(s.total_marks, 0)}</td>
                  <td className="text-right" style={{ color: SUBJECT_COLORS.physics }}>{fmtNum(s.physics_marks, 0)}</td>
                  <td className="text-right" style={{ color: SUBJECT_COLORS.chemistry }}>{fmtNum(s.chemistry_marks, 0)}</td>
                  <td className="text-right" style={{ color: SUBJECT_COLORS.maths }}>{fmtNum(s.maths_marks, 0)}</td>
                  <td className="text-right">{fmtPct(s.accuracy_pct)}</td>
                  <td className="text-right text-xs text-surface-500">P{fmtNum(s.percentile, 0)}</td>
                  <td className="px-3">
                    <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-500 rounded-full"
                        style={{ width: `${(s.total_marks / maxTotal) * 100}%` }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
