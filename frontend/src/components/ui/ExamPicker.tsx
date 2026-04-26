import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";

interface Props {
  examId: number;
  onChange: (id: number) => void;
}

export default function ExamPicker({ examId, onChange }: Props) {
  const { data: exams, isLoading } = useQuery({
    queryKey: ["exams-list"],
    queryFn: () => dashboardApi.exams().then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-surface-400">Loading exams…</span>
      </div>
    );
  }

  if (!exams || exams.length === 0) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-100 rounded-lg text-sm text-surface-600 border border-surface-200">
        No exams configured
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-surface-600 whitespace-nowrap">Exam</label>
      <select
        value={examId}
        onChange={(e) => onChange(Number(e.target.value))}
        className="input w-56 py-1.5"
      >
        {exams.map((exam) => (
          <option key={exam.id} value={exam.id}>
            {exam.exam_code} {exam.title ? `— ${exam.title}` : ""} {exam.exam_date ? `(${exam.exam_date})` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
