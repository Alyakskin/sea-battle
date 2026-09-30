import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db import get_db
from app.fleet import generate_fleet
from app.models import Game
from app.schemas import (
    AcceptedResponse,
    CloseResponse,
    OpponentShotResponse,
    ShotRequest,
    ShotResponse,
    ShotResultRequest,
    StartGameResponse,
)
from app.shots import answer_shot, choose_shot

app = FastAPI(title="Sea Battle service")

ERRORS = {
    400: {"description": "Некорректные данные запроса"},
    404: {"description": "Сессия не найдена"},
    409: {"description": "Нарушена последовательность игры"},
    410: {"description": "Сессия завершена"},
    500: {"description": "Непредвиденная ошибка"},
}


@app.exception_handler(Exception)
def unexpected_error(request: Request, error: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.exception_handler(RequestValidationError)
def wrong_request(request: Request, error: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": "некорректные данные запроса"})


def parse_session_id(session_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="сессия не найдена")


def get_game(db: Session, session_id: str) -> Game:
    game_id = parse_session_id(session_id)

    game = db.get(Game, game_id, with_for_update=True)
    if game is None:
        raise HTTPException(status_code=404, detail="сессия не найдена")
    if game.status != "active":
        raise HTTPException(status_code=410, detail="сессия завершена")

    return game


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/game",
    response_model=StartGameResponse,
    status_code=201,
    responses={500: ERRORS[500]},
)
def start_game(db: Session = Depends(get_db)):
    game = Game(ships=generate_fleet())

    db.add(game)
    db.commit()
    db.refresh(game)

    return StartGameResponse(session_id=game.session_id, ships=game.ships)


@app.post(
    "/game/{session_id}/shot",
    response_model=ShotResponse,
    responses={code: ERRORS[code] for code in (404, 409, 410, 500)},
)
def make_shot(session_id: str, db: Session = Depends(get_db)):
    game = get_game(db, session_id)

    if game.my_shots and game.my_shots[-1]["result"] is None:
        raise HTTPException(status_code=409, detail="предыдущий выстрел ещё без результата")

    coordinate = choose_shot(game.my_shots)
    game.my_shots = game.my_shots + [{"coordinate": coordinate, "result": None}]
    db.commit()

    return ShotResponse(coordinate=coordinate)


@app.post(
    "/game/{session_id}/shot/result",
    response_model=AcceptedResponse,
    responses={code: ERRORS[code] for code in (400, 404, 409, 410, 500)},
)
def accept_shot_result(
    session_id: str, request: ShotResultRequest, db: Session = Depends(get_db)
):
    game = get_game(db, session_id)

    if not game.my_shots or game.my_shots[-1]["result"] is not None:
        raise HTTPException(status_code=409, detail="нет выстрела, ожидающего результата")

    shots = [dict(shot) for shot in game.my_shots]
    shots[-1]["result"] = request.result
    game.my_shots = shots
    db.commit()

    return AcceptedResponse(status="accepted")


@app.post(
    "/game/{session_id}/opponent-shot",
    response_model=OpponentShotResponse,
    responses={code: ERRORS[code] for code in (400, 404, 410, 500)},
)
def opponent_shot(
    session_id: str, request: ShotRequest, db: Session = Depends(get_db)
):
    game = get_game(db, session_id)

    try:
        result = answer_shot(game.ships, game.opponent_shots, request.coordinate)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    game.opponent_shots = {**game.opponent_shots, request.coordinate: result}
    db.commit()

    return OpponentShotResponse(result=result)


@app.post(
    "/game/{session_id}/close",
    response_model=CloseResponse,
    responses={code: ERRORS[code] for code in (400, 404, 500)},
)
def close_game(session_id: str, db: Session = Depends(get_db)):
    game_id = parse_session_id(session_id)

    closed = db.execute(
        update(Game)
        .where(Game.session_id == game_id, Game.status == "active")
        .values(status="closed")
    )
    db.commit()

    if closed.rowcount == 1:
        return CloseResponse(status="closed")

    if db.get(Game, game_id) is None:
        raise HTTPException(status_code=404, detail="сессия не найдена")

    raise HTTPException(status_code=400, detail="сессия уже закрыта")
