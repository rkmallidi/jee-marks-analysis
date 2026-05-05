import { useContext } from "react";
import { AuthContext, AuthState } from "@/context/AuthContext";

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
