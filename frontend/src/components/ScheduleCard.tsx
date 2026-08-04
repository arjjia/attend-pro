import type { PropsWithChildren } from "react";

import { equipmentLabel, formatTime, lecturerNames } from "../lib/format";
import type { ScheduleItem } from "../types";

interface ScheduleCardProps extends PropsWithChildren {
  item: ScheduleItem;
  showRoster?: boolean;
}

export function ScheduleCard({ item, showRoster = true, children }: ScheduleCardProps) {
  const status = item.fact_passed ? "Завершено" : item.active ? "Идет сейчас" : "По расписанию";
  const statusClass = item.fact_passed ? "finished" : item.active ? "active" : "planned";

  return (
    <article className={`schedule-card ${item.active ? "is-active" : ""}`}>
      <div className="schedule-time" aria-label={`Время ${formatTime(item.start_time)} — ${formatTime(item.end_time)}`}>
        <strong>{formatTime(item.start_time)}</strong>
        <span>{formatTime(item.end_time)}</span>
        <small>{item.duration || ""}</small>
      </div>
      <div className="schedule-body">
        <div className="schedule-kicker">
          <span className={`status-chip ${statusClass}`}>{status}</span>
          <span>{[item.type, item.form].filter(Boolean).join(" · ")}</span>
        </div>
        <h2>{item.full_name || item.short_name}</h2>
        {item.short_name && item.short_name !== item.full_name && <p className="short-name">{item.short_name} · {item.module}</p>}
        <dl className="schedule-facts">
          <div><dt>Аудитория</dt><dd>{item.audience || "Не указана"}</dd></div>
          <div><dt>Группа</dt><dd>{item.group || "Не указана"}</dd></div>
          <div><dt>Преподаватель</dt><dd>{lecturerNames(item.lecturers || [])}</dd></div>
          <div><dt>Оснащение</dt><dd>{equipmentLabel(item.equipment)}</dd></div>
          <div><dt>Вместимость</dt><dd>{item.capacity ? `${item.capacity} мест` : "Не указана"}</dd></div>
        </dl>
        {showRoster && (
          <details className="roster">
            <summary>Список группы <span>{item.students?.length || 0}</span></summary>
            {item.students?.length ? (
              <ol>{item.students.map((student, index) => <li key={`${student}-${index}`}>{student}</li>)}</ol>
            ) : <p>Список студентов пока пуст.</p>}
          </details>
        )}
        {children && <div className="schedule-actions">{children}</div>}
      </div>
    </article>
  );
}
