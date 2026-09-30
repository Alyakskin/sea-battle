import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from app.models import Game
from app.shots import answer_shot

GAMES = 8


def start_games(client, count=GAMES):
    games = []
    for _ in range(count):
        body = client.post("/game").json()
        games.append((body["session_id"], body["ships"]))
    return games


def in_parallel(work, items):
    with ThreadPoolExecutor(max_workers=len(items)) as pool:
        return list(pool.map(work, items))


def test_parallel_games_get_their_own_sessions(client, db):
    def create(_):
        return client.post("/game").json()

    bodies = in_parallel(create, list(range(GAMES)))
    session_ids = [body["session_id"] for body in bodies]

    assert len(set(session_ids)) == GAMES
    for body in bodies:
        game = db.get(Game, uuid.UUID(body["session_id"]))
        assert game.ships == body["ships"]


def test_parallel_answers_match_own_placement(client, db):
    games = start_games(client)

    def shoot(game):
        session_id, ships = game
        coordinate = ships[0]["coordinates"][0]
        response = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": coordinate})
        return session_id, ships, coordinate, response

    for session_id, ships, coordinate, response in in_parallel(shoot, games):
        assert response.status_code == 200
        assert response.json()["result"] == answer_shot(ships, {}, coordinate)

        game = db.get(Game, uuid.UUID(session_id))
        db.refresh(game)
        assert game.opponent_shots == {coordinate: response.json()["result"]}


def test_parallel_shots_do_not_mix_between_sessions(client, db):
    games = start_games(client)

    def shoot(game):
        session_id, _ = game
        return session_id, client.post(f"/game/{session_id}/shot").json()["coordinate"]

    for session_id, coordinate in in_parallel(shoot, games):
        game = db.get(Game, uuid.UUID(session_id))
        db.refresh(game)
        assert game.my_shots == [{"coordinate": coordinate, "result": None}]


def test_every_answer_is_faster_than_a_second(client):
    games = start_games(client)

    def shoot(game):
        session_id, ships = game
        started = time.perf_counter()
        client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": ships[0]["coordinates"][0]})
        return time.perf_counter() - started

    assert max(in_parallel(shoot, games)) < 1


def test_closing_one_session_does_not_stop_others(client):
    games = start_games(client)
    closed_id = games[0][0]
    client.post(f"/game/{closed_id}/close")

    def shoot(game):
        session_id, _ = game
        return session_id, client.post(f"/game/{session_id}/shot").status_code

    for session_id, code in in_parallel(shoot, games):
        assert code == (410 if session_id == closed_id else 200)


def test_series_of_shots_in_parallel_games_stays_correct(client, db):
    games = start_games(client, 4)

    def play(game):
        session_id, _ = game
        fired = []
        for _ in range(5):
            coordinate = client.post(f"/game/{session_id}/shot").json()["coordinate"]
            fired.append(coordinate)
            client.post(f"/game/{session_id}/shot/result", json={"result": "miss"})
        return session_id, fired

    for session_id, fired in in_parallel(play, games):
        assert len(set(fired)) == 5
        game = db.get(Game, uuid.UUID(session_id))
        db.refresh(game)
        assert [shot["coordinate"] for shot in game.my_shots] == fired
        assert all(shot["result"] == "miss" for shot in game.my_shots)
