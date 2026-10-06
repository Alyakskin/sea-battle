import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.models import Game

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_DATABASE_URL", "sqlite").startswith("sqlite"),
    reason="sqlite не блокирует строки, эти тесты имеют смысл только на PostgreSQL",
)

REQUESTS = 10


def at_once(count, work):
    barrier = threading.Barrier(count)

    def run(index):
        barrier.wait()
        return work(index)

    with ThreadPoolExecutor(max_workers=count) as pool:
        return list(pool.map(run, range(count)))


def new_game(client):
    body = client.post("/game").json()
    return body["session_id"], body["ships"]


def load(db, session_id):
    game = db.get(Game, uuid.UUID(session_id))
    db.refresh(game)
    return game


def test_parallel_shots_leave_one_pending_shot(client, db):
    for _ in range(5):
        session_id, _ = new_game(client)

        codes = at_once(REQUESTS, lambda _: client.post(f"/game/{session_id}/shot").status_code)

        assert sorted(codes) == [200] + [409] * (REQUESTS - 1)
        game = load(db, session_id)
        assert len(game.my_shots) == 1
        assert game.my_shots[0]["result"] is None


def test_parallel_results_are_accepted_once(client, db):
    session_id, _ = new_game(client)
    client.post(f"/game/{session_id}/shot")

    codes = at_once(
        REQUESTS,
        lambda _: client.post(f"/game/{session_id}/shot/result", json={"result": "miss"}).status_code,
    )

    assert sorted(codes) == [200] + [409] * (REQUESTS - 1)
    game = load(db, session_id)
    assert len(game.my_shots) == 1
    assert game.my_shots[0]["result"] == "miss"


def test_parallel_opponent_shots_are_not_lost(client, db):
    session_id, ships = new_game(client)
    four = next(ship["coordinates"] for ship in ships if len(ship["coordinates"]) == 4)
    three = next(ship["coordinates"] for ship in ships if len(ship["coordinates"]) == 3)
    busy = {cell for ship in ships for cell in ship["coordinates"]}
    empty = [f"{l}{n}" for l in "ABCDEFGHIJ" for n in range(1, 11) if f"{l}{n}" not in busy][:3]
    cells = four + three + empty

    responses = at_once(
        len(cells),
        lambda i: client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": cells[i]}),
    )

    assert all(response.status_code == 200 for response in responses)
    game = load(db, session_id)
    assert sorted(game.opponent_shots) == sorted(cells)
    results = list(game.opponent_shots.values())
    assert results.count("killed") == 2
    assert results.count("hit") == 5
    assert results.count("miss") == 3


def test_parallel_close_succeeds_only_once(client, db):
    session_id, _ = new_game(client)

    codes = at_once(REQUESTS, lambda _: client.post(f"/game/{session_id}/close").status_code)

    assert sorted(codes) == [200] + [400] * (REQUESTS - 1)
    assert load(db, session_id).status == "closed"


def test_close_racing_with_shot_keeps_state_consistent(client, db):
    for _ in range(5):
        session_id, _ = new_game(client)

        def work(index):
            if index == 0:
                return "close", client.post(f"/game/{session_id}/close").status_code
            return "shot", client.post(f"/game/{session_id}/shot").status_code

        codes = dict(at_once(2, work))
        game = load(db, session_id)

        assert codes["close"] == 200
        assert game.status == "closed"
        if codes["shot"] == 200:
            assert len(game.my_shots) == 1
        else:
            assert codes["shot"] == 410
            assert game.my_shots == []
