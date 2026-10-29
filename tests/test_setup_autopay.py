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


def test_setup_autopay_payment_methods_on_file(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "card_last4": "4242", "bank_last4": "6789"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_autopay(payment_method="card_on_file")
    assert reply["status"] == "ok"
    assert "payment_methods_on_file" in reply["data"]
    methods = reply["data"]["payment_methods_on_file"]
    assert any(m.get("type") == "card" and m.get("last4") == "4242" for m in methods)
    assert any(m.get("type") == "card" and m.get("last4") == "8844" for m in methods)
    assert any(m.get("type") == "bank" and m.get("last4") == "6789" for m in methods)


def test_setup_autopay_new_card_capture_required(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "card_last4": "4242"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_autopay(payment_method="new_card")
    assert reply["status"] == "error"
    assert reply["error"] == "CARD_CAPTURE_REQUIRED"
    assert "payment_methods_on_file" in reply["data"]
    assert "spoken_line" in reply["data"]
    assert "security" in reply["data"]["spoken_line"].lower()
    assert "agent_action" in reply["data"]
    assert "keypad" in reply["data"]["agent_action"].lower()


def test_setup_autopay_new_card_capture_required_french(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "card_last4": "4242"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_autopay(payment_method="new_card", language="fr-CA")
    assert reply["status"] == "error"
    assert reply["error"] == "CARD_CAPTURE_REQUIRED"
    assert "sécurité" in reply["data"]["spoken_line"].lower()
    assert "clavier" in reply["data"]["agent_action"].lower()


def test_setup_autopay_new_card_invalid_digits(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "card_last4": "4242"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.setup_autopay(payment_method="new_card", card_digits="1234")
    assert reply["status"] == "error"
    assert reply["error"] == "INVALID_CARD_DIGITS"


def test_setup_autopay_new_card_valid_16_digits(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "card_last4": "4242"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    raw_digits = "4111222233335555"
    reply = tool.setup_autopay(payment_method="new_card", card_digits=raw_digits)
    assert reply["status"] == "ok"
    assert reply["data"]["autopay_enrolled"] is True
    assert reply["data"]["card_last4"] == "5555"
    assert session.state["card_last4"] == "5555"
    assert session.state["card_token"] == "tok_card_5555"
    # Invariant: never echo full raw card number
    assert raw_digits not in str(reply)
    assert raw_digits not in str(session.state)


def test_setup_autopay_new_card_valid_15_digits(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "card_last4": "4242"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    raw_digits = "378282246310005"
    reply = tool.setup_autopay(payment_method="new_card", dtmf_digits=raw_digits)
    assert reply["status"] == "ok"
    assert reply["data"]["autopay_enrolled"] is True
    assert reply["data"]["card_last4"] == "0005"
    assert session.state["card_last4"] == "0005"
    assert raw_digits not in str(reply)

