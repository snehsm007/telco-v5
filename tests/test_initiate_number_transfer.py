from types import SimpleNamespace

import cxas_app.tools.initiate_number_transfer.python_function.python_code as tool


def test_initiate_number_transfer_checklist_inquiry(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.initiate_number_transfer(phone_to_transfer="5145550199", current_carrier="Rogers")
    assert res["status"] == "ok"
    assert res["data"]["mode"] == "checklist_provided"
    assert len(res["data"]["required_port_checklist"]) == 4


def test_initiate_number_transfer_submission_unauthenticated(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    res = tool.initiate_number_transfer(
        phone_to_transfer="5145550199",
        current_carrier="Rogers",
        carrier_account_number="987654321",
        port_pin="1234",
    )
    assert res["status"] == "error"
    assert res["error"] == "NOT_AUTHENTICATED"


def test_initiate_number_transfer_submission_authenticated_with_dict(monkeypatch) -> None:
    session_dict = {"auth_status": "pass", "account_id": "A1001"}
    monkeypatch.setattr(tool, "context", session_dict, raising=False)
    res = tool.initiate_number_transfer(
        phone_to_transfer="5145550199",
        current_carrier="Rogers",
        carrier_account_number="987654321",
        port_pin="1234",
    )
    assert res["status"] == "ok"
    assert res["data"]["mode"] == "transfer_submitted"
    assert res["data"]["phone_to_transfer"] == "5145550199"
    assert "port_in_request_id" in res["data"]
    assert session_dict["port_in_request_id"] == res["data"]["port_in_request_id"]


def test_initiate_number_transfer_localization_french(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.initiate_number_transfer(language="fr-CA")
    assert res["status"] == "ok"
    assert res["data"]["mode"] == "checklist_provided"
    assert len(res["data"]["required_port_checklist"]) == 4


def test_initiate_number_transfer_localization_spanish(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.initiate_number_transfer(language="es-US")
    assert res["status"] == "ok"
    assert res["data"]["mode"] == "checklist_provided"
    assert len(res["data"]["required_port_checklist"]) == 4


def test_initiate_number_transfer_authenticated_missing_donor_details(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "ACC-0199"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.initiate_number_transfer(
        phone_to_transfer="514-555-0199",
        current_carrier="Rogers",
    )
    assert res["status"] == "ok"
    data = res["data"]
    assert data["status"] == "pending_donor_details"
    assert "port_in_request_id" in data
    assert "carrier_account_number" in data["missing_details"]
    assert "port_pin" in data["missing_details"]
    assert data["contract_disclosure_required"] is True
    assert data["early_termination_fee"] == "0.00"
    assert data["final_bill_estimate"] == "28.50"
    assert data["porting_account_number"] == "ACC-0199"
    assert data["transfer_pin"] == "849201"


def test_initiate_number_transfer_port_out_facts(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "ACC-0199"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.initiate_number_transfer(
        phone_to_transfer="514-555-0199",
        current_carrier="Bell",
    )
    assert res["status"] == "ok"
    data = res["data"]
    assert data["mode"] == "port_out_details"
    assert data["contract_disclosure_required"] is True
    assert data["early_termination_fee"] == "0.00"
    assert data["final_bill_estimate"] == "28.50"
    assert data["porting_account_number"] == "ACC-0199"
    assert data["transfer_pin"] == "849201"
    assert data["port_out_pin"] == "849201"
    assert "agent_action" in data


def test_initiate_number_transfer_checklist_agent_action(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.initiate_number_transfer(phone_to_transfer="514-555-0199")
    assert res["status"] == "ok"
    assert "agent_action" in res["data"]
    assert "contract_cancellation_fee_disclosure" in res["data"]["agent_action"]


def test_sales_equipment_language_sheet_includes_contract_disclosure() -> None:
    import cxas_app.agents.sales_equipment.before_model_callbacks.language_prompt_filter.python_code as lpf
    sheet = lpf.build_language_sheet({"language": "en-US"}, agent_name="sales_equipment")
    assert "contract_cancellation_fee_disclosure" in sheet
    assert "Please note that cancelling or transferring your line" in sheet


def test_port_in_partial_intake_across_pre_auth_verify_and_post_auth(monkeypatch) -> None:
    from lib.fakes import VALID_PINS
    from lib.services import verify_login_impl

    state: dict[str, object] = {
        "account_id": "ACC-0143",
        "phone_last4": "0143",
        "caller_provided_phone_last4": "",
    }
    session = SimpleNamespace(state=state)
    monkeypatch.setattr(tool, "context", session, raising=False)

    # 1. Pre-auth checklist records port_in_checklist_given + transfer phone state
    res_pre = tool.initiate_number_transfer(
        phone_to_transfer="514-555-0199",
        current_carrier="Rogers",
        language="en-US",
    )
    assert res_pre["status"] == "ok"
    assert res_pre["data"]["mode"] == "checklist_provided"
    assert state["port_in_checklist_given"] is True
    assert state["pending_transfer_phone"] == "514-555-0199"
    assert state["transfer_phone_last4"] == "0199"
    assert state["pending_transfer_carrier"] == "Rogers"

    # 2. verify_login_impl surfaces pending_port_in_intake + port_in_next_step (fresh login & repeat call)
    ver_res = verify_login_impl(code=min(VALID_PINS), method="pin", language="en-US", state=state)
    assert ver_res["status"] == "ok"
    assert ver_res["data"]["pending_port_in_intake"] is True
    assert "initiate_number_transfer" in ver_res["data"]["port_in_next_step"]

    ver_repeat = verify_login_impl(code=min(VALID_PINS), method="pin", language="en-US", state=state)
    assert ver_repeat["status"] == "ok"
    assert ver_repeat["data"]["pending_port_in_intake"] is True
    assert "initiate_number_transfer" in ver_repeat["data"]["port_in_next_step"]

    # 3. Post-auth zero-arg call reuses Turn-1 phone & carrier, does NOT overwrite with 0143, mints PRT ID
    res_post = tool.initiate_number_transfer(language="en-US")
    assert res_post["status"] == "ok"
    post_data = res_post["data"]
    assert post_data["mode"] == "transfer_pending_details"
    assert post_data["phone_to_transfer"] == "514-555-0199"
    assert "0143" not in post_data["phone_to_transfer"]
    assert post_data["current_carrier"] == "Rogers"
    assert post_data["port_in_request_id"].startswith("R")
    assert state["port_in_request_id"] == post_data["port_in_request_id"]
    assert post_data["missing_details"] == ["carrier_account_number", "port_pin"]
    assert "pending" in post_data["agent_action"]
    assert "contract_cancellation_fee_disclosure" not in post_data["agent_action"]

    # 4. Post-auth with neither phone nor carrier yet logs PRT pending without falling back to 0143
    empty_state: dict[str, object] = {
        "auth_status": "pass",
        "account_id": "ACC-0143",
        "phone_last4": "0143",
    }
    monkeypatch.setattr(tool, "context", SimpleNamespace(state=empty_state), raising=False)
    res_zero = tool.initiate_number_transfer(language="es-US")
    assert res_zero["status"] == "ok"
    z_data = res_zero["data"]
    assert z_data["mode"] == "transfer_pending_details"
    assert z_data["phone_to_transfer"] == ""
    assert z_data["port_in_request_id"].startswith("R")
    assert "phone_to_transfer" in z_data["missing_details"]
    assert "current_carrier" in z_data["missing_details"]




