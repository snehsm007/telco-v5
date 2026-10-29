from types import SimpleNamespace

import cxas_app.tools.setup_payment_arrangement.python_function.python_code as tool


def test_setup_payment_arrangement_happy_path(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "current_balance": "100.00", "is_suspended": True}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_payment_arrangement(extension_days=14, installments=2, amount="100.00")
    assert reply["status"] == "ok"
    assert reply["data"]["arrangement_active"] is True
    assert reply["data"]["deferred_amount"] == "100.00"
    assert reply["data"]["installments"] == 2
    assert reply["data"]["service_restored"] is True
    assert session.state["service_restored"] is True
    assert session.state["payment_arrangement_active"] is True


def test_setup_payment_arrangement_context_as_dict(monkeypatch) -> None:
    state_dict = {"account_id": "A1001", "auth_status": "pass", "current_balance": "85.50"}
    monkeypatch.setattr(tool, "context", state_dict, raising=False)
    reply = tool.setup_payment_arrangement()
    assert reply["status"] == "ok"
    assert reply["data"]["arrangement_active"] is True


def test_setup_payment_arrangement_context_none_with_inline_auth(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    reply = tool.setup_payment_arrangement(
        identifier="202 555 0143",
        verification_code="123456",
    )
    assert reply["status"] == "ok"
    assert reply["data"]["arrangement_active"] is True


def test_setup_payment_arrangement_default_balance(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "current_balance": "85.50"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_payment_arrangement(amount="")
    assert reply["status"] == "ok"
    assert reply["data"]["deferred_amount"] == "85.50"


def test_setup_payment_arrangement_not_authenticated(monkeypatch) -> None:
    session = SimpleNamespace(state={"account_id": "A1001", "auth_status": "none"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_payment_arrangement()
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_AUTHENTICATED"


def test_setup_payment_arrangement_mock_system_down(monkeypatch) -> None:
    session = SimpleNamespace(state={"account_id": "A1001", "mock_error": "SYSTEM_DOWN"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_payment_arrangement()
    assert reply["status"] == "error"
    assert reply["error"] == "SERVICE_UNAVAILABLE"


def test_setup_payment_arrangement_localization(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "current_balance": "85.50"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply_fr = tool.setup_payment_arrangement(language="fr-CA")
    assert reply_fr["status"] == "ok"
    reply_es = tool.setup_payment_arrangement(language="es-US")
    assert reply_es["status"] == "ok"
