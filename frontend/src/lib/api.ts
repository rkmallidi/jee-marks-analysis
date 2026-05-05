/**
 * Axios instance with JWT interceptors.
 * – Attaches Authorization header from localStorage
 * – On 401 attempts a single token refresh, then retries the original request
 * – On second 401 (refresh also expired) clears tokens and reloads to /login
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const BASE = import.meta.env.VITE_API_URL ?? "/api";

export const api = axios.create({ baseURL: BASE, withCredentials: false });

// ── helpers ──────────────────────────────────────────────────────────────────
const getAccess  = () => localStorage.getItem("access_token");
const getRefresh = () => localStorage.getItem("refresh_token");
const setTokens  = (access: string, refresh: string) => {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
};
export const clearTokens = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
};

// ── request interceptor ───────────────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── response interceptor (refresh logic) ─────────────────────────────────────
let refreshing: Promise<string> | null = null;

api.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original = err.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (err.response?.status !== 401 || original._retry) {
      return Promise.reject(err);
    }
    original._retry = true;

    try {
      if (!refreshing) {
        refreshing = axios
          .post(`${BASE}/auth/refresh`, { refresh_token: getRefresh() })
          .then((r) => {
            setTokens(r.data.access_token, r.data.refresh_token);
            return r.data.access_token;
          })
          .finally(() => { refreshing = null; });
      }
      const newAccess = await refreshing;
      original.headers.Authorization = `Bearer ${newAccess}`;
      return api(original);
    } catch {
      clearTokens();
      window.location.href = "/login";
      return Promise.reject(err);
    }
  },
);

// ── typed API helpers ─────────────────────────────────────────────────────────

// Auth
export const authApi = {
  login:   (u: string, p: string) =>
    api.post<{ access_token: string; refresh_token: string; user: UserMe }>
      ("/auth/login", { username: u, password: p }),
  me:      () => api.get<UserMe>("/auth/me"),
  refresh: (rt: string) =>
    api.post<{ access_token: string; refresh_token: string }>
      ("/auth/refresh", { refresh_token: rt }),
};

// Students
export const studentsApi = {
  list:   (p: StudentListParams) => api.get<StudentListResp>("/students", { params: p }),
  get:    (admissionNo: string)  => api.get<StudentDetail>(`/students/${admissionNo}`),
  create: (b: StudentCreate)     => api.post<StudentOut>("/students", b),
  update: (admissionNo: string, b: Partial<StudentCreate>) =>
    api.patch<StudentOut>(`/students/${admissionNo}`, b),
  getFilterOptions: () => api.get<FilterOptions>("/students/filters/options"),
  bulkUpload: (file: File, onProgress?: (pct: number) => void) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post<UploadJobOut>("/uploads/students", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / (e.total ?? 1))),
    });
  },
  export: (params: { search?: string; branch_name?: string; status?: string; format: "csv" | "xlsx" }) =>
    api.get("/students/export", { params, responseType: "blob" }).then((r) => r.data),
};

// Exams
export const examsApi = {
  list:      ()                        => api.get<ExamOut[]>("/exams"),
  create:    (b: ExamCreate)           => api.post<ExamOut>("/exams", b),
  update:    (id: number, b: ExamUpdate) => api.patch<ExamOut>(`/exams/${id}`, b),
  getPapers: (examId: number)      => api.get<string[]>(`/exams/${examId}/papers`),
};

// Uploads
export const uploadsApi = {
  uploadQuestions: (examId: number, paperCode: string, file: File, onProgress?: (pct: number) => void) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("exam_id", String(examId));
    fd.append("paper_code", paperCode);
    return api.post<UploadJobOut>("/uploads/questions", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / (e.total ?? 1))),
    });
  },
  uploadResponses: (examId: number, paperCode: string, file: File, onProgress?: (pct: number) => void) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("exam_id", String(examId));
    fd.append("paper_code", paperCode);
    return api.post<UploadJobOut>("/uploads/responses", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / (e.total ?? 1))),
    });
  },
  uploadAnswerKey: (examId: number, paperCode: string, keyType: "BKC" | "AKC", file: File, onProgress?: (pct: number) => void) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("exam_id", String(examId));
    fd.append("paper_code", paperCode);
    fd.append("key_type", keyType);
    return api.post<UploadJobOut>("/uploads/answer-key", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / (e.total ?? 1))),
    });
  },
  uploadOmrResponses: (examId: number, paperCode: string, file: File, onProgress?: (pct: number) => void) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("exam_id", String(examId));
    fd.append("paper_code", paperCode);
    return api.post<UploadJobOut>("/uploads/omr-responses", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => onProgress?.(Math.round((e.loaded * 100) / (e.total ?? 1))),
    });
  },
  listJobs: (examId?: number) => api.get<UploadJobOut[]>("/uploads/jobs", { params: { exam_id: examId } }),
  getJob:   (id: number)      => api.get<UploadJobOut>(`/uploads/jobs/${id}`),
};

// Questions
export const questionsApi = {
  list:       (examId: number, paperCode: string) =>
    api.get<QuestionOut[]>("/questions", { params: { exam_id: examId, paper_code: paperCode } }),
  create:     (body: QuestionCreate) =>
    api.post<QuestionOut>("/questions", body),
  update:     (questionId: number, body: QuestionUpdate) =>
    api.patch<QuestionOut>(`/questions/${questionId}`, body),
  cleanPaper: (examId: number, paperCode: string) =>
    api.delete<{ deleted_questions: number; message: string }>("/questions/paper", {
      params: { exam_id: examId, paper_code: paperCode },
    }),
};

// Evaluation
export const evalApi = {
  trigger: (examId: number, keyType: "BKC" | "AKC" = "BKC") =>
    api.post<{ exam_id: number; key_type: string; students_graded: number; questions_graded: number; duration_ms: number }>(
      `/evaluate/${examId}`, null, { params: { key_type: keyType } }
    ),
};

export interface DimensionParams {
  branch_name?:   string;
  program_name?:  string;
  student_class?: string;
  section_dim?:   string;
}

// Dashboards
export const dashboardApi = {
  overall:        (examId: number, dims?: DimensionParams) =>
    api.get<DashboardOverall>(`/dashboards/overall/${examId}`, { params: dims }),
  weakStudents:   (examId: number, dims?: DimensionParams) =>
    api.get<WeakStudentsDashboard>(`/dashboards/weak-students/${examId}`, { params: dims }),
  subjectAnalysis:(examId: number, dims?: DimensionParams) =>
    api.get<SubjectDashboard>(`/dashboards/subject-analysis/${examId}`, { params: dims }),
  topicHeatmap:   (examId: number, dims?: DimensionParams) =>
    api.get<TopicHeatmapDashboard>(`/dashboards/topic-heatmap/${examId}`, { params: dims }),
  studentDeepDive:(admissionNo: string) => api.get<StudentDeepDive>(`/dashboards/student/${admissionNo}`),
  studentExamResponses: (admissionNo: string, examId: number) =>
    api.get<QuestionResponse[]>(`/dashboards/student/${admissionNo}/exam/${examId}/responses`),
  examTrend:      (examId: number, dims?: DimensionParams) =>
    api.get<ExamTrendPoint[]>(`/dashboards/exam-trend/${examId}`, { params: dims }),
  leaderboard:    (examId: number, limit?: number, dims?: DimensionParams) =>
    api.get<LeaderboardEntry[]>(`/dashboards/leaderboard/${examId}`, { params: { limit, ...dims } }),
  scoreDistribution: (examId: number, dims?: DimensionParams) =>
    api.get<ScoreDistributionPoint[]>(`/dashboards/score-distribution`, { params: { exam_id: examId, ...dims } }),
  exams:          () => api.get<ExamOut[]>("/dashboards/exams"),
};

// Users (admin)
export const usersApi = {
  list:   ()                            => api.get<UserAdminOut[]>("/users"),
  create: (b: UserCreate)               => api.post<UserAdminOut>("/users", b),
  update: (id: number, b: UserUpdate)   => api.patch<UserAdminOut>(`/users/${id}`, b),
  delete: (id: number)                  => api.delete(`/users/${id}`),
};

// Branches
export const branchesApi = {
  list:   ()                              => api.get<BranchOut[]>("/branches"),
  create: (b: BranchCreate)              => api.post<BranchOut>("/branches", b),
  update: (id: number, b: BranchUpdate)  => api.patch<BranchOut>(`/branches/${id}`, b),
  delete: (id: number)                   => api.delete(`/branches/${id}`),
};

// Topics
export const topicsApi = {
  list:   (subject?: string)            => api.get<TopicOut[]>("/topics", { params: subject ? { subject } : {} }),
  create: (b: TopicCreate)              => api.post<TopicOut>("/topics", b),
  update: (id: number, b: TopicUpdate)  => api.patch<TopicOut>(`/topics/${id}`, b),
  delete: (id: number)                  => api.delete(`/topics/${id}`),
};

// Faculty Sections
export const facultySectionsApi = {
  list:   ()                                => api.get<FacultySectionOut[]>("/faculty-sections"),
  create: (b: FacultySectionCreate)         => api.post<FacultySectionOut>("/faculty-sections", b),
  delete: (id: number)                      => api.delete(`/faculty-sections/${id}`),
};

// Alerts
export const alertsApi = {
  list:      (p: AlertListParams)     => api.get<AlertOut[]>("/alerts", { params: p }),
  ack:       (id: number)              => api.patch(`/alerts/${id}/acknowledge`),
  getConfig: ()                        => api.get<AlertConfigEntry[]>("/alerts/config"),
  setConfig: (ruleKey: string, config: Record<string, unknown>) =>
    api.patch("/alerts/config", config, { params: { rule_key: ruleKey } }),
};

// ── domain types ──────────────────────────────────────────────────────────────

export interface UserMe {
  id: number;
  username: string;
  full_name: string;
  role: "admin" | "dean" | "faculty";
}

export interface StudentOut {
  admission_no: string;
  name: string;
  branch_name: string;
  program_name: string;
  student_class: string;
  section: string;
  dean: string;
  status: string;
  created_at: string;
}

export type StudentDetail = StudentOut;

export interface StudentCreate {
  admission_no:  string;
  name:          string;
  branch_name:   string;
  program_name:  string;
  student_class: string;
  section:       string;
  dean:          string;
  status?:       string;
}

export interface StudentListParams {
  search?:        string;
  branch_name?:   string;
  program_name?:  string;
  section?:       string;
  student_class?: string;
  dean?:          string;
  status?:        string;
  page?:          number;
  page_size?:     number;
}

export interface StudentListResp {
  items: StudentOut[];
  total: number;
  page: number;
  page_size: number;
}

export interface FilterOptions {
  branches: string[];
  programs: string[];
  classes: string[];
  sections: string[];
  deans: string[];
}

export interface UploadJobOut {
  id: number;
  job_type: string;
  exam_id?: number;
  status: "pending" | "processing" | "completed" | "failed";
  total_rows: number;
  processed_rows: number;
  failed_rows: number;
  error_json?: Array<{ row: number; field: string; message: string }>;
  created_at: string;
  completed_at?: string;
}

export interface DashboardOverall {
  exam_name: string;
  exam_date: string;
  total_students: number;
  avg_total: number;
  avg_physics: number;
  avg_chemistry: number;
  avg_maths: number;
  max_total: number;
  min_total: number;
  pass_rate_pct: number;
  branch_comparison: Array<{ branch: string; avg_total: number; student_count: number }>;
  top_students: Array<{ rank: number; name: string; admission_no: string; total: number }>;
  histogram: Array<{ bucket_start: number; bucket_end: number; count: number }>;
}

export interface WeakStudentsDashboard {
  critical_count: number;
  warning_count: number;
  info_count: number;
  students: WeakStudentEntry[];
}

export interface WeakStudentEntry {
  admission_no: string;
  name:        string;
  branch_name: string;
  severity:    "critical" | "warning" | "info";
  alerts:      Array<{ rule_key: string; message: string; context: Record<string, unknown> }>;
  latest_rank?: number;
  latest_total?: number;
}

export interface SubjectDashboard {
  exam_id: number;
  scope: string;
  scope_value: string;
  subjects: SubjectEntry[];
}

export interface SubjectEntry {
  subject: string;
  avg_marks: number;
  avg_accuracy_pct: number;
  median: number | null;
  stdev: number | null;
  min_score: number | null;
  max_score: number | null;
  n_students: number;
  top_students: Array<{ name: string; marks: number; accuracy: number }>;
  bottom_students: Array<{ name: string; marks: number; accuracy: number }>;
}

export interface TopicHeatmapDashboard {
  topics: TopicHeatEntry[];
}

export interface TopicHeatEntry {
  topic_name: string;
  subject: string;
  avg_accuracy_pct: number;
  attempt_rate_pct: number;
  student_count: number;
}

export interface StudentDeepDive {
  student: StudentOut;
  rolling_averages: Array<{
    exam_type:  string;
    avg_score:  number;
    exam_count: number;
    updated_at: string;
  }>;
  exam_history:   Array<{
    exam_id:        number;
    exam_code:      string | null;
    exam_type:      string | null;
    exam_date:      string | null;
    papers:         string[];
    is_absent?:     boolean;
    total_marks:    number;
    max_marks:      number;
    percentage:     number;
    rank_overall:      number | null;
    rank_section:      number | null;
    marks_physics:        number | null;
    max_marks_physics:    number | null;
    rank_physics:         number | null;
    correct_physics:      number | null;
    partial_physics:      number | null;
    wrong_physics:        number | null;
    blank_physics:        number | null;
    negative_physics:     number | null;
    marks_chemistry:      number | null;
    max_marks_chemistry:  number | null;
    rank_chemistry:       number | null;
    correct_chemistry:    number | null;
    partial_chemistry:    number | null;
    wrong_chemistry:      number | null;
    blank_chemistry:      number | null;
    negative_chemistry:   number | null;
    marks_mathematics:    number | null;
    max_marks_mathematics: number | null;
    rank_mathematics:     number | null;
    correct_mathematics:  number | null;
    partial_mathematics:  number | null;
    wrong_mathematics:    number | null;
    blank_mathematics:    number | null;
    negative_mathematics: number | null;
    correct_count:    number;
    partial_count:    number;
    wrong_count:      number;
    blank_count:      number;
    negative_marks:   number;
    topper_physics:     number | null;
    topper_chemistry:   number | null;
    topper_mathematics: number | null;
    avg_physics:        number | null;
    avg_chemistry:      number | null;
    avg_mathematics:    number | null;
    avg_total:          number | null;
    topper_total:       number | null;
    paper_results:      Record<string, { score: number; total_marks: number }>;
    paper_subjects:     Record<string, Record<string, { marks: number; max_marks: number; correct: number; partial: number; wrong: number; blank: number; neg: number }>>;
    paper_benchmarks:   Record<string, Record<string, { avg: number; top: number }>>;
    paper_topics:       Record<string, Array<{ topic: string; subject: string; accuracy: number; attempted: number }>>;
  }>;
  subject_trends: Array<{
    subject: string;
    data:    Array<{ exam_id: number; marks: number; accuracy: number }>;
  }>;
  weak_topics:    Array<{
    topic:    string;
    subject:  string;
    accuracy: number;   // 0–1
    attempted: number;
    exam_id:  number;
  }>;
  rank_trajectory: Array<{ exam_id: number; rank: number | null; percentile: number | null }>;
  active_alerts:   Array<{
    alert_id:    number;
    rule_key:    string;
    severity:    "critical" | "warning" | "info";
    title:       string;
    message:     string;
    exam_id:     number;
    context:     Record<string, unknown>;
  }>;
}

export interface ExamTrendPoint {
  exam_id: number;
  exam_name: string;
  exam_date: string;
  avg_total: number;
  avg_physics: number;
  avg_chemistry: number;
  avg_maths: number;
  total_students: number;
}

export interface ExamOut {
  id:            number;
  exam_code:     string;
  title?:        string;
  exam_date?:    string;
  exam_type?:    string;
  program_name?: string;
  student_class?: string;
  papers:        string[];  // ["P1"] for Mains, ["P1","P2"] for Advanced
  created_at:    string;
}

export interface ExamCreate {
  exam_code:     string;
  title:         string;
  exam_date:     string;            // ISO date "YYYY-MM-DD"
  exam_type:     "Mains" | "Advanced";
  program_name?: string;
  student_class?: string;
}

export interface ExamUpdate {
  title?:         string;
  exam_date?:     string;
  exam_type?:     "Mains" | "Advanced";
  program_name?:  string;
  student_class?: string;
}

export interface QuestionOut {
  id:                 number;
  question_no:        number;
  subject:            string;
  topic:              string | null;
  sub_topic:          string | null;
  question_type:      string;
  positive_marks:     number;
  negative_marks:     number;
  partial_marks:      number;
  correct_option_bkc: string | null;
  is_deleted_bkc:     boolean;
  correct_option_akc: string | null;
  is_deleted_akc:     boolean | null;
  difficulty:         string | null;
  paper_code:         string;
  exam_id:            number;
}

export interface QuestionCreate {
  exam_id:             number;
  paper_code:          string;
  question_no:         number;
  subject:             string;
  topic?:              string | null;
  sub_topic?:          string | null;
  question_type:       string;
  positive_marks?:     number;
  negative_marks?:     number;
  partial_marks?:      number;
  correct_option_bkc?: string | null;
  is_deleted_bkc?:     boolean;
  correct_option_akc?: string | null;
  is_deleted_akc?:     boolean | null;
  difficulty?:         string | null;
}

export interface QuestionUpdate {
  subject?:             string;
  topic?:               string | null;
  sub_topic?:           string | null;
  question_type?:       string;
  positive_marks?:      number;
  negative_marks?:      number;
  partial_marks?:       number;
  correct_option_bkc?:  string | null;
  is_deleted_bkc?:      boolean;
  correct_option_akc?:  string | null;
  is_deleted_akc?:      boolean | null;
  difficulty?:          string | null;
}

export interface LeaderboardEntry {
  rank:           number;
  admission_no:   string;
  name:           string;
  branch_name:    string;
  program_name:   string;
  student_class:  string;
  section:        string;
  total_marks:    number;
  physics_marks:  number;
  chemistry_marks: number;
  maths_marks:    number;
  accuracy_pct:   number;
  negative_marks: number;
  percentile:     number;
}

export interface ScoreDistributionPoint {
  bucket:        number;
  bucket_min:    number;
  bucket_max:    number;
  student_count: number;
}

export interface AlertOut {
  id: number;
  admission_no: string;
  student_name: string;
  exam_id?: number;
  exam_name?: string;
  rule_key: string;
  severity: "critical" | "warning" | "info";
  message: string;
  context: Record<string, unknown>;
  is_acknowledged: boolean;
  acknowledged_at?: string;
  created_at: string;
}

export interface AlertListParams {
  admission_no?: string;
  exam_id?: number;
  severity?: string;
  rule_key?: string;
  acknowledged?: boolean;
}

export interface AlertConfigEntry {
  rule_key: string;
  config: Record<string, unknown>;
}

// ── Master data types ─────────────────────────────────────────────────────────

export interface UserAdminOut {
  id: number;
  username: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface UserCreate {
  username:  string;
  full_name: string;
  role:      string;
  password:  string;
}

export interface UserUpdate {
  full_name?: string;
  role?:      string;
  is_active?: boolean;
  password?:  string;
}

export interface BranchOut {
  id:         number;
  name:       string;
  city:       string | null;
  created_at: string;
}

export interface BranchCreate {
  name: string;
  city?: string;
}

export interface BranchUpdate {
  name?: string;
  city?: string;
}

export interface TopicOut {
  id:      number;
  subject: string;
  name:    string;
}

export interface TopicCreate {
  subject: string;
  name:    string;
}

export interface TopicUpdate {
  name: string;
}

export interface FacultySectionOut {
  id:          number;
  user_id:     number;
  branch_id:   number;
  section:     string;
  username:    string;
  full_name:   string;
  branch_name: string;
}

export interface QuestionResponse {
  question_no:    number;
  paper_code:     string;
  subject:        string;
  topic:          string | null;
  sub_topic:      string | null;
  question_type:  string;
  positive_marks: number;
  negative_marks: number;
  correct_bkc:    string | null;
  is_deleted_bkc: boolean;
  correct_akc:    string | null;
  is_deleted_akc: boolean | null;
  response:       string;
  verdict_bkc:    string;
  marks_bkc:      number | null;
  verdict_akc:    string | null;
  marks_akc:      number | null;
}

export interface FacultySectionCreate {
  user_id:   number;
  branch_id: number;
  section:   string;
}
