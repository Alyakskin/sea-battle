from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.fleet import generate_fleet
from app.models import Game
from app.schemas import StartGameResponse

app = FastAPI(title="Sea Battle service")


@app.exception_handler(Exception)
def unexpected_error(request: Request, error: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/game",
    response_model=StartGameResponse,
    status_code=201,
    responses={500: {"description": "Непредвиденная ошибка"}},
)
def start_game(db: Session = Depends(get_db)):
    game = Game(ships=generate_fleet())

    db.add(game)
    db.commit()
    db.refresh(game)

    return StartGameResponse(session_id=game.session_id, ships=game.ships)
