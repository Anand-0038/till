from fastapi.testclient import TestClient

from till.main import app


def _close_then_decide(client: TestClient) -> tuple[dict, dict]:
    closed = client.post("/api/close").json()
    decided = client.post(
        "/api/decide",
        json={
            "decisions": [
                {"id": "VAR-TILL", "action": "accept"},
                {"id": "REF-4412", "action": "approve"},
            ]
        },
    ).json()
    return closed, decided


def test_http_close_pauses_then_decide_locks():
    client = TestClient(app)
    client.post("/api/reset")
    closed, decided = _close_then_decide(client)
    assert closed["run"]["status"] == "interrupted"
    assert {card["id"] for card in closed["open_asks"]} == {"VAR-TILL", "REF-4412"}
    assert closed["packet"] is None
    assert decided["status"] == "locked"
    assert decided["packet"]["id"] == "DEP-2026-08-11"
    assert decided["packet"]["cash_to_drop"] == 1228.00


def test_http_board_is_not_chat():
    client = TestClient(app)
    page = client.get("/")
    assert page.status_code == 200
    body = page.text
    assert "Run night close" in body
    assert "Decision Inbox" in body
    assert "Register tape" in body
    assert "Deposit packet" in body
    assert "<textarea" not in body.lower()
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ok"] == "till"


def test_http_initial_board_has_no_open_asks():
    client = TestClient(app)
    snapshot = client.post("/api/reset").json()

    assert snapshot["status"] == "open"
    assert snapshot["open_asks"] == []
    assert snapshot["cards"] == []


def test_http_rejects_invalid_decisions_without_server_error():
    client = TestClient(app, raise_server_exceptions=False)
    client.post("/api/reset")
    client.post("/api/close")

    response = client.post(
        "/api/decide",
        json={"decisions": [{"id": "NOPE", "action": "accept"}]},
    )

    assert response.status_code == 422
    assert "unknown card NOPE" in response.json()["detail"]

    snapshot = client.get("/api/night").json()
    assert {card["id"] for card in snapshot["open_asks"]} == {"VAR-TILL", "REF-4412"}


def test_http_rejects_incomplete_decisions_without_partial_owner_tape():
    client = TestClient(app, raise_server_exceptions=False)
    client.post("/api/reset")
    client.post("/api/close")

    response = client.post(
        "/api/decide",
        json={"decisions": [{"id": "VAR-TILL", "action": "accept"}]},
    )

    assert response.status_code == 422
    assert "REF-4412" in response.json()["detail"]
    snapshot = client.get("/api/night").json()
    assert not any(line["agent"] == "owner" for line in snapshot["tape"])
