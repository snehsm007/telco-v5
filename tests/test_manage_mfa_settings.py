from types import SimpleNamespace

import cxas_app.tools.manage_mfa_settings.python_function.python_code as tool


def test_manage_mfa_settings_unauthenticated(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "none"})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.manage_mfa_settings(action="enable")
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_AUTHENTICATED"


def test_manage_mfa_settings_wrong_code_and_lockout(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "none", "auth_failure_count": 0})
    monkeypatch.setattr(tool, "context", session, raising=False)

    r1 = tool.manage_mfa_settings(verification_code="0000")
    assert r1["status"] == "error"
    assert r1["error"] == "WRONG_CODE"
    assert r1["data"]["attempts_remaining"] == 2

    r2 = tool.manage_mfa_settings(verification_code="0000")
    assert r2["status"] == "error"
    assert r2["error"] == "WRONG_CODE"

    r3 = tool.manage_mfa_settings(verification_code="0000")
    assert r3["status"] == "error"
    assert r3["error"] == "TOO_MANY_ATTEMPTS"
    assert session.state["auth_status"] == "locked"


def test_manage_mfa_settings_case1_enable_mfa(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "mfa_enabled": False})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.manage_mfa_settings(action="enable", preferred_mfa_channel="sms")
    assert reply["status"] == "ok"
    assert reply["data"]["mfa_updated"] is True
    assert reply["data"]["mfa_enabled"] is True
    assert reply["data"]["preferred_mfa_channel"] == "sms"
    assert session.state["mfa_enabled"] is True


def test_manage_mfa_settings_case2_disable_mfa_step1_sms_stepup(monkeypatch) -> None:
    session = SimpleNamespace(state={"auth_status": "pass", "mfa_enabled": True})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.manage_mfa_settings(action="disable")
    assert reply["status"] == "ok"
    assert reply["data"]["requires_sms_step_up"] is True
    assert reply["data"]["mfa_updated"] is False
    assert session.state.get("login_code_sent") is True


def test_manage_mfa_settings_case2_disable_mfa_step2_confirmed(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"auth_status": "pass", "mfa_enabled": True, "login_code_sent": True, "login_channel": "mfa_sms"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.manage_mfa_settings(action="disable", step_up_code="123456")
    assert reply["status"] == "ok"
    assert reply["data"]["mfa_updated"] is True
    assert reply["data"]["mfa_enabled"] is False
    assert session.state["mfa_enabled"] is False


def test_manage_mfa_settings_premature_disable_blocked(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"auth_status": "pass", "mfa_enabled": True, "login_channel": "sms"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.manage_mfa_settings(action="disable")
    assert reply["status"] == "ok"
    assert reply["data"]["requires_sms_step_up"] is True
    assert reply["data"]["mfa_updated"] is False
    assert session.state["mfa_enabled"] is True


def test_manage_mfa_settings_case3_lost_authenticator_email_stepup(monkeypatch) -> None:
    session = SimpleNamespace(
        state={
            "auth_status": "pass",
            "mfa_enabled": True,
            "contact_email": "alex.doe@example.com",
        }
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.manage_mfa_settings(lost_authenticator=True)
    assert reply["status"] == "ok"
    assert reply["data"]["requires_email_step_up"] is True
    assert reply["data"]["mfa_updated"] is False
    assert "a***@example.com" == reply["data"]["masked_backup_email"]
    assert session.state.get("mfa_email_code_sent") is True


def test_manage_mfa_settings_case4_lost_authenticator_email_code_verified(monkeypatch) -> None:
    session = SimpleNamespace(
        state={
            "auth_status": "pass",
            "mfa_enabled": True,
            "lost_authenticator": True,
            "mfa_email_code_sent": True,
        }
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.manage_mfa_settings(step_up_code="123456", lost_authenticator=True)
    assert reply["status"] == "ok"
    assert reply["data"]["mfa_updated"] is True
    assert reply["data"]["mfa_enabled"] is False
    assert session.state["mfa_enabled"] is False


def test_manage_mfa_settings_dict_context(monkeypatch) -> None:
    ctx = {"auth_status": "pass", "login_code_sent": True}
    monkeypatch.setattr(tool, "context", ctx, raising=False)
    reply = tool.manage_mfa_settings(action="disable", step_up_code="123456")
    assert reply["status"] == "ok"
    assert reply["data"]["mfa_updated"] is True


def test_manage_mfa_settings_none_context(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    reply = tool.manage_mfa_settings(action="enable")
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_AUTHENTICATED"


def test_manage_mfa_settings_localization_fr_and_es(monkeypatch) -> None:
    session_fr = SimpleNamespace(state={"auth_status": "pass", "mfa_enabled": True})
    monkeypatch.setattr(tool, "context", session_fr, raising=False)
    reply_fr = tool.manage_mfa_settings(action="disable", step_up_code="123456", language="fr-CA")
    assert reply_fr["status"] == "ok"
    assert reply_fr["data"]["mfa_updated"] is True
    assert "désactivée" in reply_fr["data"]["spoken_message"]

    session_es = SimpleNamespace(
        state={
            "auth_status": "pass",
            "mfa_enabled": True,
            "lost_authenticator": True,
            "mfa_email_verified": True,
        }
    )
    monkeypatch.setattr(tool, "context", session_es, raising=False)
    reply_es = tool.manage_mfa_settings(lost_authenticator=True, language="es-US")
    assert reply_es["status"] == "ok"
    assert "desactivado" in reply_es["data"]["spoken_message"]
