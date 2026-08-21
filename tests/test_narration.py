from fastapi.testclient import TestClient

from till.main import app
from till.narration import build_prompt


def test_narration_prompt_is_bounded_to_observed_close_context():
    prompt = build_prompt(
        {
            "shop": "Oak & Bit Hardware",
            "date": "2026-08-11",
            "status": "waiting",
            "sales": 47,
            "drawer": {"expected": 1240.5, "counted": 1228.0, "variance": -12.5},
            "tape": [{"agent": "cashier", "tool": "count_drawer", "text": "observed"}],
            "open_asks": [
                {
                    "id": "VAR-TILL",
                    "kind": "variance",
                    "amount": -12.5,
                    "reason": "over cap",
                    "status": "open",
                }
            ],
            "packet": None,
            "private_field": "must not be sent",
        }
    )

    assert "Oak & Bit Hardware" in prompt
    assert "VAR-TILL" in prompt
    assert "must not be sent" not in prompt
    assert "Never invent transactions" in prompt


def test_narration_without_key_fails_closed(monkeypatch):
    monkeypatch.delenv("TILL_GEMINI_API_KEY", raising=False)
    client = TestClient(app, raise_server_exceptions=False)

    assert client.post("/api/reset").status_code == 200
    response = client.post("/api/narrate")

    assert response.status_code == 409
    assert "run the close" in response.json()["detail"]


def test_narration_without_key_after_close_reports_configuration(monkeypatch):
    monkeypatch.delenv("TILL_GEMINI_API_KEY", raising=False)
    client = TestClient(app, raise_server_exceptions=False)

    assert client.post("/api/reset").status_code == 200
    assert client.post("/api/close").status_code == 200
    response = client.post("/api/narrate")

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]
