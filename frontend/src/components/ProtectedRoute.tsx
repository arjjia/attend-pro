import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import type { UserRole } from "../types";

export function ProtectedRoute({ role }: { role: UserRole }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (user.role !== role) return <Navigate to={user.role === "student" ? "/student" : "/lecturer"} replace />;
  return <Outlet />;
}

export function RoleRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "student" ? "/student" : "/lecturer"} replace />;
}
