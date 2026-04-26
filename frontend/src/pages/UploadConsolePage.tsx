/**
 * Upload Console
 * Drag-and-drop upload zones for Questions, OMR Responses, Answer Key (BKC/AKC).
 * Question uploads require selecting an Exam + Paper (P1 / P2 based on exam type).
 */
import { useState, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadsApi, evalApi, examsApi, UploadJobOut, ExamOut } from "@/lib/api";
import { fmt, fmtNum } from "@/lib/utils";
import ErrorBanner from "@/components/ui/ErrorBanner";
import { useExamSelector } from "@/hooks/useExamSelector";
import ExamPicker from "@/components/ui/ExamPicker";
import { cn } from "@/lib/utils";

type UploadZoneType = "questions" | "responses" | "answer_key_bkc" | "answer_key_akc";

const ZONES: { type: UploadZoneType; label: string; icon: string; accept: string; desc: string }[] = [
  { type: "questions",      label: "Question Paper", icon: "📋", accept: ".xlsx", desc: "Excel (.xlsx) — qno, subject, topic, question_type, marks, …" },
  { type: "responses",      label: "OMR Responses",  icon: "📄", accept: ".csv",  desc: "CSV — admission_no column + question numbers as columns" },
  { type: "answer_key_bkc", label: "BKC Answer Key", icon: "🔑", accept: ".csv", desc: "Base Key Correction CSV — qno, correct_answer, is_deleted" },
  { type: "answer_key_akc", label: "AKC Answer Key", icon: "🗝️", accept: ".csv", desc: "Amendment Key Correction CSV — qno, correct_answer, is_deleted" },
];

const JOB_STATUS_COLOR: Record<string, string> = {
  pending:    "badge-neutral",
  processing: "badge-info",
  completed:  "badge-success",
  failed:     "badge-critical",
};

export default function UploadConsolePage() {
  const { examId, setExamId } = useExamSelector();
  const qc = useQueryClient();

  const [paperCode,   setPaperCode]   = useState<string>("P1");
  const [evalKeyType, setEvalKeyType] = useState<"BKC" | "AKC">("BKC");
  const [progMap,     setProgMap]     = useState<Record<string, number>>({});
  const [errMap,      setErrMap]      = useState<Record<string, string>>({});
  const [expandedJob, setExpandedJob] = useState<number | null>(null);

  // Fetch the selected exam to know its type + available papers
  const { data: exams } = useQuery<ExamOut[]>({
    queryKey: ["exams"],
    queryFn:  () => examsApi.list().then((r) => r.data),
  });

  const selectedExam = exams?.find((e) => e.id === examId);
  const availablePapers: string[] = selectedExam?.papers ?? ["P1"];

  // Reset paperCode when the available papers change (e.g. switching from Advanced→Mains)
  const safePaperCode = availablePapers.includes(paperCode) ? paperCode : availablePapers[0] ?? "P1";

  const { data: jobs, isError, refetch } = useQuery<UploadJobOut[]>({
    queryKey: ["upload-jobs", examId],
    queryFn:  () => uploadsApi.listJobs(examId).then((r) => r.data),
    refetchInterval: 5000,
  });

  const triggerEval = useMutation({
    mutationFn: () => evalApi.trigger(examId, evalKeyType),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["upload-jobs"] });
      const d = res.data;
      alert(`${evalKeyType} evaluation complete — ${d.students_graded} students, ${d.questions_graded} answers graded in ${d.duration_ms}ms.`);
    },
  });

  const handleUpload = useCallback(
    async (type: UploadZoneType, file: File) => {
      setErrMap((m) => ({ ...m, [type]: "" }));
      setProgMap((m) => ({ ...m, [type]: 0 }));
      const prog = (pct: number) => setProgMap((m) => ({ ...m, [type]: pct }));

      try {
        if (type === "questions")
          await uploadsApi.uploadQuestions(examId, safePaperCode, file, prog);
        else if (type === "responses")
          await uploadsApi.uploadResponses(examId, safePaperCode, file, prog);
        else if (type === "answer_key_bkc")
          await uploadsApi.uploadAnswerKey(examId, safePaperCode, "BKC", file, prog);
        else if (type === "answer_key_akc")
          await uploadsApi.uploadAnswerKey(examId, safePaperCode, "AKC", file, prog);
        qc.invalidateQueries({ queryKey: ["upload-jobs"] });
      } catch {
        setErrMap((m) => ({ ...m, [type]: "Upload failed. Check file format and try again." }));
      } finally {
        setProgMap((m) => { const n = { ...m }; delete n[type]; return n; });
      }
    },
    [examId, safePaperCode, qc],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">📤 Upload Console</h1>
          <p className="text-surface-500 text-sm mt-0.5">Upload exam data and trigger grading</p>
        </div>
        <div className="flex flex-wrap gap-3 items-center">
          <ExamPicker examId={examId} onChange={(id) => { setExamId(id); setPaperCode("P1"); }} />

          {/* Paper picker — only shown for question uploads; visible always for clarity */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-surface-600 whitespace-nowrap">Paper</label>
            <select
              value={safePaperCode}
              onChange={(e) => setPaperCode(e.target.value)}
              className="input w-24 py-1.5"
              title="Paper code for question upload"
            >
              {availablePapers.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
          {selectedExam && (
            <span className="text-xs text-surface-400 bg-surface-100 rounded-lg px-2 py-1">
              {selectedExam.exam_type ?? "—"}
            </span>
          )}

          <div className="flex items-center rounded-lg border border-surface-200 overflow-hidden">
            {(["BKC", "AKC"] as const).map((kt) => (
              <button
                key={kt}
                onClick={() => setEvalKeyType(kt)}
                className={cn(
                  "px-3 py-1.5 text-xs font-semibold transition-colors",
                  evalKeyType === kt
                    ? "bg-primary-600 text-white"
                    : "bg-white text-surface-500 hover:bg-surface-50",
                )}
              >
                {kt}
              </button>
            ))}
          </div>

          <button
            onClick={() => triggerEval.mutate()}
            disabled={triggerEval.isPending}
            className="btn-primary"
          >
            {triggerEval.isPending ? "⏳ Evaluating…" : `⚡ Evaluate (${evalKeyType})`}
          </button>
        </div>
      </div>

      {/* Paper note */}
      <p className="text-xs text-surface-400">
        The selected <strong>Paper</strong> ({safePaperCode}) applies to <em>Question Paper</em>, <em>OMR Responses</em>, and <em>Answer Key</em> uploads.
        {availablePapers.length === 1 && " P2 is disabled for Mains exams."}
      </p>

      {/* Upload zones */}
      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {ZONES.map((zone) => (
          <DropZone
            key={zone.type}
            zone={zone}
            progress={progMap[zone.type]}
            error={errMap[zone.type]}
            onFile={(f) => handleUpload(zone.type, f)}
          />
        ))}
      </div>

      {/* Jobs table */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="section-title">Upload Jobs</h2>
          <button onClick={() => refetch()} className="btn-ghost btn-sm text-surface-400">↺ Refresh</button>
        </div>

        {isError && <ErrorBanner onRetry={refetch} />}

        {!jobs || jobs.length === 0 ? (
          <div className="card py-12 text-center text-surface-400 text-sm">
            No upload jobs yet for exam {examId}.
          </div>
        ) : (
          <div className="card overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th className="text-right">Total</th>
                    <th className="text-right">Processed</th>
                    <th className="text-right">Failed</th>
                    <th>Created</th>
                    <th>Completed</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => (
                    <>
                      <tr key={job.id}>
                        <td className="font-mono text-xs">#{job.id}</td>
                        <td className="text-sm capitalize">{job.job_type.replace(/_/g, " ")}</td>
                        <td><span className={JOB_STATUS_COLOR[job.status] ?? "badge-neutral"}>{job.status}</span></td>
                        <td className="text-right">{fmtNum(job.total_rows, 0)}</td>
                        <td className="text-right text-success-dark">{fmtNum(job.processed_rows, 0)}</td>
                        <td className="text-right text-danger-dark">{job.failed_rows > 0 ? fmtNum(job.failed_rows, 0) : "—"}</td>
                        <td className="text-xs text-surface-500">{fmt(job.created_at, "dd MMM HH:mm")}</td>
                        <td className="text-xs text-surface-500">{job.completed_at ? fmt(job.completed_at, "dd MMM HH:mm") : "—"}</td>
                        <td>
                          {job.failed_rows > 0 && job.error_json && (
                            <button
                              onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                              className="btn-ghost btn-sm text-danger-dark"
                            >
                              {expandedJob === job.id ? "Hide" : "Errors ▾"}
                            </button>
                          )}
                          {job.status === "processing" && (
                            <div className="w-20 h-1.5 bg-surface-100 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary-500 rounded-full animate-pulse"
                                style={{ width: `${(job.processed_rows / (job.total_rows || 1)) * 100}%` }}
                              />
                            </div>
                          )}
                        </td>
                      </tr>
                      {expandedJob === job.id && job.error_json && (
                        <tr key={`${job.id}-err`}>
                          <td colSpan={9} className="bg-danger-light/30 px-4 pb-3">
                            <p className="text-xs font-semibold text-danger-dark mb-2">
                              Validation errors ({job.error_json.length})
                            </p>
                            <div className="max-h-48 overflow-y-auto space-y-1">
                              {job.error_json.map((e, i) => (
                                <div key={i} className="flex gap-3 text-xs font-mono bg-white/70 rounded-lg px-3 py-1.5">
                                  <span className="text-surface-400">Row {e.row}</span>
                                  <span className="text-danger-dark font-semibold">{e.field}</span>
                                  <span className="text-surface-600">{e.message}</span>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Drag-and-drop zone ────────────────────────────────────────────────────────

interface DropZoneProps {
  zone: { type: string; label: string; icon: string; accept: string; desc: string };
  progress?: number;
  error?: string;
  onFile: (f: File) => void;
}

function DropZone({ zone, progress, error, onFile }: DropZoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploading = progress !== undefined;

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) onFile(f);
  };

  return (
    <div
      onDragEnter={(e) => { e.preventDefault(); setDragging(true); }}
      onDragOver={(e)  => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !uploading && inputRef.current?.click()}
      className={cn(
        "card cursor-pointer flex flex-col items-center justify-center gap-3 py-8 text-center border-2 border-dashed transition-colors duration-150",
        dragging ? "border-primary-400 bg-primary-50" : "border-surface-200 hover:border-primary-300 hover:bg-surface-50",
        uploading && "pointer-events-none",
      )}
    >
      <input
        type="file"
        ref={inputRef}
        accept={zone.accept}
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }}
      />

      <div className="text-3xl">{zone.icon}</div>
      <div>
        <p className="font-semibold text-surface-700">{zone.label}</p>
        <p className="text-xs text-surface-400 mt-0.5">{zone.desc}</p>
        <p className="text-xs text-surface-300 mt-0.5">{zone.accept.toUpperCase()}</p>
      </div>

      {uploading && (
        <div className="w-full px-4 mt-2">
          <div className="h-1.5 bg-surface-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-500 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-primary-600 text-center mt-1">{progress}%</p>
        </div>
      )}

      {error && (
        <p className="text-xs text-danger-dark bg-danger-light rounded-lg px-3 py-1.5 w-full">
          ⚠ {error}
        </p>
      )}
    </div>
  );
}
