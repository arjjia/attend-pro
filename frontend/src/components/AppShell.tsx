import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function AppShell({ role }: { role: "student" | "lecturer" }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const links = role === "student"
    ? [{ to: "/student", label: "Сегодня", end: true }, { to: "/student/history", label: "История", end: false }]
    : [{ to: "/lecturer", label: "Расписание", end: false }];

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-frame">
      <header className="site-header">
        <NavLink className="wordmark" to="/" aria-label="AttendPro, на главную">
          <span className="wordmark-mark">AP</span>
          <span>AttendPro</span>
        </NavLink>
        <nav className="main-nav" aria-label="Основная навигация">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} className={({ isActive }) => isActive ? "active" : ""}>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="user-menu">
          <span className="user-copy"><b>{user?.full_name}</b><small>{user?.group || (role === "student" ? "Студент" : "Преподаватель")}</small></span>
          <button className="text-button" type="button" onClick={handleLogout}>Выйти</button>
        </div>
      </header>
      <main className="page-wrap"><Outlet /></main>
    </div>
  );
}
