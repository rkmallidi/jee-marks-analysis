import { useState, useMemo, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  questionsApi, uploadsApi, examsApi, evalApi,
  QuestionOut, QuestionUpdate, QuestionCreate, ExamOut, UploadJobOut,
} from "@/lib/api";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import EmptyState from "@/components/ui/EmptyState";

// ── Question type reference data ───────────────────────────────────────────────

const Q_TYPE_REFERENCE = [
  {
    value:   "SCQ",
    label:   "Single Correct (SCQ)",
    color:   "bg-indigo-100 text-indigo-700",
    answer:  "One letter: A, B, C or D",
    grading: "+marks if correct · −marks if wrong · 0 if blank",
    note:    "",
  },
  {
    value:   "MCQ",
    label:   "Multi-Correct (MCQ)",
    color:   "bg-purple-100 text-purple-700",
    answer:  "All correct letters together, e.g. ABD",
    grading: "All correct + no wrong → full marks · Subset correct + no wrong → +1 per chosen (capped at pos−1) · Any wrong → −marks · Blank → 0",
    note:    "JEE Advanced style. MCQ_MULTI is a legacy alias for the same rule.",
  },
  {
    value:   "PARTIAL_MCQ",
    label:   "Partial MCQ (flat credit)",
    color:   "bg-violet-100 text-violet-700",
    answer:  "Selected option letters, e.g. ABD",
    grading: "All correct + no wrong → full marks · Subset correct + no wrong → flat partial_marks · Any wrong → −marks · Blank → 0",
    note:    "Partial credit is a fixed value, not per-option like MCQ.",
  },
  {
    value:   "NUMERICAL_INT",
    label:   "Numerical Integer",
    color:   "bg-teal-100 text-teal-700",
    answer:  "Integer: 42   or range: 3:7",
    grading: "Exact (or within integer range) → full marks · Wrong → 0 · Blank → 0 · No negative marking",
    note:    "",
  },
  {
    value:   "NUMERICAL_DECIMAL",
    label:   "Numerical Decimal",
    color:   "bg-cyan-100 text-cyan-700",
    answer:  "Decimal: 3.14   or range: 9.95:10.05",
    grading: "Answer rounded to 2 dp. Exact (or within range) → full marks · Wrong → 0 · Blank → 0 · No negative",
    note:    "",
  },
  {
    value:   "NUMERICAL_RANGE",
    label:   "Numerical Range",
    color:   "bg-sky-100 text-sky-700",
    answer:  "Range only: min:max, e.g. 8.5:9.5",
    grading: "Student decimal must fall within [min, max] → full marks · Otherwise 0 · No negative",
    note:    "Correct option must always be in lo:hi format.",
  },
  {
    value:   "DELETED",
    label:   "Deleted / Bonus",
    color:   "bg-red-100 text-red-600",
    answer:  "N/A — question dropped",
    grading: "Every student receives full positive_marks as bonus regardless of response",
    note:    "Set via is_deleted_bkc or is_deleted_akc flag. Excluded from accuracy metrics.",
  },
  {
    value:   "NO_NEGATIVE",
    label:   "No-Negative SCQ",
    color:   "bg-indigo-50 text-indigo-500",
    answer:  "One letter: A, B, C or D",
    grading: "+marks if correct · 0 if wrong (no penalty) · 0 if blank",
    note:    "Equivalent to SCQ with negative_marks = 0.",
  },
] as const;

function QuestionTypeHelpModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-100 sticky top-0 bg-white rounded-t-2xl">
          <div>
            <h2 className="text-base font-bold text-surface-900">Question Types Reference</h2>
            <p className="text-xs text-surface-400 mt-0.5">How each type is graded by the evaluation engine</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-100 text-surface-500 text-xl leading-none">×</button>
        </div>

        <div className="px-6 py-4 space-y-3">
          {Q_TYPE_REFERENCE.map((t) => (
            <div key={t.value} className="rounded-xl border border-surface-100 p-4 space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full font-mono ${t.color}`}>{t.value}</span>
                <span className="text-sm font-semibold text-surface-800">{t.label}</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-xs">
                <div>
                  <span className="text-surface-400 font-semibold uppercase tracking-wide text-[10px]">Answer format</span>
                  <p className="font-mono text-surface-700 mt-0.5">{t.answer}</p>
                </div>
                <div>
                  <span className="text-surface-400 font-semibold uppercase tracking-wide text-[10px]">Grading</span>
                  <p className="text-surface-700 mt-0.5 leading-relaxed">{t.grading}</p>
                </div>
              </div>
              {t.note && (
                <p className="text-[11px] text-surface-400 italic border-t border-surface-50 pt-2">{t.note}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DifficultyHelpModal({ onClose }: { onClose: () => void }) {
  const levels = [
    { d: "Easy",      weight: 1, range: "avg < 1.5",        badge: "bg-emerald-100 text-emerald-700", bar: "bg-emerald-400", desc: "Straightforward recall or direct application of a single concept." },
    { d: "Medium",    weight: 2, range: "1.5 ≤ avg < 2.5",  badge: "bg-sky-100 text-sky-700",         bar: "bg-sky-400",     desc: "Requires combining two or more steps or moderate conceptual reasoning." },
    { d: "Hard",      weight: 3, range: "2.5 ≤ avg < 3.5",  badge: "bg-orange-100 text-orange-700",   bar: "bg-orange-500",  desc: "Multi-step problem with non-obvious approach or tricky conditions." },
    { d: "Very Hard", weight: 4, range: "avg ≥ 3.5",         badge: "bg-rose-100 text-rose-700",       bar: "bg-rose-600",    desc: "Involves deep insight, lengthy calculation, or highly abstract reasoning." },
  ] as const;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-xl max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-100 sticky top-0 bg-white rounded-t-2xl">
          <div>
            <h2 className="text-base font-bold text-surface-900">Difficulty Reference</h2>
            <p className="text-xs text-surface-400 mt-0.5">Levels, weights, and how the rating is computed</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-100 text-surface-500 text-xl leading-none">×</button>
        </div>

        <div className="px-6 py-4 space-y-4">
          {/* Level cards */}
          <div className="space-y-2">
            {levels.map(({ d, weight, badge, bar, desc }) => (
              <div key={d} className="flex items-start gap-3 rounded-xl border border-surface-100 p-3">
                <div className={`w-2.5 h-2.5 rounded-full mt-1 shrink-0 ${bar}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${badge}`}>{d}</span>
                    <span className="text-[11px] text-surface-400 font-mono">weight = {weight}</span>
                  </div>
                  <p className="text-xs text-surface-600 mt-1 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Calculation section */}
          <div className="rounded-xl bg-surface-50 border border-surface-100 p-4 space-y-3">
            <p className="text-xs font-bold uppercase tracking-wide text-surface-500">How the rating is calculated</p>

            <div className="space-y-1.5 text-xs text-surface-700">
              <p><span className="font-semibold">1. Assign weights</span> — Easy=1, Medium=2, Hard=3, Very Hard=4</p>
              <p><span className="font-semibold">2. Weighted average</span> over all <em>tagged</em> (non-deleted) questions:</p>
              <div className="bg-white border border-surface-200 rounded-lg px-3 py-2 font-mono text-[11px] text-surface-800">
                avg = Σ(count<sub>level</sub> × weight<sub>level</sub>) ÷ total_tagged
              </div>
              <p><span className="font-semibold">3. Map avg to label:</span></p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 pl-2">
                {levels.map(({ d, range, badge }) => (
                  <div key={d} className="flex items-center gap-1.5">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${badge}`}>{d}</span>
                    <span className="text-surface-500 text-[11px] font-mono">{range}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="border-t border-surface-100 pt-3 text-xs text-surface-500 space-y-1">
              <p>• <span className="font-semibold">Untagged questions are excluded</span> from all difficulty calculations.</p>
              <p>• <span className="font-semibold">Subject-wise rating</span> uses the same formula but restricted to questions of that subject only.</p>
              <p>• The stacked bar shows the proportion of each level among tagged questions for a visual distribution.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── constants ──────────────────────────────────────────────────────────────────

const SUBJECTS = ["Physics", "Chemistry", "Mathematics"];

const DIFFICULTIES = ["Easy", "Medium", "Hard", "Very Hard"] as const;
type Difficulty = typeof DIFFICULTIES[number];

const DIFF_STYLE: Record<Difficulty, { badge: string; bar: string }> = {
  "Easy":      { badge: "bg-emerald-100 text-emerald-700", bar: "bg-emerald-400" },
  "Medium":    { badge: "bg-sky-100 text-sky-700",         bar: "bg-sky-400"     },
  "Hard":      { badge: "bg-orange-100 text-orange-700",   bar: "bg-orange-500"  },
  "Very Hard": { badge: "bg-rose-100 text-rose-700",       bar: "bg-rose-600"    },
};

const DIFF_WEIGHT: Record<Difficulty, number> = {
  "Easy": 1, "Medium": 2, "Hard": 3, "Very Hard": 4,
};

function difficultyRating(byLevel: Record<string, number>): Difficulty | null {
  const total = DIFFICULTIES.reduce((s, d) => s + (byLevel[d] ?? 0), 0);
  if (total === 0) return null;
  const avg = DIFFICULTIES.reduce((s, d) => s + (byLevel[d] ?? 0) * DIFF_WEIGHT[d], 0) / total;
  if (avg < 1.5) return "Easy";
  if (avg < 2.5) return "Medium";
  if (avg < 3.5) return "Hard";
  return "Very Hard";
}

// Exact types from question_validator.py VALID_QUESTION_TYPES
const Q_TYPES: { value: string; hint: string }[] = [
  { value: "SCQ",              hint: "Single correct — enter one option letter: A, B, C, or D" },
  { value: "MCQ",              hint: "Single correct (legacy) — enter one option letter: A, B, C, or D" },
  { value: "MCQ_MULTI",        hint: "Multiple correct options — enter all correct letters together, e.g. ABD or AC" },
  { value: "PARTIAL_MCQ",      hint: "Multiple correct with partial marks — enter selected option letters together, e.g. ABD" },
  { value: "NUMERICAL_INT",    hint: "Integer answer — enter exact integer e.g. 42, OR a range e.g. 3:7" },
  { value: "NUMERICAL_DECIMAL",hint: "Decimal answer — enter exact decimal e.g. 3.14, OR a range e.g. 9.95:10.05" },
  { value: "NUMERICAL_RANGE",  hint: "Range answer — enter min:max format only, e.g. 8.5:9.5" },
];

function answerHint(qType: string): string {
  return Q_TYPES.find((t) => t.value === qType)?.hint ?? "Enter the correct answer";
}

// ── small helpers ──────────────────────────────────────────────────────────────

function badge(text: string, color: string) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {text}
    </span>
  );
}

function subjectColor(s: string) {
  if (s === "Physics")     return "bg-blue-100 text-blue-700";
  if (s === "Chemistry")   return "bg-green-100 text-green-700";
  if (s === "Mathematics") return "bg-orange-100 text-orange-700";
  return "bg-surface-100 text-surface-600";
}

function typeColor(t: string) {
  if (t === "SCQ")               return "bg-indigo-100 text-indigo-700";
  if (t === "MCQ")               return "bg-indigo-100 text-indigo-600";
  if (t === "MCQ_MULTI")         return "bg-purple-100 text-purple-700";
  if (t === "PARTIAL_MCQ")       return "bg-violet-100 text-violet-700";
  if (t === "NUMERICAL_INT")     return "bg-teal-100 text-teal-700";
  if (t === "NUMERICAL_DECIMAL") return "bg-cyan-100 text-cyan-700";
  if (t === "NUMERICAL_RANGE")   return "bg-sky-100 text-sky-700";
  return "bg-surface-100 text-surface-600";
}

function hasKeyChange(q: {
  correct_option_bkc: string | null;
  is_deleted_bkc: boolean;
  correct_option_akc: string | null;
  is_deleted_akc: boolean | null;
}) {
  const answerChanged  = q.correct_option_akc !== null && q.correct_option_akc !== q.correct_option_bkc;
  const deletedChanged = q.is_deleted_akc !== null && q.is_deleted_akc !== q.is_deleted_bkc;
  return answerChanged || deletedChanged;
}

// ── Upload panel ──────────────────────────────────────────────────────────────

type SlotPhase =
  | { type: "idle" }
  | { type: "uploading"; progress: number }
  | { type: "done"; job: UploadJobOut }
  | { type: "error"; message: string };

interface ColumnSpec { required: string[]; optional: string[] }

interface UploadSlotProps {
  label:    string;
  icon:     string;
  columns:  ColumnSpec;
  accept?:  string;
  onUpload: (file: File, onProgress: (p: number) => void) => Promise<UploadJobOut>;
  onDone?:  () => void;
  inline?:  boolean;
}

function UploadSlot({ label, icon, columns, accept = ".xlsx,.xls,.csv", onUpload, onDone, inline }: UploadSlotProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<SlotPhase>({ type: "idle" });

  const handleFile = useCallback(async (file: File) => {
    setState({ type: "uploading", progress: 0 });
    try {
      const job = await onUpload(file, (p) => setState({ type: "uploading", progress: p }));
      setState({ type: "done", job });
      onDone?.();
      setTimeout(() => setState({ type: "idle" }), 6000);
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "Upload failed";
      setState({ type: "error", message: detail });
      setTimeout(() => setState({ type: "idle" }), 8000);
    }
    if (inputRef.current) inputRef.current.value = "";
  }, [onUpload, onDone]);

  const errors = state.type === "done" ? (state.job.error_json ?? []) : [];
  const failed  = state.type === "done" && (state.job.status === "failed" || errors.length > 0);
  const success = state.type === "done" && !failed;

  // ── Inline variant (used in the evaluate row) ────────────────────────────
  if (inline) {
    return (
      <div className="flex items-center gap-1.5 shrink-0">
        <input
          type="file"
          ref={inputRef}
          accept={accept}
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        <span className="text-base shrink-0">{icon}</span>

        {/* info tooltip */}
        <div className="relative group shrink-0">
          <span className="text-[10px] w-3.5 h-3.5 rounded-full bg-surface-200 text-surface-500 flex items-center justify-center cursor-default leading-none select-none">i</span>
          <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 w-52 bg-surface-900 text-white text-[11px] rounded-lg px-3 py-2 shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
            <p className="font-semibold text-surface-200 mb-1">Required columns</p>
            <p className="font-mono text-primary-300">{columns.required.join(", ")}</p>
            {columns.optional.length > 0 && (
              <>
                <p className="font-semibold text-surface-200 mt-1.5 mb-1">Optional</p>
                <p className="font-mono text-surface-400">{columns.optional.join(", ")}</p>
              </>
            )}
            <div className="absolute left-1/2 -translate-x-1/2 top-full w-2 h-2 bg-surface-900 rotate-45 -mt-1" />
          </div>
        </div>

        <span className="text-xs font-semibold text-surface-600 shrink-0">{label}</span>

        {state.type === "idle" && (
          <button
            onClick={() => inputRef.current?.click()}
            className="shrink-0 px-2.5 py-1 rounded-lg text-xs font-semibold border border-surface-200 text-surface-600 hover:bg-surface-50 transition-colors"
          >
            ↑ Upload
          </button>
        )}
        {state.type === "uploading" && (
          <div className="w-16 h-1.5 rounded-full bg-surface-100 overflow-hidden">
            <div className="h-full bg-primary-500 rounded-full transition-all" style={{ width: `${state.progress || 5}%` }} />
          </div>
        )}
        {success && <span className="text-xs text-green-600 font-semibold">✓ {state.job.total_rows}r</span>}
        {failed  && <span className="text-xs text-red-500 font-semibold" title={errors[0]?.message ?? ""}>✗ Failed</span>}
        {state.type === "error" && <span className="text-xs text-red-500">✗ {state.message}</span>}
      </div>
    );
  }

  // ── Card variant (default) ───────────────────────────────────────────────
  return (
    <div className={`flex-1 min-w-0 rounded-xl border px-4 py-3 flex flex-col gap-2 transition-colors ${
      failed        ? "border-red-200 bg-red-50"
      : success     ? "border-green-200 bg-green-50"
      : state.type === "uploading" ? "border-primary-200 bg-primary-50"
      : "border-surface-200 bg-white hover:border-primary-300 hover:bg-surface-50"
    }`}>
      <input
        type="file"
        ref={inputRef}
        accept={accept}
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
      />

      {/* header row */}
      <div className="flex items-center gap-2">
        <span className="text-lg shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1">
            <p className="text-sm font-semibold text-surface-800 truncate">{label}</p>
            {/* info tooltip */}
            <div className="relative group shrink-0">
              <span className="text-[10px] w-3.5 h-3.5 rounded-full bg-surface-200 text-surface-500 flex items-center justify-center cursor-default leading-none select-none">i</span>
              <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 w-52 bg-surface-900 text-white text-[11px] rounded-lg px-3 py-2 shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                <p className="font-semibold text-surface-200 mb-1">Required columns</p>
                <p className="font-mono text-primary-300">{columns.required.join(", ")}</p>
                {columns.optional.length > 0 && (
                  <>
                    <p className="font-semibold text-surface-200 mt-1.5 mb-1">Optional</p>
                    <p className="font-mono text-surface-400">{columns.optional.join(", ")}</p>
                  </>
                )}
                <div className="absolute left-1/2 -translate-x-1/2 top-full w-2 h-2 bg-surface-900 rotate-45 -mt-1" />
              </div>
            </div>
          </div>
          <p className="text-xs text-surface-400">{accept.split(",")[0].toUpperCase()} · overwrites existing</p>
        </div>
        {state.type === "idle" && (
          <button
            onClick={() => inputRef.current?.click()}
            className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary-600 text-white hover:bg-primary-700 transition-colors"
          >
            ↑ Upload
          </button>
        )}
        {success && <span className="shrink-0 text-green-600 text-sm font-semibold">✓ Done</span>}
        {failed  && <span className="shrink-0 text-red-600 text-sm font-semibold">✗ Failed</span>}
      </div>

      {/* progress bar */}
      {state.type === "uploading" && (
        <div className="h-1.5 rounded-full bg-primary-100 overflow-hidden">
          <div
            className="h-full bg-primary-500 rounded-full transition-all duration-200"
            style={{ width: `${state.progress || 5}%` }}
          />
        </div>
      )}

      {/* success info */}
      {success && (
        <p className="text-xs text-green-700">
          {state.job.total_rows} rows processed
        </p>
      )}

      {/* error detail */}
      {state.type === "error" && (
        <p className="text-xs text-red-600">{state.message}</p>
      )}

      {/* validation errors from job */}
      {failed && errors.length > 0 && (
        <div className="max-h-28 overflow-y-auto space-y-1">
          {errors.slice(0, 10).map((e, i) => (
            <div key={i} className="text-xs font-mono bg-white/70 rounded px-2 py-1 text-red-700">
              Row {e.row} · <span className="font-semibold">{e.field}</span> — {e.message}
            </div>
          ))}
          {errors.length > 10 && (
            <p className="text-xs text-red-500">…and {errors.length - 10} more errors</p>
          )}
        </div>
      )}
    </div>
  );
}

const COL_QUESTIONS: ColumnSpec = {
  required: ["qno", "subject", "question_type", "marks", "negative_marks"],
  optional: ["topic", "sub_topic", "difficulty", "partial_marks", "correct_answer", "is_deleted"],
};
const COL_KEY: ColumnSpec = {
  required: ["qno"],
  optional: ["correct_answer", "is_deleted"],
};
const COL_RESPONSES: ColumnSpec = {
  required: ["admission_no", "1", "2", "… (one column per Q#)"],
  optional: [],
};
const COL_OMR_SCANNER: ColumnSpec = {
  required: ["x, admission_no, v1, v2, … (positional)"],
  optional: ["-1000000 = blank"],
};

// ── Combined action panel (upload + evaluate) ─────────────────────────────────

interface ActionPanelProps {
  examId:          number;
  paperCode:       string;
  hasQuestions:    boolean;
  hasKey:          boolean;   // BKC or AKC answer exists on ≥1 question
  hasResponses:    boolean;   // at least one completed responses upload job
  onUploadDone:    () => void;
  onAddQuestion:   () => void;
  onCleanPaper:    () => void;
}

function ActionPanel({ examId, paperCode, hasQuestions, hasKey, hasResponses, onUploadDone, onAddQuestion, onCleanPaper }: ActionPanelProps) {
  const [keyType,            setKeyType]            = useState<"BKC" | "AKC">("BKC");
  const [evalResult,         setEvalResult]         = useState<string>("");
  const [localKeyUploaded,   setLocalKeyUploaded]   = useState(false);
  const [localRespUploaded,  setLocalRespUploaded]  = useState(false);

  const canEvaluate = hasQuestions && (hasKey || localKeyUploaded) && (hasResponses || localRespUploaded);

  const evalMutation = useMutation({
    mutationFn: () => evalApi.trigger(examId, keyType),
    onSuccess:  (res) => {
      const d = res.data;
      setEvalResult(`✓ ${keyType} done — ${d.students_graded} students, ${d.duration_ms}ms`);
    },
    onError: () => setEvalResult("✗ Evaluation failed"),
  });

  return (
    <div className="card py-3 px-4 space-y-2.5">
      {/* Row 1: upload slots */}
      <div className="flex flex-col sm:flex-row gap-2">
        <UploadSlot
          label="Question Paper"
          icon="📋"
          columns={COL_QUESTIONS}
          onUpload={(f, p) => uploadsApi.uploadQuestions(examId, paperCode, f, p).then((r) => r.data)}
          onDone={onUploadDone}
        />
        {hasQuestions && (
          <UploadSlot
            label="BKC Answer Key"
            icon="🔑"
            columns={COL_KEY}
            onUpload={(f, p) => uploadsApi.uploadAnswerKey(examId, paperCode, "BKC", f, p).then((r) => r.data)}
            onDone={() => { setLocalKeyUploaded(true); onUploadDone(); }}
          />
        )}
        {hasQuestions && (
          <UploadSlot
            label="AKC Answer Key"
            icon="🗝️"
            columns={COL_KEY}
            onUpload={(f, p) => uploadsApi.uploadAnswerKey(examId, paperCode, "AKC", f, p).then((r) => r.data)}
            onDone={() => { setLocalKeyUploaded(true); onUploadDone(); }}
          />
        )}
        {hasQuestions && (
          <UploadSlot
            label="OMR Responses"
            icon="📊"
            columns={COL_RESPONSES}
            onUpload={(f, p) => uploadsApi.uploadResponses(examId, paperCode, f, p).then((r) => r.data)}
            onDone={() => { setLocalRespUploaded(true); onUploadDone(); }}
          />
        )}
        {hasQuestions && (
          <UploadSlot
            label="OMR Scanner (.IIT)"
            icon="🖨️"
            columns={COL_OMR_SCANNER}
            accept=".iit,.txt,.csv"
            onUpload={(f, p) => uploadsApi.uploadOmrResponses(examId, paperCode, f, p).then((r) => r.data)}
            onDone={() => { setLocalRespUploaded(true); onUploadDone(); }}
          />
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-surface-100" />

      {/* Row 2: Evaluate + Quick actions */}
      <div className="flex flex-wrap items-center gap-2">

        {/* Evaluate section */}
        <span className="text-xs font-semibold text-surface-500 shrink-0">⚡ Evaluate</span>
        <div className="flex items-center rounded-lg border border-surface-200 overflow-hidden shrink-0">
          {(["BKC", "AKC"] as const).map((kt) => (
            <button
              key={kt}
              onClick={() => setKeyType(kt)}
              className={`px-3 py-1 text-xs font-semibold transition-colors ${
                keyType === kt
                  ? "bg-primary-600 text-white"
                  : "bg-white text-surface-500 hover:bg-surface-50"
              }`}
            >
              {kt}
            </button>
          ))}
        </div>
        <button
          onClick={() => { setEvalResult(""); evalMutation.mutate(); }}
          disabled={!canEvaluate || evalMutation.isPending}
          className="shrink-0 px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {evalMutation.isPending ? "Running…" : `Run ${keyType}`}
        </button>
        {evalResult && (
          <span className={`text-xs ${evalMutation.isError ? "text-red-500" : "text-emerald-600"}`}>
            {evalResult}
          </span>
        )}
        {!hasQuestions && (
          <span className="text-xs text-surface-400">Upload questions first</span>
        )}
        {hasQuestions && !canEvaluate && (
          <span className="text-xs text-surface-400">
            {!(hasKey || localKeyUploaded) ? "Upload an answer key" : "Upload OMR responses"} to enable
          </span>
        )}

        {/* Quick actions — pushed to the right */}
        <div className="ml-auto flex items-center gap-2 shrink-0">
          <button
            onClick={onAddQuestion}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-primary-600 text-white hover:bg-primary-700 transition-colors"
          >
            ＋ Add Question
          </button>
          {hasQuestions && (
            <button
              onClick={onCleanPaper}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold border border-red-200 text-red-600 hover:bg-red-50 transition-colors"
            >
              🧹 Clean Paper
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── shared form fields ─────────────────────────────────────────────────────────

interface QuestionFormFields {
  subject:            string;
  topic:              string;
  sub_topic:          string;
  difficulty:         string;
  question_type:      string;
  positive_marks:     number;
  negative_marks:     number;
  partial_marks:      number;
  correct_option_bkc: string;
  is_deleted_bkc:     boolean;
  correct_option_akc: string;
}

function QuestionFormBody({
  form,
  set,
}: {
  form: QuestionFormFields;
  set: (k: keyof QuestionFormFields, v: unknown) => void;
}) {
  const hint = answerHint(form.question_type);
  return (
    <div className="space-y-5">
      {/* row 1: subject / type */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Subject</label>
          <select className="input" value={form.subject} onChange={(e) => set("subject", e.target.value)}>
            {SUBJECTS.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Question Type</label>
          <select className="input" value={form.question_type} onChange={(e) => set("question_type", e.target.value)}>
            {Q_TYPES.map((t) => <option key={t.value} value={t.value}>{t.value}</option>)}
          </select>
        </div>
      </div>

      {/* row 2: difficulty */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Difficulty</label>
          <select className="input" value={form.difficulty} onChange={(e) => set("difficulty", e.target.value)}>
            <option value="">— Untagged —</option>
            {DIFFICULTIES.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div className="flex items-end pb-1">
          {form.difficulty && (
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${DIFF_STYLE[form.difficulty as Difficulty]?.badge ?? ""}`}>
              {form.difficulty}
            </span>
          )}
        </div>
      </div>

      {/* row 3: topic / sub-topic */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">Topic</label>
          <input className="input" value={form.topic} onChange={(e) => set("topic", e.target.value)} placeholder="e.g. Kinematics" />
        </div>
        <div>
          <label className="label">Sub-topic</label>
          <input className="input" value={form.sub_topic} onChange={(e) => set("sub_topic", e.target.value)} placeholder="e.g. Projectile Motion" />
        </div>
      </div>

      {/* row 3: marks */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="label">Positive Marks</label>
          <input type="number" step="0.5" className="input" value={form.positive_marks}
            onChange={(e) => set("positive_marks", parseFloat(e.target.value))} />
        </div>
        <div>
          <label className="label">Negative Marks</label>
          <input type="number" step="0.25" className="input" value={form.negative_marks}
            onChange={(e) => set("negative_marks", parseFloat(e.target.value))} />
        </div>
        <div>
          <label className="label">Partial Marks</label>
          <input type="number" step="0.5" className="input" value={form.partial_marks}
            onChange={(e) => set("partial_marks", parseFloat(e.target.value))} />
        </div>
      </div>

      <hr className="border-surface-100" />

      {/* answer format guide */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 text-sm text-blue-700">
        <span className="font-semibold">Answer format ({form.question_type}): </span>
        {hint}
      </div>

      {/* BKC section */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-surface-500 mb-3">BKC (Base Key Correction)</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Correct Answer</label>
            <input className="input font-mono" value={form.correct_option_bkc}
              placeholder={
                form.question_type.startsWith("NUMERICAL") ? "e.g. 42 or 3:7"
                : form.question_type === "MCQ_MULTI" || form.question_type === "PARTIAL_MCQ" ? "e.g. ABD"
                : "e.g. A"
              }
              onChange={(e) => set("correct_option_bkc", e.target.value)} />
          </div>
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" className="w-4 h-4 accent-red-500" checked={form.is_deleted_bkc}
                onChange={(e) => set("is_deleted_bkc", e.target.checked)} />
              <span className="text-sm text-surface-700">Mark as deleted (bonus marks)</span>
            </label>
          </div>
        </div>
      </div>

      {/* AKC section */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-surface-500 mb-3">AKC (Amendment Key — optional)</p>
        <div>
          <label className="label">Corrected Answer</label>
          <input className="input font-mono w-full" value={form.correct_option_akc}
            placeholder="Leave blank to inherit BKC answer"
            onChange={(e) => set("correct_option_akc", e.target.value)} />
          <p className="text-xs text-surface-400 mt-1">
            Fill only if the answer changed after official key amendment. Leave blank to keep BKC answer.
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Edit modal ─────────────────────────────────────────────────────────────────

interface EditModalProps {
  question: QuestionOut;
  onClose:  () => void;
  onSave:   (id: number, body: QuestionUpdate) => void;
  saving:   boolean;
}

function EditModal({ question: q, onClose, onSave, saving }: EditModalProps) {
  const [form, setForm] = useState<QuestionFormFields>({
    subject:            q.subject,
    topic:              q.topic ?? "",
    sub_topic:          q.sub_topic ?? "",
    difficulty:         q.difficulty ?? "",
    question_type:      q.question_type,
    positive_marks:     q.positive_marks,
    negative_marks:     q.negative_marks,
    partial_marks:      q.partial_marks,
    correct_option_bkc: q.correct_option_bkc ?? "",
    is_deleted_bkc:     q.is_deleted_bkc,
    correct_option_akc: q.correct_option_akc ?? "",
  });

  const set = (k: keyof QuestionFormFields, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v }));

  const handleSave = () => {
    onSave(q.id, {
      ...form,
      topic:              form.topic      || null,
      sub_topic:          form.sub_topic  || null,
      difficulty:         form.difficulty || null,
      correct_option_bkc: form.correct_option_bkc || null,
      correct_option_akc: form.correct_option_akc || null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-100">
          <div>
            <h2 className="text-lg font-bold text-surface-900">
              Edit Question {q.paper_code}-Q{q.question_no}
            </h2>
            <p className="text-xs text-surface-500 mt-0.5">ID #{q.id}</p>
          </div>
          <button onClick={onClose} className="text-surface-400 hover:text-surface-700 text-xl font-bold">×</button>
        </div>

        <div className="px-6 py-5">
          <QuestionFormBody form={form} set={set} />
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-surface-100 bg-surface-50 rounded-b-2xl">
          <button onClick={onClose} className="btn-secondary" disabled={saving}>Cancel</button>
          <button onClick={handleSave} className="btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Add modal ──────────────────────────────────────────────────────────────────

interface AddModalProps {
  examId:         number;
  paperCode:      string;
  nextQuestionNo: number;
  onClose:        () => void;
  onSave:         (body: QuestionCreate) => void;
  saving:         boolean;
  error:          string;
}

function AddModal({ examId, paperCode, nextQuestionNo, onClose, onSave, saving, error }: AddModalProps) {
  const [questionNo, setQuestionNo] = useState<number>(nextQuestionNo);
  const [form, setForm] = useState<QuestionFormFields>({
    subject:            "Physics",
    topic:              "",
    sub_topic:          "",
    difficulty:         "",
    question_type:      "SCQ",
    positive_marks:     4,
    negative_marks:     1,
    partial_marks:      0,
    correct_option_bkc: "",
    is_deleted_bkc:     false,
    correct_option_akc: "",
  });

  const set = (k: keyof QuestionFormFields, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v }));

  const handleSave = () => {
    onSave({
      exam_id:            examId,
      paper_code:         paperCode,
      question_no:        questionNo,
      subject:            form.subject,
      topic:              form.topic      || null,
      sub_topic:          form.sub_topic  || null,
      difficulty:         form.difficulty || null,
      question_type:      form.question_type,
      positive_marks:     form.positive_marks,
      negative_marks:     form.negative_marks,
      partial_marks:      form.partial_marks,
      correct_option_bkc: form.correct_option_bkc || null,
      is_deleted_bkc:     form.is_deleted_bkc,
      correct_option_akc: form.correct_option_akc || null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-100">
          <div>
            <h2 className="text-lg font-bold text-surface-900">Add New Question</h2>
            <p className="text-xs text-surface-500 mt-0.5">Paper {paperCode}</p>
          </div>
          <button onClick={onClose} className="text-surface-400 hover:text-surface-700 text-xl font-bold">×</button>
        </div>

        <div className="px-6 py-5 space-y-5">
          <div className="w-40">
            <label className="label">Question Number</label>
            <input
              type="number" min={1} className="input font-mono font-bold"
              value={questionNo}
              onChange={(e) => setQuestionNo(parseInt(e.target.value) || 1)}
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">{error}</p>
          )}

          <QuestionFormBody form={form} set={set} />
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-surface-100 bg-surface-50 rounded-b-2xl">
          <button onClick={onClose} className="btn-secondary" disabled={saving}>Cancel</button>
          <button onClick={handleSave} className="btn-primary" disabled={saving}>
            {saving ? "Adding…" : "Add Question"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Clean Paper confirm ────────────────────────────────────────────────────────

interface CleanConfirmProps {
  paperCode: string;
  examCode:  string;
  onClose:   () => void;
  onConfirm: () => void;
  cleaning:  boolean;
  error:     string;
}

function CleanConfirm({ paperCode, examCode, onClose, onConfirm, cleaning, error }: CleanConfirmProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center text-red-500 text-xl shrink-0">🧹</div>
          <div>
            <h3 className="font-bold text-surface-900">Clean Paper {examCode} — {paperCode}?</h3>
            <p className="text-sm text-surface-500 mt-1">
              This will permanently delete all questions, student responses, graded results, ranks, and analytics for this paper. This cannot be undone.
            </p>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}
        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="btn-secondary flex-1" disabled={cleaning}>Cancel</button>
          <button
            onClick={onConfirm}
            className="bg-red-500 hover:bg-red-600 text-white font-semibold px-4 py-2 rounded-xl text-sm flex-1 transition-colors"
            disabled={cleaning}
          >
            {cleaning ? "Cleaning…" : "Clean Paper"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function QuestionPaperPage() {
  const qc = useQueryClient();

  const [examId,    setExamId]    = useState<number>(0);
  const [paperCode, setPaperCode] = useState<string>("P1");
  const [filterSubj, setFilterSubj] = useState("all");
  const [filterDiff, setFilterDiff] = useState("all");
  const [search,     setSearch]     = useState("");

  const [editingQ,      setEditingQ]      = useState<QuestionOut | null>(null);
  const [addingOpen,    setAddingOpen]    = useState(false);
  const [addError,      setAddError]      = useState("");
  const [cleanOpen,     setCleanOpen]     = useState(false);
  const [cleanError,    setCleanError]    = useState("");
  const [showTypeHelp,  setShowTypeHelp]  = useState(false);
  const [showDiffHelp,  setShowDiffHelp]  = useState(false);

  // ── Exams list ────────────────────────────────────────────────────────────
  const { data: exams, isLoading: examsLoading } = useQuery<ExamOut[]>({
    queryKey: ["exams"],
    queryFn:  () => examsApi.list().then((r) => r.data),
  });

  const selectedExam    = exams?.find((e) => e.id === examId);
  const availablePapers = selectedExam?.papers ?? ["P1"];

  // ── Questions list ────────────────────────────────────────────────────────
  const canFetch = examId > 0 && !!paperCode;
  const { data: questions, isLoading, isError, refetch } = useQuery<QuestionOut[]>({
    queryKey: ["questions", examId, paperCode],
    queryFn:  () => questionsApi.list(examId, paperCode).then((r) => r.data),
    enabled:  canFetch,
  });

  // ── Upload jobs (for hasResponses gate) ──────────────────────────────────
  const { data: uploadJobs } = useQuery<UploadJobOut[]>({
    queryKey: ["uploadJobs", examId],
    queryFn:  () => uploadsApi.listJobs(examId).then((r) => r.data),
    enabled:  canFetch,
  });

  const hasKey       = questions?.some(
    (q) => q.correct_option_bkc !== null || q.correct_option_akc !== null
  ) ?? false;
  const hasResponses = uploadJobs?.some(
    (j) => (j.job_type === "responses" || j.job_type === "omr_responses" || j.job_type === "responses_omr") && j.status === "completed"
  ) ?? false;

  // next sequence number for Add modal
  const nextQuestionNo = useMemo(() => {
    if (!questions || questions.length === 0) return 1;
    return Math.max(...questions.map((q) => q.question_no)) + 1;
  }, [questions]);

  // ── Create mutation ───────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: (body: QuestionCreate) => questionsApi.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["questions", examId, paperCode] });
      setAddingOpen(false);
      setAddError("");
    },
    onError: (err: any) => {
      setAddError(err.response?.data?.detail ?? "Failed to add question.");
    },
  });

  // ── Update mutation ───────────────────────────────────────────────────────
  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: QuestionUpdate }) =>
      questionsApi.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["questions", examId, paperCode] });
      setEditingQ(null);
    },
  });

  // ── Clean paper mutation ──────────────────────────────────────────────────
  const cleanMutation = useMutation({
    mutationFn: () => questionsApi.cleanPaper(examId, paperCode),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["questions", examId, paperCode] });
      setCleanOpen(false);
      setCleanError("");
    },
    onError: (err: any) => {
      setCleanError(err.response?.data?.detail ?? "Failed to clean paper.");
    },
  });

  // ── Derived / filter ──────────────────────────────────────────────────────
  const filtered = useMemo(() => {
    if (!questions) return [];
    return questions.filter((q) => {
      if (filterSubj !== "all" && q.subject !== filterSubj) return false;
      if (filterDiff !== "all" && q.difficulty !== filterDiff) return false;
      if (search) {
        const s = search.toLowerCase();
        if (
          !String(q.question_no).includes(s) &&
          !(q.topic?.toLowerCase().includes(s)) &&
          !(q.sub_topic?.toLowerCase().includes(s)) &&
          !(q.subject.toLowerCase().includes(s)) &&
          !(q.correct_option_bkc?.toLowerCase().includes(s))
        ) return false;
      }
      return true;
    });
  }, [questions, filterSubj, filterDiff, search]);

  const stats = useMemo(() => {
    if (!questions) return null;
    const bySubj:           Record<string, number> = {};
    const activeBySubj:     Record<string, number> = {};
    const activeMarksBySubj:Record<string, number> = {};
    const diffByLevel:      Record<string, number> = {};
    const diffBySubj:       Record<string, Record<string, number>> = {};
    let totalMarks       = 0;
    let activeTotalMarks = 0;
    let deleted          = 0;
    let keyChanges       = 0;
    for (const q of questions) {
      bySubj[q.subject] = (bySubj[q.subject] ?? 0) + 1;
      totalMarks += q.positive_marks;
      if (q.is_deleted_bkc) {
        deleted++;
      } else {
        activeBySubj[q.subject]      = (activeBySubj[q.subject]      ?? 0) + 1;
        activeMarksBySubj[q.subject] = (activeMarksBySubj[q.subject] ?? 0) + q.positive_marks;
        activeTotalMarks += q.positive_marks;
      }
      if (hasKeyChange(q)) keyChanges++;
      if (q.difficulty && !q.is_deleted_bkc) {
        diffByLevel[q.difficulty] = (diffByLevel[q.difficulty] ?? 0) + 1;
        if (!diffBySubj[q.subject]) diffBySubj[q.subject] = {};
        diffBySubj[q.subject][q.difficulty] = (diffBySubj[q.subject][q.difficulty] ?? 0) + 1;
      }
    }
    const diffTagged = Object.values(diffByLevel).reduce((a, b) => a + b, 0);
    return { total: questions.length, totalMarks, activeTotalMarks, bySubj, activeBySubj, activeMarksBySubj, deleted, keyChanges, diffByLevel, diffBySubj, diffTagged };
  }, [questions]);

  // ── Exam picker ───────────────────────────────────────────────────────────
  const handleExamChange = (id: number) => {
    setExamId(id);
    const exam = exams?.find((e) => e.id === id);
    setPaperCode(exam?.papers[0] ?? "P1");
  };

  // ── Render ────────────────────────────────────────────────────────────────
  if (examsLoading) return <PageLoader />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Question Papers</h1>
          <p className="text-surface-500 text-sm mt-0.5">View and edit questions, marks, and answer keys</p>
        </div>

        <div className="flex items-center gap-3">
          <select
            className="input w-56"
            value={examId}
            onChange={(e) => handleExamChange(Number(e.target.value))}
          >
            <option value={0} disabled>Select exam…</option>
            {exams?.map((e) => (
              <option key={e.id} value={e.id}>
                {e.exam_code}{e.title ? ` — ${e.title}` : ""}
                {e.program_name ? ` [${e.program_name}` : ""}
                {e.program_name && e.student_class ? ` · ${e.student_class}` : ""}
                {e.program_name ? `]` : ""}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Compact exam info bar */}
      {selectedExam && (
        <div className="rounded-xl bg-primary-600 text-white px-4 py-2.5 flex flex-wrap items-center gap-3">
          <span className="text-xs font-semibold uppercase tracking-widest text-primary-200 shrink-0">
            {selectedExam.exam_type ?? "Exam"}
          </span>
          <span className="w-px h-4 bg-primary-400 hidden sm:block" />
          <span className="font-bold text-base tracking-tight">
            {selectedExam.exam_code}
            {selectedExam.title && (
              <span className="ml-1.5 font-normal text-primary-100 text-sm">— {selectedExam.title}</span>
            )}
          </span>
          {selectedExam.exam_date && (
            <>
              <span className="w-px h-4 bg-primary-400 hidden sm:block" />
              <span className="text-xs text-primary-200">
                📅 {new Date(selectedExam.exam_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
              </span>
            </>
          )}
          {selectedExam.program_name && (
            <>
              <span className="w-px h-4 bg-primary-400 hidden sm:block" />
              <span className="text-xs text-primary-200">
                🎓 {selectedExam.program_name}
              </span>
            </>
          )}
          {selectedExam.student_class && (
            <>
              <span className="w-px h-4 bg-primary-400 hidden sm:block" />
              <span className="text-xs text-primary-200">
                🏫 {selectedExam.student_class}
              </span>
            </>
          )}
          <div className="ml-auto flex gap-1.5 shrink-0">
            {availablePapers.map((p) => (
              <button
                key={p}
                onClick={() => setPaperCode(p)}
                className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
                  paperCode === p
                    ? "bg-white text-primary-700 border-white"
                    : "bg-primary-500/50 text-white border-primary-400/50 hover:bg-primary-500"
                }`}
              >
                {p === "P1" ? "Paper 1" : "Paper 2"}
              </button>
            ))}
          </div>
        </div>
      )}

      {!canFetch && (
        <EmptyState icon="📋" title="Select an exam" description="Choose an exam and paper above to view its questions." />
      )}

      {/* Upload + Evaluate + Actions panel */}
      {canFetch && (
        <ActionPanel
          examId={examId}
          paperCode={paperCode}
          hasQuestions={!!questions && questions.length > 0}
          hasKey={hasKey}
          hasResponses={hasResponses}
          onUploadDone={() => {
            refetch();
            qc.invalidateQueries({ queryKey: ["uploadJobs", examId] });
          }}
          onAddQuestion={() => { setAddError(""); setAddingOpen(true); }}
          onCleanPaper={() => { setCleanError(""); setCleanOpen(true); }}
        />
      )}

      {canFetch && isLoading && <PageLoader />}
      {canFetch && isError   && <ErrorBanner onRetry={refetch} />}

      {canFetch && questions && (
        <>
          {/* Stats strip — compact */}
          {stats && (
            <div className="card py-2.5 px-3 space-y-2.5">
              {/* Row 1: counters + subject bars — full width */}
              <div className="flex items-stretch gap-0">
                {/* Counters — spread across flex-[2] */}
                <div className="flex-[2] flex items-center justify-between pr-4">
                  {[
                    { label: "Questions",   value: stats.total,                  color: "text-primary-700" },
                    { label: "Active Marks",value: stats.activeTotalMarks,       color: "text-emerald-600" },
                    { label: "Active",      value: stats.total - stats.deleted,  color: "text-surface-700" },
                    { label: "Deleted",     value: stats.deleted,                color: "text-red-500"     },
                    { label: "AKC Changes", value: stats.keyChanges,             color: stats.keyChanges > 0 ? "text-amber-600" : "text-surface-400" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="flex flex-col items-center gap-0.5">
                      <span className={`text-lg font-bold leading-none ${color}`}>{value}</span>
                      <span className="text-[11px] text-surface-400 text-center">{label}</span>
                    </div>
                  ))}
                </div>

                {/* Subject bars — each flex-1 with left border */}
                {SUBJECTS.map((s) => {
                  const activeMarks = stats.activeMarksBySubj[s] ?? 0;
                  const qCnt        = stats.activeBySubj[s]       ?? 0;
                  const pct         = stats.activeTotalMarks > 0
                    ? Math.round(activeMarks / stats.activeTotalMarks * 100)
                    : 0;
                  const colMap: Record<string, { bar: string; text: string }> = {
                    Physics:     { bar: "bg-blue-400",   text: "text-blue-700"   },
                    Chemistry:   { bar: "bg-green-400",  text: "text-green-700"  },
                    Mathematics: { bar: "bg-orange-400", text: "text-orange-700" },
                  };
                  const c = colMap[s] ?? { bar: "bg-surface-400", text: "text-surface-600" };
                  return (
                    <div key={s} className="flex-1 flex flex-col gap-1 pl-4 border-l border-surface-100">
                      <div className="flex items-baseline justify-between">
                        <span className={`text-[11px] font-semibold ${c.text}`}>{s}</span>
                        <span className="text-[11px] text-surface-400">{activeMarks}M · {qCnt}Q</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-surface-100">
                        <div className={`h-full rounded-full ${c.bar}`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className={`text-[10px] ${c.text} opacity-70`}>{pct}%</span>
                    </div>
                  );
                })}
              </div>

              {/* Row 2: difficulty profile (only when at least one question is tagged) */}
              {stats.diffTagged > 0 && (
                <>
                  <div className="border-t border-surface-100" />
                  <div className="flex items-stretch gap-0">

                    {/* Overall column — flex-[2] so it's wider than each subject */}
                    <div className="flex-[2] flex flex-col gap-1.5 pr-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-semibold uppercase tracking-wide text-surface-400">Overall Difficulty</span>
                          <button
                            onClick={() => setShowDiffHelp(true)}
                            className="w-3.5 h-3.5 rounded-full bg-surface-200 hover:bg-primary-100 text-surface-500 hover:text-primary-600 text-[9px] font-bold flex items-center justify-center transition-colors leading-none shrink-0"
                            title="How difficulty is calculated"
                          >
                            ?
                          </button>
                          {(() => {
                            const rating = difficultyRating(stats.diffByLevel);
                            return rating
                              ? <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${DIFF_STYLE[rating].badge}`}>{rating}</span>
                              : null;
                          })()}
                        </div>
                        <span className="text-[10px] text-surface-300">{stats.diffTagged}/{stats.total} tagged</span>
                      </div>
                      <div className="flex rounded-full overflow-hidden h-2 w-full bg-surface-100">
                        {DIFFICULTIES.map((d) => {
                          const n   = stats.diffByLevel[d] ?? 0;
                          const pct = (n / stats.diffTagged) * 100;
                          return pct > 0
                            ? <div key={d} className={`h-full ${DIFF_STYLE[d].bar}`} style={{ width: `${pct}%` }} title={`${d}: ${n}`} />
                            : null;
                        })}
                      </div>
                      <div className="flex gap-2 flex-wrap">
                        {DIFFICULTIES.map((d) => {
                          const n = stats.diffByLevel[d] ?? 0;
                          if (n === 0) return null;
                          const pct = Math.round((n / stats.diffTagged) * 100);
                          return (
                            <span key={d} className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${DIFF_STYLE[d].badge}`}>
                              {d === "Very Hard" ? "VH" : d[0]} {n} <span className="opacity-60">({pct}%)</span>
                            </span>
                          );
                        })}
                      </div>
                      {/* Score range reference */}
                      <div className="flex gap-3 flex-wrap pt-0.5">
                        {([
                          { d: "Easy",      range: "avg < 1.5"   },
                          { d: "Medium",    range: "1.5 – 2.5"   },
                          { d: "Hard",      range: "2.5 – 3.5"   },
                          { d: "Very Hard", range: "> 3.5"        },
                        ] as { d: Difficulty; range: string }[]).map(({ d, range }) => (
                          <span key={d} className="flex items-center gap-1">
                            <span className={`w-2 h-2 rounded-full inline-block ${DIFF_STYLE[d].bar}`} />
                            <span className="text-[10px] text-surface-400">{d} <span className="text-surface-300">{range}</span></span>
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Per-subject columns */}
                    {SUBJECTS.map((subj) => {
                      const sd        = stats.diffBySubj[subj] ?? {};
                      const subjTotal = DIFFICULTIES.reduce((a, d) => a + (sd[d] ?? 0), 0);
                      const rating    = difficultyRating(sd);
                      return (
                        <div key={subj} className="flex-1 flex flex-col gap-1.5 pl-4 border-l border-surface-100">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-[11px] font-semibold text-surface-500">{subj}</span>
                            {rating && <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${DIFF_STYLE[rating].badge}`}>{rating}</span>}
                          </div>
                          <div className="flex rounded-full overflow-hidden h-2 w-full bg-surface-100">
                            {subjTotal > 0 ? DIFFICULTIES.map((d) => {
                              const n   = sd[d] ?? 0;
                              const pct = (n / subjTotal) * 100;
                              return pct > 0
                                ? <div key={d} className={`h-full ${DIFF_STYLE[d].bar}`} style={{ width: `${pct}%` }} title={`${d}: ${n}`} />
                                : null;
                            }) : null}
                          </div>
                          <div className="flex gap-1.5 flex-wrap">
                            {subjTotal > 0 ? DIFFICULTIES.map((d) => {
                              const n = sd[d] ?? 0;
                              if (n === 0) return null;
                              const abbr = d === "Very Hard" ? "VH" : d[0];
                              return (
                                <span key={d} className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${DIFF_STYLE[d].badge}`}>
                                  {abbr} {n}
                                </span>
                              );
                            }) : <span className="text-[10px] text-surface-300">—</span>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Filters */}
          <div className="flex flex-wrap gap-2 items-center">
            <input
              className="input !py-1.5 !text-sm w-44"
              placeholder="Search Q#, topic, answer…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select className="input !py-1.5 !text-sm w-32" value={filterSubj} onChange={(e) => setFilterSubj(e.target.value)}>
              <option value="all">All subjects</option>
              {SUBJECTS.map((s) => <option key={s}>{s}</option>)}
            </select>
            <select className="input !py-1.5 !text-sm w-32" value={filterDiff} onChange={(e) => setFilterDiff(e.target.value)}>
              <option value="all">All difficulty</option>
              {DIFFICULTIES.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            {(filterSubj !== "all" || filterDiff !== "all" || search) && (
              <button className="text-xs text-primary-600 hover:underline"
                onClick={() => { setFilterSubj("all"); setFilterDiff("all"); setSearch(""); }}>
                Clear
              </button>
            )}
            <div className="ml-auto flex items-center gap-2">
              {stats && stats.keyChanges > 0 && (
                <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
                  AKC changes
                </span>
              )}
              <span className="text-xs text-surface-400">{filtered.length} / {questions.length}</span>
            </div>
          </div>

          {/* Table */}
          {filtered.length === 0 ? (
            <EmptyState icon="🔍" title="No questions match" description="Try adjusting your filters." />
          ) : (
            <div className="card overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th className="w-12">Q#</th>
                      <th>Subject</th>
                      <th>Topic</th>
                      <th>Sub-topic</th>
                      <th>
                        <div className="flex items-center gap-1">
                          Difficulty
                          <button
                            onClick={() => setShowDiffHelp(true)}
                            className="w-4 h-4 rounded-full bg-surface-200 hover:bg-primary-100 text-surface-500 hover:text-primary-600 text-[10px] font-bold flex items-center justify-center transition-colors leading-none"
                            title="Difficulty rating reference"
                          >
                            ?
                          </button>
                        </div>
                      </th>
                      <th>
                        <div className="flex items-center gap-1">
                          Type
                          <button
                            onClick={() => setShowTypeHelp(true)}
                            className="w-4 h-4 rounded-full bg-surface-200 hover:bg-primary-100 text-surface-500 hover:text-primary-600 text-[10px] font-bold flex items-center justify-center transition-colors leading-none"
                            title="Question type reference"
                          >
                            ?
                          </button>
                        </div>
                      </th>
                      <th className="text-right">+Marks</th>
                      <th className="text-right">−Marks</th>
                      <th>BKC Answer</th>
                      <th>AKC Answer</th>
                      <th className="w-24 text-center">Status</th>
                      <th className="w-12"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((q) => {
                      const keyChanged = hasKeyChange(q);
                      return (
                        <tr key={q.id} className={[
                          q.is_deleted_bkc ? "opacity-50" : "",
                          keyChanged ? "bg-amber-50 border-l-4 border-l-amber-400" : "",
                        ].join(" ")}>
                          <td className="font-mono font-bold text-surface-700">
                            <div className="flex items-center gap-1.5">
                              {q.question_no}
                              {keyChanged && (
                                <span title="AKC key change applied" className="text-amber-500 text-xs">●</span>
                              )}
                            </div>
                          </td>
                          <td>{badge(q.subject, subjectColor(q.subject))}</td>
                          <td className="text-surface-600 max-w-[140px] truncate" title={q.topic ?? ""}>
                            {q.topic ?? <span className="text-surface-300">—</span>}
                          </td>
                          <td className="text-surface-500 text-xs max-w-[120px] truncate" title={q.sub_topic ?? ""}>
                            {q.sub_topic ?? <span className="text-surface-300">—</span>}
                          </td>
                          <td>
                            {q.difficulty
                              ? badge(q.difficulty, DIFF_STYLE[q.difficulty as Difficulty]?.badge ?? "bg-surface-100 text-surface-600")
                              : <span className="text-surface-300 text-xs">—</span>}
                          </td>
                          <td>{badge(q.question_type, typeColor(q.question_type))}</td>
                          <td className="text-right font-semibold text-green-600">+{q.positive_marks}</td>
                          <td className="text-right font-semibold text-red-500">−{q.negative_marks}</td>
                          <td className="font-mono text-sm">
                            {q.correct_option_bkc
                              ? <span className={`px-1.5 py-0.5 rounded ${keyChanged ? "bg-blue-50 text-blue-400 line-through" : "bg-blue-50 text-blue-700"}`}>{q.correct_option_bkc}</span>
                              : <span className="text-surface-300">—</span>}
                          </td>
                          <td className="font-mono text-sm">
                            {q.correct_option_akc ? (
                              <span className="bg-amber-100 text-amber-700 border border-amber-300 px-1.5 py-0.5 rounded font-semibold">
                                {q.correct_option_akc}
                              </span>
                            ) : q.is_deleted_akc !== null && q.is_deleted_akc !== q.is_deleted_bkc ? (
                              <span className="bg-amber-100 text-amber-700 border border-amber-300 px-1.5 py-0.5 rounded text-xs font-semibold">
                                {q.is_deleted_akc ? "Deleted" : "Restored"}
                              </span>
                            ) : (
                              <span className="text-surface-300">—</span>
                            )}
                          </td>
                          <td className="text-center">
                            {q.is_deleted_bkc
                              ? badge("Deleted", "bg-red-100 text-red-600")
                              : badge("Active",  "bg-green-100 text-green-700")}
                          </td>
                          <td>
                            <button
                              onClick={() => setEditingQ(q)}
                              className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-500 hover:text-primary-600 transition-colors"
                              title="Edit"
                            >
                              ✏️
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Modals */}
      {showTypeHelp && <QuestionTypeHelpModal onClose={() => setShowTypeHelp(false)} />}
      {showDiffHelp && <DifficultyHelpModal   onClose={() => setShowDiffHelp(false)} />}
      {addingOpen && (
        <AddModal
          examId={examId}
          paperCode={paperCode}
          nextQuestionNo={nextQuestionNo}
          onClose={() => { setAddingOpen(false); setAddError(""); }}
          onSave={(body) => createMutation.mutate(body)}
          saving={createMutation.isPending}
          error={addError}
        />
      )}
      {editingQ && (
        <EditModal
          question={editingQ}
          onClose={() => setEditingQ(null)}
          onSave={(id, body) => updateMutation.mutate({ id, body })}
          saving={updateMutation.isPending}
        />
      )}
      {cleanOpen && selectedExam && (
        <CleanConfirm
          examCode={selectedExam.exam_code}
          paperCode={paperCode}
          onClose={() => { setCleanOpen(false); setCleanError(""); }}
          onConfirm={() => cleanMutation.mutate()}
          cleaning={cleanMutation.isPending}
          error={cleanError}
        />
      )}
    </div>
  );
}
