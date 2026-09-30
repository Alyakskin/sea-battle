import re
import uuid

from app.models import Game
from app.shots import answer_shot

COORDINATE = re.compile(r"^[A-J]([1-9]|10)$")


def new_game(client):
    body = client.post("/game").json()
    return body["session_id"], body["ships"]


def empty_cell(ships):
    busy = {coordinate for ship in ships for coordinate in ship["coordinates"]}
    for letter in "ABCDEFGHIJ":
        for number in range(1, 11):
            if f"{letter}{number}" not in busy:
                return f"{letter}{number}"


def test_opponent_shot_into_empty_cell_is_miss(client):
    session_id, ships = new_game(client)

    response = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": empty_cell(ships)})

    assert response.status_code == 200
    assert response.json() == {"result": "miss"}


def test_opponent_shot_into_ship_is_hit(client):
    session_id, ships = new_game(client)
    ship = next(ship for ship in ships if len(ship["coordinates"]) > 1)

    response = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": ship["coordinates"][0]})

    assert response.status_code == 200
    assert response.json() == {"result": "hit"}


def test_ship_is_killed_only_by_the_last_shot(client):
    session_id, ships = new_game(client)
    ship = next(ship for ship in ships if len(ship["coordinates"]) == 3)["coordinates"]

    results = []
    for coordinate in ship:
        results.append(client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": coordinate}).json()["result"])

    assert results == ["hit", "hit", "killed"]


def test_answers_match_the_placement(client):
    session_id, ships = new_game(client)
    opponent_shots = {}

    for letter in "ABCDE":
        for number in range(1, 11):
            coordinate = f"{letter}{number}"
            result = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": coordinate}).json()["result"]
            assert result == answer_shot(ships, opponent_shots, coordinate)
            opponent_shots[coordinate] = result


def test_repeated_opponent_shot_gives_the_same_answer(client):
    session_id, ships = new_game(client)
    coordinate = ships[0]["coordinates"][0]

    first = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": coordinate}).json()
    second = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": coordinate}).json()

    assert first == second == {"result": "hit"}


def test_opponent_shots_are_saved_in_database(client, db):
    session_id, ships = new_game(client)
    hit = ships[0]["coordinates"][0]
    miss = empty_cell(ships)

    client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": hit})
    client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": miss})

    game = db.get(Game, uuid.UUID(session_id))
    assert game.opponent_shots == {hit: "hit", miss: "miss"}


def test_wrong_coordinate_is_rejected(client):
    session_id, _ = new_game(client)

    for coordinate in ["K1", "A11", "a1", "A01", ""]:
        response = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": coordinate})
        assert response.status_code == 400
        assert isinstance(response.json()["detail"], str)


def test_body_without_coordinate_is_rejected(client):
    session_id, _ = new_game(client)

    response = client.post(f"/game/{session_id}/opponent-shot", json={})

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)


def test_unknown_session_is_not_found(client):
    response = client.post(f"/game/{uuid.uuid4()}/opponent-shot", json={"coordinate": "A1"})

    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


def test_closed_session_is_gone(client, db):
    session_id, ships = new_game(client)
    game = db.get(Game, uuid.UUID(session_id))
    game.status = "closed"
    db.commit()

    assert client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": "A1"}).status_code == 410
    assert client.post(f"/game/{session_id}/shot").status_code == 410
    assert client.post(f"/game/{session_id}/shot/result", json={"result": "miss"}).status_code == 410


def test_shot_returns_coordinate_and_saves_it(client, db):
    session_id, _ = new_game(client)

    response = client.post(f"/game/{session_id}/shot")

    assert response.status_code == 200
    coordinate = response.json()["coordinate"]
    assert COORDINATE.match(coordinate)

    game = db.get(Game, uuid.UUID(session_id))
    assert game.my_shots == [{"coordinate": coordinate, "result": None}]


def test_second_shot_without_result_is_conflict(client):
    session_id, _ = new_game(client)
    client.post(f"/game/{session_id}/shot")

    response = client.post(f"/game/{session_id}/shot")

    assert response.status_code == 409
    assert isinstance(response.json()["detail"], str)


def test_result_is_accepted_and_saved(client, db):
    session_id, _ = new_game(client)
    coordinate = client.post(f"/game/{session_id}/shot").json()["coordinate"]

    response = client.post(f"/game/{session_id}/shot/result", json={"result": "hit"})

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}

    game = db.get(Game, uuid.UUID(session_id))
    assert game.my_shots == [{"coordinate": coordinate, "result": "hit"}]


def test_result_without_shot_is_conflict(client):
    session_id, _ = new_game(client)

    response = client.post(f"/game/{session_id}/shot/result", json={"result": "miss"})

    assert response.status_code == 409


def test_unknown_result_is_rejected(client):
    session_id, _ = new_game(client)
    client.post(f"/game/{session_id}/shot")

    response = client.post(f"/game/{session_id}/shot/result", json={"result": "sunk"})

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)


def test_service_hunts_a_ship_after_a_hit(client):
    session_id, _ = new_game(client)

    first = client.post(f"/game/{session_id}/shot").json()["coordinate"]
    client.post(f"/game/{session_id}/shot/result", json={"result": "hit"})
    second = client.post(f"/game/{session_id}/shot").json()["coordinate"]

    column, row = first[0], int(first[1:])
    neighbours = [
        f"{chr(ord(column) - 1)}{row}",
        f"{chr(ord(column) + 1)}{row}",
        f"{column}{row - 1}",
        f"{column}{row + 1}",
    ]
    assert second in neighbours


def test_long_series_of_shots_does_not_repeat(client, db):
    session_id, _ = new_game(client)
    fired = []

    for _ in range(40):
        coordinate = client.post(f"/game/{session_id}/shot").json()["coordinate"]
        assert COORDINATE.match(coordinate)
        assert coordinate not in fired
        fired.append(coordinate)
        result = "hit" if len(fired) % 5 == 0 else "miss"
        client.post(f"/game/{session_id}/shot/result", json={"result": result})

    game = db.get(Game, uuid.UUID(session_id))
    assert [shot["coordinate"] for shot in game.my_shots] == fired


def test_two_sessions_do_not_mix_their_shots(client, db):
    first_id, first_ships = new_game(client)
    second_id, _ = new_game(client)

    client.post(f"/game/{first_id}/opponent-shot", json={"coordinate": first_ships[0]["coordinates"][0]})
    client.post(f"/game/{second_id}/shot")

    first_game = db.get(Game, uuid.UUID(first_id))
    second_game = db.get(Game, uuid.UUID(second_id))

    assert first_game.my_shots == []
    assert second_game.opponent_shots == {}
    assert len(first_game.opponent_shots) == 1
    assert len(second_game.my_shots) == 1
