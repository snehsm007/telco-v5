from types import SimpleNamespace

import cxas_app.tools.cancel_or_port_out_service.python_function.python_code as tool


def test_cancel_or_port_out_unauthenticated(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "none"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.cancel_or_port_out_service(action_type="cancel")
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_AUTHENTICATED"


def test_cancel_step1_requires_disclosure_and_confirmation(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.cancel_or_port_out_service(
        service_line="mobile",
        action_type="cancel",
        reason="moving abroad",
        confirmed=False,
    )
    assert reply["status"] == "ok"
    assert reply["data"]["requires_confirmation"] is True
    assert reply["data"]["service_cancelled"] is False
    assert "early cancellation fee" in reply["data"]["verbatim_disclosure"]
    assert session.state.get("cancellation_fee_disclosed") is True
    assert session.state.get("service_cancelled") is not True


def test_cancel_premature_confirmation_still_forces_disclosure(monkeypatch) -> None:
    # If confirmed=True is passed on a fresh session without prior disclosure,
    # the tool must disclose fees first before cancelling.
    session = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.cancel_or_port_out_service(
        service_line="mobile",
        action_type="cancel",
        confirmed=True,
    )
    assert reply["status"] == "ok"
    assert reply["data"]["requires_confirmation"] is True
    assert reply["data"]["service_cancelled"] is False
    assert session.state.get("cancellation_fee_disclosed") is True


def test_cancel_step2_confirmed_after_disclosure(monkeypatch) -> None:
    session = SimpleNamespace(
        state={
            "auth_status": "pass",
            "account_id": "A1001",
            "cancellation_fee_disclosed": True,
        }
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.cancel_or_port_out_service(
        service_line="mobile",
        action_type="cancel",
        confirmed=True,
        decline_retention_offer=True,
    )
    assert reply["status"] == "ok"
    assert reply["data"]["service_cancelled"] is True
    assert "cancellation_confirmation_id" in reply["data"]
    assert "equipment_return_instructions" in reply["data"]
    assert session.state.get("service_cancelled") is True


def test_port_out_step2_provides_port_out_pin(monkeypatch) -> None:
    session = SimpleNamespace(
        state={
            "auth_status": "pass",
            "account_id": "A1001",
            "cancellation_fee_disclosed": True,
        }
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.cancel_or_port_out_service(
        service_line="mobile",
        action_type="port_out",
        confirmed=True,
    )
    assert reply["status"] == "ok"
    assert reply["data"]["service_cancelled"] is True
    assert reply["data"]["port_out_pin"] == "849201"


def test_cancel_or_port_out_inline_auth(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "none"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.cancel_or_port_out_service(
        action_type="cancel",
        identifier="2025550143",
        verification_code="1234",
    )
    assert reply["status"] == "ok"
    assert reply["data"]["requires_confirmation"] is True


def test_cancel_or_port_out_dict_context(monkeypatch) -> None:
    ctx = {"auth_status": "pass", "account_id": "A1001"}
    monkeypatch.setattr(tool, "context", ctx, raising=False)
    reply = tool.cancel_or_port_out_service(action_type="cancel")
    assert reply["status"] == "ok"
    assert reply["data"]["requires_confirmation"] is True


def test_cancel_or_port_out_none_context(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    reply = tool.cancel_or_port_out_service(action_type="cancel")
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_AUTHENTICATED"


def test_cancel_disclosure_localization_fr_and_es(monkeypatch) -> None:
    session_fr = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session_fr, raising=False)
    reply_fr = tool.cancel_or_port_out_service(action_type="cancel", language="fr-CA")
    assert reply_fr["status"] == "ok"
    assert "résiliation anticipée" in reply_fr["data"]["verbatim_disclosure"]

    session_es = SimpleNamespace(state={"auth_status": "pass", "account_id": "A1001"})
    monkeypatch.setattr(tool, "context", session_es, raising=False)
    reply_es = tool.cancel_or_port_out_service(action_type="cancel", language="es-US")
    assert reply_es["status"] == "ok"
    assert "cancelación anticipada" in reply_es["data"]["verbatim_disclosure"]
