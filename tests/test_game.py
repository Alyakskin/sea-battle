import re
import uuid

from fastapi.testclient import TestClient

from app.fleet import SHIP_SIZES, validate_fleet
from app.main import app
from app.models import Game

COORDINATE = re.compile(r"^[A-J]([1-9]|10)$")


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_start_game_returns_201(client):
    response = client.post("/game")

    assert response.status_code == 201


def test_start_game_response_has_only_contract_fields(client):
    data = client.post("/game").json()

    assert "session_id" in data
    assert "ships" in data
    assert len(data) == 2

    for ship in data["ships"]:
        assert list(ship.keys()) == ["coordinates"]


def test_session_id_is_uuid(client):
    data = client.post("/game").json()

    uuid.UUID(data["session_id"])


def test_coordinates_are_in_contract_format(client):
    ships = client.post("/game").json()["ships"]

    for ship in ships:
        for coordinate in ship["coordinates"]:
            assert COORDINATE.match(coordinate), coordinate


def test_start_game_returns_fleet_by_the_rules(client):
    ships = client.post("/game").json()["ships"]
    sizes = sorted([len(ship["coordinates"]) for ship in ships], reverse=True)

    assert sizes == SHIP_SIZES
    assert sum(sizes) == 20
    assert validate_fleet(ships) == []


def test_start_game_saves_session_to_database(client, db):
    data = client.post("/game").json()

    game = db.get(Game, uuid.UUID(data["session_id"]))

    assert game is not None
    assert game.status == "active"
    assert game.created_at is not None
    assert game.ships == data["ships"]


def test_each_call_creates_its_own_session(client, db):
    first = client.post("/game").json()
    second = client.post("/game").json()

    assert first["session_id"] != second["session_id"]

    assert db.get(Game, uuid.UUID(first["session_id"])).ships == first["ships"]
    assert db.get(Game, uuid.UUID(second["session_id"])).ships == second["ships"]


def test_session_id_is_created_by_service(client, db):
    my_id = str(uuid.uuid4())

    response = client.post("/game", json={"session_id": my_id, "ships": []})

    assert response.status_code == 201
    assert response.json()["session_id"] != my_id
    assert db.get(Game, uuid.UUID(my_id)) is None


def test_unexpected_error_returns_500_in_contract_format(client, db, monkeypatch):
    def broken_generator():
        raise RuntimeError("генератор сломался")

    monkeypatch.setattr("app.main.generate_fleet", broken_generator)
    error_client = TestClient(app, raise_server_exceptions=False)

    response = error_client.post("/game")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert db.query(Game).count() == 0
