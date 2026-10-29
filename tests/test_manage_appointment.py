from types import SimpleNamespace

import cxas_app.tools.manage_appointment.python_function.python_code as tool


def test_manage_appointment_reschedule_authenticated(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001", "active_appointment_id": "APT-4021"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.manage_appointment(action="reschedule", selected_slot="SLOT-2")
    assert res["status"] == "ok"
    assert res["data"]["appointment_rescheduled"] is True
    assert res["data"]["slot_id"] == "SLOT-2"
    assert session.state["appointment_status"] == "rescheduled"


def test_manage_appointment_cancel_requires_confirmation(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.manage_appointment(action="cancel", confirmed_cancel=False)
    assert res["status"] == "ok"
    assert res["data"]["requires_confirmation"] is True
    assert res["data"]["appointment_cancelled"] is False


def test_manage_appointment_cancel_confirmed_with_dict(monkeypatch) -> None:
    session_dict = {"auth_status": "pass", "account_id": "A1001"}
    monkeypatch.setattr(tool, "context", session_dict, raising=False)
    res = tool.manage_appointment(action="cancel", confirmed_cancel=True)
    assert res["status"] == "ok"
    assert res["data"]["appointment_cancelled"] is True
    assert session_dict["appointment_status"] == "cancelled"


def test_manage_appointment_cannot_cancel_when_technician_en_route(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001", "technician_status": "en_route"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.manage_appointment(action="cancel", confirmed_cancel=True, technician_en_route=True)
    assert res["status"] == "error"
    assert res["error"] == "CANNOT_CANCEL_EN_ROUTE"
    assert res["data"]["can_cancel"] is False


def test_manage_appointment_unauthenticated(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    res = tool.manage_appointment(action="reschedule")
    assert res["status"] == "error"
    assert res["error"] == "NOT_AUTHENTICATED"


def test_manage_appointment_localization_french(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.manage_appointment(action="cancel", confirmed_cancel=False, language="fr-CA")
    assert res["status"] == "ok"
    assert "annuler" in res["data"]["spoken_message"].lower()


def test_manage_appointment_localization_spanish(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.manage_appointment(action="cancel", confirmed_cancel=False, language="es-US")
    assert res["status"] == "ok"
    assert "cancelar" in res["data"]["spoken_message"].lower()
