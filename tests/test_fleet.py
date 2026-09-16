from app.fleet import (
    SHIP_SIZES,
    format_cell,
    generate_fleet,
    is_valid_fleet,
    parse_cell,
    validate_fleet,
)

CORRECT_FLEET = [
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


def replace_ship(index, coordinates):
    fleet = [dict(ship) for ship in CORRECT_FLEET]
    fleet[index] = {"coordinates": coordinates}
    return fleet


def has_error(fleet, text):
    return any(text in error for error in validate_fleet(fleet))


def to_numbers(coordinate):
    return "ABCDEFGHIJ".index(coordinate[0]), int(coordinate[1:])


def test_parse_cell():
    assert parse_cell("A1") == (0, 0)
    assert parse_cell("D7") == (3, 6)
    assert parse_cell("J10") == (9, 9)


def test_format_cell():
    assert format_cell((0, 0)) == "A1"
    assert format_cell((3, 6)) == "D7"
    assert format_cell((9, 9)) == "J10"


def test_parse_cell_rejects_wrong_coordinates():
    wrong = ["K1", "A0", "A11", "1A", "AA", "A", "", "a1", "A01", " A1", "A1 "]
    for coordinate in wrong:
        try:
            parse_cell(coordinate)
        except ValueError:
            continue
        assert False, f"координата {coordinate!r} не должна приниматься"


def test_fleet_rules_from_the_task():
    assert SHIP_SIZES == [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]


def test_correct_fleet_is_valid():
    assert validate_fleet(CORRECT_FLEET) == []


def test_empty_fleet_is_not_valid():
    assert has_error([], "состав флота")


def test_fleet_without_one_ship_is_not_valid():
    assert has_error(CORRECT_FLEET[:-1], "состав флота")


def test_fleet_with_extra_ship_is_not_valid():
    fleet = CORRECT_FLEET + [{"coordinates": ["H9"]}]
    assert has_error(fleet, "состав флота")


def test_ten_ships_with_wrong_sizes_are_not_valid():
    fleet = replace_ship(9, ["H9", "I9"])
    assert len(fleet) == 10
    assert validate_fleet(fleet) == [
        f"состав флота [4, 3, 3, 2, 2, 2, 2, 1, 1, 1] вместо {SHIP_SIZES}"
    ]


def test_five_deck_ship_is_not_allowed():
    assert not is_valid_fleet(replace_ship(0, ["A1", "A2", "A3", "A4", "A5"]))


def test_ship_must_be_straight():
    assert has_error(replace_ship(1, ["C1", "C2", "D2"]), "не прямой")


def test_ship_must_be_without_gaps():
    assert has_error(replace_ship(1, ["C1", "C2", "C4"]), "с разрывом")


def test_ship_with_duplicate_cells_is_not_valid():
    assert has_error(replace_ship(0, ["A1", "A2", "A3", "A3"]), "указана дважды")


def test_ship_without_coordinates_is_not_valid():
    assert has_error(replace_ship(6, []), "пустой список координат")


def test_ship_must_be_inside_the_board():
    assert has_error(replace_ship(6, ["K1"]), "некорректная координата")
    assert has_error(replace_ship(6, ["A11"]), "вне поля")
    assert has_error(replace_ship(3, ["J9", "J10", "J11"]), "вне поля")


def test_ships_can_not_stand_on_the_same_cell():
    assert has_error(replace_ship(3, ["C1", "C2"]), "стоят на клетке")


def test_ships_can_not_touch_by_side():
    assert has_error(replace_ship(3, ["B1", "B2"]), "соприкасаются")


def test_ships_can_not_touch_by_corner():
    assert has_error(replace_ship(6, ["B5"]), "соприкасаются")


def test_one_deck_ships_can_not_stand_diagonally():
    assert has_error(replace_ship(7, ["I2"]), "соприкасаются")


def test_generated_fleet_has_correct_composition():
    ships = generate_fleet()
    sizes = sorted([len(ship["coordinates"]) for ship in ships], reverse=True)
    assert sizes == SHIP_SIZES
    assert sum(sizes) == 20


def test_generated_fleets_are_always_valid():
    for _ in range(200):
        assert validate_fleet(generate_fleet()) == []


def test_generated_fleets_pass_independent_geometry_check():
    for _ in range(100):
        ships = []
        for ship in generate_fleet():
            ships.append([to_numbers(coordinate) for coordinate in ship["coordinates"]])

        for cells in ships:
            for col, row in cells:
                assert 0 <= col <= 9
                assert 1 <= row <= 10

            cols = sorted(col for col, row in cells)
            rows = sorted(row for col, row in cells)
            if len(set(cols)) == 1:
                assert rows == list(range(rows[0], rows[0] + len(cells)))
            else:
                assert len(set(rows)) == 1
                assert cols == list(range(cols[0], cols[0] + len(cells)))

        for i in range(len(ships)):
            for j in range(i + 1, len(ships)):
                for col1, row1 in ships[i]:
                    for col2, row2 in ships[j]:
                        assert max(abs(col1 - col2), abs(row1 - row2)) >= 2


def test_generator_gives_different_fleets():
    first = generate_fleet()
    others = [generate_fleet() for _ in range(20)]
    assert any(fleet != first for fleet in others)
