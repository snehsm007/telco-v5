from types import SimpleNamespace

import cxas_app.tools.get_billing_summary.python_function.python_code as tool


def test_get_billing_summary_happy_path(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "current_balance": "85.50"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.get_billing_summary()
    assert reply["status"] == "ok"
    assert "85.50" in reply["data"]["current_balance"]
    assert "due_date" in reply["data"]


def test_get_billing_summary_context_as_dict(monkeypatch) -> None:
    state_dict = {"account_id": "A1001", "auth_status": "pass", "current_balance": "85.50"}
    monkeypatch.setattr(tool, "context", state_dict, raising=False)
    reply = tool.get_billing_summary()
    assert reply["status"] == "ok"
    assert "85.50" in reply["data"]["current_balance"]


def test_get_billing_summary_context_none_with_inline_auth(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    reply = tool.get_billing_summary(identifier="202 555 0143", verification_code="123456")
    assert reply["status"] == "ok"


def test_get_billing_summary_not_authenticated(monkeypatch) -> None:
    session = SimpleNamespace(state={"account_id": "A1001", "auth_status": "none"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.get_billing_summary()
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_AUTHENTICATED"


def test_get_billing_summary_mock_system_down(monkeypatch) -> None:
    session = SimpleNamespace(state={"account_id": "A1001", "mock_error": "SYSTEM_DOWN"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.get_billing_summary()
    assert reply["status"] == "error"
    assert reply["error"] == "SERVICE_UNAVAILABLE"


def test_get_billing_summary_suspended_and_autopay(monkeypatch) -> None:
    session = SimpleNamespace(
        state={
            "account_id": "A1001",
            "auth_status": "pass",
            "is_suspended": True,
            "suspension_reason": "past_due",
            "autopay_enrolled": True,
        }
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.get_billing_summary()
    assert reply["status"] == "ok"
    assert reply["data"]["is_suspended"] is True
    assert reply["data"]["autopay_enrolled"] is True


def test_get_billing_summary_localization(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "current_balance": "85.50"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply_fr = tool.get_billing_summary(language="fr-CA")
    assert reply_fr["status"] == "ok"
    reply_es = tool.get_billing_summary(language="es-US")
    assert reply_es["status"] == "ok"
