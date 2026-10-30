"""Tests for cxas_app/tools wrappers and core tool functions."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
import pytest

import cxas_app.tools.browse_plans_and_coverage.python_function.python_code as browse_tool
import cxas_app.tools.check_regional_outage.python_function.python_code as outage_tool
import cxas_app.tools.get_billing_summary.python_function.python_code as billing_tool
import cxas_app.tools.handover_to_person.python_function.python_code as handover_tool
import cxas_app.tools.lookup_account.python_function.python_code as lookup_tool
import cxas_app.tools.send_login_code.python_function.python_code as send_code_tool
import cxas_app.tools.verify_login.python_function.python_code as verify_login_tool
from lib.services import (
    ALL_TOOLS,
    handover_to_person,
    lookup_account,
    record_payment_attempt,
    send_login_code,
    verify_login,
)


def test_three_strike_login_lockout_and_direct_code_entry(monkeypatch) -> None:
    session = SimpleNamespace(state={"account_id": "A1001", "phone_last4": "0143"})
    for mod in (
        lookup_tool,
        send_code_tool,
        verify_login_tool,
        handover_tool,
        billing_tool,
        outage_tool,
        browse_tool,
    ):
        monkeypatch.setattr(mod, "context", session, raising=False)

    # Placeholder code does not consume strikes
    r_place = verify_login_tool.verify_login("0000")
    assert r_place["error"] == "CODE_NOT_RECEIVED"
    assert r_place["data"]["attempts_remaining"] == 3

    # 3 strikes with real wrong code in verify_login wrapper
    r1 = verify_login_tool.verify_login("9999")
    r2 = verify_login_tool.verify_login("9999")
    r3 = verify_login_tool.verify_login("9999")
    assert r1["data"]["attempts_remaining"] == 2
    assert r2["data"]["attempts_remaining"] == 1
    assert r3["error"] == "TOO_MANY_ATTEMPTS"
    assert r3["data"]["lockout_triggered"] is True

    # Direct login without prior send_login_code on an identified state
    fresh = SimpleNamespace(state={"account_id": "A1001", "phone_last4": "0143"})
    monkeypatch.setattr(verify_login_tool, "context", fresh, raising=False)
    ok = verify_login_tool.verify_login("1234")
    assert ok["status"] == "ok" and ok["data"]["verified"] is True
    assert verify_login(code="1234", state={"account_id": "A1001"})["status"] == "ok"


def test_domain_tool_wrappers_with_mock_context(monkeypatch) -> None:
    state = {
        "account_id": "A1001",
        "phone_last4": "0143",
        "auth_status": "pass",
        "current_balance": "85.50",
    }
    session = SimpleNamespace(state=state)
    for mod in (billing_tool, outage_tool, browse_tool):
        monkeypatch.setattr(mod, "context", session, raising=False)

    # Billing tool wrapper
    bill_res = billing_tool.get_billing_summary()
    assert bill_res["status"] == "ok"
    assert "current_balance" in bill_res["data"]

    # Outage tool wrapper
    outage_res = outage_tool.check_regional_outage(postal_code="H3Z 2Y7")
    assert outage_res["status"] == "ok"
    assert outage_res["data"]["outage_active"] is True

    # Browse plans tool wrapper
    browse_res = browse_tool.browse_plans_and_coverage(category="internet")
    assert browse_res["status"] == "ok"
    assert len(browse_res["data"]["shortlisted_plans"]) >= 2


def test_handover_language_detection_and_payment_lockout() -> None:
    r_fr = handover_to_person(reason="besoin d'un agent", language="fr-CA")
    assert "transfère" in r_fr["data"].get("handoff_message", "") or "représentant" in r_fr["data"].get("handoff_message", "")

    state_es = {"language": "es-US"}
    r_es = handover_to_person(reason="billing", state=state_es)
    assert r_es["data"]["language"] == "es-US"
    assert "transfiero" in r_es["data"].get("handoff_message", "") or "representante" in r_es["data"].get("handoff_message", "")
    explicit = handover_to_person(reason="billing", language="en-US", state={"language": "es-US"})
    assert explicit["data"]["language"] == "es-US"

    pay_state: dict[str, Any] = {}
    assert record_payment_attempt(pay_state, False)["error"] == "PAYMENT_DECLINED"
    assert record_payment_attempt(pay_state, False)["error"] == "PAYMENT_DECLINED"
    assert record_payment_attempt(pay_state, False)["error"] == "TOO_MANY_ATTEMPTS"


def _find_multilingual_keys(obj: Any, path: str = "") -> list[str]:
    bad: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            current_path = f"{path}.{k}" if path else str(k)
            if str(k).endswith(("_en", "_fr", "_es")):
                bad.append(current_path)
            bad.extend(_find_multilingual_keys(v, current_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            bad.extend(_find_multilingual_keys(item, f"{path}[{i}]"))
    return bad


@pytest.mark.parametrize("lang", ["en-US", "fr-CA", "es-US"])
def test_all_22_tools_no_multilingual_keys_leak(lang: str) -> None:
    from lib import services

    sample_args: dict[str, dict[str, Any]] = {
        "lookup_account": {"identifier": "555-123-4567"},
        "send_login_code": {"destination": "555-123-4567"},
        "verify_login": {"code": "1234"},
        "handover_to_person": {"department": "billing", "reason": "complex billing issue"},
        "get_billing_summary": {},
        "process_bill_payment": {"amount": "50.00", "payment_method_id": "CARD-1"},
        "setup_payment_arrangement": {"arrangement_date": "2026-11-15", "installments": 2},
        "setup_autopay": {"action": "enroll", "payment_method_id": "CARD-1"},
        "process_refund_or_dispute": {"charge_id": "CHG-101", "reason": "unrecognized_charge"},
        "check_regional_outage": {"postal_code": "H3Z 2Y7"},
        "run_troubleshooting_and_sms": {"service_type": "internet", "symptom": "slow_speed"},
        "get_appointment_and_ticket_status": {},
        "manage_appointment": {"action": "reschedule", "selected_slot": "SLOT-1"},
        "browse_plans_and_coverage": {"category": "internet"},
        "commit_plan_or_order": {"plan_id": "NET-PLUS", "confirmed": True},
        "initiate_number_transfer": {
            "phone_to_transfer": "555-123-4567",
            "current_carrier": "OtherCarrier",
            "carrier_account_number": "ACC-123",
            "port_pin": "1234",
        },
        "manage_warranty_claim": {"issue_description": "broken screen", "claim_type": "repair"},
        "send_password_reset_sms": {"phone_number": "555-123-4567"},
        "manage_mfa_settings": {"action": "status"},
        "execute_suspend_restore": {"action": "suspend"},
        "update_contact_profile": {"email": "test@example.com"},
        "cancel_or_port_out_service": {"action": "cancel", "confirmed": True},
    }

    assert len(services.ALL_TOOLS) == 22
    for tool_name in services.ALL_TOOLS:
        fn = getattr(services, f"{tool_name}_impl")
        args = sample_args.get(tool_name, {})
        state = {
            "auth_status": "pass",
            "account_id": "A1001",
            "phone_last4": "0143",
            "language": lang,
            "active_appointment_id": "APT-4021",
        }
        res = fn(**args, state=state, language=lang)
        bad_keys = _find_multilingual_keys(res)
        assert not bad_keys, f"Tool {tool_name} leaked multilingual keys in locale {lang}: {bad_keys}"

