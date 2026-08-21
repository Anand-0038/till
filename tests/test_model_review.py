from strands.types.exceptions import EventLoopException

from till import model_review
from till.store import night, reset


def test_model_review_is_disabled_without_a_provider_key(monkeypatch):
    monkeypatch.delenv("TILL_GEMINI_API_KEY", raising=False)
    reset()

    assert model_review.enabled() is False
    assert model_review.run_model_review() is None


def test_model_review_uses_a_read_only_tool_and_records_the_loop(monkeypatch):
    class FakeResult:
        def __str__(self):
            return "Two observed exceptions need owner attention. This is a local synthetic fixture."

    class FakeAgent:
        def __init__(self, *, tools, **kwargs):
            self.tools = tools
            self.kwargs = kwargs

        def __call__(self, prompt):
            assert "owner" in prompt
            self.tools[0]()
            return FakeResult()

    monkeypatch.setenv("TILL_GEMINI_API_KEY", "test-only-provider-value")
    monkeypatch.setattr(model_review, "Agent", FakeAgent)
    monkeypatch.setattr(model_review, "OpenAIModel", lambda **kwargs: object())
    reset()

    result = model_review.run_model_review()

    assert result is not None
    assert "local synthetic fixture" in result
    assert [line.tool for line in night().tape] == ["read_close_state"]


def test_model_review_provider_failure_returns_explicit_fallback(monkeypatch):
    class FailingAgent:
        def __init__(self, **kwargs):
            pass

        def __call__(self, prompt):
            raise EventLoopException(RuntimeError("provider unavailable"))

    monkeypatch.setenv("TILL_GEMINI_API_KEY", "test-only-provider-value")
    monkeypatch.setattr(model_review, "Agent", FailingAgent)
    monkeypatch.setattr(model_review, "OpenAIModel", lambda **kwargs: object())
    reset()

    assert model_review.run_model_review() == model_review.FALLBACK_MESSAGE
