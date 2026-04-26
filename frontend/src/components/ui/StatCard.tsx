import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: string | number;
  sub?: string;
  icon?: string;
  color?: "primary" | "success" | "warning" | "danger" | "info";
  className?: string;
}

const COLOR_MAP = {
  primary: "bg-primary-50  text-primary-600  border-primary-100",
  success: "bg-success-light text-success-dark border-green-100",
  warning: "bg-warning-light text-warning-dark border-yellow-100",
  danger:  "bg-danger-light  text-danger-dark  border-red-100",
  info:    "bg-info-light    text-info-dark    border-blue-100",
};

export default function StatCard({ label, value, sub, icon, color = "primary", className }: Props) {
  return (
    <div className={cn("card flex flex-col gap-3", className)}>
      <div className="flex items-start justify-between">
        <p className="stat-label">{label}</p>
        {icon && (
          <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center text-lg border", COLOR_MAP[color])}>
            {icon}
          </div>
        )}
      </div>
      <p className="stat-value">{value}</p>
      {sub && <p className="stat-sub">{sub}</p>}
    </div>
  );
}
