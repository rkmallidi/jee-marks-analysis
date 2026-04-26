import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  usersApi, branchesApi, facultySectionsApi, alertsApi,
  UserAdminOut, UserCreate, UserUpdate,
  BranchOut, BranchCreate,
  FacultySectionOut, FacultySectionCreate,
  AlertConfigEntry,
} from "@/lib/api";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import ErrorBanner from "@/components/ui/ErrorBanner";

type Tab = "users" | "branches" | "alert-config" | "faculty-sections";

const TABS: { id: Tab; label: string }[] = [
  { id: "users",            label: "Users" },
  { id: "branches",         label: "Branches" },
  { id: "alert-config",     label: "Alert Config" },
  { id: "faculty-sections", label: "Faculty Sections" },
];

const ROLES = ["admin", "dean", "faculty"];

// ── shared modal shell ────────────────────────────────────────────────────────

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-200">
          <h3 className="text-base font-semibold text-surface-900">{title}</h3>
          <button onClick={onClose} className="text-surface-400 hover:text-surface-700 text-xl leading-none">&times;</button>
        </div>
        <div className="px-6 py-5 space-y-4">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-surface-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

const input = "w-full border border-surface-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500";
const btn   = "px-4 py-2 text-sm font-medium rounded-lg";
const btnPrimary = `${btn} bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50`;
const btnGhost   = `${btn} border border-surface-300 text-surface-600 hover:bg-surface-100`;
const btnDanger  = `${btn} bg-red-600 text-white hover:bg-red-700`;

// ── Users tab ─────────────────────────────────────────────────────────────────

function UsersTab() {
  const qc = useQueryClient();
  const [modal, setModal] = useState<"add" | "edit" | null>(null);
  const [editing, setEditing] = useState<UserAdminOut | null>(null);
  const [form, setForm] = useState<UserCreate>({ username: "", full_name: "", role: "faculty", password: "" });
  const [editForm, setEditForm] = useState<UserUpdate>({});
  const [err, setErr] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["settings-users"],
    queryFn: () => usersApi.list().then(r => r.data),
  });

  const createMut = useMutation({
    mutationFn: () => usersApi.create(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["settings-users"] }); setModal(null); setErr(null); },
    onError: (e: any) => setErr(e.response?.data?.message ?? "Failed to create user"),
  });

  const updateMut = useMutation({
    mutationFn: () => usersApi.update(editing!.id, editForm),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["settings-users"] }); setModal(null); setErr(null); },
    onError: (e: any) => setErr(e.response?.data?.message ?? "Failed to update user"),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => usersApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings-users"] }),
  });

  const openEdit = (u: UserAdminOut) => {
    setEditing(u);
    setEditForm({ full_name: u.full_name, role: u.role, is_active: u.is_active });
    setErr(null);
    setModal("edit");
  };

  if (isLoading) return <PageLoader />;
  if (isError)   return <ErrorBanner message="Failed to load users" />;

  return (
    <div>
      <div className="flex justify-end mb-4">
        <button className={btnPrimary} onClick={() => { setForm({ username: "", full_name: "", role: "faculty", password: "" }); setErr(null); setModal("add"); }}>
          + Add User
        </button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-surface-200">
        <table className="min-w-full text-sm">
          <thead className="bg-surface-50 text-surface-500 text-xs uppercase tracking-wide">
            <tr>
              {["Username", "Full Name", "Role", "Status", "Actions"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-100">
            {data?.map(u => (
              <tr key={u.id} className="hover:bg-surface-50">
                <td className="px-4 py-3 font-mono text-xs">{u.username}</td>
                <td className="px-4 py-3">{u.full_name}</td>
                <td className="px-4 py-3 capitalize">{u.role}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${u.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                    {u.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-4 py-3 flex gap-2">
                  <button className={btnGhost} onClick={() => openEdit(u)}>Edit</button>
                  <button className={btnDanger} onClick={() => deleteMut.mutate(u.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modal === "add" && (
        <Modal title="Add User" onClose={() => setModal(null)}>
          {err && <p className="text-sm text-red-600">{err}</p>}
          <Field label="Username">
            <input className={input} value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
          </Field>
          <Field label="Full Name">
            <input className={input} value={form.full_name} onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} />
          </Field>
          <Field label="Role">
            <select className={input} value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
              {ROLES.map(r => <option key={r} value={r} className="capitalize">{r}</option>)}
            </select>
          </Field>
          <Field label="Password">
            <input className={input} type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
          </Field>
          <div className="flex justify-end gap-3 pt-2">
            <button className={btnGhost} onClick={() => setModal(null)}>Cancel</button>
            <button className={btnPrimary} disabled={createMut.isPending} onClick={() => createMut.mutate()}>
              {createMut.isPending ? "Saving..." : "Create"}
            </button>
          </div>
        </Modal>
      )}

      {modal === "edit" && editing && (
        <Modal title={`Edit — ${editing.username}`} onClose={() => setModal(null)}>
          {err && <p className="text-sm text-red-600">{err}</p>}
          <Field label="Full Name">
            <input className={input} value={editForm.full_name ?? ""} onChange={e => setEditForm(f => ({ ...f, full_name: e.target.value }))} />
          </Field>
          <Field label="Role">
            <select className={input} value={editForm.role ?? ""} onChange={e => setEditForm(f => ({ ...f, role: e.target.value }))}>
              {ROLES.map(r => <option key={r} value={r} className="capitalize">{r}</option>)}
            </select>
          </Field>
          <Field label="Status">
            <select className={input} value={editForm.is_active ? "active" : "inactive"} onChange={e => setEditForm(f => ({ ...f, is_active: e.target.value === "active" }))}>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </Field>
          <Field label="New Password (leave blank to keep)">
            <input className={input} type="password" placeholder="••••••" onChange={e => setEditForm(f => ({ ...f, password: e.target.value || undefined }))} />
          </Field>
          <div className="flex justify-end gap-3 pt-2">
            <button className={btnGhost} onClick={() => setModal(null)}>Cancel</button>
            <button className={btnPrimary} disabled={updateMut.isPending} onClick={() => updateMut.mutate()}>
              {updateMut.isPending ? "Saving..." : "Save"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Branches tab ──────────────────────────────────────────────────────────────

function BranchesTab() {
  const qc = useQueryClient();
  const [modal, setModal] = useState<"add" | "edit" | null>(null);
  const [editing, setEditing] = useState<BranchOut | null>(null);
  const [form, setForm] = useState<BranchCreate>({ name: "", city: "" });
  const [err, setErr] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["settings-branches"],
    queryFn: () => branchesApi.list().then(r => r.data),
  });

  const createMut = useMutation({
    mutationFn: () => branchesApi.create({ name: form.name, city: form.city || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["settings-branches"] }); setModal(null); setErr(null); },
    onError: (e: any) => setErr(e.response?.data?.message ?? "Failed to create branch"),
  });

  const updateMut = useMutation({
    mutationFn: () => branchesApi.update(editing!.id, { name: form.name, city: form.city || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["settings-branches"] }); setModal(null); setErr(null); },
    onError: (e: any) => setErr(e.response?.data?.message ?? "Failed to update branch"),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => branchesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings-branches"] }),
  });

  const openAdd  = () => { setForm({ name: "", city: "" }); setErr(null); setModal("add"); };
  const openEdit = (b: BranchOut) => { setEditing(b); setForm({ name: b.name, city: b.city ?? "" }); setErr(null); setModal("edit"); };

  if (isLoading) return <PageLoader />;
  if (isError)   return <ErrorBanner message="Failed to load branches" />;

  return (
    <div>
      <div className="flex justify-end mb-4">
        <button className={btnPrimary} onClick={openAdd}>+ Add Branch</button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-surface-200">
        <table className="min-w-full text-sm">
          <thead className="bg-surface-50 text-surface-500 text-xs uppercase tracking-wide">
            <tr>
              {["Name", "City", "Actions"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-100">
            {data?.map(b => (
              <tr key={b.id} className="hover:bg-surface-50">
                <td className="px-4 py-3 font-medium">{b.name}</td>
                <td className="px-4 py-3 text-surface-500">{b.city ?? "—"}</td>
                <td className="px-4 py-3 flex gap-2">
                  <button className={btnGhost} onClick={() => openEdit(b)}>Edit</button>
                  <button className={btnDanger} onClick={() => deleteMut.mutate(b.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(modal === "add" || modal === "edit") && (
        <Modal title={modal === "add" ? "Add Branch" : `Edit — ${editing?.name}`} onClose={() => setModal(null)}>
          {err && <p className="text-sm text-red-600">{err}</p>}
          <Field label="Name">
            <input className={input} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          </Field>
          <Field label="City (optional)">
            <input className={input} value={form.city ?? ""} onChange={e => setForm(f => ({ ...f, city: e.target.value }))} />
          </Field>
          <div className="flex justify-end gap-3 pt-2">
            <button className={btnGhost} onClick={() => setModal(null)}>Cancel</button>
            <button
              className={btnPrimary}
              disabled={createMut.isPending || updateMut.isPending}
              onClick={() => modal === "add" ? createMut.mutate() : updateMut.mutate()}
            >
              {(createMut.isPending || updateMut.isPending) ? "Saving..." : "Save"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Alert Config tab ──────────────────────────────────────────────────────────

const ALERT_LABELS: Record<string, Record<string, string>> = {
  performance_drop:  { drop_threshold_pct: "Drop Threshold (%)", lookback_exams: "Lookback Exams" },
  weak_topic:        { accuracy_threshold_pct: "Accuracy Threshold (%)", min_attempts: "Min Attempts" },
  below_branch_avg:  { deviation_pct: "Deviation (%)", min_exams: "Min Exams" },
  consistently_low:  { percentile_threshold: "Percentile Threshold", consecutive_exams: "Consecutive Exams" },
};

function AlertConfigTab() {
  const qc = useQueryClient();
  const [localConfigs, setLocalConfigs] = useState<Record<string, Record<string, number>> | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["settings-alert-config"],
    queryFn: () => alertsApi.getConfig().then(r => r.data),
  });

  useEffect(() => {
    if (!data) return;
    const map: Record<string, Record<string, number>> = {};
    data.forEach((c: AlertConfigEntry) => { map[c.rule_key] = { ...(c.config as Record<string, number>) }; });
    setLocalConfigs(map);
  }, [data]);

  const saveMut = useMutation({
    mutationFn: (ruleKey: string) =>
      alertsApi.setConfig(ruleKey, localConfigs![ruleKey] as Record<string, unknown>),
    onSuccess: (_, ruleKey) => {
      qc.invalidateQueries({ queryKey: ["settings-alert-config"] });
      setSaved(ruleKey);
      setTimeout(() => setSaved(null), 2000);
    },
  });

  if (isLoading || !localConfigs) return <PageLoader />;
  if (isError) return <ErrorBanner message="Failed to load alert config" />;

  return (
    <div className="space-y-6 max-w-2xl">
      {data?.map((entry: AlertConfigEntry) => {
        const labels = ALERT_LABELS[entry.rule_key] ?? {};
        const cfg    = localConfigs[entry.rule_key] ?? {};
        return (
          <div key={entry.rule_key} className="border border-surface-200 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-semibold text-surface-800 capitalize">
                {entry.rule_key.replace(/_/g, " ")}
              </h4>
              <button
                className={btnPrimary}
                disabled={saveMut.isPending}
                onClick={() => saveMut.mutate(entry.rule_key)}
              >
                {saved === entry.rule_key ? "Saved" : "Save"}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(cfg).map(([key, val]) => (
                <Field key={key} label={labels[key] ?? key}>
                  <input
                    className={input}
                    type="number"
                    value={val}
                    onChange={e => setLocalConfigs(prev => ({
                      ...prev!,
                      [entry.rule_key]: { ...prev![entry.rule_key], [key]: Number(e.target.value) },
                    }))}
                  />
                </Field>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Faculty Sections tab ──────────────────────────────────────────────────────

function FacultySectionsTab() {
  const qc = useQueryClient();
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState<FacultySectionCreate>({ user_id: 0, branch_id: 0, section: "" });
  const [err, setErr] = useState<string | null>(null);

  const { data: sections, isLoading: secLoading, isError: secError } = useQuery({
    queryKey: ["settings-faculty-sections"],
    queryFn: () => facultySectionsApi.list().then(r => r.data),
  });

  const { data: users } = useQuery({
    queryKey: ["settings-users"],
    queryFn: () => usersApi.list().then(r => r.data),
  });

  const { data: branches } = useQuery({
    queryKey: ["settings-branches"],
    queryFn: () => branchesApi.list().then(r => r.data),
  });

  const facultyUsers = users?.filter(u => u.role === "faculty") ?? [];

  const createMut = useMutation({
    mutationFn: () => facultySectionsApi.create(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["settings-faculty-sections"] }); setModal(false); setErr(null); },
    onError: (e: any) => setErr(e.response?.data?.message ?? "Failed to create assignment"),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => facultySectionsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings-faculty-sections"] }),
  });

  const openAdd = () => {
    setForm({ user_id: facultyUsers[0]?.id ?? 0, branch_id: branches?.[0]?.id ?? 0, section: "" });
    setErr(null);
    setModal(true);
  };

  if (secLoading) return <PageLoader />;
  if (secError)   return <ErrorBanner message="Failed to load faculty sections" />;

  return (
    <div>
      <div className="flex justify-end mb-4">
        <button className={btnPrimary} onClick={openAdd}>+ Assign Section</button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-surface-200">
        <table className="min-w-full text-sm">
          <thead className="bg-surface-50 text-surface-500 text-xs uppercase tracking-wide">
            <tr>
              {["Faculty", "Branch", "Section", "Actions"].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-100">
            {sections?.map((fs: FacultySectionOut) => (
              <tr key={fs.id} className="hover:bg-surface-50">
                <td className="px-4 py-3">{fs.full_name} <span className="text-surface-400 text-xs">(@{fs.username})</span></td>
                <td className="px-4 py-3">{fs.branch_name}</td>
                <td className="px-4 py-3 font-mono text-xs">{fs.section}</td>
                <td className="px-4 py-3">
                  <button className={btnDanger} onClick={() => deleteMut.mutate(fs.id)}>Remove</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modal && (
        <Modal title="Assign Faculty to Section" onClose={() => setModal(false)}>
          {err && <p className="text-sm text-red-600">{err}</p>}
          <Field label="Faculty User">
            <select className={input} value={form.user_id} onChange={e => setForm(f => ({ ...f, user_id: Number(e.target.value) }))}>
              {facultyUsers.map(u => <option key={u.id} value={u.id}>{u.full_name} (@{u.username})</option>)}
            </select>
          </Field>
          <Field label="Branch">
            <select className={input} value={form.branch_id} onChange={e => setForm(f => ({ ...f, branch_id: Number(e.target.value) }))}>
              {branches?.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </Field>
          <Field label="Section">
            <input className={input} placeholder="e.g. J1" value={form.section} onChange={e => setForm(f => ({ ...f, section: e.target.value }))} />
          </Field>
          <div className="flex justify-end gap-3 pt-2">
            <button className={btnGhost} onClick={() => setModal(false)}>Cancel</button>
            <button className={btnPrimary} disabled={createMut.isPending} onClick={() => createMut.mutate()}>
              {createMut.isPending ? "Saving..." : "Assign"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Page shell ────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("users");

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-surface-900 mb-6">Settings</h1>

      <div className="flex gap-1 mb-6 border-b border-surface-200">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={[
              "px-4 py-2.5 text-sm font-medium rounded-t-lg -mb-px border-b-2 transition-colors",
              activeTab === t.id
                ? "border-primary-600 text-primary-700"
                : "border-transparent text-surface-500 hover:text-surface-800",
            ].join(" ")}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div>
        {activeTab === "users"            && <UsersTab />}
        {activeTab === "branches"         && <BranchesTab />}
        {activeTab === "alert-config"     && <AlertConfigTab />}
        {activeTab === "faculty-sections" && <FacultySectionsTab />}
      </div>
    </div>
  );
}
