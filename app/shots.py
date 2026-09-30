import random

from app.fleet import BOARD_SIZE, format_cell, parse_cell

RESULTS = ("miss", "hit", "killed")


def answer_shot(ships: list, opponent_shots: dict, coordinate: str) -> str:
    parse_cell(coordinate)

    if coordinate in opponent_shots:
        return opponent_shots[coordinate]

    damaged = {cell for cell, result in opponent_shots.items() if result != "miss"}

    for ship in ships:
        cells = ship["coordinates"]
        if coordinate not in cells:
            continue
        if all(cell == coordinate or cell in damaged for cell in cells):
            return "killed"
        return "hit"

    return "miss"


def wounded_cells(my_shots: list) -> list:
    wounded = []
    for shot in reversed(my_shots):
        if shot["result"] == "killed":
            break
        if shot["result"] == "hit":
            wounded.append(shot["coordinate"])
    return wounded


def on_board(cell: tuple) -> bool:
    col, row = cell
    return 0 <= col < BOARD_SIZE and 0 <= row < BOARD_SIZE


def targets_around(wounded: list, fired: set) -> list:
    cells = [parse_cell(coordinate) for coordinate in wounded]

    if len(cells) == 1:
        col, row = cells[0]
        candidates = [(col - 1, row), (col + 1, row), (col, row - 1), (col, row + 1)]
    elif len({col for col, row in cells}) == 1:
        col = cells[0][0]
        rows = sorted(row for _, row in cells)
        candidates = [(col, rows[0] - 1), (col, rows[-1] + 1)]
    elif len({row for col, row in cells}) == 1:
        row = cells[0][1]
        cols = sorted(col for col, _ in cells)
        candidates = [(cols[0] - 1, row), (cols[-1] + 1, row)]
    else:
        candidates = []

    return [
        format_cell(cell)
        for cell in candidates
        if on_board(cell) and format_cell(cell) not in fired
    ]


def choose_shot(my_shots: list) -> str:
    fired = {shot["coordinate"] for shot in my_shots}

    wounded = wounded_cells(my_shots)
    if wounded:
        targets = targets_around(wounded, fired)
        if targets:
            return targets[0]

    free = []
    checkerboard = []
    for col in range(BOARD_SIZE):
        for row in range(BOARD_SIZE):
            coordinate = format_cell((col, row))
            if coordinate in fired:
                continue
            free.append(coordinate)
            if (col + row) % 2 == 0:
                checkerboard.append(coordinate)

    if checkerboard:
        return random.choice(checkerboard)
    if free:
        return random.choice(free)

    raise RuntimeError("стрелять больше некуда")
