from types import SimpleNamespace

import cxas_app.tools.process_bill_payment.python_function.python_code as tool


def test_process_bill_payment_happy_path(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "current_balance": "85.50", "is_suspended": True}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.process_bill_payment(amount="85.50", card_last4="4242")
    assert reply["status"] == "ok"
    assert reply["data"]["payment_processed"] is True
    assert reply["data"]["amount_paid"] == "85.50"
    assert reply["data"]["service_restored"] is True
    assert session.state["service_restored"] is True
    assert session.state["current_balance"] == "0.00"


def test_process_bill_payment_context_as_dict(monkeypatch) -> None:
    state_dict = {"account_id": "A1001", "auth_status": "pass", "current_balance": "50.00"}
    monkeypatch.setattr(tool, "context", state_dict, raising=False)
    reply = tool.process_bill_payment(amount="50.00")
    assert reply["status"] == "ok"
    assert reply["data"]["payment_processed"] is True


def test_process_bill_payment_context_none_with_inline_auth(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    reply = tool.process_bill_payment(
        amount="25.00",
        identifier="202 555 0143",
        verification_code="123456",
    )
    assert reply["status"] == "ok"
    assert reply["data"]["payment_processed"] is True


def test_process_bill_payment_full_balance_string(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "current_balance": "95.00"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.process_bill_payment(amount="full")
    assert reply["status"] == "ok"
    assert reply["data"]["amount_paid"] == "95.00"


def test_process_bill_payment_declined_card(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "payment_failure_count": 0}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.process_bill_payment(amount="50.00", card_last4="0000")
    assert reply["status"] == "error"
    assert reply["error"] == "PAYMENT_DECLINED"


def test_process_bill_payment_too_many_attempts(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "payment_failure_count": 2}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.process_bill_payment(amount="50.00", card_last4="0000")
    assert reply["status"] == "error"
    assert reply["error"] == "TOO_MANY_ATTEMPTS"


def test_process_bill_payment_not_authenticated(monkeypatch) -> None:
    session = SimpleNamespace(state={"account_id": "A1001", "auth_status": "none"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.process_bill_payment(amount="50.00")
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_AUTHENTICATED"


def test_process_bill_payment_mock_system_down(monkeypatch) -> None:
    session = SimpleNamespace(state={"account_id": "A1001", "mock_error": "SYSTEM_DOWN"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.process_bill_payment(amount="50.00")
    assert reply["status"] == "error"
    assert reply["error"] == "SERVICE_UNAVAILABLE"


def test_process_bill_payment_localization(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "current_balance": "50.00"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply_fr = tool.process_bill_payment(amount="50.00", language="fr-CA")
    assert reply_fr["status"] == "ok"
    reply_es = tool.process_bill_payment(amount="50.00", language="es-US")
    assert reply_es["status"] == "ok"
