from datetime import date as Date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from till.engine import export_close, reset_night, resume_close, snapshot, start_close
from till.narration import (
    NarrationProviderError,
    NarrationUnavailable,
    generate_narration,
)

WEB = Path(__file__).resolve().parents[1] / "web"

app = FastAPI(title="Till")


class Decision(BaseModel):
    id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    note: str | None = Field(default=None, max_length=240)


class DecideBody(BaseModel):
    decisions: list[Decision] = Field(min_length=1)


class TenderInput(BaseModel):
    method: str = Field(min_length=1, max_length=40)
    amount: float = Field(ge=0, le=100_000_000)
    txn_count: int = Field(ge=0, le=1_000_000)


class ExceptionInput(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["refund", "void", "no-sale"]
    amount: float = Field(default=0, ge=0, le=100_000_000)
    reason: str = Field(min_length=1, max_length=240)
    manager_code: bool = False
    time_hhmm: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    receipt: bool = False


class CloseScenario(BaseModel):
    shop: str = Field(min_length=1, max_length=120)
    owner: str = Field(min_length=1, max_length=120)
    date: Date
    register_name: str = Field(
        alias="register",
        serialization_alias="register",
        min_length=1,
        max_length=80,
    )
    sales_count: int = Field(ge=0, le=10_000_000)
    expected_cash: float = Field(ge=0, le=100_000_000)
    counted_cash: float = Field(ge=0, le=100_000_000)
    tenders: list[TenderInput] = Field(min_length=1, max_length=20)
    exceptions: list[ExceptionInput] = Field(default_factory=list, max_length=100)
    variance_id: str = Field(default="VAR-CLOSE", min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_exception_ids(self) -> "CloseScenario":
        ids = [item.id for item in self.exceptions]
        if len(ids) != len(set(ids)):
            raise ValueError("exception ids must be unique")
        if self.variance_id in ids:
            raise ValueError("variance_id must differ from exception ids")
        return self


class CloseBody(BaseModel):
    scenario: CloseScenario | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"ok": "till"}


@app.get("/api/night")
def api_night() -> dict:
    return snapshot()


@app.get("/api/export")
def api_export() -> JSONResponse:
    try:
        artifact = export_close()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    packet_id = artifact["night"]["packet"]["id"]
    return JSONResponse(
        content=artifact,
        headers={
            "Content-Disposition": f'attachment; filename="till-{packet_id}.json"'
        },
    )


@app.post("/api/close")
def api_close(body: CloseBody | None = None) -> dict:
    scenario = (
        body.scenario.model_dump(by_alias=True) if body and body.scenario else None
    )
    try:
        return start_close(scenario)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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


@app.post("/api/narrate")
def api_narrate() -> dict[str, str]:
    """Ask the optional model to explain observed state, never to decide policy."""

    night = snapshot()
    if not night.get("tape"):
        raise HTTPException(
            status_code=409,
            detail="run the close before requesting an optional explanation",
        )

    try:
        return generate_narration(night)
    except NarrationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except NarrationProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


if WEB.exists():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
