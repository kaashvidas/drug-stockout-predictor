import { createContext, useContext, useState, type ReactNode } from "react";
import type { AuthState } from "../types";

interface AuthContextValue {
  auth: AuthState | null;
  login: (auth: AuthState) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function loadStoredAuth(): AuthState | null {
  const token = localStorage.getItem("sc_token");
  const role = localStorage.getItem("sc_role");
  const scope = localStorage.getItem("sc_scope");
  const displayName = localStorage.getItem("sc_display_name");
  const username = localStorage.getItem("sc_username");
  if (token && role && scope && displayName && username) {
    return { token, role: role as AuthState["role"], scope, displayName, username };
  }
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(loadStoredAuth());

  const login = (next: AuthState) => {
    localStorage.setItem("sc_token", next.token);
    localStorage.setItem("sc_role", next.role);
    localStorage.setItem("sc_scope", next.scope);
    localStorage.setItem("sc_display_name", next.displayName);
    localStorage.setItem("sc_username", next.username);
    setAuth(next);
  };

  const logout = () => {
    localStorage.removeItem("sc_token");
    localStorage.removeItem("sc_role");
    localStorage.removeItem("sc_scope");
    localStorage.removeItem("sc_display_name");
    localStorage.removeItem("sc_username");
    setAuth(null);
  };

  return <AuthContext.Provider value={{ auth, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
