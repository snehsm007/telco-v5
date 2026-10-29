"""Complete 22-tool atomic backend implementation for telco agent.

Each `<tool>_impl` backs the thin wrapper in cxas_app/tools/<tool>/.
The wrapper passes in the session state (`context.state`) as `state`, so tools
read what the session already knows instead of re-asking the model.
Every key used here is declared in cxas_app/app.json.
"""

from __future__ import annotations

from decimal import Decimal
import re
from typing import Any

from lib.copy import (
    SPOKEN_LINES,
    localized_text,
    resolve_copy_locale,
    resolve_locale,
    spoken_line,
)
from lib.fakes import (
    ACCOUNTS,
    ALWAYS_WRONG_LOGIN_CODES,
    BLOCKED_CALLER_NUMBERS,
    DECLINED_CARD_LAST4,
    FAKE_ADDON_CATALOG,
    FAKE_APPOINTMENTS_DATA,
    FAKE_BILLING_LEDGER,
    FAKE_PLAN_CATALOG,
    FAKE_TROUBLESHOOTING_GUIDES,
    FAKE_WARRANTY_DATA,
    OUTAGE_POSTAL_PREFIXES,
    VALID_LOGIN_CODES,
    VALID_OTPS,
    VALID_PINS,
    find_account,
    is_synthetic_wrong_identifier,
    login_code_accepted,
    normalize_code,
    only_digits,
    read_count,
    secret_pin_accepted,
)
from lib.replies import (
    ERROR_CODES,
    display_amount,
    error_reply,
    ok_reply,
    tracking_id,
)

ALL_TOOLS = (
    "lookup_account",
    "send_login_code",
    "verify_login",
    "handover_to_person",
    "get_billing_summary",
    "process_bill_payment",
    "setup_payment_arrangement",
    "setup_autopay",
    "process_refund_or_dispute",
    "check_regional_outage",
    "run_troubleshooting_and_sms",
    "get_appointment_and_ticket_status",
    "manage_appointment",
    "browse_plans_and_coverage",
    "commit_plan_or_order",
    "initiate_number_transfer",
    "manage_warranty_claim",
    "send_password_reset_sms",
    "manage_mfa_settings",
    "execute_suspend_restore",
    "update_contact_profile",
    "cancel_or_port_out_service",
)

MAX_LOGIN_ATTEMPTS = 3
MAX_PIN_ATTEMPTS = 3
MAX_PAYMENT_ATTEMPTS = 3
LOGIN_CODE_LENGTH = 6
SECRET_PIN_LENGTH = 4

_DEFAULT_STATE: dict[str, Any] = {}


def _get_state(
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    reset_if_locked: bool = False,
) -> dict[str, Any]:
    """Return the caller's session state dict, falling back to module default state when omitted."""
    if state is not None:
        return state
    if session_state is not None:
        return session_state
    if reset_if_locked and (
        _DEFAULT_STATE.get("auth_status") == "locked"
        or max(
            read_count(_DEFAULT_STATE, "auth_failure_count"),
            read_count(_DEFAULT_STATE, "login_attempts"),
        )
        >= MAX_LOGIN_ATTEMPTS
    ):
        _DEFAULT_STATE.clear()
    return _DEFAULT_STATE


def _ensure_default_profile(state: dict[str, Any]) -> None:
    """Populate default account profile keys so mid-flow tool calls never crash on missing state."""
    default_acct = ACCOUNTS[0] if ACCOUNTS else {}
    if not state.get("account_id"):
        state["account_id"] = default_acct.get("account_id", "")
    if not state.get("phone_last4"):
        state["phone_last4"] = default_acct.get("phone", "")[-4:]
    state.setdefault("auth_status", "none")
    state.setdefault("auth_failure_count", 0)
    state.setdefault("pin_failure_count", 0)
    state.setdefault("payment_failure_count", 0)


def _record_audit(state: dict[str, Any]) -> None:
    """Increment audit log count inside auth, mutation, and handover tools."""
    state["audit_log_count"] = read_count(state, "audit_log_count") + 1


def _check_mock_error(state: dict[str, Any], lang: str) -> dict[str, Any] | None:
    """Return synthetic system outage error if mock_error is injected."""
    val = str(state.get("mock_error") or "").strip().upper()
    if val in {"SYSTEM_DOWN", "SERVICE_UNAVAILABLE", "BACKEND_FAILURE"}:
        return error_reply(
            "SERVICE_UNAVAILABLE",
            language=lang,
            data={
                "error_category": "SYSTEM",
                "must_escalate_immediately": True,
                "escalation_reason": "system_unavailable",
                "handoff_message": spoken_line("live_agent_handoff", lang),
            },
        )
    return None


def _detect_handover_language(
    state: dict[str, Any],
    language: str | None = None,
    reason: str | None = None,
    summary: str | None = None,
    target_queue: str | None = None,
    session_context: str | None = None,
) -> str:
    """Pick the handover language (docs/DESIGN_RULES.md rule 25)."""
    if language and str(language).strip():
        return resolve_locale(language)
    active = state.get("language")
    if active and str(active).strip():
        return resolve_locale(str(active))
    combined = re.sub(
        r"[_-]+",
        " ",
        " ".join(
            str(x or "")
            for x in (
                reason,
                summary,
                target_queue,
                session_context,
                state.get("handoff_reason"),
                state.get("last_user_utterance"),
                state.get("request_summary"),
            )
        ),
    ).lower()
    fr_pattern = (
        r"\b(?:bonjour|merci|compte|facture|facturation|paiement|transfert|transf[eé]rer|"
        r"repr[eé]sentant|humain|personne|aide|svp|oui|num[eé]ro|"
        r"t[eé]l[eé]phone|connexion|verrouill[eé]|tentatives|fran[cç]ais|"
        r"parler|quelqu|besoin|équipe|equipe|pirat[eé]|superviseur|"
        r"plainte|r[eé]silier|annuler|sp[eé]cialiste|french|fr)\b"
    )
    es_pattern = (
        r"\b(?:hola|gracias|cuenta|factura|pago|transferir|agente|"
        r"representante|humano|ayuda|por\s+favor|n[uú]mero|"
        r"tel[eé]fono|c[oó]digo|acceso|bloqueado|intentos|espa[nñ]ol|"
        r"hablar|alguien|necesito|equipo|cliente|servicio|especialista|"
        r"cancelar|quiero|spanish|es)\b"
    )
    if re.search(fr_pattern, combined):
        return "fr-CA"
    if re.search(es_pattern, combined):
        return "es-US"
    preferred = state.get("preferred_language")
    if preferred and str(preferred).strip():
        return resolve_locale(str(preferred))
    return "en-US"


def not_identified_reply(reference: str) -> dict[str, Any]:
    """Reply for a tool called before the caller's account was found."""
    return error_reply(
        "NOT_IDENTIFIED",
        "The caller's account has not been found yet.",
        "Transfer the caller back to the router agent so it can find the account.",
        reference,
    )


def locked_reply(reference: str, attempts: int = MAX_LOGIN_ATTEMPTS) -> dict[str, Any]:
    """Reply once the caller has used up their login attempts."""
    return error_reply(
        "TOO_MANY_ATTEMPTS",
        "Too many wrong login codes on this call.",
        "Call handover_to_person immediately, speak handoff_message, and call end_session.",
        reference,
        data={
            "attempts": attempts,
            "attempts_remaining": 0,
            "attempts_left": 0,
            "lockout_triggered": True,
        },
    )


def record_payment_attempt(
    state: dict[str, Any],
    card_or_success: Any = False,
    method: str = "card",
    reference: str | None = None,
) -> dict[str, Any]:
    """Track payment attempts, clear stale card_last4 on decline, and trigger lockout on 3rd decline."""
    ref = reference or tracking_id("payment_attempt", state.get("account_id", ""))
    if isinstance(card_or_success, bool):
        is_success = card_or_success
        card_digits = normalize_code(state.get("card_last4", ""))
    else:
        card_digits = normalize_code(card_or_success)
        last4_check = card_digits[-4:] if len(card_digits) >= 4 else card_digits
        is_success = bool(last4_check) and last4_check not in DECLINED_CARD_LAST4
    last4 = card_digits[-4:] if len(card_digits) >= 4 else card_digits
    if is_success:
        state["payment_failure_count"] = 0
        if last4:
            state["card_last4"] = last4
        state["last_payment_method"] = str(method or "card")
        return ok_reply(
            {
                "payment_processed": True,
                "attempts": 0,
                "card_last4": state.get("card_last4", ""),
                "last_payment_method": state["last_payment_method"],
            },
            ref,
        )
    failures = read_count(state, "payment_failure_count") + 1
    state["payment_failure_count"] = failures
    state["card_last4"] = ""
    if last4:
        state["declined_card_last4"] = last4
    state["payment_declined_once"] = True
    if failures >= MAX_PAYMENT_ATTEMPTS:
        return error_reply(
            "TOO_MANY_ATTEMPTS",
            "Too many declined payment attempts on this call.",
            "Call handover_to_person immediately, speak handoff_message, and call end_session.",
            ref,
            data={
                "attempts": failures,
                "attempts_remaining": 0,
                "attempts_left": 0,
                "lockout_triggered": True,
            },
        )
    remaining = MAX_PAYMENT_ATTEMPTS - failures
    return error_reply(
        "PAYMENT_DECLINED",
        "The payment method was declined.",
        "Tell the caller the payment was declined and ask for another payment method.",
        ref,
        data={
            "attempts": failures,
            "attempts_remaining": remaining,
            "attempts_left": remaining,
            "lockout_triggered": False,
        },
    )


def _submit_request_fallback(
    summary: str,
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compatibility implementation for test_submit_request_needs_a_login."""
    state = _get_state(state, session_state)
    account_id = str(state.get("account_id") or "")
    clean_summary = " ".join(str(summary or "").split())
    reference = tracking_id("submit_request", account_id, clean_summary)
    if state.get("logged_in") is False:
        state["auth_status"] = "none"
    if state.get("auth_status") != "pass":
        return error_reply(
            "NOT_LOGGED_IN",
            "The caller has not passed login.",
            "Log the caller in with send_login_code and verify_login, then call submit_request again.",
            reference,
        )
    if not account_id:
        _ensure_default_profile(state)
        account_id = str(state.get("account_id") or "")
        reference = tracking_id("submit_request", account_id, clean_summary)
    if not clean_summary:
        return error_reply(
            "INVALID_INPUT",
            "The request is empty.",
            "Ask the caller what the request is.",
            reference,
        )
    state["request_summary"] = clean_summary
    state["last_tracking_id"] = reference
    return ok_reply({"submitted": True}, reference)


def _maybe_inline_auth(
    identifier: Any,
    verification_code: Any,
    lang: str,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    """Helper to authenticate in the same turn if verification_code is supplied (T-06)."""
    if str(verification_code or "").strip():
        return verify_login_impl(
            code=verification_code,
            identifier=identifier,
            language=lang,
            state=state,
        )
    if not state.get("account_id") and str(identifier or "").strip():
        lookup_account_impl(identifier=identifier, language=lang, state=state)
    return None


# ============================================================================
# Tool 1: lookup_account
# ============================================================================

def lookup_account_impl(
    identifier: str | int | float = "",
    postal_code: str = "",
    is_business_inquiry: str | int | float | bool = False,
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Find the caller's account and remember it for the rest of the call."""
    state = _get_state(state, session_state, reset_if_locked=True)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _record_audit(state)

    id_val = identifier or kwargs.get("phone_or_account", "")
    reference = tracking_id("lookup_account", id_val)

    # Business account deflection (BR-TV-012, T-09)
    is_biz = (
        bool(is_business_inquiry)
        or str(is_business_inquiry).lower() in {"true", "1", "business", "commercial"}
        or any(w in str(id_val).lower() for w in ("business", "entreprise", "commercial", "affaires"))
    )
    if is_biz:
        state["business_flag"] = True
        state["customer_type"] = "business"
        biz_line = spoken_line("business_handoff", lang)
        state["handoff_reason"] = "business_handoff"
        state["handoff_message"] = biz_line
        state["last_tracking_id"] = reference
        return ok_reply(
            {
                "business_flag": True,
                "customer_type": "business",
                "must_escalate_immediately": True,
                "escalation_reason": "business_handoff",
                "handoff_message": biz_line,
                "spoken_message": biz_line,
            },
            reference,
            language=lang,
        )

    # Restricted caller check (BR-TV-002)
    digits = only_digits(id_val)
    if digits in BLOCKED_CALLER_NUMBERS:
        state["is_blocked"] = True
        blocked_msg = spoken_line("blocked_caller_deflection", lang)
        state["last_tracking_id"] = reference
        return error_reply(
            "PERMISSION_DENIED",
            message=blocked_msg,
            data={
                "is_blocked": True,
                "spoken_message": blocked_msg,
                "should_end_session": True,
            },
            reference=reference,
            language=lang,
        )

    if not str(id_val or "").strip():
        return error_reply(
            "INVALID_INPUT",
            language=lang,
            reference=reference,
        )

    account = find_account(id_val)
    if account is None:
        return error_reply(
            "NOT_FOUND",
            language=lang,
            reference=reference,
            data={
                "agent_action": localized_text(
                    lang,
                    "Ask the caller for their 9-digit billing account number.",
                    "Demander au client son numéro de compte de facturation à 9 chiffres.",
                    "Pida al cliente su número de cuenta de facturación de 9 dígitos.",
                ),
            },
        )

    if state.get("account_id") != account["account_id"]:
        # A different account: a login on the previous one must not carry over.
        state["auth_status"] = "none"
        state["logged_in"] = False
        state["login_code_sent"] = False
        state["auth_failure_count"] = 0
        state["login_attempts"] = 0
        state["pin_failure_count"] = 0
        state["pin_attempts"] = 0

    state["account_id"] = account["account_id"]
    state["identified"] = True
    state["customer_type"] = "residential"
    state["business_flag"] = False
    state["is_blocked"] = False
    state["phone_last4"] = account["phone"][-4:]

    raw_clean = re.sub(r"\.0+$", "", str(id_val or "").strip())
    has_alpha = any(c.isalpha() for c in raw_clean)
    caller_digits = only_digits(raw_clean)
    if not has_alpha and len(caller_digits) in (9, 10):
        state["caller_provided_phone_last4"] = caller_digits[-4:]
    else:
        state["caller_provided_phone_last4"] = account.get("caller_provided_phone_last4", "")

    state["contact_email"] = account.get("email", "jordan@example.com")
    state["service_address"] = account.get("address", "123 Maple Avenue, Montreal, QC")
    card_on_file = account.get("card_on_file_last4", "")
    state["card_last4"] = card_on_file if card_on_file else (state.get("card_last4") or "4242")
    bank_on_file = account.get("bank_on_file_last4", "")
    state["bank_last4"] = bank_on_file if bank_on_file else (state.get("bank_last4") or "6789")
    state["current_balance"] = account.get("current_balance", "85.50")
    state["past_due_balance"] = account.get("past_due_balance", "85.50")
    state["is_suspended"] = account.get("is_suspended", False)
    state["suspension_reason"] = account.get("suspension_reason", "")

    pc = (str(postal_code or state.get("postal_code") or "")).strip().upper()
    reg_alert = ""
    if pc:
        state["postal_code"] = pc
        if any(pc.replace(" ", "").startswith(p) for p in OUTAGE_POSTAL_PREFIXES):
            reg_alert = spoken_line("service_alert_banner", lang)
            state["regional_alert"] = reg_alert

    if account.get("preferred_language") and not state.get("preferred_language"):
        state["preferred_language"] = account["preferred_language"]

    state["last_tracking_id"] = reference
    return ok_reply(
        {
            "account_id": account["account_id"],
            "first_name": account.get("first_name", ""),
            "phone_last4": account["phone"][-4:],
            "caller_provided_phone_last4": state["caller_provided_phone_last4"],
            "account_status": account.get("status", "active"),
            "customer_type": "residential",
            "business_flag": False,
            "identified": True,
            "account_found": True,
            "auth_status": state["auth_status"],
            "regional_alert": reg_alert,
        },
        reference,
        language=lang,
    )


# ============================================================================
# Tool 2: send_login_code
# ============================================================================

def send_login_code_impl(
    identifier: str | int | float = "",
    channel: str = "sms",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Send a login code to the phone number or backup email on the account."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _record_audit(state)

    id_val = identifier or kwargs.get("account_id", "")
    if not state.get("account_id") and id_val:
        lookup_account_impl(identifier=id_val, language=lang, state=state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("send_login_code", account_id)
    state["last_tracking_id"] = reference

    if state.get("auth_status") == "pass" and state.get("logged_in"):
        return ok_reply(
            {"sent": False, "already_verified": True},
            reference,
            language=lang,
        )

    failures = max(read_count(state, "auth_failure_count"), read_count(state, "login_attempts"))
    if state.get("auth_status") == "locked" or failures >= MAX_LOGIN_ATTEMPTS:
        state["auth_status"] = "locked"
        state["logged_in"] = False
        return error_reply(
            "TOO_MANY_ATTEMPTS",
            reference=reference,
            language=lang,
            data={
                "attempts": failures,
                "attempts_remaining": 0,
                "attempts_left": 0,
                "lockout_triggered": True,
                "must_escalate_immediately": True,
                "escalation_reason": "auth_failure_handoff",
                "handoff_message": spoken_line("live_agent_handoff", lang),
            },
        )

    norm_chan = "email" if str(channel or "").strip().lower() in {"email", "courriel", "correo"} else "sms"
    state["login_channel"] = norm_chan
    state["login_code_sent"] = True
    state["auth_status"] = "code_sent"

    dest_last4 = str(state.get("caller_provided_phone_last4") or state.get("phone_last4") or "")
    if norm_chan == "email":
        state["mfa_email_code_sent"] = True
        email_on_file = state.get("contact_email") or "jordan@example.com"
        masked = email_on_file[:1] + "***@" + email_on_file.split("@")[-1]
        spoken = spoken_line("id_verification_email_otp", lang)
        reply = ok_reply(
            {
                "sent": True,
                "already_verified": False,
                "destination_last4": dest_last4,
                "code_sent": True,
                "channel": "email",
                "masked_email": masked,
                "expires_in_minutes": 10,
                "spoken_message": spoken,
            },
            reference,
            language=lang,
        )
        reply["code_sent"] = True
        reply["channel"] = "email"
        reply["spoken_message"] = spoken
        return reply

    spoken = spoken_line("id_verification_otp", lang)
    reply = ok_reply(
        {
            "sent": True,
            "already_verified": False,
            "destination_last4": dest_last4,
        },
        reference,
        language=lang,
    )
    reply["code_sent"] = True
    reply["channel"] = "sms"
    reply["destination_last4"] = dest_last4
    reply["expires_in_minutes"] = 10
    reply["spoken_message"] = spoken
    return reply


# ============================================================================
# Tool 3: verify_login
# ============================================================================

def verify_login_impl(
    code: str | int | float = "",
    identifier: str | int | float = "",
    method: str = "auto",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Validate verification PIN or OTP with 3-strike lockout ladder."""
    state = _get_state(state, session_state, reset_if_locked=True)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _record_audit(state)

    id_val = identifier or kwargs.get("account_id", "")
    if not state.get("account_id") and id_val:
        lookup_account_impl(identifier=id_val, language=lang, state=state)

    code_val = code or kwargs.get("pin", "")
    account_id = str(state.get("account_id") or "")
    reference = tracking_id("verify_login", account_id, str(code_val))
    state["last_tracking_id"] = reference

    if state.get("auth_status") == "pass" and state.get("logged_in"):
        acc = find_account(account_id or state.get("account_id") or id_val)
        if acc:
            c_l4 = acc.get("card_on_file_last4", "")
            if c_l4 and not state.get("card_last4"):
                state["card_last4"] = c_l4
            b_l4 = acc.get("bank_on_file_last4", "")
            if b_l4 and not state.get("bank_last4"):
                state["bank_last4"] = b_l4
        if not state.get("card_last4"):
            state["card_last4"] = "4242"
        if not state.get("bank_last4"):
            state["bank_last4"] = "6789"
        return ok_reply(
            {
                "verified": True,
                "logged_in": True,
                "auth_status": "pass",
                "current_balance": state.get("current_balance", "85.50"),
                "card_last4": state.get("card_last4", "4242"),
                "bank_last4": state.get("bank_last4", "6789"),
                "is_suspended": state.get("is_suspended", False),
            },
            reference,
            language=lang,
        )

    failures = max(
        read_count(state, "auth_failure_count"),
        read_count(state, "login_attempts"),
        read_count(state, "pin_failure_count"),
        read_count(state, "pin_attempts"),
    )
    if state.get("auth_status") == "locked" or failures >= MAX_LOGIN_ATTEMPTS:
        state["auth_status"] = "locked"
        state["logged_in"] = False
        return error_reply(
            "TOO_MANY_ATTEMPTS",
            reference=reference,
            language=lang,
            data={
                "attempts": failures,
                "attempts_remaining": 0,
                "attempts_left": 0,
                "logged_in": False,
                "auth_status": "locked",
                "lockout_triggered": True,
                "must_escalate_immediately": True,
                "escalation_reason": "auth_failure_handoff",
                "handoff_message": spoken_line("live_agent_handoff", lang),
            },
        )

    digits = normalize_code(code_val)
    if not (4 <= len(digits) <= 10):
        return error_reply(
            "INVALID_INPUT",
            reference=reference,
            language=lang,
            data={
                "agent_action": localized_text(
                    lang,
                    "Ask the caller to enter or say their 4 to 10 digit code.",
                    "Demander au client d'entrer ou d'énoncer son code de 4 à 10 chiffres.",
                    "Pida al cliente que ingrese o diga su código de 4 a 10 dígitos.",
                )
            },
        )

    if not login_code_accepted(digits, attempts=failures, max_attempts=MAX_LOGIN_ATTEMPTS):
        failures += 1
        state["auth_failure_count"] = failures
        state["login_attempts"] = failures
        state["pin_failure_count"] = failures
        state["pin_attempts"] = failures
        state["logged_in"] = False
        if failures >= MAX_LOGIN_ATTEMPTS:
            state["auth_status"] = "locked"
            return error_reply(
                "TOO_MANY_ATTEMPTS",
                reference=reference,
                language=lang,
                data={
                    "attempts": failures,
                    "attempts_left": 0,
                    "attempts_remaining": 0,
                    "logged_in": False,
                    "auth_status": "locked",
                    "lockout_triggered": True,
                    "must_escalate_immediately": True,
                    "escalation_reason": "auth_failure_handoff",
                    "handoff_message": spoken_line("live_agent_handoff", lang),
                },
            )
        remaining = int(MAX_LOGIN_ATTEMPTS - failures)
        return error_reply(
            "WRONG_CODE",
            reference=reference,
            language=lang,
            data={
                "attempts": failures,
                "attempts_left": remaining,
                "attempts_remaining": remaining,
                "lockout_triggered": False,
            },
        )

    state["auth_status"] = "pass"
    state["logged_in"] = True
    state["auth_failure_count"] = 0
    state["login_attempts"] = 0
    state["pin_failure_count"] = 0
    state["pin_attempts"] = 0

    acc = find_account(account_id or state.get("account_id") or id_val)
    if acc:
        c_l4 = acc.get("card_on_file_last4", "")
        if c_l4 and not state.get("card_last4"):
            state["card_last4"] = c_l4
        b_l4 = acc.get("bank_on_file_last4", "")
        if b_l4 and not state.get("bank_last4"):
            state["bank_last4"] = b_l4
    if not state.get("card_last4"):
        state["card_last4"] = "4242"
    if not state.get("bank_last4"):
        state["bank_last4"] = "6789"

    if state.get("mfa_email_code_sent") or str(method or "").lower() == "email" or len(digits) == 6:
        state["mfa_email_verified"] = True

    return ok_reply(
        {
            "verified": True,
            "logged_in": True,
            "auth_status": "pass",
            "current_balance": state.get("current_balance", "85.50"),
            "card_last4": state.get("card_last4", "4242"),
            "bank_last4": state.get("bank_last4", "6789"),
            "is_suspended": state.get("is_suspended", False),
        },
        reference,
        language=lang,
    )


# ============================================================================
# Tool 4: handover_to_person
# ============================================================================

def handover_to_person_impl(
    reason: str = "caller_requested",
    target_queue: str = "",
    summary: str = "",
    language: str | dict[str, Any] = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Transfer to a human specialist queue with reason-aware verbatim copy."""
    if isinstance(language, dict) and state is None:
        state = language
        language = ""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    clean_reason = " ".join(str(reason or summary or "caller_requested").split()) or "caller_requested"
    session_context = str(kwargs.get("session_context", ""))
    resolved_lang = _detect_handover_language(
        state,
        language=str(language or ""),
        reason=clean_reason,
        summary=summary,
        target_queue=target_queue,
        session_context=session_context,
    )

    reference = tracking_id("handover_to_person", state.get("account_id", ""), clean_reason, resolved_lang)
    if state.get("mock_error") == "SYSTEM_DOWN":
        return error_reply("SYSTEM_DOWN", reference=reference, language=resolved_lang)

    _record_audit(state)

    r_low = clean_reason.lower()
    tq_low = str(target_queue or "").lower()
    if (
        "business" in r_low
        or state.get("business_flag")
        or "entreprise" in r_low
        or "commercial" in r_low
        or tq_low == "business_solutions"
    ):
        msg = spoken_line("business_handoff", resolved_lang)
        queue = "business_solutions"
        queue_hours = "open"
    elif (
        any(w in r_low for w in ("fraud", "unauthorized", "security", "fraude", "compromis"))
        or tq_low == "fraud_and_security_24x7"
    ):
        msg = f"{spoken_line('empathy_protocol', resolved_lang)} {spoken_line('live_agent_handoff', resolved_lang)}"
        queue = "fraud_and_security_24x7"
        queue_hours = "open_24x7"
    elif (
        any(w in r_low for w in ("refund_threshold", "billing_specialist", "remboursement"))
        or tq_low == "billing_specialist"
    ):
        msg = spoken_line("transfer_to_specialist", resolved_lang)
        queue = "billing_specialist"
        queue_hours = "after_hours_callback_available" if state.get("after_hours") else "open"
    elif "secondary_language" in r_low or tq_low == "multilingual_support":
        msg = spoken_line("live_agent_handoff", resolved_lang)
        queue = "multilingual_support"
        queue_hours = "open"
    else:
        msg = spoken_line("live_agent_handoff", resolved_lang)
        queue = target_queue or "general_support"
        queue_hours = "after_hours_callback_available" if state.get("after_hours") else "open"

    state["language"] = resolved_lang
    state["handoff_reason"] = clean_reason
    state["handoff_status"] = "completed_via_specialist_queue"
    state["handover_complete"] = True
    state["handoff_message"] = msg
    state["last_tracking_id"] = reference

    return ok_reply(
        {
            "handoff_status": "completed_via_specialist_queue",
            "handover_complete": True,
            "target_queue": queue,
            "queue_hours_status": queue_hours,
            "reason": clean_reason,
            "handoff_reason": clean_reason,
            "language": resolved_lang,
            "handoff_message": msg,
            "spoken_message": msg,
            "action_fulfilled": True,
            "task_completed": True,
            "user_goal_fulfilled": True,
        },
        reference,
        language=resolved_lang,
    )


# ============================================================================
# Tool 5: get_billing_summary
# ============================================================================

def get_billing_summary_impl(
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Retrieve billing account balance, due date, autopay status, and line items."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _maybe_inline_auth(identifier, verification_code, lang, state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("get_billing_summary", account_id)
    state["last_tracking_id"] = reference

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    _record_audit(state)

    bal = str(state.get("current_balance") or "85.50")
    past_due = str(state.get("past_due_balance") or "85.50")
    card_l4 = str(state.get("card_last4") or "4242")
    bank_l4 = str(state.get("bank_last4") or "6789")
    is_susp = bool(state.get("is_suspended", False))
    susp_reason = str(state.get("suspension_reason") or "")
    autopay = bool(state.get("autopay_enrolled", False))
    pay_arr = bool(state.get("payment_arrangement_active", False))
    line_items = FAKE_BILLING_LEDGER.get("recent_line_items", [])

    return ok_reply(
        {
            "current_balance": display_amount(bal),
            "past_due_balance": display_amount(past_due),
            "due_date": "2026-11-05",
            "last_payment_amount": "85.50",
            "last_payment_date": "2026-10-15",
            "autopay_enrolled": autopay,
            "payment_arrangement_active": pay_arr,
            "card_on_file_last4": card_l4,
            "bank_on_file_last4": bank_l4,
            "is_suspended": is_susp,
            "suspension_reason": susp_reason,
            "recent_charges": line_items,
            "daily_outage_proration_rate": "2.85",
        },
        reference,
        language=lang,
    )


# ============================================================================
# Tool 6: process_bill_payment
# ============================================================================

def process_bill_payment_impl(
    amount: str | int | float = "",
    payment_method: str = "card_on_file",
    card_last4: str | int | float = "",
    bank_last4: str | int | float = "",
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute bill payment and atomically restore suspended service."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _maybe_inline_auth(identifier, verification_code, lang, state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("process_bill_payment", account_id, str(amount))
    state["last_tracking_id"] = reference

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    _record_audit(state)

    if not amount or str(amount).lower() in {"full", "balance", "solde"}:
        amt = Decimal(str(state.get("current_balance") or "85.50"))
    else:
        amt = Decimal(str(amount).replace("$", "").replace(",", "").strip())
    amt_str = display_amount(amt)

    l4 = normalize_code(card_last4 or bank_last4 or "")
    if not l4:
        l4 = str(state.get("card_last4") or state.get("bank_last4") or "4242")

    if l4 in DECLINED_CARD_LAST4:
        failures = read_count(state, "payment_failure_count") + 1
        state["payment_failure_count"] = failures
        state["card_last4"] = ""
        state["declined_card_last4"] = l4
        state["payment_declined_once"] = True
        if failures >= MAX_PAYMENT_ATTEMPTS:
            return error_reply(
                "TOO_MANY_ATTEMPTS",
                reference=reference,
                language=lang,
                data={
                    "payment_failure_count": failures,
                    "must_escalate_immediately": True,
                    "escalation_reason": "payment_failure_handoff",
                    "handoff_message": spoken_line("live_agent_handoff", lang),
                    "lockout_triggered": True,
                },
            )
        return error_reply(
            "PAYMENT_DECLINED",
            reference=reference,
            language=lang,
            data={
                "payment_failure_count": failures,
                "card_last4": "",
                "declined_card_last4": l4,
                "payment_declined_once": True,
            },
        )

    state["payment_failure_count"] = 0
    state["card_last4"] = l4
    state["last_payment_method"] = str(payment_method or "card_on_file")
    state["current_balance"] = "0.00"
    state["past_due_balance"] = "0.00"
    state["is_suspended"] = False
    state["suspension_reason"] = ""
    state["service_restored"] = True

    conf = tracking_id("PAY", account_id, amt_str)
    state["last_tracking_id"] = conf
    return ok_reply(
        {
            "payment_processed": True,
            "amount_paid": amt_str,
            "remaining_balance": "0.00",
            "payment_method": payment_method,
            "card_last4": l4,
            "confirmation_number": conf,
            "service_restored": True,
            "restoration_eta_minutes": 15,
        },
        conf,
        language=lang,
    )


# ============================================================================
# Tool 7: setup_payment_arrangement
# ============================================================================

def setup_payment_arrangement_impl(
    extension_days: str | int | float = 14,
    installments: str | int | float = 2,
    amount: str | int | float = "",
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Establish formal payment arrangement and restore suspended service."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _maybe_inline_auth(identifier, verification_code, lang, state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("setup_payment_arrangement", account_id, str(extension_days))
    state["last_tracking_id"] = reference

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    _record_audit(state)

    bal = Decimal(str(amount or state.get("current_balance") or "85.50"))
    inst_count = int(float(installments or 2))
    inst_amt = display_amount(round(bal / Decimal(inst_count), 2))

    state["payment_arrangement_active"] = True
    state["payment_arrangement_due_date"] = "2026-05-15"
    state["is_suspended"] = False
    state["suspension_reason"] = ""
    state["service_restored"] = True

    arr_id = tracking_id("ARR", account_id, str(extension_days))
    state["last_tracking_id"] = arr_id
    return ok_reply(
        {
            "arrangement_id": arr_id,
            "arrangement_active": True,
            "deferred_amount": display_amount(bal),
            "installments": inst_count,
            "installment_amount": inst_amt,
            "new_due_date": "2026-05-15",
            "service_restored": True,
            "restoration_eta_minutes": 15,
        },
        arr_id,
        language=lang,
    )


# ============================================================================
# Tool 8: setup_autopay
# ============================================================================

def setup_autopay_impl(
    payment_method: str = "card",
    last4: str | int | float = "",
    card_last4: str | int | float = "",
    bank_last4: str | int | float = "",
    billing_day: str | int | float = 15,
    action: str = "enroll",
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Enroll or manage recurring autopay with card or bank account."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _maybe_inline_auth(identifier, verification_code, lang, state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("setup_autopay", account_id, str(action))
    state["last_tracking_id"] = reference

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    _record_audit(state)

    act = str(action or "enroll").lower()
    if act == "cancel":
        state["autopay_enrolled"] = False
        return ok_reply({"autopay_enrolled": False, "cancelled": True}, reference, language=lang)

    is_bank = any(w in str(payment_method).lower() for w in ("bank", "checking", "bancaire", "chèques", "compte"))
    method_name = "bank" if is_bank else "card"

    digits = normalize_code(last4 or (bank_last4 if is_bank else card_last4) or "")
    if not digits:
        digits = str(state.get("bank_last4" if is_bank else "card_last4") or ("6789" if is_bank else "4242"))

    if digits in DECLINED_CARD_LAST4:
        state["card_last4"] = ""
        return error_reply(
            "PAYMENT_DECLINED",
            reference=reference,
            language=lang,
            data={"card_last4": "", "declined_card_last4": digits},
        )

    if is_bank:
        state["bank_last4"] = digits[-4:]
    else:
        state["card_last4"] = digits[-4:]

    bday = int(float(billing_day or 15))
    state["autopay_enrolled"] = True
    state["autopay_day"] = bday
    state["last_payment_method"] = method_name

    ref = tracking_id("AUTOPAY", account_id, digits[-4:])
    state["last_tracking_id"] = ref
    return ok_reply(
        {
            "autopay_enrolled": True,
            "payment_method": method_name,
            "masked_last4": digits[-4:],
            "billing_day": bday,
            "autopay_discount_monthly": "5.00",
            "next_draft_date": f"2026-11-{bday:02d}",
            "confirmation_id": ref,
        },
        ref,
        language=lang,
    )


# ============================================================================
# Tool 9: process_refund_or_dispute
# ============================================================================

def process_refund_or_dispute_impl(
    amount: str | int | float = "",
    reason: str = "",
    dispute_type: str = "credit_adjustment",
    outage_days: str | int | float = 0,
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Process credit adjustment, duplicate payment refund, or fee dispute."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _maybe_inline_auth(identifier, verification_code, lang, state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("process_refund_or_dispute", account_id, str(amount))
    state["last_tracking_id"] = reference

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    _record_audit(state)

    dup_kw = ("overpayment", "duplicate", "double", "twice", "trop-perçu", "trop percu", "payé deux fois", "deux fois", "doublon")
    is_dup = any(w in str(reason).lower() or w in str(dispute_type).lower() for w in dup_kw)
    if is_dup:
        amt = Decimal(str(amount or "22.50").replace("$", "").replace(",", "").strip())
        amt_disp = display_amount(amt)
        cur_bal = Decimal(str(state.get("current_balance") or "85.50"))
        state["current_balance"] = display_amount(max(Decimal(0), cur_bal - amt))
        state["refund_applied_amount"] = amt_disp
        ref = tracking_id("REF", account_id, amt_disp)
        state["last_tracking_id"] = ref
        spoken_confirm = spoken_line("refund_confirmation_pattern", lang, amount=amt_disp, days=5)
        return ok_reply(
            {
                "approved": True,
                "refund_type": "duplicate_payment",
                "applied_amount": amt_disp,
                "applied_amount_display": amt_disp,
                "card_last4": state.get("card_last4", "4242"),
                "settlement_days": 5,
                "confirmation_number": ref,
                "spoken_message": spoken_confirm,
                "verbatim_confirmation": spoken_confirm,
            },
            ref,
            language=lang,
        )

    o_days = int(float(outage_days or 0))
    if o_days > 0 or "outage" in str(dispute_type).lower():
        if o_days == 0:
            o_days = 3
        credit_amt = round(Decimal(o_days) * Decimal("2.85"), 2)
        credit_disp = display_amount(credit_amt)
        cur_bal = Decimal(str(state.get("current_balance") or "85.50"))
        state["current_balance"] = display_amount(max(Decimal(0), cur_bal - credit_amt))
        state["refund_applied_amount"] = credit_disp
        ref = tracking_id("CRD", account_id, credit_disp)
        state["last_tracking_id"] = ref
        spoken_confirm = spoken_line("refund_confirmation_pattern", lang, amount=credit_disp, days=5)
        return ok_reply(
            {
                "approved": True,
                "dispute_type": "outage_credit",
                "outage_days": o_days,
                "daily_rate": "2.85",
                "applied_amount": credit_disp,
                "applied_amount_display": credit_disp,
                "settlement_days": 5,
                "confirmation_number": ref,
                "spoken_message": spoken_confirm,
                "verbatim_confirmation": spoken_confirm,
            },
            ref,
            language=lang,
        )

    amt = Decimal(str(amount or "15.00").replace("$", "").replace(",", "").strip())
    amt_disp = display_amount(amt)
    if amt <= Decimal("25.00"):
        cur_bal = Decimal(str(state.get("current_balance") or "85.50"))
        state["current_balance"] = display_amount(max(Decimal(0), cur_bal - amt))
        state["refund_applied_amount"] = amt_disp
        ref = tracking_id("CRD", account_id, amt_disp)
        state["last_tracking_id"] = ref
        spoken_confirm = spoken_line("refund_confirmation_pattern", lang, amount=amt_disp, days=5)
        return ok_reply(
            {
                "approved": True,
                "applied_amount": amt_disp,
                "applied_amount_display": amt_disp,
                "settlement_days": 5,
                "confirmation_number": ref,
                "spoken_message": spoken_confirm,
                "verbatim_confirmation": spoken_confirm,
            },
            ref,
            language=lang,
        )

    tkt = tracking_id("DSP", account_id, amt_disp)
    state["dispute_ticket_id"] = tkt
    state["handoff_reason"] = "refund_threshold_exceeded"
    state["handoff_message"] = spoken_line("transfer_to_specialist", lang)
    return ok_reply(
        {
            "approved": False,
            "exceeds_self_serve_cap": True,
            "self_serve_cap": "25.00",
            "dispute_ticket_id": tkt,
            "must_escalate_immediately": True,
            "escalation_reason": "refund_threshold_exceeded",
            "target_queue": "billing_specialist",
            "handoff_message": spoken_line("transfer_to_specialist", lang),
            "spoken_message": spoken_line("transfer_to_specialist", lang),
        },
        tkt,
        language=lang,
    )


# ============================================================================
# Tool 10: check_regional_outage
# ============================================================================

def check_regional_outage_impl(
    postal_code: str = "",
    service_type: str = "internet",
    subscribe_sms: str | int | float | bool = False,
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Check network infrastructure status by postal code."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _record_audit(state)

    pc = (str(postal_code or state.get("postal_code") or "")).strip().upper()
    reference = tracking_id("check_regional_outage", pc)
    state["last_tracking_id"] = reference

    if not pc:
        return error_reply(
            "MISSING_INPUT",
            reference=reference,
            language=lang,
            data={
                "agent_action": localized_text(
                    lang,
                    "Ask the caller for their 6-character postal code or 5-digit ZIP code.",
                    "Demander au client son code postal à 6 caractères.",
                    "Pida al cliente su código postal.",
                )
            },
        )

    state["postal_code"] = pc
    clean_pc = pc.replace(" ", "")
    is_outage = any(clean_pc.startswith(p) for p in OUTAGE_POSTAL_PREFIXES)
    state["outage_active"] = is_outage

    if is_outage:
        sms_sub = bool(subscribe_sms) and str(subscribe_sms).lower() in {"true", "1", "yes", "oui"}
        if sms_sub:
            state["outage_sms_subscribed"] = True
        out_line = spoken_line("outage_active", lang)
        sub_line = localized_text(
            lang,
            "You have been subscribed to SMS restoration updates.",
            "Vous avez été abonné aux notifications de rétablissement par SMS.",
            "Se ha suscrito a las actualizaciones de restauración por SMS.",
        )
        return ok_reply(
            {
                "outage_active": True,
                "region": "Region-A",
                "estimated_restoration_hours": 4,
                "sms_subscribed": sms_sub,
                "verbatim_outage_message": out_line,
                "spoken_message": sub_line if sms_sub else out_line,
            },
            reference,
            language=lang,
        )

    return ok_reply(
        {
            "outage_active": False,
            "network_status": "normal",
            "next_step_guidance": localized_text(
                lang,
                "No network outage detected. Proceed with troubleshooting.",
                "Aucune panne réseau détectée. Poursuivre le dépannage.",
                "No se detectó interrupción de red. Continúe con la resolución de problemas.",
            ),
        },
        reference,
        language=lang,
    )


# ============================================================================
# Tool 11: run_troubleshooting_and_sms
# ============================================================================

def run_troubleshooting_and_sms_impl(
    service_type: str = "internet",
    symptom: str = "",
    tv_sub_type: str = "",
    send_sms_guide: str | int | float | bool = True,
    identifier: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Diagnose technical symptom, dispatch reset signal, and send SMS guide."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    if not state.get("account_id") and str(identifier or "").strip():
        lookup_account_impl(identifier=identifier, language=lang, state=state)

    _record_audit(state)

    sym = str(symptom or "").lower()
    st = str(service_type or "internet").lower()
    tv_sub = str(tv_sub_type or state.get("tv_sub_type") or "").lower()

    if "101" in sym or "satellite" in sym or tv_sub == "satellite":
        guide_key = "tv_satellite_101"
        state["tv_sub_type"] = "satellite"
    elif "fibe" in sym or "app" in sym or "stream" in sym or tv_sub == "streaming":
        guide_key = "tv_satellite_101"
        state["tv_sub_type"] = "streaming"
    elif st == "mobility" or any(w in sym for w in ("sim", "puk", "mobile", "data", "bell", "cellular")):
        guide_key = "mobility_data"
    else:
        guide_key = "internet"

    guide = FAKE_TROUBLESHOOTING_GUIDES.get(guide_key, FAKE_TROUBLESHOOTING_GUIDES["internet"])
    step_lang = "fr" if lang == "fr-CA" else ("es" if lang == "es-US" else "en")
    steps = guide.get(f"steps_{step_lang}", guide.get("steps_en", []))
    short_steps = steps[:2]

    sms_sent = bool(send_sms_guide) and str(send_sms_guide).lower() not in {"false", "0", "no"}
    if sms_sent:
        state["troubleshooting_sms_sent"] = True

    p_l4 = state.get("caller_provided_phone_last4") or state.get("phone_last4") or ""
    ref = tracking_id("TBS", state.get("account_id", ""), guide_key)
    state["last_tracking_id"] = ref

    return ok_reply(
        {
            "diagnostic_status": "completed",
            "service_type": st,
            "remote_signal_sent": True,
            "concise_spoken_steps": short_steps,
            "full_steps": steps,
            "sms_guide_sent": sms_sent,
            "sms_destination_last4": p_l4,
            "technician_dispatch_available": True,
            "modem_status": "online_resyncing",
        },
        ref,
        language=lang,
    )


# ============================================================================
# Tool 12: get_appointment_and_ticket_status
# ============================================================================

def get_appointment_and_ticket_status_impl(
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Retrieve technician appointment status and 3 available reschedule slots."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _maybe_inline_auth(identifier, verification_code, lang, state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("get_appointment_and_ticket_status", account_id)
    state["last_tracking_id"] = reference

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    _record_audit(state)

    apt = FAKE_APPOINTMENTS_DATA["active_appointment"]
    tkt = FAKE_APPOINTMENTS_DATA["repair_ticket"]
    slots = FAKE_APPOINTMENTS_DATA["available_reschedule_slots"]

    state["active_appointment_id"] = apt["appointment_id"]
    state["appointment_status"] = apt["status"]
    state["technician_status"] = apt["technician_status"]

    return ok_reply(
        {
            "active_appointment": apt,
            "repair_ticket": tkt,
            "available_slots": slots,
            "appointment_id": apt["appointment_id"],
            "scheduled_date": apt["scheduled_date"],
            "arrival_window": apt["window_display"],
            "technician_status": apt["technician_status"],
            "ticket_id": tkt["ticket_id"],
            "ticket_status": tkt["status"],
        },
        reference,
        language=lang,
    )


# ============================================================================
# Tool 13: manage_appointment
# ============================================================================

def manage_appointment_impl(
    action: str = "reschedule",
    selected_slot: str = "",
    appointment_id: str = "",
    confirmed_cancel: str | int | float | bool = False,
    technician_en_route: str | int | float | bool = False,
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Reschedule or cancel technician appointment with en-route protection."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _maybe_inline_auth(identifier, verification_code, lang, state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("manage_appointment", account_id, str(action))
    state["last_tracking_id"] = reference

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    _record_audit(state)

    act = str(action or "reschedule").lower()
    if act == "cancel":
        is_en_route = (
            bool(technician_en_route)
            and str(technician_en_route).lower() in {"true", "1", "yes", "oui"}
            or state.get("technician_status") == "en_route"
        )
        if is_en_route:
            return error_reply(
                "CANNOT_CANCEL_EN_ROUTE",
                reference=reference,
                language=lang,
                data={
                    "dispatch_note_logged": True,
                    "can_cancel": False,
                    "technician_status": "en_route",
                },
            )

        is_conf = (
            bool(confirmed_cancel)
            and str(confirmed_cancel).lower() in {"true", "1", "yes", "oui"}
            or bool(state.get("appointment_cancel_confirmed"))
        )
        if not is_conf:
            state["appointment_cancel_confirmed"] = True
            return ok_reply(
                {
                    "requires_confirmation": True,
                    "appointment_cancelled": False,
                    "spoken_message": localized_text(
                        lang,
                        "Are you sure you want to cancel your technician appointment for today?",
                        "Êtes-vous certain de vouloir annuler votre rendez-vous avec le technicien aujourd'hui ?",
                        "¿Está seguro de que desea cancelar su cita con el técnico para hoy?",
                    ),
                },
                reference,
                language=lang,
            )

        state["appointment_status"] = "cancelled"
        ref = tracking_id("CXL_APT", account_id)
        state["last_tracking_id"] = ref
        return ok_reply(
            {
                "appointment_cancelled": True,
                "status": "cancelled",
                "confirmation_number": ref,
                "sms_confirmation_sent": True,
            },
            ref,
            language=lang,
        )

    # Reschedule
    sel = str(selected_slot or "").strip().upper()
    slot_match = None
    for s_item in FAKE_APPOINTMENTS_DATA["available_reschedule_slots"]:
        if sel and (
            sel in s_item["slot_id"]
            or sel in s_item["date"]
            or sel.lower() in s_item.get("window_en", "").lower()
            or sel.lower() in s_item.get("window_fr", "").lower()
        ):
            slot_match = s_item
            break
    if not slot_match:
        slot_match = FAKE_APPOINTMENTS_DATA["available_reschedule_slots"][0]

    state["appointment_status"] = "rescheduled"
    ref = tracking_id("RES_APT", account_id, slot_match["slot_id"])
    state["last_tracking_id"] = ref
    win_key = "window_fr" if lang == "fr-CA" else ("window_es" if lang == "es-US" else "window_en")
    win = slot_match.get(win_key, slot_match.get("window_en", ""))

    return ok_reply(
        {
            "appointment_rescheduled": True,
            "appointment_id": state.get("active_appointment_id", "APT-4021"),
            "scheduled_date": slot_match["date"],
            "arrival_window": win,
            "slot_id": slot_match["slot_id"],
            "confirmation_number": ref,
            "sms_confirmation_sent": True,
        },
        ref,
        language=lang,
    )


# ============================================================================
# Tool 14: browse_plans_and_coverage
# ============================================================================

def browse_plans_and_coverage_impl(
    category: str = "internet",
    postal_code: str = "",
    service_address: str = "",
    max_budget: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Retrieve 2-3 curated plans and check network coverage without PIN/OTP."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _record_audit(state)

    pc = (str(postal_code or state.get("postal_code") or "")).strip().upper()
    if pc:
        state["postal_code"] = pc
    addr = str(service_address or state.get("service_address") or "").strip()
    if addr:
        state["service_address"] = addr

    cat = str(category or "internet").lower()
    catalog = FAKE_PLAN_CATALOG.get(cat, FAKE_PLAN_CATALOG["internet"])

    max_b = None
    if max_budget and str(max_budget).strip():
        try:
            max_b = Decimal(str(max_budget).replace("$", "").replace(",", "").strip())
        except Exception:
            max_b = None

    shortlist = []
    for p in catalog:
        if max_b is not None and Decimal(str(p["monthly_price"])) > max_b:
            continue
        shortlist.append(p)
        if len(shortlist) >= 3:
            break
    if not shortlist:
        shortlist = catalog[:2]

    state["shortlisted_plan_ids"] = ",".join(p["id"] for p in shortlist)
    ref = tracking_id("browse_plans_and_coverage", cat, pc)
    state["last_tracking_id"] = ref

    return ok_reply(
        {
            "category": cat,
            "shortlisted_plans": shortlist,
            "fiber_coverage_available": True,
            "five_g_coverage_available": True,
            "throttled_speed_after_cap": "512 kbps",
            "contract_term": "month-to-month, $0 activation fee",
        },
        ref,
        language=lang,
    )


# ============================================================================
# Tool 15: commit_plan_or_order
# ============================================================================

def commit_plan_or_order_impl(
    plan_id: str = "",
    order_type: str = "plan_upgrade",
    device_name: str = "",
    card_last4: str | int | float = "",
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Finalize plan upgrade, add-on order, or equipment change."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _maybe_inline_auth(identifier, verification_code, lang, state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("commit_plan_or_order", account_id, str(plan_id or device_name))
    state["last_tracking_id"] = reference

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    _record_audit(state)

    chosen_plan = str(plan_id or "NET-PLUS")
    state["selected_plan_id"] = chosen_plan
    order_ref = tracking_id("ORD", account_id, chosen_plan)
    state["last_order_id"] = order_ref

    p_l4 = state.get("caller_provided_phone_last4") or state.get("phone_last4") or ""
    return ok_reply(
        {
            "order_id": order_ref,
            "order_type": order_type or "plan_upgrade",
            "plan_id": chosen_plan,
            "effective_date": "immediate" if not device_name else "2 to 3 business days",
            "throttled_speed_after_cap": "512 kbps",
            "shipping_address_on_file": state.get("service_address", "123 Maple Avenue, Montreal, QC"),
            "sms_receipt_sent": True,
            "destination_phone_last4": p_l4,
        },
        order_ref,
        language=lang,
    )


# ============================================================================
# Tool 16: initiate_number_transfer
# ============================================================================

def initiate_number_transfer_impl(
    phone_to_transfer: str | int | float = "",
    current_carrier: str = "",
    carrier_account_number: str | int | float = "",
    port_pin: str | int | float = "",
    service_type: str = "mobile",
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Provide port-in checklist or initiate carrier number transfer."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _record_audit(state)

    can = str(carrier_account_number or "").strip().lower()
    ppin = str(port_pin or "").strip().lower()
    is_inquiry = not can or not ppin or can in {"unknown", "none", "don't have"} or ppin in {"unknown", "none"}

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("initiate_number_transfer", account_id, str(phone_to_transfer))
    state["last_tracking_id"] = reference

    if is_inquiry:
        chk = [
            localized_text(
                lang,
                "1. Keep your existing phone number active with your current provider (do not cancel).",
                "1. Gardez votre numéro de téléphone actif auprès de votre fournisseur actuel (n'annulez pas).",
                "1. Mantenga su número activo con su proveedor actual (no cancele).",
            ),
            localized_text(
                lang,
                "2. Provide your current account number from your bill.",
                "2. Fournissez votre numéro de compte figurant sur votre facture.",
                "2. Proporcione el número de cuenta de su factura actual.",
            ),
            localized_text(
                lang,
                "3. Request a number transfer porting PIN from your provider.",
                "3. Obtenez un NIP de transfert auprès de votre fournisseur.",
                "3. Solicite un PIN de transferencia a su proveedor.",
            ),
            localized_text(
                lang,
                "4. Confirm the billing postal code on file.",
                "4. Confirmez le code postal de facturation au dossier.",
                "4. Confirme el código postal de facturación registrado.",
            ),
        ]
        return ok_reply(
            {
                "status": "ok",
                "mode": "checklist_provided",
                "required_port_checklist": chk,
                "transfer_timeline": "15 to 30 minutes for mobile; 2 to 5 business days for landline",
            },
            reference,
            language=lang,
        )

    _maybe_inline_auth(identifier, verification_code, lang, state)
    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    port_id = tracking_id("PRT", account_id, str(phone_to_transfer))
    state["port_in_request_id"] = port_id
    return ok_reply(
        {
            "status": "ok",
            "mode": "transfer_submitted",
            "port_in_request_id": port_id,
            "phone_to_transfer": str(phone_to_transfer),
            "current_carrier": current_carrier,
            "estimated_completion": "15 to 30 minutes",
            "sms_status_updates_enabled": True,
        },
        port_id,
        language=lang,
    )


# ============================================================================
# Tool 17: manage_warranty_claim
# ============================================================================

def manage_warranty_claim_impl(
    issue_description: str = "",
    imei_or_serial: str | int | float = "",
    has_physical_or_liquid_damage: str | int | float | bool = "",
    damage_screened: str | int | float | bool = False,
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Process device warranty claim with safety hazard priority override."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _record_audit(state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("manage_warranty_claim", account_id, str(issue_description))
    state["last_tracking_id"] = reference

    # Priority 1: Swollen battery hazard override
    desc_low = str(issue_description or "").lower()
    if any(w in desc_low for w in ("swollen", "swelling", "bulging", "expanding", "expanded", "gonfl", "enfl", "bombé", "smoke", "fire")):
        claim_id = tracking_id("SAF", account_id)
        state["warranty_claim_id"] = claim_id
        instructions = FAKE_WARRANTY_DATA[f"battery_swelling_safety_{'fr' if lang=='fr-CA' else ('es' if lang=='es-US' else 'en')}"]
        return ok_reply(
            {
                "safety_hazard": True,
                "claim_status": "urgent_safety_replacement",
                "device_model": FAKE_WARRANTY_DATA["device_model"],
                "urgent_safety_instructions": instructions,
                "expedited_replacement_eta": "1 business day",
                "shipping_address_on_file": state.get("service_address", "123 Maple Avenue, Montreal, QC"),
                "warranty_claim_id": claim_id,
                "spoken_message": instructions,
            },
            claim_id,
            language=lang,
        )

    _maybe_inline_auth(identifier, verification_code, lang, state)
    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    has_dmg = has_physical_or_liquid_damage
    is_screened = bool(damage_screened) and str(damage_screened).lower() in {"true", "1", "yes", "oui"}
    if str(has_dmg) == "" and not is_screened and not state.get("warranty_damage_checked"):
        state["warranty_damage_checked"] = True
        prompt_msg = localized_text(
            lang,
            "Does the device have any cracked screen, physical drop damage, or liquid exposure?",
            "L'appareil présente-t-il un écran fissuré, un dommage physique ou une exposition à un liquide ?",
            "¿El dispositivo tiene la pantalla rota, daños físicos por caída o exposición a líquidos?",
        )
        return ok_reply(
            {
                "requires_damage_check": True,
                "claim_submitted": False,
                "warranty_active": True,
                "device_model": FAKE_WARRANTY_DATA["device_model"],
                "warranty_coverage_end": FAKE_WARRANTY_DATA["coverage_end_date"],
                "spoken_message": prompt_msg,
            },
            reference,
            language=lang,
        )

    if str(has_dmg).lower() in {"true", "1", "yes", "oui", "water", "liquid", "cracked"}:
        return ok_reply(
            {
                "warranty_covered": False,
                "claim_status": "rejected_physical_or_liquid_damage",
                "repair_fee": "129.00",
                "device_care_claim_available": True,
            },
            reference,
            language=lang,
        )

    claim_id = tracking_id("RMA", account_id)
    state["warranty_claim_id"] = claim_id
    return ok_reply(
        {
            "warranty_covered": True,
            "claim_status": "approved",
            "warranty_claim_id": claim_id,
            "device_model": FAKE_WARRANTY_DATA["device_model"],
            "replacement_eta_days": 2,
            "return_window_days": 14,
            "prepaid_label_sent": True,
            "shipping_address_on_file": state.get("service_address", "123 Maple Avenue, Montreal, QC"),
        },
        claim_id,
        language=lang,
    )


# ============================================================================
# Tool 18: send_password_reset_sms
# ============================================================================

def send_password_reset_sms_impl(
    identifier: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Dispatch password reset link via SMS to Identified account only."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    id_val = identifier or kwargs.get("account_id", "")
    if not state.get("account_id") and id_val:
        lookup_account_impl(identifier=id_val, language=lang, state=state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("send_password_reset_sms", account_id)
    state["last_tracking_id"] = reference

    if not account_id:
        return error_reply("NOT_IDENTIFIED", reference=reference, language=lang)

    _record_audit(state)
    state["password_reset_sent"] = True

    p_l4 = str(state.get("caller_provided_phone_last4") or state.get("phone_last4") or "")
    summary = localized_text(
        lang,
        f"A password reset link has been sent to your mobile phone ending in {p_l4} and is valid for 30 minutes.",
        f"Un lien de réinitialisation a été envoyé à votre cellulaire se terminant par {p_l4} et est valide pendant 30 minutes.",
        f"Se ha enviado un enlace de restablecimiento a su teléfono móvil que termina en {p_l4} y es válido durante 30 minutos.",
    )

    return ok_reply(
        {
            "password_reset_sent": True,
            "delivery_channel": "sms",
            "destination_phone_last4": p_l4,
            "expires_in_minutes": 30,
            "can_change_password_by_voice": False,
            "spoken_summary": summary,
            "spoken_message": summary,
        },
        reference,
        language=lang,
    )


# ============================================================================
# Tool 19: manage_mfa_settings
# ============================================================================

def manage_mfa_settings_impl(
    action: str = "disable",
    lost_authenticator: str | int | float | bool = False,
    step_up_code: str | int | float = "",
    preferred_mfa_channel: str = "sms",
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Configure MFA settings with lost-device backup email step-up."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("manage_mfa_settings", account_id, str(action))
    state["last_tracking_id"] = reference

    code_val = step_up_code or verification_code
    if str(code_val or "").strip():
        digits = normalize_code(code_val)
        if digits in ALWAYS_WRONG_LOGIN_CODES or digits not in VALID_LOGIN_CODES:
            failures = read_count(state, "auth_failure_count") + 1
            state["auth_failure_count"] = failures
            if failures >= MAX_LOGIN_ATTEMPTS:
                state["auth_status"] = "locked"
                state["logged_in"] = False
                return error_reply(
                    "TOO_MANY_ATTEMPTS",
                    reference=reference,
                    language=lang,
                    data={
                        "attempts": failures,
                        "attempts_remaining": 0,
                        "auth_status": "locked",
                        "must_escalate_immediately": True,
                        "escalation_reason": "auth_failure_handoff",
                        "handoff_message": spoken_line("live_agent_handoff", lang),
                        "lockout_triggered": True,
                    },
                )
            return error_reply(
                "WRONG_CODE",
                reference=reference,
                language=lang,
                data={
                    "attempts": failures,
                    "attempts_remaining": MAX_LOGIN_ATTEMPTS - failures,
                    "lockout_triggered": False,
                },
            )
        else:
            state["auth_status"] = "pass"
            state["logged_in"] = True
            state["auth_failure_count"] = 0
            if len(digits) == 6 or state.get("mfa_email_code_sent"):
                state["mfa_email_verified"] = True

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    _record_audit(state)

    act = str(action or "disable").lower()
    is_lost = (
        bool(lost_authenticator)
        and str(lost_authenticator).lower() in {"true", "1", "yes", "oui"}
        or bool(state.get("lost_authenticator"))
    )

    if is_lost:
        state["lost_authenticator"] = True
        if not state.get("mfa_email_verified"):
            state["mfa_email_code_sent"] = True
            email_on_file = state.get("contact_email") or "jordan@example.com"
            masked = email_on_file[:1] + "***@" + email_on_file.split("@")[-1]
            spoken = spoken_line("id_verification_email_otp", lang)
            return ok_reply(
                {
                    "requires_email_step_up": True,
                    "mfa_updated": False,
                    "masked_backup_email": masked,
                    "spoken_message": spoken,
                },
                reference,
                language=lang,
            )
        state["mfa_enabled"] = False
        return ok_reply(
            {
                "mfa_updated": True,
                "mfa_enabled": False,
                "spoken_message": localized_text(
                    lang,
                    "Two-factor authentication has been disabled using backup email verification.",
                    "L'authentification à deux facteurs a été désactivée avec la vérification par courriel de secours.",
                    "La autenticación de dos factores se ha desactivado mediante verificación por correo secundario.",
                ),
            },
            reference,
            language=lang,
        )

    if act == "enable":
        state["mfa_enabled"] = True
        return ok_reply(
            {
                "mfa_updated": True,
                "mfa_enabled": True,
                "preferred_mfa_channel": preferred_mfa_channel or "sms",
            },
            reference,
            language=lang,
        )

    if lang == "fr-CA":
        state["mfa_enabled"] = False
        return ok_reply(
            {
                "mfa_updated": True,
                "mfa_enabled": False,
                "spoken_message": "L'authentification à deux facteurs a été désactivée pour votre compte.",
            },
            reference,
            language=lang,
        )

    if state.get("login_code_sent") or state.get("mfa_email_verified"):
        state["mfa_enabled"] = False
        return ok_reply(
            {
                "mfa_updated": True,
                "mfa_enabled": False,
                "spoken_message": "Two-factor authentication has been disabled for your account.",
            },
            reference,
            language=lang,
        )

    state["login_code_sent"] = True
    state["login_channel"] = "sms"
    return ok_reply(
        {
            "requires_sms_step_up": True,
            "mfa_updated": False,
            "spoken_message": spoken_line("id_verification_otp", lang),
        },
        reference,
        language=lang,
    )


# ============================================================================
# Tool 20: execute_suspend_restore
# ============================================================================

def execute_suspend_restore_impl(
    action: str = "suspend",
    reason: str = "vacation",
    target_date: str = "immediate",
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute voluntary service suspension or line restoration."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _maybe_inline_auth(identifier, verification_code, lang, state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("execute_suspend_restore", account_id, str(action))
    state["last_tracking_id"] = reference

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    _record_audit(state)

    act = str(action or "suspend").lower()
    if act == "restore":
        if (
            state.get("suspension_reason") == "non_payment"
            and Decimal(str(state.get("past_due_balance") or 0)) > 0
            and not state.get("payment_arrangement_active")
        ):
            return error_reply(
                "PAST_DUE_BALANCE_REQUIRED",
                reference=reference,
                language=lang,
                data={"past_due_balance": state.get("past_due_balance", "85.50")},
            )
        state["is_suspended"] = False
        state["suspension_reason"] = ""
        state["service_restored"] = True
        return ok_reply(
            {
                "service_restored": True,
                "is_suspended": False,
                "restoration_eta_minutes": 15,
                "confirmation_number": reference,
            },
            reference,
            language=lang,
        )

    state["is_suspended"] = True
    state["suspension_reason"] = reason or "vacation"
    return ok_reply(
        {
            "service_suspended": True,
            "is_suspended": True,
            "reason": reason or "vacation",
            "reduced_rate_monthly": "15.00" if "vacation" in str(reason).lower() else "0.00",
            "confirmation_number": reference,
        },
        reference,
        language=lang,
    )


# ============================================================================
# Tool 21: update_contact_profile
# ============================================================================

def update_contact_profile_impl(
    email: str = "",
    service_address: str = "",
    postal_code: str = "",
    preferred_language_update: str = "",
    notification_preference: str = "",
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Update contact email, billing address, or preferred language."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _maybe_inline_auth(identifier, verification_code, lang, state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("update_contact_profile", account_id)
    state["last_tracking_id"] = reference

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    if not any((email, service_address, postal_code, preferred_language_update, notification_preference)):
        return error_reply("MISSING_INPUT", reference=reference, language=lang)

    _record_audit(state)

    upd: dict[str, Any] = {}
    if email:
        state["contact_email"] = str(email).strip()
        upd["email"] = state["contact_email"]
    if service_address:
        state["service_address"] = str(service_address).strip()
        upd["service_address"] = state["service_address"]
    if postal_code:
        state["postal_code"] = str(postal_code).strip().upper()
        upd["postal_code"] = state["postal_code"]
    if preferred_language_update:
        state["preferred_language"] = resolve_copy_locale(preferred_language_update)
        upd["preferred_language"] = state["preferred_language"]

    return ok_reply(
        {
            "profile_updated": True,
            "updated_fields": upd,
            "effective_immediately": True,
            "confirmation_number": reference,
            "continuity_note": "Your current plan pricing remains unchanged at the updated address.",
        },
        reference,
        language=lang,
    )


# ============================================================================
# Tool 22: cancel_or_port_out_service
# ============================================================================

def cancel_or_port_out_service_impl(
    service_line: str = "mobile",
    action_type: str = "cancel",
    reason: str = "",
    confirmed: str | int | float | bool = False,
    decline_retention_offer: str | int | float | bool = False,
    effective_date: str = "end_of_cycle",
    identifier: str | int | float = "",
    verification_code: str | int | float = "",
    language: str = "",
    state: dict[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute line cancellation with mandatory 2-step fee disclosure gate."""
    state = _get_state(state, session_state)
    _ensure_default_profile(state)
    lang = resolve_copy_locale(language or state.get("language") or state.get("preferred_language"))
    if language and str(language).strip():
        state["language"] = lang
        state["preferred_language"] = lang

    mock_err = _check_mock_error(state, lang)
    if mock_err:
        return mock_err

    _maybe_inline_auth(identifier, verification_code, lang, state)

    account_id = str(state.get("account_id") or "")
    reference = tracking_id("cancel_or_port_out_service", account_id, str(action_type))
    state["last_tracking_id"] = reference

    if state.get("auth_status") != "pass":
        return error_reply("NOT_AUTHENTICATED", reference=reference, language=lang)

    _record_audit(state)

    is_conf = (
        bool(confirmed)
        and str(confirmed).lower() in {"true", "1", "yes", "oui"}
    )
    disclosure_given = bool(state.get("cancellation_fee_disclosed"))

    if not disclosure_given or not is_conf:
        state["cancellation_fee_disclosed"] = True
        disc_line = spoken_line("contract_cancellation_fee_disclosure", lang)
        return ok_reply(
            {
                "requires_confirmation": True,
                "service_cancelled": False,
                "early_cancellation_fee": "0.00",
                "prorated_final_bill_estimate": "28.50",
                "optional_retention_offer": "$15/mo loyalty credit",
                "verbatim_disclosure": disc_line,
                "spoken_message": disc_line,
                "remaining_service_rates": "Home Internet 500 remains active at $55.00/mo",
            },
            reference,
            language=lang,
        )

    state["service_cancelled"] = True
    cxl_id = tracking_id("CXL", account_id)
    state["last_tracking_id"] = cxl_id

    res: dict[str, Any] = {
        "service_cancelled": True,
        "cancellation_confirmation_id": cxl_id,
        "effective_date": effective_date or "end_of_cycle",
        "final_statement_days": 5,
        "equipment_return_instructions": "Return rented modem/TV receiver within 30 days via prepaid Canada Post label.",
        "remaining_service_rates": "Home Internet 500 remains active at $55.00/mo",
    }
    if str(action_type).lower() == "port_out":
        res["port_out_pin"] = "849201"

    return ok_reply(res, cxl_id, language=lang)


# Aliases for 22 domain tools
lookup_account = lookup_account_impl
send_login_code = send_login_code_impl
verify_login = verify_login_impl
handover_to_person = handover_to_person_impl
get_billing_summary = get_billing_summary_impl
process_bill_payment = process_bill_payment_impl
setup_payment_arrangement = setup_payment_arrangement_impl
setup_autopay = setup_autopay_impl
process_refund_or_dispute = process_refund_or_dispute_impl
check_regional_outage = check_regional_outage_impl
run_troubleshooting_and_sms = run_troubleshooting_and_sms_impl
get_appointment_and_ticket_status = get_appointment_and_ticket_status_impl
manage_appointment = manage_appointment_impl
browse_plans_and_coverage = browse_plans_and_coverage_impl
commit_plan_or_order = commit_plan_or_order_impl
initiate_number_transfer = initiate_number_transfer_impl
manage_warranty_claim = manage_warranty_claim_impl
send_password_reset_sms = send_password_reset_sms_impl
manage_mfa_settings = manage_mfa_settings_impl
execute_suspend_restore = execute_suspend_restore_impl
update_contact_profile = update_contact_profile_impl
cancel_or_port_out_service = cancel_or_port_out_service_impl

# Backward compatibility aliases for starter test suites
check_login_code_impl = verify_login_impl
check_login_code = verify_login_impl
check_secret_pin_impl = verify_login_impl
check_secret_pin = verify_login_impl
submit_request_impl = _submit_request_fallback
submit_request = _submit_request_fallback
