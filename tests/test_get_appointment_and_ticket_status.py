from types import SimpleNamespace

import cxas_app.tools.get_appointment_and_ticket_status.python_function.python_code as tool


def test_get_appointment_and_ticket_status_authenticated(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.get_appointment_and_ticket_status()
    assert res["status"] == "ok"
    assert res["data"]["appointment_id"] == "APT-4021"
    assert len(res["data"]["available_slots"]) == 3
    assert session.state["active_appointment_id"] == "APT-4021"
    assert session.state["appointment_status"] == "scheduled"
    assert session.state["technician_status"] == "en_route"


def test_get_appointment_and_ticket_status_with_dict_context(monkeypatch) -> None:
    session_dict = {"auth_status": "pass", "account_id": "A1002"}
    monkeypatch.setattr(tool, "context", session_dict, raising=False)
    res = tool.get_appointment_and_ticket_status()
    assert res["status"] == "ok"
    assert res["data"]["ticket_id"] == "TKT-8841"
    assert len(res["data"]["available_slots"]) == 3


def test_get_appointment_and_ticket_status_unauthenticated(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    res = tool.get_appointment_and_ticket_status()
    assert res["status"] == "error"
    assert res["error"] == "NOT_AUTHENTICATED"


def test_get_appointment_and_ticket_status_localization_french(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.get_appointment_and_ticket_status(language="fr-CA")
    assert res["status"] == "ok"
    assert res["data"]["technician_status"] == "en_route"
    assert len(res["data"]["available_slots"]) == 3


def test_get_appointment_and_ticket_status_localization_spanish(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.get_appointment_and_ticket_status(language="es-US")
    assert res["status"] == "ok"
    assert res["data"]["appointment_id"] == "APT-4021"
