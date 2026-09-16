import random

BOARD_SIZE = 10
LETTERS = "ABCDEFGHIJ"

FLEET = {4: 1, 3: 2, 2: 3, 1: 4}
SHIP_SIZES = sorted(
    [size for size, count in FLEET.items() for _ in range(count)], reverse=True
)


def parse_cell(coordinate: str) -> tuple[int, int]:
    letter = coordinate[:1]
    digits = coordinate[1:]

    if letter not in LETTERS or not digits.isdigit():
        raise ValueError(f"некорректная координата: {coordinate!r}")

    row = int(digits)
    if str(row) != digits:
        raise ValueError(f"некорректная координата: {coordinate!r}")
    if row < 1 or row > BOARD_SIZE:
        raise ValueError(f"координата вне поля: {coordinate!r}")

    return LETTERS.index(letter), row - 1


def format_cell(cell: tuple[int, int]) -> str:
    col, row = cell
    return LETTERS[col] + str(row + 1)


def neighbours(cell: tuple[int, int]) -> set:
    col, row = cell
    around = set()
    for dcol in (-1, 0, 1):
        for drow in (-1, 0, 1):
            if dcol != 0 or drow != 0:
                around.add((col + dcol, row + drow))
    return around


def is_straight(cells: list) -> bool:
    if len(cells) == 1:
        return True

    cols = {col for col, row in cells}
    rows = {row for col, row in cells}

    if len(cols) == 1:
        line = sorted(row for col, row in cells)
    elif len(rows) == 1:
        line = sorted(col for col, row in cells)
    else:
        return False

    return line == list(range(line[0], line[0] + len(cells)))


def validate_fleet(ships: list) -> list:
    errors = []
    parsed = []

    for number, ship in enumerate(ships, start=1):
        coordinates = ship.get("coordinates") or []
        if not coordinates:
            errors.append(f"корабль {number}: пустой список координат")
            parsed.append([])
            continue

        try:
            cells = [parse_cell(coordinate) for coordinate in coordinates]
        except ValueError as error:
            errors.append(f"корабль {number}: {error}")
            parsed.append([])
            continue

        if len(set(cells)) != len(cells):
            errors.append(f"корабль {number}: одна и та же клетка указана дважды")
        elif not is_straight(cells):
            errors.append(f"корабль {number}: не прямой или с разрывом")

        parsed.append(cells)

    sizes = sorted([len(cells) for cells in parsed if cells], reverse=True)
    if sizes != SHIP_SIZES:
        errors.append(f"состав флота {sizes} вместо {SHIP_SIZES}")

    owners = {}
    for number, cells in enumerate(parsed, start=1):
        for cell in cells:
            if cell in owners:
                errors.append(
                    f"корабли {owners[cell]} и {number} стоят на клетке {format_cell(cell)}"
                )
            else:
                owners[cell] = number

    for number, cells in enumerate(parsed, start=1):
        for cell in cells:
            for around in neighbours(cell):
                other = owners.get(around)
                if other is not None and other > number:
                    errors.append(f"корабли {number} и {other} соприкасаются")

    return list(dict.fromkeys(errors))


def is_valid_fleet(ships: list) -> bool:
    return len(validate_fleet(ships)) == 0


def place_ship(size: int, forbidden: set):
    for _ in range(200):
        horizontal = random.choice([True, False])
        if horizontal:
            col = random.randint(0, BOARD_SIZE - size)
            row = random.randint(0, BOARD_SIZE - 1)
            cells = [(col + shift, row) for shift in range(size)]
        else:
            col = random.randint(0, BOARD_SIZE - 1)
            row = random.randint(0, BOARD_SIZE - size)
            cells = [(col, row + shift) for shift in range(size)]

        if not forbidden.intersection(cells):
            return cells

    return None


def generate_fleet() -> list:
    for _ in range(100):
        forbidden = set()
        ships = []

        for size in SHIP_SIZES:
            cells = place_ship(size, forbidden)
            if cells is None:
                break

            for cell in cells:
                forbidden.add(cell)
                forbidden.update(neighbours(cell))

            ships.append({"coordinates": [format_cell(cell) for cell in cells]})

        if len(ships) == len(SHIP_SIZES):
            return ships

    raise RuntimeError("не удалось расставить флот")
