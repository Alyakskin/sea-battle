# Sea Battle

Игровой сервис морского боя: FastAPI, SQLAlchemy, Alembic, PostgreSQL.
Контракт API — [docs/contract.md](docs/contract.md).

## Запуск

```
cp .env.example .env
docker compose up --build -d
```

Миграции применяются при старте контейнера.

## Тесты

```
docker compose exec app pytest -v
```

## Swagger

http://localhost:8000/docs
