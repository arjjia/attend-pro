import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { getApiError } from "../lib/api";

const TEST_USERS = [
  { role: "Студент", email: "student1@test.ru", password: "123456" },
  { role: "Преподаватель", email: "lecturer@test.ru", password: "123456" },
] as const;

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to={user.role === "student" ? "/student" : "/lecturer"} replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const loggedInUser = await login(email.trim(), password);
      const requestedPath = (location.state as { from?: string } | null)?.from;
      const rolePath = loggedInUser.role === "student" ? "/student" : "/lecturer";
      const destination = requestedPath?.startsWith(`/${loggedInUser.role}`) ? requestedPath : rolePath;
      navigate(destination, { replace: true });
    } catch (requestError) {
      setError(getApiError(requestError, "Неверная почта или пароль"));
    } finally {
      setSubmitting(false);
    }
  }

  function useTestUser(emailValue: string, passwordValue: string) {
    setEmail(emailValue);
    setPassword(passwordValue);
    setError("");
  }

  return (
    <main className="login-page">
      <section className="login-intro" aria-labelledby="login-brand-title">
        <div className="login-brand"><span>AP</span> AttendPro</div>
        <p className="eyebrow">Университетская среда</p>
        <h1 id="login-brand-title">Отмечайтесь на занятиях без лишней переклички.</h1>
        <p>Расписание, код присутствия и история посещений в одном спокойном рабочем пространстве.</p>
        <div className="academic-rule"><span>01</span><i /><span>Присутствие</span></div>
      </section>
      <section className="login-panel" aria-labelledby="login-title">
        <form className="login-form" onSubmit={handleSubmit}>
          <p className="eyebrow">Личный кабинет</p>
          <h2 id="login-title">Вход в AttendPro</h2>
          <label>
            Университетская почта
            <input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" required />
          </label>
          <label>
            Пароль
            <input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button wide" type="submit" disabled={submitting}>{submitting ? "Входим…" : "Войти"}</button>
        </form>
        <div className="test-users">
          <h3>Тестовый доступ</h3>
          {TEST_USERS.map((testUser) => (
            <button key={testUser.role} type="button" onClick={() => useTestUser(testUser.email, testUser.password)}>
              <b>{testUser.role}</b>
              <span>{testUser.email}</span>
              <code>{testUser.password}</code>
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}
