/**
 * Persists the selected exam ID in localStorage.
 * Returns null until the exams list has loaded and a valid id is confirmed,
 * so callers never fire queries with a stale/non-existent id.
 */
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";

const KEY = "jee_selected_exam_id";

export function useExamSelector() {
  const stored = localStorage.getItem(KEY);
  const [examId, setExamIdRaw] = useState<number>(stored ? parseInt(stored) : 0);

  const { data: exams } = useQuery({
    queryKey: ["exams-list"],
    queryFn: () => dashboardApi.exams().then((r) => r.data),
  });

  // Resolved id: stored if valid, else first available, else null
  const resolvedExamId: number | null = (() => {
    if (!exams || exams.length === 0) return null;
    return exams.find((e) => e.id === examId) ? examId : exams[0].id;
  })();

  useEffect(() => {
    if (resolvedExamId !== null && resolvedExamId !== examId) {
      setExamIdRaw(resolvedExamId);
      localStorage.setItem(KEY, String(resolvedExamId));
    }
  }, [resolvedExamId]);

  const setExamId = (id: number) => {
    localStorage.setItem(KEY, String(id));
    setExamIdRaw(id);
  };

  return { examId: resolvedExamId ?? 0, resolvedExamId, setExamId };
}
