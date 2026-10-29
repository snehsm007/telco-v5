"""Tests for after_model_callbacks/speech_hygiene across all 5 agents."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
import pytest

from cxas_app.agents.account.after_model_callbacks.speech_hygiene import python_code as account_callback
from cxas_app.agents.billing.after_model_callbacks.speech_hygiene import python_code as billing_callback
from cxas_app.agents.router.after_model_callbacks.speech_hygiene import python_code as router_callback
from cxas_app.agents.sales_equipment.after_model_callbacks.speech_hygiene import python_code as sales_callback
from cxas_app.agents.tech_support.after_model_callbacks.speech_hygiene import python_code as tech_callback

CALLBACKS = [
    router_callback,
    billing_callback,
    tech_callback,
    sales_callback,
    account_callback,
]


def make_response(*texts: str) -> SimpleNamespace:
    parts = [SimpleNamespace(text=text) for text in texts]
    parts.append(SimpleNamespace(text=None, function_call=SimpleNamespace(name="end_session", args={})))
    return SimpleNamespace(content=SimpleNamespace(parts=parts))


class FakePart:
    """Mock Part class supporting from_text."""

    def __init__(self, text: str) -> None:
        self.text = text

    @classmethod
    def from_text(cls, text: str) -> FakePart:
        return cls(text=text)


@pytest.mark.parametrize("callback", CALLBACKS)
def test_cleans_text_parts_and_keeps_tool_calls(callback) -> None:
    response = make_response("**Your number is 2025550143.**", "Anything else?")
    assert callback.after_model_callback(SimpleNamespace(state={}), response) is response
    assert response.content.parts[0].text == "Your number is 0143."
    assert response.content.parts[1].text == "Anything else?"
    assert response.content.parts[2].function_call.name == "end_session"


@pytest.mark.parametrize("callback", CALLBACKS)
def test_injects_handoff_message_when_handover_turn_has_no_spoken_text_simple_namespace(
    callback,
) -> None:
    msg = "Je vous transfère maintenant à un membre de notre équipe. Merci de votre patience."
    state = {"handover_complete": True, "handoff_message": msg}
    tool_only = SimpleNamespace(
        content=SimpleNamespace(
            parts=[SimpleNamespace(text=None, function_call=SimpleNamespace(name="end_session", args={}))]
        )
    )
    res = callback.after_model_callback(SimpleNamespace(state=state), tool_only)
    assert res is tool_only
    assert tool_only.content.parts[0].text == msg


@pytest.mark.parametrize("callback", CALLBACKS)
def test_injects_handoff_message_with_part_from_text(callback, monkeypatch) -> None:
    monkeypatch.setattr(callback, "Part", FakePart, raising=False)
    msg = "I'm transferring you to a member of our team now. Thank you for your patience."
    state = {"handover_complete": True, "handoff_message": msg}
    tool_only = SimpleNamespace(
        content=SimpleNamespace(
            parts=[SimpleNamespace(text="", function_call=None)]
        )
    )
    res = callback.after_model_callback(SimpleNamespace(state=state), tool_only)
    assert res is tool_only
    assert tool_only.content.parts[0].text == msg


@pytest.mark.parametrize("callback", CALLBACKS)
def test_keeps_the_spoken_transfer_line_after_a_handover(callback) -> None:
    msg = "I'm transferring you to a member of our team now. Thank you for your patience."
    state = {"handover_complete": True, "handoff_message": msg}
    step_line = "I'm transferring you to a billing specialist now."
    response = make_response(step_line)
    assert callback.after_model_callback(SimpleNamespace(state=state), response) is None
    assert response.content.parts[0].text == step_line


@pytest.mark.parametrize("callback", CALLBACKS)
def test_returns_none_when_nothing_changes(callback) -> None:
    assert callback.after_model_callback(SimpleNamespace(state={}), make_response("All set.")) is None
    assert callback.after_model_callback(SimpleNamespace(state={}), SimpleNamespace(content=None)) is None
    assert callback.after_model_callback(SimpleNamespace(state={}), SimpleNamespace(content=SimpleNamespace(parts=None))) is None
