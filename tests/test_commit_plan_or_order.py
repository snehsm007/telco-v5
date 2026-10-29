from types import SimpleNamespace

import cxas_app.tools.commit_plan_or_order.python_function.python_code as tool


def test_commit_plan_or_order_plan_upgrade_authenticated(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001", "phone_last4": "0143"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.commit_plan_or_order(plan_id="NET-GIG", order_type="plan_upgrade", confirmed=True)
    assert res["status"] == "ok"
    assert res["data"]["plan_id"] == "NET-GIG"
    assert res["data"]["effective_date"] == "immediate"
    assert res["data"]["sms_receipt_sent"] is True
    assert session.state["selected_plan_id"] == "NET-GIG"


def test_commit_plan_or_order_device_with_dict_context(monkeypatch) -> None:
    session_dict = {"auth_status": "pass", "account_id": "A1002", "service_address": "456 Oak St"}
    monkeypatch.setattr(tool, "context", session_dict, raising=False)
    res = tool.commit_plan_or_order(device_name="Wi-Fi Pod 2", order_type="device", confirmed=True)
    assert res["status"] == "ok"
    assert res["data"]["effective_date"] == "2 to 3 business days"
    assert res["data"]["shipping_address_on_file"] == "456 Oak St"


def test_commit_plan_or_order_unauthenticated(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    res = tool.commit_plan_or_order(plan_id="NET-PLUS")
    assert res["status"] == "error"
    assert res["error"] == "NOT_AUTHENTICATED"


def test_commit_plan_or_order_localization_french(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.commit_plan_or_order(plan_id="NET-PLUS", language="fr-CA", confirmed=True)
    assert res["status"] == "ok"
    assert res["data"]["plan_id"] == "NET-PLUS"


def test_commit_plan_or_order_localization_spanish(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.commit_plan_or_order(plan_id="NET-PLUS", language="es-US", confirmed=True)
    assert res["status"] == "ok"
    assert res["data"]["plan_id"] == "NET-PLUS"


def test_commit_plan_or_order_requires_confirmation_flow(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    # 1. Unconfirmed returns REQUIRES_CONFIRMATION
    res_unconfirmed = tool.commit_plan_or_order(plan_id="NET-PLUS", confirmed=False)
    assert res_unconfirmed["status"] == "error"
    assert res_unconfirmed["error"] == "REQUIRES_CONFIRMATION"
    data = res_unconfirmed["data"]
    assert "quote_summary" in data
    assert "monthly_total_with_tax" in data
    assert "estimated_tax" in data
    assert "contract_term" in data
    assert "read the quote" in res_unconfirmed["agent_action"].lower()
    assert "confirmed=true" in res_unconfirmed["agent_action"].lower()

    # 2. Confirmed returns ok
    res_confirmed = tool.commit_plan_or_order(plan_id="NET-PLUS", confirmed=True)
    assert res_confirmed["status"] == "ok"
    assert res_confirmed["data"]["order_id"] != ""
    assert "monthly_total_with_tax" in res_confirmed["data"]


def test_commit_plan_or_order_unknown_plan_id(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.commit_plan_or_order(plan_id="nonexistent_plan_xyz", confirmed=True)
    assert res["status"] == "error"
    assert res["error"] == "UNKNOWN_PLAN_ID"
    assert "valid_plan_ids" in res["data"]
    assert len(res["data"]["valid_plan_ids"]) > 0

