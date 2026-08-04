# AttendPro

MVP системы автоматизированного учёта посещаемости для университета. Студент
отмечается динамическим шестизначным кодом или QR, а преподаватель видит новые
отметки в реальном времени.

## Возможности

- JWT-аутентификация и отдельные интерфейсы студента и преподавателя.
- Расписание на текущую дату с фильтрацией по группе или преподавателю.
- Серверный код с ротацией каждые 15 секунд и QR-кодом.
- Проверка группы, активного занятия и действительности кода.
- Фиксация серверного времени, опоздания и статуса зачёта.
- WebSocket-обновления списка отметившихся.
- История посещаемости студента.
- PostgreSQL, async SQLAlchemy, Alembic и идемпотентные fixtures.
- Адаптивный React-интерфейс и отдельный проекторный виджет.

## Быстрый запуск

Требуются Docker и Docker Compose.

```bash
cp .env.example .env
docker compose up --build
```

После запуска доступны:

- приложение: <http://localhost:3000>
- Swagger UI: <http://localhost:8000/docs>
- проверка API: <http://localhost:8000/health>

Миграции и тестовые данные применяются автоматически при старте backend.
`SEED_DATE` в `.env` позволяет задать дату расписания в формате `YYYY-MM-DD`;
по умолчанию используется текущая дата в Тюмени (UTC+5).

Для полного сброса данных:

```bash
docker compose down -v
```

## Тестовые пользователи

| Роль | Email | Пароль |
| --- | --- | --- |
| Студент | `student1@test.ru` | `123456` |
| Студент | `student2@test.ru` | `123456` |
| Преподаватель | `lecturer@test.ru` | `123456` |
| Преподаватель | `vorobieva@test.ru` | `123456` |

Основное занятие fixtures назначено на 15:55–17:25 по Тюмени. Кнопки начала и
отметки намеренно доступны только внутри интервала занятия.

## Локальная разработка

Backend:

```bash
cd backend
cp .env.example .env
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Frontend в другом терминале:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## Проверки

```bash
cd backend && .venv/bin/pytest -q
cd frontend && npm run typecheck && npm test && npm run build
docker compose config
```

## Структура

- `backend/app/routers` — документированные REST и WebSocket endpoints.
- `backend/app/services` — границы сервисов расписания, кодов и real-time.
- `backend/migrations` — начальная Alembic-миграция.
- `backend/tests` — интеграционные тесты API и WebSocket.
- `frontend/src/pages` — кабинеты, история и проекторный виджет.

Расписание сейчас читается через `ScheduleService` из локальной БД. Этот слой
предназначен для последующей замены источника на Modeus. Динамические коды
хранятся в памяти процесса; для нескольких backend-реплик хранилище необходимо
заменить на Redis.
