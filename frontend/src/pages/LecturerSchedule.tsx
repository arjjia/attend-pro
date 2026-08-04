import { useCallback, useEffect, useState } from "react";

import { ErrorState, LoadingState } from "../components/LoadingState";
import { ScheduleCard } from "../components/ScheduleCard";
import { api, getApiError } from "../lib/api";
import { formatDate } from "../lib/format";
import type { ScheduleItem } from "../types";

interface StartConfig {
  allowedLateMinutes: number;
  exitEnabled: boolean;
}

export function LecturerSchedule() {
  const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
  const [configs, setConfigs] = useState<Record<string, StartConfig>>({});
  const [startingId, setStartingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");

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

  function updateConfig(id: string, displayedConfig: StartConfig, patch: Partial<StartConfig>) {
    setConfigs((current) => ({ ...current, [id]: { ...(current[id] || displayedConfig), ...patch } }));
  }

  function openWidget(item: ScheduleItem) {
    setActionError("");
    const id = String(item.id);
    const popup = window.open("", `attendpro-${id}`, "popup=yes,width=1180,height=760,resizable=yes,scrollbars=yes");
    if (!popup) {
      setActionError("Браузер заблокировал окно виджета. Разрешите всплывающие окна для AttendPro.");
      return;
    }
    popup.document.title = "AttendPro — запуск занятия";
    popup.document.body.innerHTML = '<p style="font:18px system-ui;padding:32px;color:#173b57">Запускаем занятие…</p>';

    const target = new URL(`/lecturer/attendance/${encodeURIComponent(id)}`, window.location.origin).toString();
    if (item.attendance_active) {
      popup.location.assign(target);
      return;
    }

    const config = configs[id] || {
      allowedLateMinutes: item.allowed_late_minutes,
      exitEnabled: item.exit_enabled,
    };
    setStartingId(id);
    void api.post(`/lecturer/start/${encodeURIComponent(id)}`, {
      allowed_late_minutes: config.allowedLateMinutes,
      exit_enabled: config.exitEnabled,
    }).then(() => {
      popup.location.assign(target);
      setSchedule((current) => current.map((entry) => entry.id === item.id ? {
        ...entry,
        attendance_active: true,
        attendance_started_at: new Date().toISOString(),
      } : entry));
    }).catch((requestError) => {
      popup.close();
      setActionError(getApiError(requestError, "Не удалось запустить отметку посещаемости"));
    }).finally(() => setStartingId(null));
  }

  return (
    <>
      <header className="page-heading">
        <div><p className="eyebrow">Рабочий день</p><h1>Расписание преподавателя</h1></div>
        <time>{formatDate(new Date().toISOString())}</time>
      </header>
      {actionError && <div className="inline-alert" role="alert">{actionError}</div>}
      {loading ? <LoadingState label="Загружаем занятия" /> : error ? <ErrorState message={error} retry={loadSchedule} /> : schedule.length === 0 ? (
        <div className="empty-state"><span>Нет пар</span><h2>На сегодня занятий нет</h2></div>
      ) : (
        <div className="schedule-list lecturer-list">
          {schedule.map((item) => {
            const id = String(item.id);
            const config = configs[id] || {
              allowedLateMinutes: item.allowed_late_minutes,
              exitEnabled: item.exit_enabled,
            };
            const sessionOpen = item.attendance_active;
            return (
              <ScheduleCard key={item.id} item={item} showRoster>
                <div className="session-config" aria-label="Настройки занятия">
                  <label>
                    Допустимое опоздание
                    <span><input type="number" min="0" max="180" value={config.allowedLateMinutes} disabled={!item.active || sessionOpen} onChange={(event) => updateConfig(id, config, { allowedLateMinutes: Math.max(0, Number(event.target.value)) })} /> мин</span>
                  </label>
                  <label className="checkbox-label">
                    <input type="checkbox" checked={config.exitEnabled} disabled={!item.active || sessionOpen} onChange={(event) => updateConfig(id, config, { exitEnabled: event.target.checked })} />
                    Разрешить отметку выхода
                    <small>Подготовка для учета времени ухода</small>
                  </label>
                </div>
                <button className="primary-button" type="button" disabled={!item.active || item.fact_passed || startingId === id} onClick={() => openWidget(item)}>
                  {startingId === id ? "Запускаем…" : sessionOpen ? "Открыть виджет" : item.active ? "Начать занятие" : "Доступно во время занятия"}
                </button>
              </ScheduleCard>
            );
          })}
        </div>
      )}
    </>
  );
}
