import uuid

from pydantic import BaseModel


class Ship(BaseModel):
    coordinates: list[str]


class StartGameResponse(BaseModel):
    session_id: uuid.UUID
    ships: list[Ship]
