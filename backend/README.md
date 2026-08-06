# AttendPro backend

FastAPI/PostgreSQL authority для signed local-first attendance protocol. Python
3.12 и все зависимости зафиксированы в `uv.lock`; используйте только `uv`.

```bash
cp .env.example .env
uv sync --locked --group dev
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload
```

Проверки:

```bash
uv run pytest -q
```

Mock SSO accounts: `teacher@attend.test` и `student1@attend.test` …
`student3@attend.test`. Подробный сценарий находится в `../docs/README.md`,
формат подписей — в `../docs/CRYPTO-PROTOCOL.md`.
