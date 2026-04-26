/**
 * Exams Management Page
 * List existing exams and create new ones with exam_type-driven paper assignment.
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { examsApi, ExamOut, ExamCreate } from "@/lib/api";
import ErrorBanner from "@/components/ui/ErrorBanner";
import { fmt } from "@/lib/utils";

const EXAM_TYPE_PAPERS: Record<string, string[]> = {
  Mains:    ["P1"],
  Advanced: ["P1", "P2"],
};

const EMPTY_FORM: ExamCreate = {
  exam_code: "",
  title:     "",
  exam_date: "",
  exam_type: "Mains",
};

export default function ExamsPage() {
  const qc = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm]         = useState<ExamCreate>(EMPTY_FORM);
  const [formErr, setFormErr]   = useState("");

  const { data: exams, isLoading, isError, refetch } = useQuery<ExamOut[]>({
    queryKey: ["exams"],
    queryFn:  () => examsApi.list().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: ExamCreate) => examsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["exams"] });
      qc.invalidateQueries({ queryKey: ["exams-list"] });
      setShowForm(false);
      setForm(EMPTY_FORM);
      setFormErr("");
    },
    onError: (err: any) => {
      setFormErr(err.response?.data?.message ?? "Failed to create exam. Check inputs and try again.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormErr("");
    if (!form.exam_code.trim() || !form.title.trim() || !form.exam_date) {
      setFormErr("Exam code, title, and date are all required.");
      return;
    }
    createMutation.mutate(form);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">📝 Exams</h1>
          <p className="text-surface-500 text-sm mt-0.5">
            Create and manage exam entries. Papers are assigned automatically by exam type.
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() => { setShowForm(!showForm); setFormErr(""); }}
        >
          {showForm ? "✕ Cancel" : "+ New Exam"}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="card max-w-xl">
          <h2 className="section-title mb-4">Create Exam</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Exam Code */}
            <div>
              <label className="label-text" htmlFor="exam_code">
                Exam Code <span className="text-danger-dark">*</span>
              </label>
              <input
                id="exam_code"
                type="text"
                className="input w-full mt-1"
                placeholder="e.g. JEE-MAIN-2025-APR"
                value={form.exam_code}
                onChange={(e) => setForm({ ...form, exam_code: e.target.value })}
                maxLength={50}
                required
              />
            </div>

            {/* Title */}
            <div>
              <label className="label-text" htmlFor="title">
                Title <span className="text-danger-dark">*</span>
              </label>
              <input
                id="title"
                type="text"
                className="input w-full mt-1"
                placeholder="e.g. JEE Main April 2025"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                maxLength={200}
                required
              />
            </div>

            {/* Date */}
            <div>
              <label className="label-text" htmlFor="exam_date">
                Exam Date <span className="text-danger-dark">*</span>
              </label>
              <input
                id="exam_date"
                type="date"
                className="input w-full mt-1"
                value={form.exam_date}
                onChange={(e) => setForm({ ...form, exam_date: e.target.value })}
                required
              />
            </div>

            {/* Exam Type */}
            <div>
              <label className="label-text">
                Exam Type <span className="text-danger-dark">*</span>
              </label>
              <div className="mt-2 flex gap-6">
                {(["Mains", "Advanced"] as const).map((t) => (
                  <label key={t} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="exam_type"
                      value={t}
                      checked={form.exam_type === t}
                      onChange={() => setForm({ ...form, exam_type: t })}
                      className="accent-primary-500"
                    />
                    <span className="text-sm font-medium text-surface-700">{t}</span>
                    <span className="text-xs text-surface-400">
                      ({EXAM_TYPE_PAPERS[t].join(", ")})
                    </span>
                  </label>
                ))}
              </div>
              <p className="text-xs text-surface-400 mt-1">
                {form.exam_type === "Mains"
                  ? "Mains → Paper 1 (P1) only"
                  : "Advanced → Paper 1 (P1) and Paper 2 (P2)"}
              </p>
            </div>

            {formErr && (
              <p className="text-sm text-danger-dark bg-danger-light rounded-lg px-3 py-2">
                ⚠ {formErr}
              </p>
            )}

            <div className="flex gap-3 pt-1">
              <button
                type="submit"
                className="btn-primary"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? "Creating…" : "Create Exam"}
              </button>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => { setShowForm(false); setForm(EMPTY_FORM); setFormErr(""); }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Exam list */}
      {isError && <ErrorBanner onRetry={refetch} />}

      {isLoading ? (
        <div className="card py-12 text-center text-surface-400 text-sm">Loading exams…</div>
      ) : !exams || exams.length === 0 ? (
        <div className="card py-12 text-center text-surface-400 text-sm">
          No exams yet. Create one with the button above.
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Title</th>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Papers</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {exams.map((exam) => (
                  <tr key={exam.id}>
                    <td className="font-mono text-sm font-semibold text-primary-700">
                      {exam.exam_code}
                    </td>
                    <td className="text-sm">{exam.title ?? <span className="text-surface-400">—</span>}</td>
                    <td className="text-sm">
                      {exam.exam_date
                        ? new Date(exam.exam_date).toLocaleDateString("en-IN", {
                            day: "2-digit", month: "short", year: "numeric",
                          })
                        : <span className="text-surface-400">—</span>}
                    </td>
                    <td>
                      <span
                        className={
                          exam.exam_type === "Advanced"
                            ? "badge badge-info"
                            : "badge badge-neutral"
                        }
                      >
                        {exam.exam_type ?? "—"}
                      </span>
                    </td>
                    <td>
                      <div className="flex gap-1">
                        {exam.papers.map((p) => (
                          <span key={p} className="badge badge-success text-xs">{p}</span>
                        ))}
                      </div>
                    </td>
                    <td className="text-xs text-surface-500">
                      {fmt(exam.created_at, "dd MMM yyyy")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
