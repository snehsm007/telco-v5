from types import SimpleNamespace

import cxas_app.tools.lookup_account.python_function.python_code as tool
from lib.services import lookup_account_impl


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



def test_lookup_account_blocked_caller_11_digit_nanp(monkeypatch) -> None:
    for raw_blocked in ("+1 (900) 555-0199", "1-800-555-0000", 19005550199):
        session = SimpleNamespace(state={})
        monkeypatch.setattr(tool, "context", session, raising=False)
        reply = tool.lookup_account(raw_blocked)
        assert reply["status"] == "error"
        assert reply["error"] == "PERMISSION_DENIED"
        assert session.state["is_blocked"] is True
        assert "account_id" not in session.state


def test_lookup_account_by_full_name_found(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account(full_name="Taylor")
    assert reply["status"] == "ok"
    assert reply["data"]["account_id"] == "ACC-1002"
    assert reply["data"]["first_name"] == "Taylor"
    assert session.state["account_id"] == "ACC-1002"
    assert session.state["identified"] is True


def test_lookup_account_by_full_name_unknown_synthesis(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account(full_name="Marcus Thorne")
    assert reply["status"] == "ok"
    assert reply["data"]["account_id"] == "A1001"
    assert reply["data"]["first_name"] == "Marcus"
    assert session.state["account_id"] == "A1001"
    assert session.state["contact_email"] == "marcus@example.com"
    assert session.state["phone_last4"] == ""
    assert session.state["caller_provided_phone_last4"] == ""
    assert reply["data"]["phone_last4"] == ""
    assert reply["data"]["linked_mobile_last4"] == ""
    assert reply["data"]["caller_provided_phone_last4"] == ""
    assert session.state["current_balance"] == "85.50"
    assert session.state["past_due_balance"] == "85.50"
    assert session.state["card_last4"] == "4242"
    assert session.state["bank_last4"] == "6789"
    assert "agent_action" in reply["data"]
    assert session.state["identified"] is True


def test_lookup_account_by_name_with_caller_phone(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account(full_name="Marcus Thorne", identifier="514-555-0199")
    assert reply["status"] == "ok"
    assert reply["data"]["phone_last4"] == "0199"
    assert session.state["phone_last4"] == "0199"
    assert session.state["caller_provided_phone_last4"] == "0199"


def test_lookup_account_by_name_with_email(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account(full_name="Marcus Thorne", email="marcus@example.com")
    assert reply["status"] == "ok"
    assert reply["data"].get("email") == "marcus@example.com"
    assert session.state["contact_email"] == "marcus@example.com"
    assert session.state["phone_last4"] == ""


def test_lookup_account_nine_digit_ban_has_no_invented_phone(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account(identifier="928374651")
    assert reply["status"] == "ok"
    assert reply["data"]["phone_last4"] == ""
    assert reply["data"]["linked_mobile_last4"] == ""
    assert session.state["phone_last4"] == ""
    assert session.state["current_balance"] == "85.50"
    assert session.state["past_due_balance"] == "85.50"


def test_lookup_account_by_full_name_and_postal_code(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account(full_name="Marcus Thorne", postal_code="H3Z 2Y7")
    assert reply["status"] == "ok"
    assert session.state["postal_code"] == "H3Z 2Y7"
    assert reply["data"]["regional_alert"] != ""


def test_lookup_account_digits_only_behaves_as_before(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.lookup_account("202 555 0143")
    assert reply["status"] == "ok"
    assert reply["data"]["account_id"] == "A1001"

    session_err = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session_err, raising=False)
    reply_err = tool.lookup_account("9999999999")
    assert reply_err["status"] == "error"
    assert reply_err["error"] == "NOT_FOUND"


def test_lookup_account_impl_direct_name() -> None:
    state: dict = {}
    reply = lookup_account_impl(full_name="Taylor", state=state)
    assert reply["status"] == "ok"
    assert state["account_id"] == "ACC-1002"

    state2: dict = {}
    reply2 = lookup_account_impl(full_name="Marcus Thorne", state=state2)
    assert reply2["status"] == "ok"
    assert state2["account_id"] == "A1001"


