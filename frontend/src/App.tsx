import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import { AppShell } from "./components/AppShell";
import { ProtectedRoute, RoleRedirect } from "./components/ProtectedRoute";
import { AttendanceWidget } from "./pages/AttendanceWidget";
import { LecturerSchedule } from "./pages/LecturerSchedule";
import { LoginPage } from "./pages/LoginPage";
import { StudentDashboard } from "./pages/StudentDashboard";
import { StudentHistory } from "./pages/StudentHistory";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<RoleRedirect />} />

          <Route element={<ProtectedRoute role="student" />}>
            <Route element={<AppShell role="student" />}>
              <Route path="/student" element={<StudentDashboard />} />
              <Route path="/student/history" element={<StudentHistory />} />
            </Route>
          </Route>

          <Route element={<ProtectedRoute role="lecturer" />}>
            <Route path="/lecturer/attendance/:scheduleId" element={<AttendanceWidget />} />
            <Route element={<AppShell role="lecturer" />}>
              <Route path="/lecturer" element={<LecturerSchedule />} />
              <Route path="/lecturer/schedule" element={<LecturerSchedule />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
