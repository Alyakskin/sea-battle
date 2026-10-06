import pytest

from app.fleet import parse_cell
from app.shots import answer_shot, cells_around_killed, choose_shot, targets_around, wounded_cells

SHIPS = [
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


def shots(*pairs):
    return [{"coordinate": coordinate, "result": result} for coordinate, result in pairs]


def test_shot_into_empty_cell_is_miss():
    assert answer_shot(SHIPS, {}, "B5") == "miss"


def test_shot_into_ship_is_hit():
    assert answer_shot(SHIPS, {}, "A1") == "hit"


def test_one_deck_ship_is_killed_at_once():
    assert answer_shot(SHIPS, {}, "J1") == "killed"


def test_ship_is_killed_only_after_last_deck():
    opponent_shots = {}
    for coordinate in ["A1", "A2", "A3"]:
        result = answer_shot(SHIPS, opponent_shots, coordinate)
        assert result == "hit"
        opponent_shots[coordinate] = result

    assert answer_shot(SHIPS, opponent_shots, "A4") == "killed"


def test_damaged_ship_is_not_killed_by_a_miss_nearby():
    opponent_shots = {"C1": "hit", "C2": "hit", "B5": "miss"}

    assert answer_shot(SHIPS, opponent_shots, "C3") == "killed"


def test_repeated_shot_returns_the_same_answer():
    opponent_shots = {"A1": "hit", "B5": "miss", "J1": "killed"}

    assert answer_shot(SHIPS, opponent_shots, "A1") == "hit"
    assert answer_shot(SHIPS, opponent_shots, "B5") == "miss"
    assert answer_shot(SHIPS, opponent_shots, "J1") == "killed"


def test_sunken_ship_answers_killed_only_once():
    opponent_shots = {"A6": "hit", "A7": "killed"}

    assert answer_shot(SHIPS, opponent_shots, "A6") == "hit"
    assert answer_shot(SHIPS, opponent_shots, "A7") == "killed"


def test_answer_needs_correct_coordinate():
    for coordinate in ["K1", "A11", "a1", "", "A01"]:
        with pytest.raises(ValueError):
            answer_shot(SHIPS, {}, coordinate)


def test_wounded_cells_are_taken_after_last_kill():
    history = shots(("B2", "miss"), ("D4", "hit"), ("D5", "killed"), ("F6", "hit"), ("F7", "miss"))

    assert wounded_cells(history) == ["F6"]


def test_first_shot_goes_to_checkerboard_cell():
    for _ in range(50):
        col, row = parse_cell(choose_shot([]))
        assert (col + row) % 2 == 0


def test_service_never_repeats_its_shots():
    history = []
    for _ in range(100):
        coordinate = choose_shot(history)
        assert coordinate not in [shot["coordinate"] for shot in history]
        history.append({"coordinate": coordinate, "result": "miss"})

    assert len(history) == 100


def test_no_shots_left_is_an_error():
    history = shots(*((f"{letter}{number}", "miss") for letter in "ABCDEFGHIJ" for number in range(1, 11)))

    with pytest.raises(RuntimeError):
        choose_shot(history)


def test_after_hit_service_shoots_next_to_it():
    history = shots(("D4", "hit"))

    assert choose_shot(history) in ["C4", "E4", "D3", "D5"]


def test_two_hits_in_a_row_continue_the_line():
    history = shots(("D4", "hit"), ("D5", "hit"))

    assert choose_shot(history) in ["D3", "D6"]


def test_two_hits_in_a_column_continue_the_line():
    history = shots(("D4", "hit"), ("E4", "hit"))

    assert choose_shot(history) in ["C4", "F4"]


def test_busy_cells_are_skipped_while_finishing_a_ship():
    history = shots(("D4", "hit"), ("D3", "miss"))
    coordinate = choose_shot(history)

    assert coordinate != "D3"
    assert coordinate in ["C4", "E4", "D5"]


def test_after_kill_service_returns_to_search():
    history = shots(("D4", "hit"), ("D5", "killed"))
    coordinate = choose_shot(history)

    col, row = parse_cell(coordinate)
    assert (col + row) % 2 == 0
    assert coordinate not in ["D4", "D5"]


def test_cells_around_killed_ship_are_found():
    history = shots(("D4", "hit"), ("D5", "killed"))

    assert cells_around_killed(history) == {
        "C3", "D3", "E3", "C4", "D4", "E4", "C5", "D5", "E5", "C6", "D6", "E6",
    }


def test_service_does_not_shoot_around_killed_ship():
    history = shots(("D4", "hit"), ("D5", "killed"))
    around = {"C3", "D3", "E3", "C4", "E4", "C5", "E5", "C6", "D6", "E6"}

    for _ in range(100):
        assert choose_shot(history) not in around


def test_finishing_a_ship_skips_cells_near_killed_one():
    history = shots(("B2", "killed"), ("D2", "hit"))

    assert choose_shot(history) in ["E2", "D1", "D3"]


def test_targets_around_ignore_cells_outside_the_board():
    assert sorted(targets_around(["A1"], set())) == ["A2", "B1"]
