/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // ── primary brand (indigo) ─────────────────────────────────────
        primary: {
          50:  "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
          950: "#1e1b4b",
        },
        // ── surface / neutral ──────────────────────────────────────────
        surface: {
          50:  "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
          950: "#020617",
        },
        // ── semantic ───────────────────────────────────────────────────
        success:  { DEFAULT: "#22c55e", light: "#dcfce7", dark: "#15803d" },
        warning:  { DEFAULT: "#f59e0b", light: "#fef3c7", dark: "#b45309" },
        danger:   { DEFAULT: "#ef4444", light: "#fee2e2", dark: "#b91c1c" },
        info:     { DEFAULT: "#3b82f6", light: "#dbeafe", dark: "#1d4ed8" },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        card:  "0 1px 3px 0 rgb(0 0 0 / .1), 0 1px 2px -1px rgb(0 0 0 / .1)",
        "card-hover": "0 4px 6px -1px rgb(0 0 0 / .1), 0 2px 4px -2px rgb(0 0 0 / .1)",
        glow:  "0 0 20px -5px rgb(99 102 241 / .5)",
      },
    },
  },
  plugins: [],
};
