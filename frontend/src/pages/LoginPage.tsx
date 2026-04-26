import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  // already logged in
  if (isAuthenticated) {
    navigate("/dashboard/overall", { replace: true });
    return null;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate("/dashboard/overall", { replace: true });
    } catch {
      setError("Invalid username or password. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-950 via-surface-900 to-surface-800 p-4">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-primary-600/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Logo / Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-500 text-white text-3xl font-bold shadow-glow mb-4">
            J
          </div>
          <h1 className="text-2xl font-bold text-white">JEE Analytics</h1>
          <p className="text-surface-400 text-sm mt-1">Student Performance Intelligence Platform</p>
        </div>

        {/* Card */}
        <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-3xl p-8 shadow-2xl">
          <h2 className="text-lg font-semibold text-white mb-6">Sign in to your account</h2>

          {error && (
            <div className="flex items-center gap-2 bg-danger-light/20 border border-danger/40 text-red-300 rounded-xl px-4 py-3 mb-5 text-sm">
              <span>⚠️</span>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="form-group">
              <label className="label text-surface-300">Username</label>
              <input
                type="text"
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input bg-white/10 border-white/20 text-white placeholder-surface-500 focus:border-primary-400 focus:ring-primary-400"
                placeholder="admin"
              />
            </div>

            <div className="form-group">
              <label className="label text-surface-300">Password</label>
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input bg-white/10 border-white/20 text-white placeholder-surface-500 focus:border-primary-400 focus:ring-primary-400"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full btn-lg mt-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-white/10">
            <p className="text-xs text-surface-400 text-center">Demo credentials</p>
            <div className="grid grid-cols-3 gap-2 mt-3">
              {[
                { role: "Admin",   u: "admin",    p: "admin123" },
                { role: "Dean",    u: "dean",     p: "dean123"  },
                { role: "Faculty", u: "faculty1", p: "faculty123" },
              ].map(({ role, u, p }) => (
                <button
                  key={u}
                  type="button"
                  onClick={() => { setUsername(u); setPassword(p); }}
                  className="text-xs bg-white/10 hover:bg-white/20 transition text-surface-300 rounded-xl px-2 py-2 font-medium"
                >
                  {role}
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-surface-500 text-xs mt-6">
          © {new Date().getFullYear()} JEE Analytics Platform
        </p>
      </div>
    </div>
  );
}
