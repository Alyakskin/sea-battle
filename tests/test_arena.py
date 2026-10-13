import json
import time
import uuid

import httpx

from app.models import Game
from app.shots import answer_shot
from arena.board import board_lines
from arena.client import ServiceClient
from arena.match import Side, play_match

FLEET = [
    {"coordinates": ["A1", "A2", "A3", "A4"]},
    {"coordinates": ["C1", "C2", "C3"]},
    {"coordinates": ["E1", "F1", "G1"]},
    {"coordinates": ["A6", "A7"]},
    {"coordinates": ["C6", "C7"]},
    {"coordinates": ["E6", "E7"]},
    {"coordinates": ["J1"]},
    {"coordinates": ["J3"]},
    {"coordinates": ["J5"]},
    {"coordinates": ["J7"]},
]


class FakeService:
    def __init__(self, broken=None):
        self.broken = broken
        self.received = {}
        self.queue = [f"{letter}{number}" for number in range(1, 11) for letter in "ABCDEFGHIJ"]
        self.closed = False

    def handle(self, request):
        path = request.url.path
        body = json.loads(request.content) if request.content else {}

        if path == "/game":
            ships = FLEET[:-1] if self.broken == "fleet" else FLEET
            session_id = "game-1" if self.broken == "session_id" else str(uuid.uuid4())
            code = 200 if self.broken == "game_code" else 201
            return httpx.Response(code, json={"session_id": session_id, "ships": ships})

        if path.endswith("/opponent-shot"):
            if self.broken == "timeout":
                raise httpx.ReadTimeout("timeout", request=request)
            if self.broken == "slow":
                time.sleep(0.2)
            result = answer_shot(FLEET, self.received, body["coordinate"])
            self.received.setdefault(body["coordinate"], result)
            if self.broken == "liar" and result != "miss":
                result = "miss"
            return httpx.Response(200, json={"result": result})

        if path.endswith("/shot/result"):
            if self.broken == "result_body":
                return httpx.Response(200, json={"status": "ok"})
            return httpx.Response(200, json={"status": "accepted"})

        if path.endswith("/shot"):
            if self.broken == "error":
                return httpx.Response(500, json={"detail": "Internal Server Error"})
            if self.broken == "coordinate":
                return httpx.Response(200, json={"coordinate": "K11"})
            if self.broken == "repeat":
                return httpx.Response(200, json={"coordinate": "A1"})
            return httpx.Response(200, json={"coordinate": self.queue.pop(0)})

        if path.endswith("/close"):
            self.closed = True
            if self.broken == "close_body":
                return httpx.Response(200, json={"closed": True})
            return httpx.Response(200, json={"status": "closed"})

        return httpx.Response(404, json={"detail": "Not Found"})


def fake_client(name, service, timeout=1.0):
    http = httpx.Client(base_url="http://fake", transport=httpx.MockTransport(service.handle))
    return ServiceClient(name, http=http, timeout=timeout)


def run(first_service, second_service, timeout=1.0):
    first = fake_client("A", first_service, timeout)
    second = fake_client("B", second_service, timeout)
    return play_match(first, second, first=0, log=lambda text: None)


def test_honest_match_goes_until_whole_fleet_is_sunk():
    a, b = FakeService(), FakeService()

    result = run(a, b)

    assert result.winner == "A"
    assert result.loser == "B"
    assert result.reason == "потоплен весь флот"
    assert result.sides[1].decks_left() == 0
    assert result.sides[0].decks_left() > 0


def test_hit_gives_one_more_shot_and_miss_passes_turn():
    result = run(FakeService(), FakeService())

    for current, following in zip(result.moves, result.moves[1:]):
        if current[2] == "miss":
            assert following[0] != current[0]
        else:
            assert following[0] == current[0]


def test_both_sessions_are_closed_after_match():
    a, b = FakeService(), FakeService()

    result = run(a, b)

    assert a.closed and b.closed
    assert all(side.closed for side in result.sides)


def test_liar_loses_the_match():
    result = run(FakeService(), FakeService(broken="liar"))

    assert result.winner == "A"
    assert result.loser == "B"
    assert "враньё" in result.reason


def test_invalid_fleet_loses_before_first_shot():
    result = run(FakeService(broken="fleet"), FakeService())

    assert result.loser == "A"
    assert "невалидная расстановка" in result.reason
    assert result.moves == []


def test_timeout_loses_the_match():
    result = run(FakeService(), FakeService(broken="timeout"))

    assert result.loser == "B"
    assert "нет ответа" in result.reason


def test_slow_answer_over_the_limit_loses():
    result = run(FakeService(), FakeService(broken="slow"), timeout=0.1)

    assert result.loser == "B"
    assert "лимит" in result.reason


def test_server_error_loses_the_match():
    result = run(FakeService(broken="error"), FakeService())

    assert result.loser == "A"
    assert "500" in result.reason


def test_wrong_coordinate_loses_the_match():
    result = run(FakeService(broken="coordinate"), FakeService())

    assert result.loser == "A"
    assert "K11" in result.reason


def test_repeated_shot_passes_the_turn():
    result = run(FakeService(broken="repeat"), FakeService())

    assert result.moves[0] == ("A", "A1", "hit")
    assert result.moves[1] == ("A", "A1", "hit")
    assert result.moves[2][0] == "B"


def test_start_game_must_answer_201():
    result = run(FakeService(broken="game_code"), FakeService())

    assert result.loser == "A"
    assert "201" in result.reason


def test_session_id_must_be_uuid():
    result = run(FakeService(), FakeService(broken="session_id"))

    assert result.loser == "B"
    assert "не UUID" in result.reason


def test_result_answer_must_follow_contract():
    result = run(FakeService(broken="result_body"), FakeService())

    assert result.loser == "A"
    assert "/shot/result" in result.reason


def test_wrong_close_answer_is_not_counted_as_closed():
    result = run(FakeService(), FakeService(broken="close_body"))

    assert result.sides[0].closed
    assert not result.sides[1].closed


def test_arena_ignores_proxy_settings():
    assert ServiceClient("A", base_url="http://localhost:8000").http.trust_env is False


def test_sessions_are_closed_after_technical_loss():
    a, b = FakeService(), FakeService(broken="liar")

    run(a, b)

    assert a.closed and b.closed


def test_board_shows_ships_hits_and_misses():
    side = Side(client=type("Named", (), {"name": "A"})(), ships=FLEET, received={"A1": "hit", "B5": "miss"})

    lines = board_lines(side)

    assert lines[2].split()[1:4] == ["X", ".", "#"]
    assert lines[6].split()[2] == "o"


def test_real_service_plays_a_full_match_against_itself(client, db):
    first = ServiceClient("A", http=client)
    second = ServiceClient("B", http=client)

    result = play_match(first, second, first=0, log=lambda text: None)

    assert result.winner in ("A", "B")
    assert result.reason == "потоплен весь флот"
    loser = result.sides[0] if result.loser == "A" else result.sides[1]
    assert loser.decks_left() == 0
    assert len(loser.received) >= 20

    for side in result.sides:
        assert side.closed
        game = db.get(Game, uuid.UUID(side.client.session_id))
        db.refresh(game)
        assert game.status == "closed"
