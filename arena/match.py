import random
from dataclasses import dataclass, field

from app.fleet import parse_cell, validate_fleet
from app.shots import answer_shot
from arena.client import ServiceError

MAX_SHOTS = 300


@dataclass
class Side:
    client: object
    ships: list = field(default_factory=list)
    received: dict = field(default_factory=dict)
    fired: list = field(default_factory=list)
    closed: bool = False

    @property
    def name(self):
        return self.client.name

    def decks_left(self):
        damaged = {cell for cell, result in self.received.items() if result != "miss"}
        return sum(1 for ship in self.ships for cell in ship["coordinates"] if cell not in damaged)


@dataclass
class MatchResult:
    winner: str
    loser: str
    reason: str
    moves: list
    sides: list


def check_fleet(ships):
    if not isinstance(ships, list):
        return ["расстановка не является списком"]
    try:
        return validate_fleet(ships)
    except (AttributeError, TypeError, KeyError):
        return ["расстановка не по формату контракта"]


def result_for(sides, loser, reason, moves):
    winner = sides[1] if loser is sides[0] else sides[0]
    return MatchResult(winner.name, loser.name, reason, moves, sides)


def play(sides, moves, first, log):
    for side in sides:
        try:
            side.ships = side.client.start()
        except ServiceError as error:
            return result_for(sides, side, f"не начал игру: {error}", moves)
        errors = check_fleet(side.ships)
        if errors:
            return result_for(sides, side, "невалидная расстановка: " + "; ".join(errors), moves)

    turn = random.randint(0, 1) if first is None else first
    log(f"Первым стреляет {sides[turn].name}")

    while len(moves) < MAX_SHOTS:
        attacker, defender = sides[turn], sides[1 - turn]

        try:
            coordinate = attacker.client.shot()
        except ServiceError as error:
            return result_for(sides, attacker, str(error), moves)
        try:
            parse_cell(coordinate)
        except ValueError:
            return result_for(sides, attacker, f"некорректная координата выстрела {coordinate!r}", moves)

        repeated = coordinate in attacker.fired
        expected = answer_shot(defender.ships, defender.received, coordinate)

        try:
            answer = defender.client.opponent_shot(coordinate)
        except ServiceError as error:
            return result_for(sides, defender, str(error), moves)
        if not repeated and answer != expected:
            return result_for(
                sides, defender, f"враньё: на {coordinate} ответил {answer}, а по расстановке {expected}", moves
            )

        defender.received.setdefault(coordinate, answer)
        attacker.fired.append(coordinate)
        moves.append((attacker.name, coordinate, answer))
        log(f"{len(moves):>3}. {attacker.name} -> {coordinate}: {answer}" + (" (повтор, ход переходит)" if repeated else ""))

        try:
            attacker.client.send_result(answer)
        except ServiceError as error:
            return result_for(sides, attacker, str(error), moves)

        if defender.decks_left() == 0:
            return result_for(sides, defender, "потоплен весь флот", moves)
        if answer == "miss" or repeated:
            turn = 1 - turn

    return MatchResult(None, None, f"ничья: превышен лимит в {MAX_SHOTS} выстрелов", moves, sides)


def play_match(first_client, second_client, first=None, log=print):
    sides = [Side(first_client), Side(second_client)]
    moves = []
    try:
        return play(sides, moves, first, log)
    finally:
        for side in sides:
            side.closed = side.client.close()
