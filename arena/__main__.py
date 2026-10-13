import argparse

from arena.board import render_boards
from arena.client import ServiceClient
from arena.match import play_match


def main():
    parser = argparse.ArgumentParser(
        prog="python -m arena",
        description="Арена морского боя: матч между двумя сервисами",
    )
    parser.add_argument("first", help="адрес первого сервиса, например http://localhost:8001")
    parser.add_argument("second", help="адрес второго сервиса, например http://localhost:8002")
    parser.add_argument("--quiet", action="store_true", help="не печатать каждый выстрел")
    args = parser.parse_args()

    first = ServiceClient("A", base_url=args.first)
    second = ServiceClient("B", base_url=args.second)
    print(f"A: {args.first}")
    print(f"B: {args.second}")

    log = (lambda text: None) if args.quiet else print
    result = play_match(first, second, log=log)

    print()
    print(render_boards(result.sides))
    print()
    if result.winner:
        print(f"Победитель: {result.winner}")
        print(f"Проиграл {result.loser}: {result.reason}")
    else:
        print(result.reason)
    print(f"Выстрелов всего: {len(result.moves)}")
    print(f"Самый долгий ответ: A {first.slowest:.3f} с, B {second.slowest:.3f} с")
    print("Сессии закрыты: " + ", ".join(f"{side.name} - {'да' if side.closed else 'нет'}" for side in result.sides))


if __name__ == "__main__":
    main()
