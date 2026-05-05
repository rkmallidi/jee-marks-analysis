import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";

interface NavItem {
  label: string;
  to: string;
  icon: string;
  roles?: string[];
}

const NAV: Array<{ group: string; items: NavItem[] }> = [
  {
    group: "Dashboards",
    items: [
      { label: "Overview",       to: "/dashboard/overall",       icon: "📊" },
      { label: "Weak Students",  to: "/dashboard/weak-students", icon: "🚨" },
      { label: "Subject Analysis",to: "/dashboard/subjects",     icon: "📐" },
      { label: "Topic Heatmap",  to: "/dashboard/topics",        icon: "🔥" },
      { label: "Leaderboard",    to: "/dashboard/leaderboard",   icon: "🏆" },
    ],
  },
  {
    group: "Management",
    items: [
      { label: "Students",       to: "/students", icon: "👥" },
      { label: "Exams",          to: "/exams",     icon: "📝", roles: ["admin"] },
      { label: "Questions",      to: "/questions", icon: "❓", roles: ["admin"] },
      { label: "Upload Console", to: "/uploads",   icon: "📤", roles: ["admin", "faculty"] },
      { label: "Alerts",         to: "/alerts",   icon: "🔔" },
      { label: "Settings",       to: "/settings", icon: "⚙️", roles: ["admin"] },
    ],
  },
];

interface Props {
  open: boolean;
  onToggle: () => void;
}

export default function Sidebar({ open }: Props) {
  const { user } = useAuth();

  return (
    <aside
      className={cn(
        "flex flex-col bg-surface-900 text-white transition-all duration-300 ease-in-out shrink-0",
        open ? "w-60" : "w-16",
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-surface-700 shrink-0">
        <div className="w-8 h-8 rounded-xl bg-primary-500 flex items-center justify-center text-white font-bold text-sm shrink-0">
          J
        </div>
        {open && (
          <div className="overflow-hidden">
            <p className="text-sm font-bold text-white leading-tight">JEE Analytics</p>
            <p className="text-xs text-surface-400 leading-tight">Platform</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-6">
        {NAV.map((section) => (
          <div key={section.group}>
            {open && (
              <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-surface-500">
                {section.group}
              </p>
            )}
            <ul className="space-y-0.5">
              {section.items
                .filter((item) => !item.roles || item.roles.includes(user?.role ?? ""))
                .map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors duration-150",
                          isActive
                            ? "bg-primary-600 text-white shadow-glow"
                            : "text-surface-300 hover:bg-surface-800 hover:text-white",
                          !open && "justify-center",
                        )
                      }
                      title={!open ? item.label : undefined}
                    >
                      <span className="text-base shrink-0">{item.icon}</span>
                      {open && <span className="truncate">{item.label}</span>}
                    </NavLink>
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* User badge */}
      {user && (
        <div
          className={cn(
            "px-3 py-4 border-t border-surface-700",
            open ? "flex items-center gap-3" : "flex justify-center",
          )}
        >
          <div className="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
            {user.full_name.charAt(0).toUpperCase()}
          </div>
          {open && (
            <div className="overflow-hidden">
              <p className="text-sm font-medium text-white truncate">{user.full_name}</p>
              <p className="text-xs text-surface-400 capitalize">{user.role}</p>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
