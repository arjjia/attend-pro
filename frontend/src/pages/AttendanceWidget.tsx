import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { api, attendanceWebSocketUrl, getApiError } from "../lib/api";
import { formatTime } from "../lib/format";
import type { AttendanceRecord, CodeResponse, ScheduleItem } from "../types";

export function AttendanceWidget() {
  const { scheduleId = "" } = useParams();
  const { token, logout } = useAuth();
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState<ScheduleItem | null>(null);
  const [code, setCode] = useState<CodeResponse | null>(null);
  const [expiresAt, setExpiresAt] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [connection, setConnection] = useState<"connecting" | "online" | "offline">("connecting");
  const [error, setError] = useState("");
  const [stopped, setStopped] = useState(false);
  const [stopping, setStopping] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadInitialData() {
      try {
        const [scheduleResponse, attendanceResponse] = await Promise.all([
          api.get<ScheduleItem[]>("/schedule/current"),
          api.get<AttendanceRecord[]>(`/lecturer/attendance/${encodeURIComponent(scheduleId)}`),
        ]);
        if (!cancelled) {
          setSchedule(scheduleResponse.data.find((item) => String(item.id) === scheduleId) || null);
          setAttendance(attendanceResponse.data);
        }
      } catch (requestError) {
        if (!cancelled) setError(getApiError(requestError, "Не удалось загрузить данные занятия"));
      }
    }
    void loadInitialData();
    return () => { cancelled = true; };
  }, [scheduleId]);

  useEffect(() => {
    if (stopped) return;
    let cancelled = false;
    async function refreshCode() {
      try {
        const { data } = await api.get<CodeResponse>(`/lecturer/code/${encodeURIComponent(scheduleId)}`);
        if (!cancelled) {
          setCode(data);
          setExpiresAt(Date.now() + Math.max(0, data.expires_in) * 1000);
          setError("");
        }
      } catch (requestError) {
        if (!cancelled) setError(getApiError(requestError, "Код временно недоступен"));
      }
    }
    void refreshCode();
    const refreshTimer = window.setInterval(() => void refreshCode(), 5_000);
    return () => { cancelled = true; window.clearInterval(refreshTimer); };
  }, [scheduleId, stopped]);

  useEffect(() => {
    if (!expiresAt || stopped) return;
    function tick() { setSecondsLeft(Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000))); }
    tick();
    const timer = window.setInterval(tick, 250);
    return () => window.clearInterval(timer);
  }, [expiresAt, stopped]);

  useEffect(() => {
    if (!token || stopped) return;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;
    let disposed = false;

    function connect() {
      if (disposed) return;
      setConnection("connecting");
      socket = new WebSocket(attendanceWebSocketUrl(scheduleId, token as string));
      socket.onopen = () => setConnection("online");
      socket.onmessage = (event) => {
        try {
          const payload: unknown = JSON.parse(event.data);
          if (Array.isArray(payload)) setAttendance(payload as AttendanceRecord[]);
          else if (payload && typeof payload === "object" && "attendance" in payload && Array.isArray((payload as { attendance: unknown }).attendance)) {
            setAttendance((payload as { attendance: AttendanceRecord[] }).attendance);
          }
        } catch {
          // A malformed update should not interrupt subsequent WebSocket messages.
        }
      };
      socket.onerror = () => setConnection("offline");
      socket.onclose = () => {
        if (!disposed) {
          setConnection("offline");
          reconnectTimer = window.setTimeout(connect, 2_000);
        }
      };
    }
    connect();
    return () => {
      disposed = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [scheduleId, stopped, token]);

  async function stopAttendance() {
    if (!window.confirm("Завершить отметку посещаемости? Текущий код перестанет работать.")) return;
    setStopping(true);
    setError("");
    try {
      await api.post(`/lecturer/stop/${encodeURIComponent(scheduleId)}`);
      setStopped(true);
      setSecondsLeft(0);
    } catch (requestError) {
      setError(getApiError(requestError, "Не удалось завершить занятие"));
    } finally {
      setStopping(false);
    }
  }

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  const qrSource = code?.qr_code ? (code.qr_code.startsWith("data:") ? code.qr_code : `data:image/png;base64,${code.qr_code}`) : "";
  const capacity = schedule?.capacity || schedule?.students?.length || 0;
  const percentage = capacity ? Math.min(100, Math.round(attendance.length / capacity * 100)) : 0;

  return (
    <main className={`widget-page ${stopped ? "is-stopped" : ""}`}>
      <header className="widget-header">
        <div className="widget-brand"><span>AP</span><b>AttendPro</b></div>
        <div className="widget-title">
          <p>{schedule?.short_name || schedule?.module || "Текущее занятие"}</p>
          <h1>{schedule?.full_name || "Отметка посещаемости"}</h1>
        </div>
        <div className="widget-place">
          <b>{schedule?.audience || "Аудитория"}</b>
          <span>{schedule ? `${formatTime(schedule.start_time)}–${formatTime(schedule.end_time)}` : ""}</span>
        </div>
      </header>

      {stopped ? (
        <section className="stopped-state">
          <span>Занятие завершено</span>
          <h2>Отметка присутствия закрыта</h2>
          <p>Всего отметились: <b>{attendance.length}</b>{capacity ? ` из ${capacity}` : ""}</p>
          <button className="secondary-button" type="button" onClick={() => window.close()}>Закрыть окно</button>
        </section>
      ) : (
        <div className="widget-grid">
          <section className="code-stage" aria-label="Код присутствия">
            <p className="eyebrow">Введите в приложении</p>
            <div className="giant-code" aria-label={`Код ${code?.code || "загружается"}`}>{code?.code || "••••••"}</div>
            <div className="code-meta">
              <span className={`countdown ${secondsLeft <= 5 ? "urgent" : ""}`}><i style={{ "--progress": `${Math.max(0, Math.min(100, secondsLeft / Math.max(1, code?.expires_in || 15) * 100))}%` } as React.CSSProperties} />Новый код через <b>{secondsLeft} сек</b></span>
              <span className={`connection ${connection}`}><i />{connection === "online" ? "Данные обновляются" : connection === "connecting" ? "Подключение…" : "Переподключение…"}</span>
            </div>
            {error && <div className="widget-error" role="alert">{error}</div>}
          </section>

          <aside className="qr-stage">
            <div className="qr-frame">{qrSource ? <img src={qrSource} alt="QR-код присутствия" /> : <span className="qr-placeholder">QR</span>}</div>
            <p>Наведите камеру телефона</p>
          </aside>

          <section className="attendance-stage">
            <header>
              <div><p className="eyebrow">В аудитории</p><h2>{attendance.length}<small>{capacity ? ` / ${capacity}` : ""}</small></h2></div>
              <div className="attendance-meter" aria-label={`${percentage}% группы отметилось`}><i style={{ width: `${percentage}%` }} /></div>
            </header>
            <div className="attendance-list" aria-live="polite">
              {attendance.length === 0 ? <p className="attendance-empty">Ждем первые отметки…</p> : attendance.map((record, index) => (
                <div className="attendance-person" key={record.id || record.student_id || `${record.full_name}-${index}`}>
                  <span>{index + 1}</span>
                  <div>
                    <b>{record.student_name || record.full_name || record.name || "Студент"}</b>
                    <small>{[record.group, attendanceRecordStatus(record)].filter(Boolean).join(" · ")}</small>
                  </div>
                  <time>{formatTime(record.timestamp || record.marked_at)}</time>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      <footer className="widget-footer">
        <span>Идентификатор занятия: {scheduleId}</span>
        {!stopped && <button className="stop-button" type="button" onClick={stopAttendance} disabled={stopping}>{stopping ? "Завершаем…" : "Завершить занятие"}</button>}
        <button className="widget-logout" type="button" onClick={handleLogout}>Выйти из аккаунта</button>
      </footer>
    </main>
  );
}

function attendanceRecordStatus(record: AttendanceRecord): string {
  const timing = record.late_minutes !== undefined && record.late_minutes > 0
    ? `Опоздание ${record.late_minutes} мин`
    : "Вовремя";
  return `${timing} · ${record.credited ? "зачтено" : "не зачтено"}`;
}
