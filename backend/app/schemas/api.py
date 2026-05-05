from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Shared ─────────────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    row: Optional[int] = None
    column: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    status: Literal["failed"] = "failed"
    error_code: str
    message: str
    errors: list[ErrorDetail] = []


class OkResponse(BaseModel):
    status: Literal["ok"] = "ok"
    message: str = "success"


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[Any]


# ── Auth ───────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(TokenResponse):
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool


# ── Students ───────────────────────────────────────────────────────────────────

VALID_STATUSES = {"active", "inactive", "transferred"}


class StudentCreate(BaseModel):
    admission_no:  str
    name:          str   = Field(min_length=2, max_length=150)
    branch_name:   str
    program_name:  str
    student_class: str
    section:       str   = Field(min_length=1, max_length=10)
    dean:          str
    status:        str   = "active"

    model_config = ConfigDict(populate_by_name=True)


class StudentUpdate(BaseModel):
    name:          Optional[str] = Field(default=None, min_length=2, max_length=150)
    branch_name:   Optional[str] = None
    program_name:  Optional[str] = None
    student_class: Optional[str] = None
    section:       Optional[str] = Field(default=None, min_length=1, max_length=10)
    dean:          Optional[str] = None
    status:        Optional[str] = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    admission_no:  str
    name:          str
    branch_name:   str
    program_name:  str
    student_class: str
    section:       str
    dean:          str
    status:        str
    created_at:    datetime


# ── Upload / Jobs ──────────────────────────────────────────────────────────────

class UploadJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             int
    job_type:       str
    filename:       str
    status:         str
    total_rows:     Optional[int]
    processed_rows: Optional[int]
    failed_rows:    Optional[int]
    error_json:     Optional[list]
    created_at:     datetime
    completed_at:   Optional[datetime]

    @model_validator(mode="before")
    @classmethod
    def _remap(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        return {
            "id":             data.id,
            "job_type":       data.upload_type,
            "filename":       data.filename,
            "status":         data.status,
            "total_rows":     data.total_rows,
            "processed_rows": data.accepted_rows,
            "failed_rows":    data.rejected_rows,
            "error_json":     data.error_json,
            "created_at":     data.created_at,
            "completed_at":   data.completed_at,
        }


# ── Evaluation ─────────────────────────────────────────────────────────────────

class EvaluationResult(BaseModel):
    exam_id:          int
    key_type:         str
    students_graded:  int
    questions_graded: int
    duration_ms:      int


class DryRunResult(BaseModel):
    exam_id:           int
    students_affected: int
    rank_changes:      list[dict[str, Any]]


# ── Dashboard: D1 Overall ──────────────────────────────────────────────────────

class ExamTrendPoint(BaseModel):
    exam_id:    int
    exam_code:  str
    exam_date:  Optional[date]
    avg:        Optional[float]
    median:     Optional[float]
    n_students: int
    physics_avg:     Optional[float]
    chemistry_avg:   Optional[float]
    mathematics_avg: Optional[float]


class BranchComparePoint(BaseModel):
    exam_id:     int
    branch_id:   int
    branch_name: str
    avg:         Optional[float]
    median:      Optional[float]
    n_students:  int


class OverallDashboard(BaseModel):
    exam_trend:      list[ExamTrendPoint]
    branch_compare:  list[BranchComparePoint]
    subject_breakdown: list[dict[str, Any]]
    top_students:    list[dict[str, Any]]


# ── Dashboard: D2 Weak Students ────────────────────────────────────────────────

class WeakStudentRow(BaseModel):
    admission_no:  str
    name:          str
    section:       str
    branch_name:   str
    total_marks:   float
    max_marks:     float
    percentage:    float
    rank_overall:  Optional[int]
    rank_section:  Optional[int]
    severity:      str
    rule_key:      str
    alert_title:   str
    alert_message: str
    alert_id:      int
    acknowledged:  bool


class WeakStudentsDashboard(BaseModel):
    exam_id:       int
    total_flagged: int
    critical:      int
    warning:       int
    info:          int
    students:      list[WeakStudentRow]


# ── Dashboard: D3 Subject Analysis ────────────────────────────────────────────

class SubjectStat(BaseModel):
    subject:      str
    avg:          Optional[float]
    median:       Optional[float]
    stdev:        Optional[float]
    min_score:    Optional[float]
    max_score:    Optional[float]
    n_students:   int
    top_performers:    list[dict[str, Any]]
    bottom_performers: list[dict[str, Any]]


class SubjectDashboard(BaseModel):
    exam_id:     int
    scope:       str
    scope_value: str
    subjects:    list[SubjectStat]


# ── Dashboard: D4 Topic Heatmap ────────────────────────────────────────────────

class TopicHeatmapCell(BaseModel):
    admission_no: str
    name:         str
    topic:        str
    subject:      str
    accuracy:     float
    attempted:    int
    correct:      int


class TopicHeatmapDashboard(BaseModel):
    exam_id:  int
    section:  Optional[str]
    topics:   list[str]
    students: list[dict[str, Any]]
    cells:    list[TopicHeatmapCell]


# ── Dashboard: D5 Student Deep Dive ───────────────────────────────────────────

class StudentDeepDive(BaseModel):
    student:          StudentOut
    exam_history:     list[dict[str, Any]]
    subject_trends:   list[dict[str, Any]]
    topic_heatmap:    list[dict[str, Any]]
    active_alerts:    list[dict[str, Any]]
    rank_trajectory:  list[dict[str, Any]]
    weak_topics:      list[dict[str, Any]] = []
    rolling_averages: list[dict[str, Any]] = []


# ── Alerts ─────────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              int
    admission_no:    str
    student_name:    str
    exam_id:         int
    exam_name:       Optional[str]
    rule_key:        str
    severity:        str
    message:         str
    context:         dict
    is_acknowledged: bool
    acknowledged_at: Optional[datetime]
    created_at:      datetime

    @model_validator(mode="before")
    @classmethod
    def _remap(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        return {
            "id":              data.id,
            "admission_no":    data.admission_no,
            "student_name":    data.student.name if data.student else data.admission_no,
            "exam_id":         data.exam_id,
            "exam_name":       (data.exam.title or data.exam.exam_code) if data.exam else None,
            "rule_key":        data.rule_key,
            "severity":        data.severity,
            "message":         data.message,
            "context":         data.context_json,
            "is_acknowledged": data.acknowledged_at is not None,
            "acknowledged_at": data.acknowledged_at,
            "created_at":      data.created_at,
        }


class AlertConfigOut(BaseModel):
    rule_key: str
    config:   dict[str, Any]


class AlertConfigUpdate(BaseModel):
    config: dict[str, Any]


# ── Users (admin management) ──────────────────────────────────────────────────

class UserCreate(BaseModel):
    username:  str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=100)
    role:      str
    password:  str = Field(min_length=6, max_length=100)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    role:      Optional[str] = None
    is_active: Optional[bool] = None
    password:  Optional[str] = Field(default=None, min_length=6, max_length=100)


class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    username:   str
    full_name:  str
    role:       str
    is_active:  bool
    created_at: datetime


# ── Branches ───────────────────────────────────────────────────────────────────

class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    city: Optional[str] = None


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    city: Optional[str] = None


class BranchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    name:       str
    city:       Optional[str]
    created_at: datetime


# ── Topics ─────────────────────────────────────────────────────────────────────

class TopicCreate(BaseModel):
    subject: str
    name:    str = Field(min_length=1, max_length=200)


class TopicUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:      int
    subject: str
    name:    str


# ── Faculty Sections ───────────────────────────────────────────────────────────

class FacultySectionCreate(BaseModel):
    user_id:   int
    branch_id: int
    section:   str = Field(min_length=1, max_length=10)


class FacultySectionOut(BaseModel):
    id:          int
    user_id:     int
    branch_id:   int
    section:     str
    username:    str
    full_name:   str
    branch_name: str


# ── Exams ──────────────────────────────────────────────────────────────────────

class ExamCreate(BaseModel):
    exam_code:     str                          = Field(min_length=1, max_length=50)
    title:         str                          = Field(min_length=1, max_length=200)
    exam_date:     date
    exam_type:     Literal["Mains", "Advanced"]
    program_name:  Optional[str]                = Field(default=None, max_length=50)
    student_class: Optional[str]                = Field(default=None, max_length=30)


class ExamUpdate(BaseModel):
    title:         Optional[str]                          = Field(default=None, max_length=200)
    exam_date:     Optional[date]                         = None
    exam_type:     Optional[Literal["Mains", "Advanced"]] = None
    program_name:  Optional[str]                          = Field(default=None, max_length=50)
    student_class: Optional[str]                          = Field(default=None, max_length=30)


class ExamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:            int
    exam_code:     str
    title:         Optional[str]
    exam_date:     Optional[date]
    exam_type:     Optional[str]
    program_name:  Optional[str]
    student_class: Optional[str]
    created_at:    datetime
    papers:        list[str] = []

    @model_validator(mode="before")
    @classmethod
    def _extract_papers(cls, data: Any) -> Any:
        """Flatten exam_paper_links relationship into a plain list of codes."""
        if isinstance(data, dict):
            return data
        if hasattr(data, "exam_paper_links"):
            return {
                "id":            data.id,
                "exam_code":     data.exam_code,
                "title":         data.title,
                "exam_date":     data.exam_date,
                "exam_type":     data.exam_type,
                "program_name":  data.program_name,
                "student_class": data.student_class,
                "created_at":    data.created_at,
                "papers":        sorted(ep.paper_code for ep in (data.exam_paper_links or [])),
            }
        return data


# ── Questions ──────────────────────────────────────────────────────────────────

class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  int
    question_no:         int
    subject:             str
    topic:               Optional[str]
    sub_topic:           Optional[str]
    question_type:       str
    positive_marks:      float
    negative_marks:      float
    partial_marks:       float
    correct_option_bkc:  Optional[str]
    is_deleted_bkc:      bool
    correct_option_akc:  Optional[str]
    is_deleted_akc:      Optional[bool]
    difficulty:          Optional[str]
    paper_code:          str
    exam_id:             int

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        ep = getattr(data, "exam_paper", None)
        return {
            "id":                 data.id,
            "question_no":        data.question_no,
            "subject":            data.subject,
            "topic":              data.topic,
            "sub_topic":          data.sub_topic,
            "question_type":      data.question_type,
            "positive_marks":     data.positive_marks,
            "negative_marks":     data.negative_marks,
            "partial_marks":      data.partial_marks,
            "correct_option_bkc": data.correct_option_bkc,
            "is_deleted_bkc":     data.is_deleted_bkc,
            "correct_option_akc": data.correct_option_akc,
            "is_deleted_akc":     data.is_deleted_akc,
            "difficulty":         data.difficulty,
            "paper_code":         ep.paper_code if ep else "",
            "exam_id":            ep.exam_id    if ep else 0,
        }


class QuestionUpdate(BaseModel):
    subject:             Optional[str]   = None
    topic:               Optional[str]   = None
    sub_topic:           Optional[str]   = None
    question_type:       Optional[str]   = None
    positive_marks:      Optional[float] = None
    negative_marks:      Optional[float] = None
    partial_marks:       Optional[float] = None
    correct_option_bkc:  Optional[str]   = None
    is_deleted_bkc:      Optional[bool]  = None
    correct_option_akc:  Optional[str]   = None
    is_deleted_akc:      Optional[bool]  = None
    difficulty:          Optional[str]   = None


class QuestionCreate(BaseModel):
    exam_id:             int
    paper_code:          str
    question_no:         int
    subject:             str
    topic:               Optional[str]   = None
    sub_topic:           Optional[str]   = None
    question_type:       str
    positive_marks:      float           = 4.0
    negative_marks:      float           = 1.0
    partial_marks:       float           = 0.0
    correct_option_bkc:  Optional[str]   = None
    is_deleted_bkc:      bool            = False
    correct_option_akc:  Optional[str]   = None
    is_deleted_akc:      Optional[bool]  = None
    difficulty:          Optional[str]   = None


# ── Results ────────────────────────────────────────────────────────────────────

class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:          int
    student_id:  str
    exam_id:     int
    paper_code:  Optional[str]
    score:       float
    total_marks: float
    result_type: str  # "PAPER" | "CONSOLIDATED"
