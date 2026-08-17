from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from till.engine import reset_night, resume_close, snapshot, start_close

WEB = Path(__file__).resolve().parents[1] / "web"

app = FastAPI(title="Till")


class Decision(BaseModel):
    id: str = Field(min_length=1)
    action: str = Field(min_length=1)


class DecideBody(BaseModel):
    decisions: list[Decision] = Field(min_length=1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"ok": "till"}


@app.get("/api/night")
def api_night() -> dict:
    return snapshot()


@app.post("/api/close")
def api_close() -> dict:
    return start_close()


@app.post("/api/decide")
def api_decide(body: DecideBody) -> dict:
    try:
        return resume_close([row.model_dump() for row in body.decisions])
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/reset")
def api_reset() -> dict:
    return reset_night()


if WEB.exists():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
