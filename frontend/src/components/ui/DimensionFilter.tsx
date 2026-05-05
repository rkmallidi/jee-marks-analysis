import { useQuery } from "@tanstack/react-query";
import { studentsApi, DimensionParams, FilterOptions } from "@/lib/api";

interface Props {
  value:    DimensionParams;
  onChange: (d: DimensionParams) => void;
}

const LABELS: Record<keyof DimensionParams, string> = {
  branch_name:   "Branch",
  program_name:  "Program",
  student_class: "Class",
  section_dim:   "Section",
};

export default function DimensionFilter({ value, onChange }: Props) {
  const { data: opts } = useQuery<FilterOptions>({
    queryKey:  ["student-filter-options"],
    queryFn:   () => studentsApi.getFilterOptions().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const set = (k: keyof DimensionParams, v: string) => {
    const next = { ...value, [k]: v || undefined };
    // reset downstream when a broader dimension changes
    if (k === "branch_name")   { delete next.program_name; delete next.student_class; delete next.section_dim; }
    if (k === "program_name")  { delete next.student_class; delete next.section_dim; }
    if (k === "student_class") { delete next.section_dim; }
    onChange(next);
  };

  const hasFilter = Object.values(value).some(Boolean);

  const scopeLabel = [
    value.branch_name,
    value.program_name,
    value.student_class && `Class ${value.student_class}`,
    value.section_dim   && `§${value.section_dim}`,
  ].filter(Boolean).join(" › ");

  return (
    <div className="card py-2.5 px-4 flex flex-wrap items-center gap-3">
      <span className="text-[11px] font-extrabold uppercase tracking-widest text-surface-400 shrink-0">
        Scope
      </span>

      {(
        [
          { key: "branch_name",   opts: opts?.branches  ?? [] },
          { key: "program_name",  opts: opts?.programs  ?? [] },
          { key: "student_class", opts: opts?.classes   ?? [] },
          { key: "section_dim",   opts: opts?.sections  ?? [] },
        ] as { key: keyof DimensionParams; opts: string[] }[]
      ).map(({ key, opts: list }) => (
        <select
          key={key}
          value={value[key] ?? ""}
          onChange={(e) => set(key, e.target.value)}
          className="input w-auto py-1 text-sm"
        >
          <option value="">All {LABELS[key]}s</option>
          {list.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ))}

      {hasFilter ? (
        <>
          <span className="flex items-center gap-1.5 px-2.5 py-1 bg-primary-50 border border-primary-200 rounded-full text-xs font-semibold text-primary-700">
            <span className="w-1.5 h-1.5 rounded-full bg-primary-500 inline-block" />
            {scopeLabel}
          </span>
          <button
            onClick={() => onChange({})}
            className="text-xs text-surface-400 hover:text-surface-600 ml-auto"
          >
            Reset scope
          </button>
        </>
      ) : (
        <span className="text-xs text-surface-400 ml-auto">Showing all students</span>
      )}
    </div>
  );
}
