from types import SimpleNamespace

import cxas_app.tools.send_login_code.python_function.python_code as tool


def test_send_login_code_happy_path(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "phone_last4": "0143", "auth_status": "none", "auth_failure_count": 0.0}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code()
    assert reply["status"] == "ok"
    assert reply["data"]["sent"] is True
    assert reply["data"]["destination_last4"] == "0143"
    assert session.state["auth_status"] == "code_sent"


def test_send_login_code_context_as_dict(monkeypatch) -> None:
    state_dict = {"account_id": "A1001", "phone_last4": "0143"}
    monkeypatch.setattr(tool, "context", state_dict, raising=False)
    reply = tool.send_login_code(channel="sms")
    assert reply["status"] == "ok"
    assert reply["data"]["sent"] is True


def test_send_login_code_context_none_with_identifier(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    reply = tool.send_login_code(identifier="202 555 0143")
    assert reply["status"] == "ok"
    assert reply["data"]["sent"] is True


def test_send_login_code_already_verified(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "pass", "logged_in": True}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code()
    assert reply["status"] == "ok"
    assert reply["data"]["already_verified"] is True


def test_send_login_code_too_many_attempts(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_failure_count": 3.0}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code()
    assert reply["status"] == "error"
    assert reply["error"] == "TOO_MANY_ATTEMPTS"


def test_send_login_code_channel_email(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "auth_status": "none", "contact_email": "test@example.com"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code(channel="email")
    assert reply["status"] == "ok"
    assert reply["data"]["channel"] == "email"
    assert "masked_email" in reply["data"]


def test_send_login_code_mock_system_down(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "mock_error": "SYSTEM_DOWN"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code()
    assert reply["status"] == "error"
    assert reply["error"] == "SERVICE_UNAVAILABLE"


def test_send_login_code_localization(monkeypatch) -> None:
    session = SimpleNamespace(
        state={"account_id": "A1001", "phone_last4": "0143", "auth_status": "none"}
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply_fr = tool.send_login_code(language="fr-CA")
    assert reply_fr["status"] == "ok"
    session.state["auth_status"] = "none"
    reply_es = tool.send_login_code(language="es-US")
    assert reply_es["status"] == "ok"


def test_send_login_code_unidentified_returns_error(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code()
    assert reply["status"] == "error"
    assert reply["error"] == "NOT_IDENTIFIED"
    assert "agent_action" in reply
    assert "mobile number" in reply["agent_action"].lower() or "10-digit" in reply["agent_action"].lower()


def test_send_login_code_accepts_caller_given_phone_and_records_last4(monkeypatch) -> None:
    session = SimpleNamespace(state={"account_id": "ACC-4651", "phone_last4": ""})
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code(identifier="514-555-0199")
    assert reply["status"] == "ok"
    assert reply["data"]["sent"] is True
    assert reply["data"]["destination_last4"] == "0199"
    assert session.state["caller_provided_phone_last4"] == "0199"
    assert session.state["phone_last4"] == "0199"


def test_send_login_code_sms_no_mobile_on_file_returns_no_mobile_on_file(monkeypatch) -> None:
    session = SimpleNamespace(
        state={
            "account_id": "A1001",
            "phone_last4": "",
            "caller_provided_phone_last4": "",
            "auth_failure_count": 0,
            "login_attempts": 0,
            "auth_status": "none",
        }
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code(channel="sms")
    assert reply["status"] == "error"
    assert reply["error"] == "NO_MOBILE_ON_FILE"
    assert "agent_action" in reply
    assert "10-digit mobile number" in reply["agent_action"].lower()
    assert "lookup_account" in reply["agent_action"].lower()
    # No strike recorded and auth_status untouched
    assert session.state["auth_failure_count"] == 0
    assert session.state["login_attempts"] == 0
    assert session.state["auth_status"] == "none"
    assert not session.state.get("login_code_sent")


def test_send_login_code_sms_lookup_by_name_allows_otp_dispatch(monkeypatch) -> None:
    session = SimpleNamespace(
        state={
            "account_id": "ACC-1001",
            "phone_last4": "",
            "caller_provided_phone_last4": "",
            "lookup_by_name": True,
            "auth_failure_count": 0,
            "login_attempts": 0,
            "auth_status": "none",
        }
    )
    monkeypatch.setattr(tool, "context", session, raising=False)
    reply = tool.send_login_code(channel="sms")
    assert reply["status"] == "ok"
    assert reply["data"]["sent"] is True
    assert reply["data"]["destination_last4"] == ""
    assert session.state["auth_status"] == "code_sent"
    assert session.state["login_code_sent"] is True



def test_send_login_code_email_masked_format_mirrors_persona(monkeypatch) -> None:
    session_marcus = SimpleNamespace(
        state={
            "account_id": "A1001",
            "first_name": "Marcus",
            "contact_email": "marcus@example.com",
            "auth_status": "none",
        }
    )
    monkeypatch.setattr(tool, "context", session_marcus, raising=False)
    reply_marcus = tool.send_login_code(channel="email")
    assert reply_marcus["status"] == "ok"
    assert reply_marcus["data"]["masked_email"] == "m***@example.com"
    assert "starting with 'm'" in reply_marcus["data"]["spoken_message"]
    assert "starting with m" in reply_marcus["data"]["agent_action"]

    session_riley = SimpleNamespace(
        state={
            "account_id": "A1001",
            "first_name": "Riley",
            "contact_email": "riley.t.design@example.com",
            "auth_status": "none",
        }
    )
    monkeypatch.setattr(tool, "context", session_riley, raising=False)
    reply_riley = tool.send_login_code(channel="email")
    assert reply_riley["status"] == "ok"
    assert reply_riley["data"]["masked_email"] == "r***@example.com"


def test_send_login_code_email_spoken_phrases_locales(monkeypatch) -> None:
    # Named emails include starting initial across en-US / fr-CA / es-US
    for locale, expected_spoken, expected_action in (
        ("en-US", "starting with 'c'", "starting with c"),
        ("fr-CA", "commençant par « c »", "commençant par c"),
        ("es-US", "comienza con 'c'", "comenzando con c"),
    ):
        session_named = SimpleNamespace(
            state={
                "account_id": "ACC-0198",
                "contact_email": "claire@example.com",
                "auth_status": "none",
            }
        )
        monkeypatch.setattr(tool, "context", session_named, raising=False)
        res_named = tool.send_login_code(channel="email", language=locale)
        assert res_named["data"]["masked_email"] == "c***@example.com"
        assert expected_spoken in res_named["data"]["spoken_message"]
        assert expected_action in res_named["data"]["agent_action"]

    # Synthetic placeholder emails omit fake initial 'u' while allowing domain confirmation
    session_en = SimpleNamespace(
        state={
            "account_id": "ACC-0198",
            "contact_email": "user0198@example.com",
            "auth_status": "none",
        }
    )
    monkeypatch.setattr(tool, "context", session_en, raising=False)
    res_en = tool.send_login_code(channel="email", language="en-US")
    assert res_en["data"]["masked_email"] == "***@example.com"
    assert res_en["data"]["email_domain"] == "example.com"
    assert "to the email address on file" in res_en["data"]["spoken_message"]
    assert "starting with" not in res_en["data"]["spoken_message"]
    assert "@example.com" in res_en["data"]["agent_action"]

    session_fr = SimpleNamespace(
        state={
            "account_id": "ACC-0198",
            "contact_email": "user0198@example.com",
            "auth_status": "none",
        }
    )
    monkeypatch.setattr(tool, "context", session_fr, raising=False)
    res_fr = tool.send_login_code(channel="email", language="fr-CA")
    assert res_fr["data"]["masked_email"] == "***@example.com"
    assert res_fr["data"]["email_domain"] == "example.com"
    assert "à l'adresse courriel au dossier" in res_fr["data"]["spoken_message"]
    assert "commençant par" not in res_fr["data"]["spoken_message"]
    assert "@example.com" in res_fr["data"]["agent_action"]

    session_es = SimpleNamespace(
        state={
            "account_id": "ACC-0198",
            "contact_email": "user0198@example.com",
            "auth_status": "none",
        }
    )
    monkeypatch.setattr(tool, "context", session_es, raising=False)
    res_es = tool.send_login_code(channel="email", language="es-US")
    assert res_es["data"]["masked_email"] == "***@example.com"
    assert res_es["data"]["email_domain"] == "example.com"
    assert "al correo electrónico registrado" in res_es["data"]["spoken_message"]
    assert "comienza con" not in res_es["data"]["spoken_message"]
    assert "@example.com" in res_es["data"]["agent_action"]

    # Caller-provided email in identifier updates contact_email without overwriting existing account_id
    session_caller_email = SimpleNamespace(
        state={
            "account_id": "ACC-0987",
            "contact_email": "user0987@example.com",
            "auth_status": "none",
        }
    )
    monkeypatch.setattr(tool, "context", session_caller_email, raising=False)
    res_dubois = tool.send_login_code(
        identifier="jl.dubois@example.fr",
        channel="email",
        language="fr-CA",
    )
    assert session_caller_email.state["account_id"] == "ACC-0987"
    assert session_caller_email.state["contact_email"] == "jl.dubois@example.fr"
    assert res_dubois["data"]["masked_email"] == "j***@example.fr"
    assert res_dubois["data"]["email_domain"] == "example.fr"
    assert "jl.dubois@example.fr" in res_dubois["data"]["spoken_message"]

    # Caller-provided email in identifier also resolves account when session has no account_id yet
    session_unidentified_email = SimpleNamespace(state={"auth_status": "none"})
    monkeypatch.setattr(tool, "context", session_unidentified_email, raising=False)
    res_unid = tool.send_login_code(
        identifier="jl.dubois@example.fr",
        channel="email",
        language="fr-CA",
    )
    assert res_unid["status"] == "ok"
    assert session_unidentified_email.state["contact_email"] == "jl.dubois@example.fr"
    assert res_unid["data"]["masked_email"] == "j***@example.fr"


def test_caller_provided_email_confirms_directly_and_handles_same_email_resend(
    monkeypatch,
) -> None:
    from lib.services import manage_mfa_settings_impl, update_contact_profile_impl

    for locale, expected_spoken, expected_action, expected_resend_spoken in (
        (
            "en-US",
            "sent a 6-digit verification code to pat.sample@customdomain.org",
            "Confirm directly that the 6-digit verification code was sent to pat.sample@customdomain.org without spelling asterisks",
            "I have resent the 6-digit verification code to pat.sample@customdomain.org",
        ),
        (
            "fr-CA",
            "envoyer un code de vérification à 6 chiffres à pat.sample@customdomain.org",
            "Confirmez directement que le code de vérification à 6 chiffres a été envoyé à pat.sample@customdomain.org sans épeler d'astérisques",
            "J'ai renvoyé le code de vérification à 6 chiffres à pat.sample@customdomain.org",
        ),
        (
            "es-US",
            "enviar un código de verificación de 6 dígitos a pat.sample@customdomain.org",
            "Confirme directamente que el código de verificación de 6 dígitos se envió a pat.sample@customdomain.org sin deletrear asteriscos",
            "He reenviado el código de verificación de 6 dígitos a pat.sample@customdomain.org",
        ),
    ):
        session_c = SimpleNamespace(
            state={
                "account_id": "ACC-0198",
                "contact_email": "user0198@example.com",
                "auth_status": "none",
            }
        )
        monkeypatch.setattr(tool, "context", session_c, raising=False)
        res = tool.send_login_code(
            identifier="pat.sample@customdomain.org",
            channel="email",
            language=locale,
        )
        assert res["status"] == "ok"
        assert res["data"]["masked_email"] == "p***@customdomain.org"
        assert expected_spoken in res["data"]["spoken_message"]
        assert expected_action in res["data"]["agent_action"]

        # Same-email resend in send_login_code sets code_resent and confirms direct resend
        res_resend = tool.send_login_code(
            identifier="pat.sample@customdomain.org",
            channel="email",
            language=locale,
        )
        assert res_resend["status"] == "ok"
        assert res_resend.get("code_resent") is True
        assert res_resend["data"]["code_resent"] is True
        assert expected_resend_spoken in res_resend["data"]["spoken_message"]

    # Also verify example.com caller-provided email and manage_mfa_settings already_sent branch
    st_mfa: dict = {
        "account_id": "ACC-0198",
        "auth_status": "pass",
        "logged_in": True,
    }
    upd_res = update_contact_profile_impl(email="pat.sample@example.com", state=st_mfa)
    assert upd_res["status"] == "ok"
    assert st_mfa["caller_provided_email"] == "pat.sample@example.com"

    mfa1 = manage_mfa_settings_impl(
        action="disable",
        lost_authenticator=True,
        email="pat.sample@customdomain.org",
        state=st_mfa,
    )
    assert mfa1["status"] == "ok"
    assert "pat.sample@customdomain.org" in mfa1["spoken_message"]
    assert "Confirm directly that the 6-digit verification code was sent to pat.sample@customdomain.org" in mfa1["agent_action"]

    # Resend without passing email again preserves caller_provided_email spoken & action_text
    mfa2 = manage_mfa_settings_impl(
        action="disable",
        lost_authenticator=True,
        state=st_mfa,
    )
    assert mfa2["status"] == "ok"
    assert mfa2.get("code_resent") is True
    assert "I have resent the 6-digit verification code to pat.sample@customdomain.org" in mfa2["spoken_message"]
    assert "Confirm directly that the 6-digit verification code was resent to pat.sample@customdomain.org" in mfa2["agent_action"]


def test_send_login_code_post_auth_sms_stepup_and_new_phone_verification(monkeypatch) -> None:
    from lib.services import manage_mfa_settings_impl, verify_login_impl

    # (a) Pending lost-authenticator step-up allows SMS code dispatch while logged in without wiping session
    st_lost: dict = {
        "account_id": "A1001",
        "identified": True,
        "auth_status": "pass",
        "logged_in": True,
        "lost_authenticator": True,
        "mfa_email_code_sent": True,
        "mfa_email_verified": False,
    }
    monkeypatch.setattr(tool, "context", SimpleNamespace(state=st_lost), raising=False)
    sms_stepup = tool.send_login_code(identifier="514-555-0199", channel="sms")
    assert sms_stepup["status"] == "ok"
    assert sms_stepup["data"]["sent"] is True
    assert sms_stepup["data"]["already_verified"] is False
    assert sms_stepup["data"]["destination_last4"] == "0199"
    assert st_lost["account_id"] == "A1001"
    assert st_lost["auth_status"] == "pass"
    assert st_lost["logged_in"] is True
    assert st_lost["login_channel"] == "mfa_sms"
    assert st_lost["mfa_email_code_sent"] is True

    ver_res = verify_login_impl(code="384920", identifier="514-555-0199", state=st_lost)
    assert ver_res["status"] == "ok"
    assert st_lost["account_id"] == "A1001"
    assert st_lost["login_channel"] == "mfa_sms_verified"
    assert st_lost["mfa_email_verified"] is True

    dis_res = manage_mfa_settings_impl(action="disable", lost_authenticator=True, state=st_lost)
    assert dis_res["status"] == "ok"
    assert dis_res["data"]["mfa_updated"] is True
    assert dis_res["data"]["mfa_enabled"] is False

    # (b) Caller explicitly provides a valid phone number while logged in (e.g. verifying new SMS 2FA number)
    st_new_phone: dict = {
        "account_id": "ACC-1001",
        "identified": True,
        "lookup_by_name": True,
        "phone_unconfirmed": True,
        "phone_last4": "",
        "auth_status": "pass",
        "logged_in": True,
        "mfa_email_verified": True,
    }
    monkeypatch.setattr(tool, "context", SimpleNamespace(state=st_new_phone), raising=False)
    sms_new = tool.send_login_code(identifier="708-555-0192", channel="sms")
    assert sms_new["status"] == "ok"
    assert sms_new["data"]["sent"] is True
    assert sms_new["data"]["destination_last4"] == "0192"
    assert st_new_phone["account_id"] == "ACC-1001"
    assert st_new_phone["auth_status"] == "pass"
    assert st_new_phone["logged_in"] is True
    assert st_new_phone["login_channel"] == "mfa_sms"
    assert st_new_phone["caller_provided_phone_last4"] == "0192"
    assert st_new_phone["phone_last4"] == "0192"
    assert st_new_phone["lookup_by_name"] is False
    assert st_new_phone["phone_unconfirmed"] is False


def test_send_login_code_email_fallback_after_prior_code_invites_caller_email(monkeypatch) -> None:
    # 1. Direct initial email send (prior_code_sent == False, e.g. VE-41 no-signal caller) stays unchanged
    st_direct: dict = {
        "account_id": "ACC-4433",
        "identified": True,
        "contact_email": "user@example.com",
        "auth_status": "none",
    }
    monkeypatch.setattr(tool, "context", SimpleNamespace(state=st_direct), raising=False)
    res_direct = tool.send_login_code(channel="email", language="en-US")
    assert res_direct["status"] == "ok"
    assert (
        res_direct["data"]["spoken_message"]
        == "For your security, I just sent a 6-digit verification code to the email address on file — please read it back to me."
    )
    assert "without proactively naming an initial letter" in res_direct["data"]["agent_action"]

    # 2. Email fallback after prior SMS attempt (prior_code_sent == True) on placeholder email invites caller email/phone
    for locale, expected_spoken_part, expected_action_part in (
        (
            "en-US",
            "share your email address if you need me to send it directly there",
            "ask once for their email address or alternate mobile number before considering transfer",
        ),
        (
            "fr-CA",
            "indiquez-moi votre adresse courriel si vous souhaitez que je l'y envoie directement",
            "demandez une fois son courriel ou un autre numéro avant d'envisager un transfert",
        ),
        (
            "es-US",
            "indíqueme su dirección de correo si necesita que lo envíe directamente allí",
            "pida una vez su correo o número alternativo antes de transferir",
        ),
    ):
        st_fallback: dict = {
            "account_id": "ACC-4433",
            "identified": True,
            "phone_last4": "4433",
            "caller_provided_phone_last4": "4433",
            "contact_email": "user@example.com",
            "auth_status": "none",
        }
        monkeypatch.setattr(tool, "context", SimpleNamespace(state=st_fallback), raising=False)
        res_sms = tool.send_login_code(identifier="5550124433", channel="sms", language=locale)
        assert res_sms["status"] == "ok"
        assert st_fallback["login_code_sent"] is True

        res_email = tool.send_login_code(identifier="5550124433", channel="email", language=locale)
        assert res_email["status"] == "ok"
        assert expected_spoken_part in res_email["data"]["spoken_message"]
        assert expected_action_part in res_email["data"]["agent_action"]

        # Subsequent caller-provided real email uses normal caller-email confirmation
        res_real = tool.send_login_code(
            identifier="alex.morgan@custommail.org",
            channel="email",
            language=locale,
        )
        assert res_real["status"] == "ok"
        assert res_real["data"]["masked_email"] == "a***@custommail.org"
        assert expected_spoken_part not in res_real["data"]["spoken_message"]


def test_send_login_code_sms_resend_acknowledgement() -> None:
    from lib.copy import spoken_line
    from lib.services import send_login_code_impl

    # (a) & (b): first SMS send -> no code_resent and verbatim id_verification_otp;
    # second SMS call to same number -> code_resent is True and spoken contains "resent" + last4
    st_pre: dict = {
        "account_id": "ACC-1001",
        "identified": True,
        "phone_last4": "0199",
        "auth_status": "none",
    }
    first = send_login_code_impl(identifier="514-555-0199", channel="sms", state=st_pre)
    assert first["status"] == "ok"
    assert "code_resent" not in first
    assert "code_resent" not in first["data"]
    assert first["spoken_message"] == spoken_line("id_verification_otp", "en-US")

    second = send_login_code_impl(identifier="514-555-0199", channel="sms", state=st_pre)
    assert second["status"] == "ok"
    assert second.get("code_resent") is True
    assert second["data"].get("code_resent") is True
    assert "resent" in second["spoken_message"].lower()
    assert "0199" in second["spoken_message"]
    assert "agent_action" in second and "email address" in second["agent_action"]

    # (c) second call with a NEW 10-digit number -> no code_resent
    st_new_num: dict = {
        "account_id": "ACC-1001",
        "identified": True,
        "phone_last4": "0199",
        "auth_status": "none",
    }
    send_login_code_impl(identifier="514-555-0199", channel="sms", state=st_new_num)
    diff_num = send_login_code_impl(identifier="514-555-0143", channel="sms", state=st_new_num)
    assert diff_num["status"] == "ok"
    assert "code_resent" not in diff_num
    assert "code_resent" not in diff_num["data"]
    assert diff_num["spoken_message"] == spoken_line("id_verification_otp", "en-US")

    # (d) post-login shape with mfa_enabled=True, preferred_mfa_channel="sms"
    st_post: dict = {
        "account_id": "ACC-1001",
        "identified": True,
        "auth_status": "pass",
        "logged_in": True,
        "mfa_enabled": True,
        "preferred_mfa_channel": "sms",
    }
    mfa_first = send_login_code_impl(
        channel="sms",
        identifier="+1-555-010-8842",
        state=st_post,
    )
    assert mfa_first["status"] == "ok"
    assert "code_resent" not in mfa_first

    mfa_second = send_login_code_impl(
        channel="sms",
        identifier="+1-555-010-8842",
        resend=True,
        state=st_post,
    )
    assert mfa_second["status"] == "ok"
    assert mfa_second.get("code_resent") is True
    assert mfa_second["data"].get("code_resent") is True
    assert "8842" in mfa_second["spoken_message"]

    # (e) fr-CA variant contains "renvoyé"
    st_fr: dict = {
        "account_id": "ACC-1001",
        "identified": True,
        "phone_last4": "0199",
        "auth_status": "none",
    }
    send_login_code_impl(channel="sms", language="fr-CA", state=st_fr)
    fr_second = send_login_code_impl(channel="sms", resend=True, language="fr-CA", state=st_fr)
    assert fr_second["status"] == "ok"
    assert fr_second.get("code_resent") is True
    assert "renvoyé" in fr_second["spoken_message"]
    assert "0199" in fr_second["spoken_message"]
