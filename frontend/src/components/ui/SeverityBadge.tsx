import { cn } from "@/lib/utils";

type Severity = "critical" | "warning" | "info" | "success";

const MAP: Record<Severity, { cls: string; dot: string; label: string }> = {
  critical: { cls: "badge-critical", dot: "bg-danger",  label: "Critical" },
  warning:  { cls: "badge-warning",  dot: "bg-warning", label: "Warning"  },
  info:     { cls: "badge-info",     dot: "bg-info",    label: "Info"     },
  success:  { cls: "badge-success",  dot: "bg-success", label: "OK"       },
};

interface Props {
  severity: Severity;
  label?: string;
  className?: string;
}

export default function SeverityBadge({ severity, label, className }: Props) {
  const { cls, dot, label: def } = MAP[severity];
  return (
    <span className={cn(cls, className)}>
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", dot)} />
      {label ?? def}
    </span>
  );
}
