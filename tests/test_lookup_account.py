from types import SimpleNamespace

import cxas_app.tools.lookup_account.python_function.python_code as tool


def test_lookup_account_happy_path_simplenamespace(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "none", "auth_failure_count": 0.0})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account("202 555 0143")
    assert reply["status"] == "ok"
    assert reply["data"]["account_id"] == "A1001"
    assert session.state["account_id"] == "A1001"
    assert session.state["caller_provided_phone_last4"] == "0143"


def test_lookup_account_context_as_dict(monkeypatch) -> None:
    state_dict = {"auth_status": "none"}
    monkeypatch.setattr(tool, "context", state_dict, raising=False)
    reply = tool.lookup_account("202-555-0143")
    assert reply["status"] == "ok"
    assert reply["data"]["account_id"] == "A1001"
    assert state_dict["account_id"] == "A1001"


def test_lookup_account_context_none(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    reply = tool.lookup_account("202 555 0143")
    assert reply["status"] == "ok"
    assert reply["data"]["account_id"] == "A1001"


def test_lookup_account_invalid_empty_input(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account("")
    assert reply["status"] == "error"
    assert reply["error"] == "INVALID_INPUT"


def test_lookup_account_not_found(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account("9999999999")
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_FOUND"


def test_lookup_account_business_inquiry(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account(
        identifier="202 555 0143",
        is_business_inquiry=True,
    )
    assert reply["status"] == "ok"
    assert reply["data"]["business_flag"] is True
    assert reply["data"]["must_escalate_immediately"] is True


def test_lookup_account_blocked_caller(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account("8005550000")
    assert reply["status"] == "error"
    assert reply["error"] == "PERMISSION_DENIED"


def test_lookup_account_localization(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply_fr = tool.lookup_account("202 555 0143", language="fr-CA")
    assert reply_fr["status"] == "ok"
    reply_es = tool.lookup_account("202 555 0143", language="es-US")
    assert reply_es["status"] == "ok"


def test_lookup_account_populates_card_and_bank_last4(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account("202 555 0143")
    assert reply["status"] == "ok"
    assert session.state["card_last4"] == "4242"
    assert session.state["bank_last4"] == "6789"

