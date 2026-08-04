import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { AUTH_STORAGE_KEY } from "../lib/api";
import type { AuthSession, ScheduleItem } from "../types";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("../lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../lib/api")>();
  return {
    ...original,
    api: { get: mocks.get, post: mocks.post },
  };
});

vi.mock("html5-qrcode", () => ({
  Html5Qrcode: class {
    isScanning = false;
    start = vi.fn().mockResolvedValue(undefined);
    stop = vi.fn().mockResolvedValue(undefined);
    clear = vi.fn();
  },
}));

const scheduleItem: ScheduleItem = {
  id: 42,
  module: "CS-101",
  short_name: "Алгоритмы",
  full_name: "Алгоритмы и структуры данных",
  type: "Лекция",
  form: "Очно",
  group: "РСОДПО-П-МОиАИС-23.01",
  audience: "Б-304",
  capacity: 30,
  equipment: ["Проектор"],
  start_time: "2026-08-04T10:00:00",
  end_time: "2026-08-04T11:30:00",
  duration: "1 п.",
  fact_passed: false,
  lecturers: [{ id: 1, full_name: "Анна Петрова" }],
  students: ["Иванов Иван"],
  active: true,
  attendance_active: true,
  allowed_late_minutes: 10,
  attendance_started_at: "2026-08-04T10:00:00",
  attendance_finished_at: null,
  exit_enabled: false,
};

const studentSession: AuthSession = {
  access_token: "student-token",
  token_type: "bearer",
  user: {
    id: 7,
    email: "student1@test.ru",
    role: "student",
    full_name: "Иванов Иван",
    group: "РСОДПО-П-МОиАИС-23.01",
  },
};

describe("AttendPro application", () => {
  beforeEach(() => {
    mocks.get.mockReset();
    mocks.post.mockReset();
  });

  it("logs a student in and redirects to the student schedule", async () => {
    const user = userEvent.setup();
    mocks.post.mockResolvedValueOnce({ data: studentSession });
    mocks.get.mockResolvedValueOnce({ data: [] });
    window.history.replaceState({}, "", "/login");

    render(<App />);
    expect(screen.getByRole("button", { name: /Преподаватель lecturer@test.ru 123456/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Студент student1@test.ru 123456/i }));
    await user.click(screen.getByRole("button", { name: "Войти" }));

    expect(await screen.findByRole("heading", { name: "Мои занятия" })).toBeInTheDocument();
    expect(screen.getByText("Иванов Иван")).toBeInTheDocument();
    expect(screen.getByText("РСОДПО-П-МОиАИС-23.01")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/student");
    expect(mocks.post).toHaveBeenCalledWith("/auth/login", {
      email: "student1@test.ru",
      password: "123456",
    });
  });

  it("marks attendance using an exact six digit code", async () => {
    const user = userEvent.setup();
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(studentSession));
    window.history.replaceState({}, "", "/student");
    mocks.get.mockResolvedValueOnce({ data: [scheduleItem] });
    mocks.post.mockResolvedValueOnce({
      data: {
        message: "Присутствие сохранено",
        timestamp: "2026-08-04T10:08:00",
        late_minutes: 8,
        credited: true,
        schedule_name: scheduleItem.full_name,
      },
    });

    render(<App />);
    expect(await screen.findByText("1 п.")).toBeInTheDocument();
    expect(screen.queryByText("1 п. мин")).not.toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Отметить присутствие" }));
    const codeInput = screen.getByLabelText("Шестизначный код с экрана преподавателя");
    await user.type(codeInput, "123456");
    await user.click(screen.getByRole("button", { name: "Подтвердить присутствие" }));

    expect(await screen.findByRole("heading", { name: "Присутствие отмечено" })).toBeInTheDocument();
    expect(screen.getByText(/Опоздание: 8 мин/)).toBeInTheDocument();
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith("/student/mark", { schedule_id: 42, code: "123456" }));
  });

  it("does not allow marking before the lecturer opens attendance", async () => {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(studentSession));
    window.history.replaceState({}, "", "/student");
    mocks.get.mockResolvedValueOnce({ data: [{ ...scheduleItem, attendance_active: false }] });

    render(<App />);

    const button = await screen.findByRole("button", { name: "Преподаватель еще не открыл отметку" });
    expect(button).toBeDisabled();
    expect(mocks.post).not.toHaveBeenCalled();
  });
});
