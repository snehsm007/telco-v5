from types import SimpleNamespace

import cxas_app.tools.verify_login.python_function.python_code as tool


def test_verify_login_happy_path(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "phone_last4": "0143", "auth_status": "code_sent", "auth_failure_count": 0.0}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.verify_login(code="123456")
    assert reply["status"] == "ok"
    assert reply["data"]["verified"] is True
    assert reply["data"]["logged_in"] is True
    assert reply["data"]["auth_status"] == "pass"
    assert session.state["auth_status"] == "pass"


def test_verify_login_context_as_dict(monkeypatch) -> None:
    state_dict = {"account_id": "A1001", "auth_status": "code_sent"}
    monkeypatch.setattr(tool, "context", state_dict, raising=False)
    reply = tool.verify_login(code="123456")
    assert reply["status"] == "ok"
    assert reply["data"]["verified"] is True


def test_verify_login_context_none_with_identifier(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    reply = tool.verify_login(code="123456", identifier="202 555 0143")
    assert reply["status"] == "ok"
    assert reply["data"]["verified"] is True


def test_verify_login_already_verified(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "logged_in": True}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.verify_login(code="123456")
    assert reply["status"] == "ok"
    assert reply["data"]["verified"] is True


def test_verify_login_wrong_code(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "code_sent", "auth_failure_count": 0.0}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.verify_login(code="000000")
    assert reply["status"] == "error"
    assert reply["error"] == "WRONG_CODE"


def test_verify_login_invalid_input(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "code_sent"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.verify_login(code="12")
    assert reply["status"] == "error"
    assert reply["error"] == "INVALID_INPUT"


def test_verify_login_too_many_attempts(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_failure_count": 3.0}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.verify_login(code="123456")
    assert reply["status"] == "error"
    assert reply["error"] == "TOO_MANY_ATTEMPTS"


def test_verify_login_mock_system_down(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "mock_error": "SYSTEM_DOWN"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.verify_login(code="123456")
    assert reply["status"] == "error"
    assert reply["error"] == "SERVICE_UNAVAILABLE"


def test_verify_login_localization(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "code_sent", "auth_failure_count": 0.0}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply_fr = tool.verify_login(code="123456", language="fr-CA")
    assert reply_fr["status"] == "ok"
    session.state["auth_status"] = "code_sent"
    reply_es = tool.verify_login(code="123456", language="es-US")
    assert reply_es["status"] == "ok"


def test_verify_login_populates_card_and_bank_last4(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "code_sent", "auth_failure_count": 0.0}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.verify_login(code="123456")
    assert reply["status"] == "ok"
    assert session.state["card_last4"] == "4242"
    assert session.state["bank_last4"] == "6789"


def test_verify_login_does_not_overwrite_caller_entered_card_last4(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "code_sent", "card_last4": "1111", "auth_failure_count": 0.0}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.verify_login(code="123456")
    assert reply["status"] == "ok"
    assert session.state["card_last4"] == "1111"
    assert session.state["bank_last4"] == "6789"

