/**
 * Student Management – paginated table with search, filters, and inline upload
 */
import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { studentsApi, StudentOut } from "@/lib/api";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import EmptyState from "@/components/ui/EmptyState";
import { EditStudentModal } from "@/components/ui/EditStudentModal";

const PAGE_SIZE = 20;

export default function StudentsPage() {
  const qc = useQueryClient();

  const [search, setSearch]           = useState("");
  const [debouncedSearch, setDbSearch]= useState("");
  const [branchName, setBranchName]   = useState("");
  const [section, setSection]         = useState("");
  const [page, setPage]               = useState(1);
  const [downloadFormat, setDownloadFormat] = useState<"csv" | "xlsx">("csv");
  const [editingStudent, setEditingStudent] = useState<StudentOut | null>(null);

  const searchTimer = useRef<ReturnType<typeof setTimeout>>();
  const handleSearch = (v: string) => {
    setSearch(v);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => { setDbSearch(v); setPage(1); }, 350);
  };

  const [uploadPct, setUploadPct] = useState<number | null>(null);
  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["students", debouncedSearch, branchName, section, page],
    queryFn: () =>
      studentsApi
        .list({
          search:      debouncedSearch || undefined,
          branch_name: branchName || undefined,
          section:     section || undefined,
          page,
          page_size: PAGE_SIZE,
        })
        .then((r) => r.data),
  });

  const uploadMut = useMutation({
    mutationFn: (file: File) =>
      studentsApi.bulkUpload(file, (pct) => setUploadPct(pct)),
    onSuccess: (response: any) => {
      setUploadPct(null);
      // Check if upload actually succeeded (UploadJob.status === "completed")
      if (response.status === "completed") {
        qc.invalidateQueries({ queryKey: ["students"] });
        setUploadErr(null);
      } else {
        // Validation failed - show detailed errors grouped by row
        const errors = response.error_json || [];
        if (errors.length > 0) {
          // Group errors by row
          const errorsByRow: Record<number, Array<{column: string; message: string}>> = {};
          errors.forEach((e: any) => {
            if (!errorsByRow[e.row]) errorsByRow[e.row] = [];
            errorsByRow[e.row].push({ column: e.column, message: e.message });
          });

          // Format error message showing all rows with issues
          const errorLines = Object.entries(errorsByRow)
            .sort(([rowA], [rowB]) => parseInt(rowA) - parseInt(rowB))
            .map(([row, rowErrors]) => {
              const issues = rowErrors
                .map((e: any) => `${e.column}: ${e.message}`)
                .join(" | ");
              return `Row ${row}: ${issues}`;
            });

          setUploadErr("Validation failed:\n\n" + errorLines.join("\n"));
        } else {
          setUploadErr("Upload failed due to validation errors.");
        }
      }
    },
    onError: (err: any) => {
      setUploadPct(null);
      const message = err.response?.data?.message || "Upload failed. Please check the file format and try again.";
      setUploadErr(message);
    },
  });

  const downloadMut = useMutation({
    mutationFn: () =>
      studentsApi.export({
        search:      debouncedSearch || undefined,
        branch_name: branchName || undefined,
        format:      downloadFormat,
      }),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a   = document.createElement("a");
      a.href     = url;
      a.download = `students.${downloadFormat}`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;
  const hasFilters = search || branchName || section;

  return (
    <div className="space-y-6">
      <EditStudentModal
        student={editingStudent!}
        isOpen={!!editingStudent}
        onClose={() => setEditingStudent(null)}
      />
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Students</h1>
          <p className="text-surface-500 text-sm mt-0.5">
            {data ? `${data.total.toLocaleString()} students` : "Loading…"}
          </p>
        </div>
        <div className="flex gap-2">
          <input
            type="file"
            accept=".xlsx,.csv"
            ref={fileRef}
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) { setUploadErr(null); uploadMut.mutate(f); }
            }}
          />
          <select
            value={downloadFormat}
            onChange={(e) => setDownloadFormat(e.target.value as "csv" | "xlsx")}
            className="input w-auto py-1.5 btn-sm"
          >
            <option value="csv">CSV</option>
            <option value="xlsx">Excel</option>
          </select>
          <button
            onClick={() => downloadMut.mutate()}
            disabled={downloadMut.isPending || !data || data.items.length === 0}
            className="btn-secondary btn-sm"
          >
            {downloadMut.isPending ? "Downloading…" : "Download"}
          </button>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploadMut.isPending}
            className="btn-secondary btn-sm"
          >
            Bulk Upload
          </button>
        </div>
      </div>

      {/* Upload progress */}
      {uploadPct !== null && (
        <div className="card py-3">
          <div className="flex items-center gap-3 text-sm text-surface-700 mb-2">
            <span className="font-medium">Uploading… {uploadPct}%</span>
          </div>
          <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
            <div className="h-full bg-primary-500 rounded-full transition-all" style={{ width: `${uploadPct}%` }} />
          </div>
        </div>
      )}
      {uploadErr && (
        <div className="card bg-red-50 border border-red-200 p-4 max-h-96 overflow-y-auto">
          <div className="text-sm font-semibold text-red-900 mb-2">⚠️ Upload Validation Errors</div>
          <div className="text-xs text-red-800 whitespace-pre-wrap font-mono">{uploadErr}</div>
        </div>
      )}

      {/* Filters */}
      <div className="card py-3 flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="Search name or admission no…"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="input flex-1 min-w-[200px] py-1.5"
        />
        <input
          type="text"
          placeholder="Branch…"
          value={branchName}
          onChange={(e) => { setBranchName(e.target.value); setPage(1); }}
          className="input w-40 py-1.5"
        />
        <input
          type="text"
          placeholder="Section…"
          value={section}
          onChange={(e) => { setSection(e.target.value); setPage(1); }}
          className="input w-32 py-1.5"
        />
        {hasFilters && (
          <button
            onClick={() => {
              setSearch(""); setDbSearch(""); setBranchName(""); setSection(""); setPage(1);
            }}
            className="btn-ghost btn-sm text-surface-400"
          >
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <PageLoader />
      ) : isError ? (
        <ErrorBanner onRetry={refetch} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState icon="👥" title="No students found" description="Try adjusting your filters or upload a student file." />
      ) : (
        <>
          <div className="card overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Admission No</th>
                    <th>Name</th>
                    <th>Branch</th>
                    <th>Program</th>
                    <th>Class</th>
                    <th>Section</th>
                    <th>Dean</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((s) => (
                    <StudentRow key={s.admission_no} student={s} onEdit={setEditingStudent} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm text-surface-500">
            <span>
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.total)} of {data.total}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="btn-secondary btn-sm disabled:opacity-40"
              >
                ← Prev
              </button>
              <span className="px-3 py-1.5 bg-surface-100 rounded-xl font-medium text-surface-700">
                {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="btn-secondary btn-sm disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StudentRow({ student: s, onEdit }: { student: StudentOut; onEdit: (s: StudentOut) => void }) {
  return (
    <tr>
      <td className="font-mono text-xs text-surface-500">{s.admission_no}</td>
      <td>
        <Link to={`/students/${s.admission_no}`} className="font-medium text-surface-800 hover:text-primary-600">
          {s.name}
        </Link>
      </td>
      <td className="text-sm">{s.branch_name}</td>
      <td className="text-sm">{s.program_name}</td>
      <td className="text-sm">{s.student_class}</td>
      <td className="text-sm">{s.section}</td>
      <td className="text-sm">{s.dean}</td>
      <td className="flex gap-2">
        <button
          onClick={() => onEdit(s)}
          className="btn-ghost btn-sm text-amber-600 hover:bg-amber-50"
        >
          Edit
        </button>
        <Link to={`/students/${s.admission_no}`} className="btn-ghost btn-sm text-primary-600">
          View →
        </Link>
      </td>
    </tr>
  );
}
