import { cn } from "@/lib/utils";

interface Props {
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
}

const SIZE_MAP = { sm: "w-5 h-5", md: "w-8 h-8", lg: "w-12 h-12" };
const BORDER_MAP = { sm: "border-2", md: "border-3", lg: "border-4" };

export default function LoadingSpinner({ size = "md", className, label }: Props) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3", className)}>
      <div
        className={cn(
          "rounded-full border-primary-200 border-t-primary-600 animate-spin",
          SIZE_MAP[size],
          BORDER_MAP[size],
        )}
      />
      {label && <p className="text-sm text-surface-500">{label}</p>}
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <LoadingSpinner size="lg" label="Loading…" />
    </div>
  );
}
