import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmt(date: string | Date | undefined, pattern = "dd MMM yyyy") {
  if (!date) return "—";
  const d = typeof date === "string" ? parseISO(date) : date;
  return format(d, pattern);
}

export function fmtNum(n: number | undefined, decimals = 1) {
  if (n === undefined || n === null) return "—";
  return n.toFixed(decimals);
}

export function fmtPct(n: number | undefined) {
  if (n === undefined || n === null) return "—";
  return `${n.toFixed(1)}%`;
}

export function severityColor(s: "critical" | "warning" | "info") {
  return s === "critical" ? "badge-critical"
       : s === "warning"  ? "badge-warning"
       :                     "badge-info";
}

export function subjectColor(subject: string): string {
  const map: Record<string, string> = {
    Physics:   "#6366f1",
    Chemistry: "#22c55e",
    Maths:     "#f59e0b",
  };
  return map[subject] ?? "#94a3b8";
}

export const SUBJECT_COLORS = {
  physics:   "#6366f1",
  chemistry: "#22c55e",
  maths:     "#f59e0b",
};

export function pctToHeatColor(pct: number): string {
  // 0–40 → red, 40–60 → yellow, 60–80 → teal, 80–100 → green
  if (pct < 40) return "#fee2e2";
  if (pct < 60) return "#fef3c7";
  if (pct < 80) return "#ccfbf1";
  return "#dcfce7";
}

export function pctToTextColor(pct: number): string {
  if (pct < 40) return "#b91c1c";
  if (pct < 60) return "#b45309";
  if (pct < 80) return "#0f766e";
  return "#15803d";
}

export function rankSuffix(rank: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = rank % 100;
  return rank + (s[(v - 20) % 10] ?? s[v] ?? s[0]);
}
