import uuid

from app.models import Game


def new_game(client):
    body = client.post("/game").json()
    return body["session_id"], body["ships"]


def test_close_returns_status_closed(client):
    session_id, _ = new_game(client)

    response = client.post(f"/game/{session_id}/close")

    assert response.status_code == 200
    assert response.json() == {"status": "closed"}


def test_closed_session_is_saved_in_database(client, db):
    session_id, _ = new_game(client)

    client.post(f"/game/{session_id}/close")

    game = db.get(Game, uuid.UUID(session_id))
    assert game is not None
    assert game.status == "closed"


def test_second_close_is_bad_request(client):
    session_id, _ = new_game(client)
    client.post(f"/game/{session_id}/close")

    response = client.post(f"/game/{session_id}/close")

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)


def test_close_of_unknown_session_is_not_found(client):
    response = client.post(f"/game/{uuid.uuid4()}/close")

    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


def test_close_of_broken_session_id_is_not_found(client):
    response = client.post("/game/not-a-uuid/close")

    assert response.status_code == 404


def test_other_handles_are_gone_after_close(client):
    session_id, ships = new_game(client)
    client.post(f"/game/{session_id}/close")

    assert client.post(f"/game/{session_id}/shot").status_code == 410
    assert client.post(f"/game/{session_id}/shot/result", json={"result": "miss"}).status_code == 410
    assert (
        client.post(
            f"/game/{session_id}/opponent-shot", json={"coordinate": ships[0]["coordinates"][0]}
        ).status_code
        == 410
    )


def test_close_does_not_touch_other_sessions(client, db):
    first_id, _ = new_game(client)
    second_id, _ = new_game(client)

    client.post(f"/game/{first_id}/close")

    assert db.get(Game, uuid.UUID(first_id)).status == "closed"
    assert db.get(Game, uuid.UUID(second_id)).status == "active"
    assert client.post(f"/game/{second_id}/shot").status_code == 200


def test_game_history_stays_after_close(client, db):
    session_id, ships = new_game(client)
    coordinate = ships[0]["coordinates"][0]
    client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": coordinate})
    client.post(f"/game/{session_id}/shot")

    client.post(f"/game/{session_id}/close")

    game = db.get(Game, uuid.UUID(session_id))
    assert game.opponent_shots == {coordinate: "hit"}
    assert len(game.my_shots) == 1
