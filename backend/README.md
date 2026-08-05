# AttendPro backend

Python 3.10+, FastAPI, SQLAlchemy 2 async, PostgreSQL and the `uv` package
manager. The repository pins Python 3.12 for local development and commits
`uv.lock` for reproducible environments.

```bash
cp .env.example .env
uv sync --extra test --locked
uv run --locked alembic upgrade head
uv run --locked python -m app.seed
uv run --locked uvicorn app.main:app --reload
```

Run tests with `uv run --extra test --locked pytest -q`. Update dependencies
with `uv lock --upgrade`, review `uv.lock`, and commit it together with
`pyproject.toml`. Seed credentials are `student1@test.ru`,
`student2@test.ru`, `lecturer@test.ru`, `vorobieva@test.ru`; every
password is `123456`. `SEED_DATE` optionally pins the seed day, otherwise the
current date in Tyumen (UTC+5) is used.
