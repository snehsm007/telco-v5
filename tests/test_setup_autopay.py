from types import SimpleNamespace

import cxas_app.tools.setup_autopay.python_function.python_code as tool


def test_setup_autopay_happy_path(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "card_last4": "4242"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_autopay(payment_method="card", last4="4242", billing_day=15)
    assert reply["status"] == "ok"
    assert reply["data"]["autopay_enrolled"] is True
    assert reply["data"]["payment_method"] == "card"
    assert reply["data"]["billing_day"] == 15
    assert session.state["autopay_enrolled"] is True


def test_setup_autopay_context_as_dict(monkeypatch) -> None:
    state_dict = {"account_id": "A1001", "auth_status": "pass"}
    monkeypatch.setattr(tool, "context", state_dict, raising=False)
    reply = tool.setup_autopay(payment_method="card", last4="4242")
    assert reply["status"] == "ok"
    assert reply["data"]["autopay_enrolled"] is True


def test_setup_autopay_context_none_with_inline_auth(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    reply = tool.setup_autopay(
        identifier="202 555 0143",
        verification_code="123456",
        last4="4242",
    )
    assert reply["status"] == "ok"
    assert reply["data"]["autopay_enrolled"] is True


def test_setup_autopay_cancel(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "autopay_enrolled": True}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_autopay(action="cancel")
    assert reply["status"] == "ok"
    assert reply["data"]["autopay_enrolled"] is False
    assert reply["data"]["cancelled"] is True
    assert session.state["autopay_enrolled"] is False


def test_setup_autopay_bank_account(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_autopay(payment_method="bank", last4="6789")
    assert reply["status"] == "ok"
    assert reply["data"]["payment_method"] == "bank"
    assert session.state["bank_last4"] == "6789"


def test_setup_autopay_declined_card(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_autopay(payment_method="card", last4="0000")
    assert reply["status"] == "error"
    assert reply["error"] == "PAYMENT_DECLINED"


def test_setup_autopay_not_authenticated(monkeypatch) -> None:
    session = SimpleNamespace(state={"account_id": "A1001", "auth_status": "none"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_autopay()
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_AUTHENTICATED"


def test_setup_autopay_mock_system_down(monkeypatch) -> None:
    session = SimpleNamespace(state={"account_id": "A1001", "mock_error": "SYSTEM_DOWN"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_autopay()
    assert reply["status"] == "error"
    assert reply["error"] == "SERVICE_UNAVAILABLE"


def test_setup_autopay_localization(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "card_last4": "4242"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply_fr = tool.setup_autopay(language="fr-CA")
    assert reply_fr["status"] == "ok"
    reply_es = tool.setup_autopay(language="es-US")
    assert reply_es["status"] == "ok"
