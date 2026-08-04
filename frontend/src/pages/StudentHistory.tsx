import { useCallback, useEffect, useState } from "react";

import { ErrorState, LoadingState } from "../components/LoadingState";
import { api, getApiError } from "../lib/api";
import { formatDate } from "../lib/format";
import type { HistoryItem } from "../types";

export function StudentHistory() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<HistoryItem[]>("/student/history");
      setHistory(data);
    } catch (requestError) {
      setError(getApiError(requestError, "Не удалось загрузить историю"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadHistory(); }, [loadHistory]);

  return (
    <>
      <header className="page-heading"><div><p className="eyebrow">Личный архив</p><h1>История посещений</h1></div></header>
      {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={loadHistory} /> : history.length === 0 ? (
        <div className="empty-state"><span>Чистый лист</span><h2>Отметок пока нет</h2><p>После первого занятия здесь появится запись.</p></div>
      ) : (
        <div className="history-table-wrap">
          <table className="history-table">
            <thead><tr><th>Занятие</th><th>Дата и время</th><th>Аудитория</th><th>Опоздание</th><th>Статус</th></tr></thead>
            <tbody>{history.map((item, index) => (
              <tr key={item.id || `${item.schedule_id}-${item.timestamp}-${index}`}>
                <td><b>{item.schedule_name || item.full_name || item.short_name || item.module || "Занятие"}</b></td>
                <td>{formatDate(item.timestamp || item.start_time, true)}</td>
                <td>{item.audience || "—"}</td>
                <td>{item.late_minutes ? `${item.late_minutes} мин` : "Нет"}</td>
                <td><span className={`history-status ${item.credited === false ? "missed" : "credited"}`}>{item.credited === false ? "Не зачтено" : "Зачтено"}</span></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </>
  );
}
