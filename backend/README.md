# AttendPro backend

Python 3.10+, FastAPI, SQLAlchemy 2 async and PostgreSQL.

```bash
cp .env.example .env
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Run tests with `pytest -q`. Seed credentials are `student1@test.ru`,
`student2@test.ru`, `lecturer@test.ru`, `vorobieva@test.ru`; every
password is `123456`. `SEED_DATE` optionally pins the seed day, otherwise the
current date in Tyumen (UTC+5) is used.
