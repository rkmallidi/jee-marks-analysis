import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { studentsApi, StudentOut, StudentCreate } from "@/lib/api";

interface EditStudentModalProps {
  student: StudentOut | null;
  isOpen: boolean;
  onClose: () => void;
}

export function EditStudentModal({ student, isOpen, onClose }: EditStudentModalProps) {
  const qc = useQueryClient();
  const [formData, setFormData] = useState<Partial<StudentCreate>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (student && isOpen) {
      setFormData({
        name: student.name,
        branch_name: student.branch_name,
        program_name: student.program_name,
        student_class: student.student_class,
        section: student.section,
        dean: student.dean,
        status: student.status,
      });
      setError(null);
    }
  }, [student, isOpen]);

  const updateMut = useMutation({
    mutationFn: () => {
      if (!student) throw new Error("No student selected");
      return studentsApi.update(student.admission_no, formData);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["students"] });
      if (student) {
        qc.invalidateQueries({ queryKey: ["student", student.admission_no] });
      }
      setError(null);
      onClose();
    },
    onError: (err: any) => {
      setError(err.response?.data?.message || "Update failed");
    },
  });

  if (!isOpen || !student) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg p-6 w-full max-w-md">
        <h2 className="text-lg font-semibold mb-4">Edit Student</h2>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              Admission No
            </label>
            <input
              type="text"
              disabled
              value={student.admission_no}
              className="input w-full bg-surface-100 text-surface-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              Name
            </label>
            <input
              type="text"
              value={formData.name || ""}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="input w-full py-2"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-sm font-medium text-surface-700 mb-1">
                Branch
              </label>
              <input
                type="text"
                value={formData.branch_name || ""}
                onChange={(e) => setFormData({ ...formData, branch_name: e.target.value })}
                className="input w-full py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-700 mb-1">
                Program
              </label>
              <input
                type="text"
                value={formData.program_name || ""}
                onChange={(e) => setFormData({ ...formData, program_name: e.target.value })}
                className="input w-full py-2"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-sm font-medium text-surface-700 mb-1">
                Class
              </label>
              <input
                type="text"
                value={formData.student_class || ""}
                onChange={(e) => setFormData({ ...formData, student_class: e.target.value })}
                className="input w-full py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-700 mb-1">
                Section
              </label>
              <input
                type="text"
                value={formData.section || ""}
                onChange={(e) => setFormData({ ...formData, section: e.target.value })}
                className="input w-full py-2"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              Dean
            </label>
            <input
              type="text"
              value={formData.dean || ""}
              onChange={(e) => setFormData({ ...formData, dean: e.target.value })}
              className="input w-full py-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              Status
            </label>
            <select
              value={formData.status || ""}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="input w-full py-2"
            >
              <option value="">Select status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>

        <div className="flex gap-2 justify-end mt-6">
          <button
            onClick={onClose}
            disabled={updateMut.isPending}
            className="btn-ghost"
          >
            Cancel
          </button>
          <button
            onClick={() => updateMut.mutate()}
            disabled={updateMut.isPending}
            className="btn-primary"
          >
            {updateMut.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
