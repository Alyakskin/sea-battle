from app.fleet import LETTERS


def board_lines(side):
    ship_cells = {cell for ship in side.ships for cell in ship["coordinates"]}
    lines = [f"Поле {side.name}", "   " + " ".join(LETTERS)]
    for row in range(1, 11):
        marks = []
        for letter in LETTERS:
            cell = f"{letter}{row}"
            result = side.received.get(cell)
            if result in ("hit", "killed"):
                marks.append("X")
            elif result == "miss":
                marks.append("o")
            elif cell in ship_cells:
                marks.append("#")
            else:
                marks.append(".")
        lines.append(f"{row:>2} " + " ".join(marks))
    return lines


def render_boards(sides):
    left, right = board_lines(sides[0]), board_lines(sides[1])
    rows = [f"{a:<26}    {b}" for a, b in zip(left, right)]
    rows.append("")
    rows.append("# корабль   X попадание   o промах   . не обстреляно")
    return "\n".join(rows)
