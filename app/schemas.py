import uuid
from typing import Literal

from pydantic import BaseModel


class Ship(BaseModel):
    coordinates: list[str]


class StartGameResponse(BaseModel):
    session_id: uuid.UUID
    ships: list[Ship]


class ShotRequest(BaseModel):
    coordinate: str


class ShotResponse(BaseModel):
    coordinate: str


class ShotResultRequest(BaseModel):
    result: Literal["miss", "hit", "killed"]


class AcceptedResponse(BaseModel):
    status: str


class OpponentShotResponse(BaseModel):
    result: str
