# AttendPro MVP: реализация, запуск и тестирование

Этот документ описывает текущее состояние MVP AttendPro, используемый стек,
архитектуру, способы запуска и полный набор автоматических и ручных проверок.

Все команды ниже выполняются из корня проекта, если явно не указана другая
директория:

```text
/Users/masha/src/github.com/arjjia/src/Submodules/attend-pro
```

## 1. Что реализовано

### 1.1. Общий сценарий

1. Пользователь входит по тестовой почте и паролю.
2. Backend возвращает JWT access token и роль пользователя.
3. Студент видит расписание своей группы на выбранную дату.
4. Преподаватель видит только назначенные ему занятия.
5. Во время активного занятия преподаватель запускает отметку.
6. Backend создаёт шестизначный код и QR-код, действующие 15 секунд.
7. Виджет преподавателя регулярно получает актуальный код.
8. Студент вводит код вручную или сканирует QR камерой.
9. Backend проверяет JWT, группу, время занятия, состояние сессии и код.
10. Отметка записывается с серверным timestamp и числом минут опоздания.
11. Виджет преподавателя получает обновлённый список через WebSocket.
12. После остановки сессии код удаляется и больше не принимается.

### 1.2. Функции студента

- Авторизация по email и паролю.
- Автоматическое перенаправление в кабинет своей роли.
- Расписание на текущую дату только для группы студента.
- Подробные карточки занятий: модуль, название, тип, форма, аудитория,
  преподаватели, время, оснащение, вместимость и список группы.
- Кнопка отметки только для активного занятия с запущенной преподавателем
  сессией посещаемости.
- Ввод шестизначного кода.
- Сканирование QR через `html5-qrcode`.
- Разбор как простого цифрового значения, так и ссылки вида
  `attendpro://mark?schedule_id=1&code=123456`.
- Сообщение об успешной отметке, точном времени и опоздании.
- Незачтённая, но сохранённая отметка при превышении допустимого опоздания.
- История всех отметок со статусом зачёта.
- Защита от повторной отметки на одном занятии.

### 1.3. Функции преподавателя

- Расписание только назначенных преподавателю занятий.
- Настройка допустимого опоздания от 0 до 180 минут.
- Переключатель будущего режима отметки выхода. Сам выход в MVP не реализован.
- Запуск отметки только во время активного занятия.
- Открытие виджета в отдельном popup-окне.
- Крупный шестизначный код, QR-код и обратный отсчёт.
- Автоматическое получение нового кода после истечения 15 секунд.
- Список отметившихся с временем и опозданием.
- Обновление списка через WebSocket без перезагрузки.
- Индикатор состояния WebSocket и прогресс заполнения аудитории.
- Остановка сессии и немедленная инвалидизация кода.

### 1.4. Backend и данные

- Асинхронные FastAPI endpoints.
- JWT Bearer-аутентификация.
- Хеширование тестовых паролей через bcrypt.
- Ролевая авторизация `student` и `lecturer`.
- SQLAlchemy 2 async models и PostgreSQL `timestamp with time zone`.
- Alembic-миграция начальной схемы.
- Идемпотентный seed: повторный запуск не создаёт дубликаты.
- Серверное вычисление активности занятия и опоздания.
- In-memory хранилище кодов с ротацией 15 секунд.
- PNG QR-код в виде data URI, сгенерированный библиотекой `qrcode`.
- Комнаты WebSocket по `schedule_id`.
- Уникальность отметки по студенту, занятию и типу `entry`.
- `ScheduleService` как граница будущей интеграции с Modeus.
- Swagger/OpenAPI генерируется FastAPI автоматически.

### 1.5. Тестовые данные

| Роль | Email | Пароль | Имя | Группа |
| --- | --- | --- | --- | --- |
| Студент | `student1@test.ru` | `123456` | Иванов Иван | РСОДПО-П-МОиАИС-23.01 |
| Студент | `student2@test.ru` | `123456` | Петров Пётр | РСОДПО-П-МОиАИС-23.01 |
| Преподаватель | `lecturer@test.ru` | `123456` | Мельникова Антонина Владимировна | нет |
| Преподаватель | `vorobieva@test.ru` | `123456` | Воробьева Марина Сергеевна | нет |

Seed создаёт два занятия на текущую дату в Тюмени или на дату из `SEED_DATE`:

| Занятие | Время UTC+5 | Аудитория | Преподаватели |
| --- | --- | --- | --- |
| Разработка интерфейса пользователя. Практическое занятие | 15:55–17:25 | Главный корпус / 209 | Мельникова А.В., Воробьева М.С. |
| Аттестация по программе МОиАИС | 17:40–19:10 | Главный корпус / 209 | Мельникова А.В. |

В первом занятии сохранён список из 24 студентов.

## 2. Технологический стек

### Backend

| Назначение | Технология |
| --- | --- |
| Язык | Python 3.10+ |
| Package manager | uv 0.9.16, `uv.lock` |
| HTTP API | FastAPI |
| ASGI server | Uvicorn |
| ORM | SQLAlchemy 2 async |
| PostgreSQL driver | asyncpg |
| Миграции | Alembic |
| Валидация и настройки | Pydantic 2, pydantic-settings |
| JWT | PyJWT |
| Пароли | bcrypt |
| QR | qrcode + Pillow |
| Real-time | FastAPI WebSocket |
| Тесты | pytest, pytest-asyncio, HTTPX, aiosqlite |

### Frontend

| Назначение | Технология |
| --- | --- |
| UI | React 18 |
| Язык | TypeScript |
| Сборка | Vite |
| Маршрутизация | React Router |
| HTTP | Axios |
| QR-сканер | html5-qrcode |
| Unit/component tests | Vitest, React Testing Library, jsdom |
| Browser E2E | Playwright |
| Production web server | nginx |

### Инфраструктура

| Компонент | Технология |
| --- | --- |
| База данных | `postgres:latest` |
| Контейнеризация | Docker, Docker Compose |
| Frontend image | Node 22 build + nginx 1.27 |
| Backend image | Python 3.12 slim |

## 3. Структура проекта

```text
attend-pro/
├── backend/
│   ├── app/
│   │   ├── routers/       REST и WebSocket endpoints
│   │   ├── services/      расписание, коды, attendance, WebSocket hub
│   │   ├── models.py      SQLAlchemy models
│   │   ├── schemas.py     Pydantic API schemas
│   │   ├── security.py    JWT и bcrypt
│   │   └── seed.py        тестовые данные
│   ├── migrations/        Alembic migration
│   ├── pyproject.toml      зависимости и настройки Python-проекта
│   ├── uv.lock             зафиксированное дерево Python-зависимостей
│   ├── .python-version     локальная версия Python 3.12 для uv
│   └── tests/             backend integration tests
├── frontend/
│   ├── e2e/               Playwright-сценарий
│   ├── src/
│   │   ├── auth/          состояние авторизации
│   │   ├── components/    общие компоненты
│   │   ├── pages/         страницы студента, преподавателя и виджет
│   │   └── test/          Vitest-тесты
│   └── nginx.conf         SPA, API и WebSocket proxy
├── docs/                  документация
└── docker-compose.yml     PostgreSQL, backend, frontend
```

## 4. Способ запуска №1: весь проект через Docker

Это основной способ увидеть готовый результат.

### Требования

- Docker Desktop или другой запущенный Docker daemon.
- Docker Compose v2.
- Свободные порты `3000`, `8000` и `5432`.

### Запуск

```bash
cp .env.example .env
docker compose up --build
```

Можно запустить в фоне:

```bash
docker compose up -d --build
docker compose ps
```

При старте автоматически выполняются:

1. Запуск PostgreSQL.
2. Ожидание healthcheck базы данных.
3. `uv run --locked alembic upgrade head`.
4. `uv run --locked python -m app.seed`.
5. Запуск Uvicorn.
6. Сборка React и запуск nginx после готовности backend.

### Что открыть

- Полное приложение: <http://localhost:3000>
- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Backend healthcheck: <http://localhost:8000/health>

### Полезные команды Docker

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
docker compose restart backend
docker compose down
docker compose down -v
```

`docker compose down -v` удаляет PostgreSQL volume и полностью сбрасывает
тестовые данные.

## 5. Способ запуска №2: PostgreSQL в Docker, код локально

Этот способ удобен для разработки с hot reload.

Для локального backend установите `uv`: <https://docs.astral.sh/uv/>.

### Терминал 1: база данных

```bash
docker compose up db
```

### Терминал 2: backend

```bash
cd backend
cp .env.example .env
uv sync --extra test --locked
uv run --locked alembic upgrade head
uv run --locked python -m app.seed
uv run --locked uvicorn app.main:app --reload
```

Backend будет доступен на <http://localhost:8000>.

### Терминал 3: frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Vite покажет точный URL, обычно <http://localhost:5173>.

## 6. Способ запуска №3: production-сборка frontend

Проверка того, что frontend компилируется и работает как собранное приложение:

```bash
cd frontend
cp .env.example .env
npm install
npm run build
npx vite preview --host 127.0.0.1 --port 4173
```

Результат сборки находится в `frontend/dist`. Откройте
<http://127.0.0.1:4173>. Backend при этом должен работать на порту `8000`.

## 7. Как сделать занятие активным для демонстрации

Кнопки запуска и отметки доступны только между `start_time` и `end_time`.
Основное занятие seed имеет время 15:55–17:25 по Тюмени. Если тестирование идёт
в другое время, временно передвиньте занятие вокруг текущего времени.

### Для Docker PostgreSQL

Сначала сбросьте текущую сессию backend, затем измените БД:

```bash
docker compose restart backend
docker compose exec db psql -U attendpro -d attendpro -c \
  "DELETE FROM attendance WHERE schedule_id = 1; UPDATE schedule SET start_time = NOW() - INTERVAL '5 minutes', end_time = NOW() + INTERVAL '85 minutes', fact_passed = FALSE, attendance_started_at = NULL, attendance_finished_at = NULL WHERE id = 1;"
```

Не перезапускайте backend после `UPDATE`: при старте seed снова установит
штатное время 15:55–17:25.

Если в `.env` изменены `POSTGRES_USER` или `POSTGRES_DB`, подставьте свои
значения в команду `psql`.

### Вернуть штатные fixtures

```bash
docker compose down -v
docker compose up -d --build
```

## 8. Ручной браузерный тест полного сценария

Для наглядной проверки используйте два независимых профиля браузера, обычное и
приватное окно либо два разных браузера.

### Окно преподавателя

1. Откройте <http://localhost:3000/login>.
2. Войдите как `lecturer@test.ru` с паролем `123456`.
3. Убедитесь, что видно два занятия и полный состав карточек.
4. На активном занятии задайте допустимое опоздание, например 15 минут.
5. Нажмите «Начать занятие».
6. Разрешите popup-окна, если браузер их блокирует.
7. Проверьте крупный цифровой код, QR и обратный отсчёт.
8. Оставьте виджет открытым.

### Окно студента

1. Откройте приватное окно и перейдите на <http://localhost:3000/login>.
2. Войдите как `student1@test.ru` с паролем `123456`.
3. Убедитесь, что показываются занятия группы РСОДПО-П-МОиАИС-23.01.
4. Нажмите «Отметить присутствие» у активного занятия.
5. Введите текущий код из виджета до окончания обратного отсчёта.
6. Нажмите «Подтвердить присутствие».
7. Проверьте сообщение, время, опоздание и статус зачёта.
8. Откройте раздел «История» и проверьте новую строку.

### Снова окно преподавателя

1. Убедитесь, что Иванов Иван появился без обновления страницы.
2. Проверьте время и текст опоздания.
3. Нажмите «Завершить занятие» и подтвердите действие.
4. Проверьте экран закрытой отметки.

## 9. Проверка QR-сканирования

1. Запустите сессию преподавателем.
2. Откройте кабинет студента на устройстве с камерой.
3. Нажмите «Отметить присутствие» и «Сканировать QR-код».
4. Разрешите браузеру доступ к камере.
5. Наведите камеру на QR в виджете преподавателя.
6. Убедитесь, что поле автоматически получает шесть цифр.
7. Подтвердите отметку.

Камера браузера обычно требует secure context. На `localhost` она работает, но
при открытии frontend на телефоне по обычному HTTP через LAN IP браузер может
запретить камеру. В этом случае используйте цифровой код или HTTPS tunnel.

## 10. Автоматические backend-тесты

### Установка

```bash
cd backend
uv sync --extra test --locked
```

`uv` автоматически установит Python 3.12 из `.python-version`, если совместимый
интерпретатор отсутствует, создаст `.venv` и синхронизирует его с `uv.lock`.

### Полный набор

```bash
uv run --extra test --locked python -m compileall -q app migrations tests
uv run --extra test --locked pytest -q
```

Текущая база проверок: 27 тестов.

### Подробный вывод

```bash
uv run --extra test --locked pytest -vv
```

### Проверка отдельных областей

```bash
uv run --extra test --locked pytest -q tests/test_auth.py
uv run --extra test --locked pytest -q tests/test_schedule.py
uv run --extra test --locked pytest -q tests/test_lecturer.py
uv run --extra test --locked pytest -q tests/test_attendance.py
uv run --extra test --locked pytest -q tests/test_websocket.py
uv run --extra test --locked pytest -q tests/test_seed.py
uv run --extra test --locked pytest -q tests/test_schema.py
```

Backend-тесты используют отдельную временную SQLite БД через `aiosqlite` и не
изменяют локальную PostgreSQL БД. Проверяются:

- правильный и неправильный логин;
- обязательность JWT;
- роли и запрет доступа к чужим endpoints;
- фильтрация расписания;
- точный OpenAPI-контракт;
- назначение преподавателя;
- запрет запуска неактивного занятия;
- генерация QR и шестизначного кода;
- ротация и остановка кода;
- корректная и ошибочная отметка;
- несовпадение группы;
- просроченный или неверный код;
- опоздание и незачтённая отметка;
- защита от дубликатов;
- список преподавателя и история студента;
- WebSocket-авторизация и broadcast;
- повторный безопасный запуск seed.

### Работа с Python-зависимостями

Добавить runtime-зависимость:

```bash
cd backend
uv add package-name
```

Добавить зависимость в optional extra для тестов:

```bash
uv add --optional test package-name
```

Обновить разрешённые версии зависимостей:

```bash
uv lock --upgrade
uv sync --extra test --locked
```

После изменения зависимостей необходимо коммитить вместе `pyproject.toml` и
`uv.lock`. Флаг `--locked` запрещает незаметное изменение lock-файла во время
сборки или тестирования.

## 11. Автоматические frontend-тесты

### Установка

```bash
cd frontend
npm install
```

### TypeScript

```bash
npm run typecheck
```

### Unit и component tests

```bash
npm test
```

Текущая база: 6 Vitest-тестов. Они проверяют авторизацию, ролевый redirect,
получение расписания, ввод ровно шести цифр, закрытую сессию посещаемости и
разбор QR payload.

### Watch mode

```bash
npm run test:watch
```

### Production build

```bash
npm run build
```

Эта команда одновременно выполняет TypeScript build и сборку Vite.

## 12. Playwright E2E

E2E-тест использует реальный frontend и backend, два browser context и popup:

1. Вход преподавателя.
2. Запуск или открытие виджета.
3. Проверка шестизначного кода.
4. Вход студента в отдельном контексте.
5. Отправка кода или проверка существующей истории.
6. Получение имени студента в виджете.
7. Остановка сессии преподавателем.

### Установка браузера

```bash
cd frontend
npx playwright install chromium
```

### E2E против Docker frontend

Убедитесь, что первое занятие активно по инструкции из раздела 7:

```bash
cd frontend
E2E_BASE_URL=http://localhost:3000 npm run test:e2e
```

### E2E против Vite dev server

Backend должен работать на `localhost:8000`, Vite на `localhost:5173`:

```bash
cd frontend
E2E_BASE_URL=http://localhost:5173 npm run test:e2e
```

### Отладка Playwright

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test --headed
E2E_BASE_URL=http://localhost:3000 npx playwright test --debug
E2E_BASE_URL=http://localhost:3000 npx playwright show-report
```

При падении сохраняется trace. Его можно открыть командой, которую Playwright
печатает в консоли, например `npx playwright show-trace <trace.zip>`.

## 13. Проверка API через Swagger

1. Откройте <http://localhost:8000/docs>.
2. Выполните `POST /auth/login` с тестовыми данными.
3. Скопируйте `access_token`.
4. Нажмите `Authorize` и вставьте token в Bearer-авторизацию.
5. Выполните `GET /schedule/current`.
6. Войдите lecturer token и вызовите `POST /lecturer/start/1`.
7. Скопируйте поле `code`.
8. Авторизуйтесь student token и вызовите `POST /student/mark`.
9. Снова используйте lecturer token для `GET /lecturer/attendance/1`.
10. Завершите сессию через `POST /lecturer/stop/1`.

## 14. Проверка API через cURL

### Healthcheck

```bash
curl --fail http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

### Логин преподавателя

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"lecturer@test.ru","password":"123456"}' | jq
```

### Логин студента

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"student1@test.ru","password":"123456"}' | jq
```

Для следующих команд сохраните токены:

```bash
LECTURER_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"lecturer@test.ru","password":"123456"}' | jq -r .access_token)

STUDENT_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"student1@test.ru","password":"123456"}' | jq -r .access_token)
```

### Расписание

```bash
curl -s http://localhost:8000/schedule/current \
  -H "Authorization: Bearer $LECTURER_TOKEN" | jq
```

Можно запросить конкретную дату:

```bash
curl -s 'http://localhost:8000/schedule/current?date=2026-08-04' \
  -H "Authorization: Bearer $LECTURER_TOKEN" | jq
```

### Запуск сессии

```bash
START_RESPONSE=$(curl -s -X POST http://localhost:8000/lecturer/start/1 \
  -H "Authorization: Bearer $LECTURER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"allowed_late_minutes":15,"exit_enabled":false}')

printf '%s\n' "$START_RESPONSE" | jq
CODE=$(printf '%s\n' "$START_RESPONSE" | jq -r .code)
```

### Отметка студента

```bash
curl -s -X POST http://localhost:8000/student/mark \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"schedule_id\":1,\"code\":\"$CODE\"}" | jq
```

### Список и история

```bash
curl -s http://localhost:8000/lecturer/attendance/1 \
  -H "Authorization: Bearer $LECTURER_TOKEN" | jq

curl -s http://localhost:8000/student/history \
  -H "Authorization: Bearer $STUDENT_TOKEN" | jq
```

### Остановка

```bash
curl -s -X POST http://localhost:8000/lecturer/stop/1 \
  -H "Authorization: Bearer $LECTURER_TOKEN" | jq
```

После остановки `GET /lecturer/code/1` должен вернуть HTTP 409.

## 15. Полный список API

| Метод | Endpoint | Роль | Назначение |
| --- | --- | --- | --- |
| POST | `/auth/login` | все | Получить JWT и пользователя |
| GET | `/schedule/current` | student, lecturer | Расписание с ролевым фильтром |
| POST | `/lecturer/start/{schedule_id}` | lecturer | Начать сессию и получить код |
| GET | `/lecturer/code/{schedule_id}` | lecturer | Получить или ротировать код |
| POST | `/lecturer/stop/{schedule_id}` | lecturer | Остановить сессию |
| GET | `/lecturer/attendance/{schedule_id}` | lecturer | Список отметившихся |
| POST | `/student/mark` | student | Сохранить вход |
| GET | `/student/history` | student | История студента |
| WS | `/ws/attendance/{schedule_id}?token=...` | lecturer | Real-time attendance |
| GET | `/health` | все | Healthcheck |

## 16. Дополнительные ручные проверки

### Ротация кода

1. Запустите виджет.
2. Запишите текущий код.
3. Дождитесь окончания 15 секунд.
4. Убедитесь, что код и QR изменились без перезагрузки страницы.
5. Попробуйте старый код. Backend должен его отклонить.

### Защита от дубликатов

1. Успешно отметьтесь студентом.
2. Не завершая сессию, попробуйте отправить новый действующий код ещё раз.
3. Backend должен вернуть HTTP 409 `Attendance already marked`.

### Неверный код

1. Запустите отметку.
2. Введите любые шесть цифр, отличные от виджета.
3. Убедитесь, что запись в истории не появилась.

### Остановка сессии

1. Получите действующий код.
2. Остановите занятие преподавателем.
3. Попробуйте отправить сохранённый код студентом.
4. Backend должен сообщить, что сессия не запущена.

### Опоздание сверх лимита

1. Сделайте занятие активным, но установите `start_time` более чем на 15 минут
   раньше текущего времени.
2. Запустите сессию с `allowed_late_minutes: 15`.
3. Отметьтесь студентом.
4. Убедитесь, что отметка сохранена, `credited` равен `false`, а
   `late_minutes` больше 15.

Пример изменения PostgreSQL:

```bash
docker compose exec db psql -U attendpro -d attendpro -c \
  "DELETE FROM attendance WHERE schedule_id = 1; UPDATE schedule SET start_time = NOW() - INTERVAL '20 minutes', end_time = NOW() + INTERVAL '70 minutes', attendance_started_at = NULL, attendance_finished_at = NULL WHERE id = 1;"
```

### Ролевые ограничения

- Student token на `/lecturer/start/1` должен получить HTTP 403.
- Lecturer token на `/student/history` должен получить HTTP 403.
- Запрос без Bearer token к защищённому endpoint должен получить HTTP 401.
- Чужой преподаватель не должен запускать неназначенное ему занятие.

### Адаптивность

Проверьте в DevTools размеры:

- 390 × 844 для телефона;
- 768 × 1024 для планшета;
- 1440 × 900 для desktop;
- небольшое отдельное popup-окно виджета.

Проверьте отсутствие горизонтальной прокрутки, доступность кнопок, таблицы
истории, списка группы и модального окна.

## 17. Проверка данных в PostgreSQL

Открыть `psql`:

```bash
docker compose exec db psql -U attendpro -d attendpro
```

Полезные запросы:

```sql
SELECT id, email, role, full_name, "group" FROM users ORDER BY id;

SELECT id, short_name, "group", start_time, end_time,
       attendance_started_at, attendance_finished_at
FROM schedule
ORDER BY start_time;

SELECT a.id, u.full_name, a.schedule_id, a.timestamp,
       a.late_minutes, a.is_credited
FROM attendance a
JOIN users u ON u.id = a.user_id
ORDER BY a.timestamp;
```

Выйти из `psql`: `\q`.

## 18. Проверка миграций и seed

### Текущая версия миграции

```bash
cd backend
uv run --locked alembic current
uv run --locked alembic history
```

### Чистая миграция в Docker

```bash
docker compose down -v
docker compose up -d db
docker compose run --rm backend uv run --locked alembic upgrade head
```

### Идемпотентность seed

```bash
docker compose run --rm backend uv run --locked python -m app.seed
docker compose run --rm backend uv run --locked python -m app.seed
```

После двух запусков должны остаться 4 пользователя и 2 занятия без дубликатов.
Автоматически это также проверяет `backend/tests/test_seed.py`.

## 19. Диагностика проблем

### Docker daemon is not running

Сообщение `Cannot connect to the Docker daemon` означает, что нужно запустить
Docker Desktop или системный Docker daemon.

### Порт уже занят

Проверьте, кто использует `3000`, `8000` или `5432`, либо измените внешний порт
в `docker-compose.yml`.

### Кнопка запуска недоступна

Проверьте:

- текущую дату в Тюмени;
- `SEED_DATE`;
- `start_time` и `end_time` занятия;
- `active` в ответе `/schedule/current`;
- что преподаватель назначен на занятие.

Для демонстрации используйте инструкцию из раздела 7.

### Кнопка студента недоступна

Для студента одновременно должны быть истинны `active` и `attendance_active`.
Сначала преподаватель должен нажать «Начать занятие».

### Popup не открылся

Разрешите всплывающие окна для `localhost:3000` или Vite-origin.

### Камера не запускается

Проверьте разрешение камеры и secure context. Всегда остаётся ручной ввод кода.

### Код перестал работать

Код намеренно живёт 15 секунд. Получите актуальный код. После перезапуска
backend in-memory коды также исчезают, и сессию нужно запустить заново.

### WebSocket переподключается

Проверьте backend logs, JWT, nginx proxy и URL `/api/ws/...` в Docker-режиме.
Начальный список загружается REST-запросом, последующие изменения идут по WS.

### CORS при локальной разработке

Проверьте `CORS_ORIGINS` в `backend/.env` и фактический адрес Vite. Стандартная
конфигурация разрешает `localhost:5173`, `127.0.0.1:4173` и `localhost:3000`.

### Данные не обновились после изменения SEED_DATE

Seed идентифицирует занятие по названию, времени и группе. Для полностью чистого
набора выполните `docker compose down -v`, задайте `SEED_DATE` и запустите стек.

## 20. Текущие ограничения MVP

- Вместо университетского SSO используется тестовый JWT login.
- Refresh token и регистрация отсутствуют.
- Modeus пока не подключён; подготовлена только сервисная граница расписания.
- Коды находятся в памяти одного backend-процесса, а не в Redis.
- Несколько backend-реплик без общего Redis использовать нельзя.
- Перезапуск backend удаляет текущий код.
- Отметка выхода представлена настройкой, но не реализована.
- Нет ролей администратора и деканата.
- Нет сложной аналитики и экспорта в Modeus.
- Нет проверки IP, геолокации и вузовской Wi-Fi сети.
- Для production необходимы HTTPS, сильный `JWT_SECRET`, ограниченный CORS,
  резервное копирование PostgreSQL и production secret management.

## 21. Рекомендуемый чек-лист приёмки

- [ ] `docker compose config` проходит без ошибок.
- [ ] Все три контейнера healthy/running.
- [ ] `/health` возвращает HTTP 200.
- [ ] Swagger открывается.
- [ ] Все четыре тестовых пользователя входят.
- [ ] Студент и преподаватель получают разные кабинеты.
- [ ] Расписание фильтруется по роли.
- [ ] Неактивное занятие нельзя запустить.
- [ ] Активное занятие запускается преподавателем.
- [ ] Код состоит из шести цифр.
- [ ] QR отображается.
- [ ] Код меняется примерно каждые 15 секунд.
- [ ] Старый и неверный коды отклоняются.
- [ ] Студент успешно отмечается действующим кодом.
- [ ] Повторная отметка отклоняется.
- [ ] Опоздание вычисляется по серверному времени.
- [ ] Сверхлимитная отметка сохраняется как незачтённая.
- [ ] Виджет обновляется через WebSocket.
- [ ] История содержит отметку.
- [ ] После остановки код не принимается.
- [ ] QR-сканер работает или показывает понятную ошибку камеры.
- [ ] Интерфейс usable на desktop и телефоне.
- [ ] 27 backend-тестов проходят.
- [ ] 6 frontend-тестов проходят.
- [ ] TypeScript typecheck проходит.
- [ ] Production build проходит.
- [ ] Playwright E2E проходит.

## 22. Последняя подтверждённая матрица тестов

На момент подготовки документации подтверждены:

| Проверка | Результат |
| --- | --- |
| `uv lock --check` | успешно |
| Backend compileall | успешно |
| Backend pytest | 27 passed |
| Frontend TypeScript | успешно |
| Frontend Vitest | 6 passed |
| Frontend production build | успешно |
| Playwright full attendance flow | успешно |
| Повторный Playwright запуск на той же БД | успешно |
| Alembic upgrade на чистой БД | успешно |
| Идемпотентный seed после изменения времени | успешно на SQLite и PostgreSQL |
| Docker Compose config validation | успешно |
| Backend Docker build без cache | успешно |
| Полный Docker Compose stack | PostgreSQL и backend healthy, frontend running |
| API напрямую и через nginx | HTTP 200 |

Последняя полная проверка выполнена на Docker Desktop с PostgreSQL,
production nginx frontend и backend-образом, собранным через `uv 0.9.16`.
