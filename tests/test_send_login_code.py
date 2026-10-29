from types import SimpleNamespace

import cxas_app.tools.send_login_code.python_function.python_code as tool


def test_send_login_code_happy_path(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "phone_last4": "0143", "auth_status": "none", "auth_failure_count": 0.0}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code()
    assert reply["status"] == "ok"
    assert reply["data"]["sent"] is True
    assert reply["data"]["destination_last4"] == "0143"
    assert session.state["auth_status"] == "code_sent"


def test_send_login_code_context_as_dict(monkeypatch) -> None:
    state_dict = {"account_id": "A1001", "phone_last4": "0143"}
    monkeypatch.setattr(tool, "context", state_dict, raising=False)
    reply = tool.send_login_code(channel="sms")
    assert reply["status"] == "ok"
    assert reply["data"]["sent"] is True


def test_send_login_code_context_none_with_identifier(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    reply = tool.send_login_code(identifier="202 555 0143")
    assert reply["status"] == "ok"
    assert reply["data"]["sent"] is True


def test_send_login_code_already_verified(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "logged_in": True}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code()
    assert reply["status"] == "ok"
    assert reply["data"]["already_verified"] is True


def test_send_login_code_too_many_attempts(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_failure_count": 3.0}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code()
    assert reply["status"] == "error"
    assert reply["error"] == "TOO_MANY_ATTEMPTS"


def test_send_login_code_channel_email(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "none", "contact_email": "test@example.com"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code(channel="email")
    assert reply["status"] == "ok"
    assert reply["data"]["channel"] == "email"
    assert "masked_email" in reply["data"]


def test_send_login_code_mock_system_down(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "mock_error": "SYSTEM_DOWN"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code()
    assert reply["status"] == "error"
    assert reply["error"] == "SERVICE_UNAVAILABLE"


def test_send_login_code_localization(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "phone_last4": "0143", "auth_status": "none"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply_fr = tool.send_login_code(language="fr-CA")
    assert reply_fr["status"] == "ok"
    session.state["auth_status"] = "none"
    reply_es = tool.send_login_code(language="es-US")
    assert reply_es["status"] == "ok"


def test_send_login_code_unidentified_returns_error(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code()
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_IDENTIFIED"
    assert "agent_action" in reply
    assert "mobile number" in reply["agent_action"].lower() or "10-digit" in reply["agent_action"].lower()


def test_send_login_code_accepts_caller_given_phone_and_records_last4(monkeypatch) -> None:
    session = SimpleNamespace(state={"account_id": "ACC-4651", "phone_last4": ""})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code(identifier="514-555-0199")
    assert reply["status"] == "ok"
    assert reply["data"]["sent"] is True
    assert reply["data"]["destination_last4"] == "0199"
    assert session.state["caller_provided_phone_last4"] == "0199"
    assert session.state["phone_last4"] == "0199"
