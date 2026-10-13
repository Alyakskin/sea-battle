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

## Арена

Матч между двумя сервисами по их адресам:

```
python -m arena http://localhost:8001 http://localhost:8002
```

Сервис против самого себя внутри контейнера:

```
docker compose exec app python -m arena http://localhost:8000 http://localhost:8000
```

Арена проверяет расстановки, сверяет каждый ответ с полем, следит за таймаутом 1 секунда
и засчитывает поражение за враньё, просрочку и ответы не по контракту.
