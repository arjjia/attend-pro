import axios from "axios";

import type { AuthSession } from "../types";

export const AUTH_STORAGE_KEY = "attendpro.auth";
export const API_URL = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

export const api = axios.create({
  baseURL: API_URL,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  try {
    const rawSession = localStorage.getItem(AUTH_STORAGE_KEY);
    const session = rawSession ? (JSON.parse(rawSession) as AuthSession) : null;
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }
  } catch {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }
  return config;
});

export function getApiError(error: unknown, fallback = "Не удалось выполнить запрос"): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    const message = error.response?.data?.message;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item?.msg).filter(Boolean).join("; ") || fallback;
    }
    if (typeof message === "string") return message;
    if (error.code === "ECONNABORTED") return "Сервер не ответил вовремя";
    if (!error.response) return "Нет связи с сервером";
  }
  return error instanceof Error && error.message ? error.message : fallback;
}

export function attendanceWebSocketUrl(scheduleId: string, token: string): string {
  const base = new URL(API_URL || "/api", window.location.origin);
  const protocol = base.protocol === "https:" ? "wss:" : "ws:";
  const prefix = base.pathname.replace(/\/$/, "");
  return `${protocol}//${base.host}${prefix}/ws/attendance/${encodeURIComponent(scheduleId)}?token=${encodeURIComponent(token)}`;
}
