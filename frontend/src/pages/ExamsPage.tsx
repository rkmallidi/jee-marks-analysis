/**
 * Exams Management Page
 * List existing exams and create new ones with exam_type-driven paper assignment.
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { examsApi, ExamOut, ExamCreate, ExamUpdate } from "@/lib/api";
import ErrorBanner from "@/components/ui/ErrorBanner";
import { fmt } from "@/lib/utils";

const EXAM_TYPE_PAPERS: Record<string, string[]> = {
  Mains:    ["P1"],
  Advanced: ["P1", "P2"],
};

const EMPTY_FORM: ExamCreate = {
  exam_code:     "",
  title:         "",
  exam_date:     "",
  exam_type:     "Mains",
  program_name:  "",
  student_class: "",
};

export default function ExamsPage() {
  const qc = useQueryClient();

  const [showForm, setShowForm]       = useState(false);
  const [form, setForm]               = useState<ExamCreate>(EMPTY_FORM);
  const [formErr, setFormErr]         = useState("");
  const [editingExam, setEditingExam] = useState<ExamOut | null>(null);
  const [editForm, setEditForm]       = useState<ExamUpdate>({});
  const [editErr, setEditErr]         = useState("");

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

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ExamUpdate }) => examsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["exams"] });
      qc.invalidateQueries({ queryKey: ["exams-list"] });
      setEditingExam(null);
      setEditErr("");
    },
    onError: (err: any) => {
      setEditErr(err.response?.data?.message ?? "Failed to update exam.");
    },
  });

  const openEdit = (exam: ExamOut) => {
    setEditingExam(exam);
    setEditErr("");
    setEditForm({
      title:         exam.title         ?? "",
      exam_date:     exam.exam_date     ?? "",
      exam_type:     (exam.exam_type as "Mains" | "Advanced") ?? "Mains",
      program_name:  exam.program_name  ?? "",
      student_class: exam.student_class ?? "",
    });
  };

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

            {/* Program Name */}
            <div>
              <label className="label-text" htmlFor="program_name">
                Program Name
              </label>
              <input
                id="program_name"
                type="text"
                className="input w-full mt-1"
                placeholder="e.g. IIT-JEE (optional)"
                value={form.program_name ?? ""}
                onChange={(e) => setForm({ ...form, program_name: e.target.value || undefined })}
                maxLength={50}
              />
              <p className="text-xs text-surface-400 mt-1">
                Used to scope All India Rank and absent tracking.
              </p>
            </div>

            {/* Student Class */}
            <div>
              <label className="label-text" htmlFor="student_class">
                Student Class
              </label>
              <input
                id="student_class"
                type="text"
                className="input w-full mt-1"
                placeholder="e.g. Class 12 (optional)"
                value={form.student_class ?? ""}
                onChange={(e) => setForm({ ...form, student_class: e.target.value || undefined })}
                maxLength={30}
              />
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
                  <th>Program</th>
                  <th>Class</th>
                  <th>Papers</th>
                  <th>Created</th>
                  <th className="w-12"></th>
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
                    <td className="text-sm">
                      {exam.program_name
                        ? <span className="font-medium text-primary-700">{exam.program_name}</span>
                        : <span className="text-surface-400">—</span>}
                    </td>
                    <td className="text-sm">
                      {exam.student_class ?? <span className="text-surface-400">—</span>}
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
                    <td>
                      <button
                        onClick={() => openEdit(exam)}
                        className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-400 hover:text-primary-600 transition-colors"
                        title="Edit exam"
                      >
                        ✏️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingExam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
            <div className="flex items-center justify-between px-6 py-4 border-b border-surface-100">
              <div>
                <h2 className="text-base font-bold text-surface-900">Edit Exam</h2>
                <p className="text-xs text-surface-400 font-mono mt-0.5">{editingExam.exam_code}</p>
              </div>
              <button
                onClick={() => setEditingExam(null)}
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-100 text-surface-500 text-xl leading-none"
              >×</button>
            </div>

            <div className="px-6 py-5 space-y-4">
              <div>
                <label className="label">Title</label>
                <input
                  type="text"
                  className="input w-full"
                  value={editForm.title ?? ""}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  maxLength={200}
                />
              </div>

              <div>
                <label className="label">Exam Date</label>
                <input
                  type="date"
                  className="input w-full"
                  value={editForm.exam_date ?? ""}
                  onChange={(e) => setEditForm({ ...editForm, exam_date: e.target.value })}
                />
              </div>

              <div>
                <label className="label">Exam Type</label>
                <div className="flex gap-6 mt-2">
                  {(["Mains", "Advanced"] as const).map((t) => (
                    <label key={t} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="edit_exam_type"
                        value={t}
                        checked={editForm.exam_type === t}
                        onChange={() => setEditForm({ ...editForm, exam_type: t })}
                        className="accent-primary-500"
                      />
                      <span className="text-sm font-medium text-surface-700">{t}</span>
                      <span className="text-xs text-surface-400">({EXAM_TYPE_PAPERS[t].join(", ")})</span>
                    </label>
                  ))}
                </div>
                {editForm.exam_type !== editingExam.exam_type && editForm.exam_type === "Advanced" && (
                  <p className="text-xs text-amber-600 mt-1">P2 paper will be added to this exam.</p>
                )}
              </div>

              <div>
                <label className="label">Program Name</label>
                <input
                  type="text"
                  className="input w-full"
                  value={editForm.program_name ?? ""}
                  onChange={(e) => setEditForm({ ...editForm, program_name: e.target.value })}
                  maxLength={50}
                  placeholder="e.g. IIT-JEE (optional)"
                />
              </div>

              <div>
                <label className="label">Student Class</label>
                <input
                  type="text"
                  className="input w-full"
                  value={editForm.student_class ?? ""}
                  onChange={(e) => setEditForm({ ...editForm, student_class: e.target.value })}
                  maxLength={30}
                  placeholder="e.g. Class 12 (optional)"
                />
              </div>

              {editErr && (
                <p className="text-sm text-danger-dark bg-danger-light rounded-lg px-3 py-2">⚠ {editErr}</p>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-surface-100 bg-surface-50 rounded-b-2xl">
              <button
                onClick={() => setEditingExam(null)}
                className="btn-secondary"
                disabled={updateMutation.isPending}
              >
                Cancel
              </button>
              <button
                onClick={() => updateMutation.mutate({ id: editingExam.id, data: editForm })}
                className="btn-primary"
                disabled={updateMutation.isPending}
              >
                {updateMutation.isPending ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
