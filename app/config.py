import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://seabattle:change_me@localhost:5432/seabattle",
)
