from types import SimpleNamespace

import cxas_app.tools.execute_suspend_restore.python_function.python_code as tool


def test_execute_suspend_restore_unauthenticated(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "none"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.execute_suspend_restore(action="suspend")
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_AUTHENTICATED"


def test_execute_suspend_vacation_happy_path(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.execute_suspend_restore(action="suspend", reason="vacation")
    assert reply["status"] == "ok"
    assert reply["data"]["service_suspended"] is True
    assert reply["data"]["is_suspended"] is True
    assert reply["data"]["reduced_rate_monthly"] == "15.00"
    assert "confirmation_number" in reply["data"]
    assert session.state["is_suspended"] is True


def test_execute_suspend_other_reason(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.execute_suspend_restore(action="suspend", reason="travel")
    assert reply["status"] == "ok"
    assert reply["data"]["reduced_rate_monthly"] == "0.00"


def test_execute_restore_happy_path(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"auth_status": "pass", "account_id": "A1001", "is_suspended": True}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.execute_suspend_restore(action="restore")
    assert reply["status"] == "ok"
    assert reply["data"]["service_restored"] is True
    assert reply["data"]["is_suspended"] is False
    assert reply["data"]["restoration_eta_minutes"] == 15
    assert session.state["is_suspended"] is False


def test_execute_restore_blocked_by_past_due(monkeypatch) -> None:
    session = SimpleNamespace(
        state={
            "auth_status": "pass",
            "account_id": "A1001",
            "is_suspended": True,
            "suspension_reason": "non_payment",
            "past_due_balance": "150.00",
            "payment_arrangement_active": False,
        }
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.execute_suspend_restore(action="restore")
    assert reply["status"] == "error"
    assert reply["error"] == "PAST_DUE_BALANCE_REQUIRED"


def test_execute_restore_allowed_after_posted_payment(monkeypatch) -> None:
    session = SimpleNamespace(
        state={
            "auth_status": "pass",
            "account_id": "A1001",
            "is_suspended": False,
            "suspension_reason": "",
            "past_due_balance": "85.50",
            "payment_arrangement_active": False,
        }
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.execute_suspend_restore(action="restore")
    assert reply["status"] == "ok"
    assert reply["data"]["status"] == "restored"
    assert reply["data"]["service_restored"] is True
    assert reply["data"]["restored_after_payment"] is True
    assert reply["data"]["is_suspended"] is False
    assert reply["data"]["past_due_balance"] == "0.00"
    assert reply["data"]["restoration_eta_minutes"] == 15
    assert session.state["is_suspended"] is False
    assert session.state["past_due_balance"] == "0.00"


def test_execute_restore_allowed_with_payment_arrangement(monkeypatch) -> None:
    session = SimpleNamespace(
        state={
            "auth_status": "pass",
            "account_id": "A1001",
            "is_suspended": True,
            "suspension_reason": "non_payment",
            "past_due_balance": "85.50",
            "payment_arrangement_active": True,
        }
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.execute_suspend_restore(action="restore")
    assert reply["status"] == "ok"
    assert reply["data"]["service_restored"] is True


def test_execute_suspend_inline_auth(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "none"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.execute_suspend_restore(
        action="suspend",
        identifier="2025550143",
        verification_code="1234",
    )
    assert reply["status"] == "ok"
    assert reply["data"]["service_suspended"] is True


def test_execute_suspend_dict_context(monkeypatch) -> None:
    ctx = {"auth_status": "pass", "account_id": "A1001"}
    monkeypatch.setattr(tool, "context", ctx, raising=False)
    reply = tool.execute_suspend_restore(action="suspend")
    assert reply["status"] == "ok"
    assert reply["data"]["service_suspended"] is True


def test_execute_suspend_none_context(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    reply = tool.execute_suspend_restore(action="suspend")
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_AUTHENTICATED"


def test_execute_suspend_localization(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.execute_suspend_restore(action="suspend", language="fr-CA")
    assert reply["status"] == "ok"
    assert session.state["language"] == "fr-CA"
