import { useCallback, useEffect, useState, type FormEvent } from "react";

import { ErrorState, LoadingState } from "../components/LoadingState";
import { Modal } from "../components/Modal";
import { QrScanner } from "../components/QrScanner";
import { ScheduleCard } from "../components/ScheduleCard";
import { api, getApiError } from "../lib/api";
import { formatDate } from "../lib/format";
import type { MarkResult, ScheduleItem } from "../types";

export function StudentDashboard() {
  const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<ScheduleItem | null>(null);

  const loadSchedule = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<ScheduleItem[]>("/schedule/current");
      setSchedule(data);
    } catch (requestError) {
      setError(getApiError(requestError, "Не удалось загрузить расписание"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadSchedule(); }, [loadSchedule]);

  return (
    <>
      <header className="page-heading">
        <div><p className="eyebrow">Расписание на сегодня</p><h1>Мои занятия</h1></div>
        <time>{formatDate(new Date().toISOString())}</time>
      </header>
      {loading ? <LoadingState label="Загружаем расписание" /> : error ? <ErrorState message={error} retry={loadSchedule} /> : schedule.length === 0 ? (
        <div className="empty-state"><span>Свободный день</span><h2>На сегодня занятий нет</h2><p>Можно заглянуть в историю посещений.</p></div>
      ) : (
        <div className="schedule-list">
          {schedule.map((item) => (
            <ScheduleCard key={item.id} item={item}>
              <button className="primary-button" type="button" disabled={!item.active || !item.attendance_active || item.fact_passed} onClick={() => setSelected(item)}>
                {item.fact_passed
                  ? "Занятие завершено"
                  : !item.active
                    ? "Занятие еще не началось"
                    : item.attendance_active
                      ? "Отметить присутствие"
                      : "Преподаватель еще не открыл отметку"}
              </button>
            </ScheduleCard>
          ))}
        </div>
      )}
      {selected && <MarkModal schedule={selected} onClose={() => setSelected(null)} />}
    </>
  );
}

function MarkModal({ schedule, onClose }: { schedule: ScheduleItem; onClose: () => void }) {
  const [code, setCode] = useState("");
  const [scannerOpen, setScannerOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<MarkResult | null>(null);

  const handleScannedCode = useCallback((value: string) => {
    setCode(value);
    setScannerOpen(false);
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!/^\d{6}$/.test(code)) {
      setError("Введите ровно 6 цифр");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const { data } = await api.post<MarkResult>("/student/mark", { schedule_id: schedule.id, code });
      setResult(data);
      setScannerOpen(false);
    } catch (requestError) {
      setError(getApiError(requestError, "Код не принят. Проверьте цифры и попробуйте еще раз"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title={result ? "Присутствие отмечено" : "Код присутствия"} onClose={onClose}>
      {result ? (
        <div className="mark-result">
          <span className={`result-seal ${result.credited ? "success" : "warning"}`}>{result.credited ? "✓" : "!"}</span>
          <h3>{result.message || "Отметка сохранена"}</h3>
          <p>{result.schedule_name || schedule.full_name}</p>
          {result.late_minutes > 0 && (
            <div className="late-warning" role="status">
              Опоздание: {result.late_minutes} мин. {result.credited ? "Присутствие зачтено." : "Присутствие не зачтено."}
            </div>
          )}
          <p className="muted">Время отметки: {formatDate(result.timestamp, true)}</p>
          <button className="primary-button wide" type="button" onClick={onClose}>Готово</button>
        </div>
      ) : (
        <form className="mark-form" onSubmit={submit}>
          <p className="modal-context">{schedule.full_name}<br /><b>{schedule.audience}</b></p>
          <label htmlFor="attendance-code">Шестизначный код с экрана преподавателя</label>
          <input
            id="attendance-code"
            className="code-input"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            value={code}
            onChange={(event) => { setCode(event.target.value.replace(/\D/g, "").slice(0, 6)); setError(""); }}
            placeholder="000000"
            aria-describedby={error ? "mark-error" : undefined}
            autoFocus
          />
          {error && <p id="mark-error" className="field-error" role="alert">{error}</p>}
          <button className="scanner-toggle" type="button" onClick={() => setScannerOpen((value) => !value)} aria-expanded={scannerOpen}>
            {scannerOpen ? "Закрыть камеру" : "Сканировать QR-код"}
          </button>
          {scannerOpen && <QrScanner onCode={handleScannedCode} />}
          <button className="primary-button wide" type="submit" disabled={submitting || code.length !== 6}>
            {submitting ? "Проверяем…" : "Подтвердить присутствие"}
          </button>
        </form>
      )}
    </Modal>
  );
}
