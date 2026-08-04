export function formatTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (!Number.isNaN(date.getTime())) {
    return new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" }).format(date);
  }
  return value.slice(0, 5);
}

export function formatDate(value?: string | null, includeTime = false): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

export function lecturerNames(lecturers: Array<{ full_name?: string; name?: string }>): string {
  return lecturers.map((item) => item.full_name || item.name).filter(Boolean).join(", ") || "Не указан";
}

export function equipmentLabel(equipment: string | string[] | null): string {
  if (Array.isArray(equipment)) return equipment.join(", ") || "Не указано";
  return equipment || "Не указано";
}
