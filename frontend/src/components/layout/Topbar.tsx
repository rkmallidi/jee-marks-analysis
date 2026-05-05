import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

interface Props {
  onMenuClick: () => void;
}

export default function Topbar({ onMenuClick }: Props) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="h-16 shrink-0 bg-white border-b border-surface-200 flex items-center justify-between px-4 gap-4 shadow-sm">
      {/* Menu toggle */}
      <button
        onClick={onMenuClick}
        className={cn("btn-icon btn-ghost text-surface-500")}
        aria-label="Toggle sidebar"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Brand */}
      <div className="flex-1">
        <p className="text-surface-600 text-sm font-medium hidden sm:block">
          JEE Student Performance Intelligence Platform
        </p>
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-2">
        {user && (
          <div className="hidden sm:flex flex-col items-end">
            <span className="text-sm font-medium text-surface-800">{user.full_name}</span>
            <span className="text-xs text-surface-400 capitalize">{user.role}</span>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="btn-secondary btn-sm"
          title="Sign out"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          <span className="hidden sm:inline">Sign out</span>
        </button>
      </div>
    </header>
  );
}
