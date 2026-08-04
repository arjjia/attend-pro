import { createContext, useContext, useState, type PropsWithChildren } from "react";

import { api, AUTH_STORAGE_KEY } from "../lib/api";
import type { AuthSession, User, UserRole } from "../types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readSession(): AuthSession | null {
  try {
    const value = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!value) return null;
    const session = JSON.parse(value) as AuthSession;
    if (!session.access_token || !session.user || !["student", "lecturer"].includes(session.user.role)) {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      return null;
    }
    return session;
  } catch {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<AuthSession | null>(readSession);

  async function login(email: string, password: string): Promise<User> {
    const { data } = await api.post<AuthSession>("/auth/login", { email, password });
    const normalizedRole = data.user.role.toLowerCase() as UserRole;
    if (normalizedRole !== "student" && normalizedRole !== "lecturer") {
      throw new Error("Для этой роли интерфейс пока недоступен");
    }
    const nextSession = { ...data, user: { ...data.user, role: normalizedRole } };
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(nextSession));
    setSession(nextSession);
    return nextSession.user;
  }

  function logout() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    setSession(null);
  }

  return (
    <AuthContext.Provider value={{ user: session?.user ?? null, token: session?.access_token ?? null, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
