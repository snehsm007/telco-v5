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


