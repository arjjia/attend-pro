export type UserRole = "student" | "lecturer";

export interface User {
  id: number | string;
  email: string;
  role: UserRole;
  full_name: string;
  group: string | null;
}

export interface AuthSession {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Lecturer {
  id: number | string;
  full_name?: string;
  name?: string;
}

export interface ScheduleItem {
  id: number | string;
  module: string;
  short_name: string;
  full_name: string;
  type: string;
  form: string;
  group: string;
  audience: string;
  capacity: number;
  equipment: string | string[] | null;
  start_time: string;
  end_time: string;
  duration: string;
  fact_passed: boolean;
  lecturers: Lecturer[];
  students: string[];
  active: boolean;
  attendance_active: boolean;
  allowed_late_minutes: number;
  attendance_started_at: string | null;
  attendance_finished_at: string | null;
  exit_enabled: boolean;
}

export interface MarkResult {
  message: string;
  timestamp: string;
  late_minutes: number;
  credited: boolean;
  schedule_name: string;
}

export interface HistoryItem extends Partial<MarkResult> {
  id?: number | string;
  schedule_id?: number | string;
  module?: string;
  short_name?: string;
  full_name?: string;
  start_time?: string;
  audience?: string;
}

export interface CodeResponse {
  code: string;
  qr_code: string;
  expires_in: number;
}

export interface AttendanceRecord {
  id?: number | string;
  student_id?: number | string;
  student_name?: string;
  full_name?: string;
  name?: string;
  group?: string;
  timestamp?: string;
  marked_at?: string;
  late_minutes?: number;
  credited: boolean;
}
