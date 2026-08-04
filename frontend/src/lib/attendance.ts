export function parseAttendanceCode(value: string): string | null {
  const normalized = value.trim();
  if (/^\d{6}$/.test(normalized)) return normalized;

  try {
    const code = new URL(normalized).searchParams.get("code");
    return code && /^\d{6}$/.test(code) ? code : null;
  } catch {
    return null;
  }
}
