"""Speech hygiene for spoken replies: markdown stripping and number masking."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any

if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.copy import SPOKEN_LINES, resolve_copy_locale, spoken_line

SPEAKABLE_NUMBERS: frozenset[str] = frozenset()

NUMBER_RUN_RE = re.compile(r"\(?\d+\)?(?:[-.]\(?\d+\)?|\s\(?\d{3,}\)?)*")
MARKDOWN_RE = re.compile(r"\*+|`+|^#+[ \t]*", re.MULTILINE)
_LAST4_CONTEXT_RE = re.compile(
    r"((?:ending\s+in|terminant\s+par|termina\s+en|number\s+is|num[eé]ro\s+est|n[uú]mero\s+es)\s+)(\d{4})\b",
    re.IGNORECASE,
)


def mask_long_numbers(text: str, min_digits: int = 9) -> str:
    """Replace every number of min_digits or more digits by its last 4 digits."""

    def _mask(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) < min_digits or digits in SPEAKABLE_NUMBERS:
            return match.group(0)
        return digits[-4:]

    return NUMBER_RUN_RE.sub(_mask, text)


def strip_markdown(text: str) -> str:
    """Drop markdown formatting characters from spoken text."""
    return MARKDOWN_RE.sub("", text)


def clean_speech(text: str) -> str:
    """Clean markdown formatting and long numbers from spoken text."""
    return mask_long_numbers(strip_markdown(text))


def clean_agent_speech(
    text: str,
    session_params: dict[str, Any] | None = None,
) -> str:
    """Clean speech and preserve caller phone, card, and bank last-4 numbers."""
    cleaned = clean_speech(text)
    if not isinstance(session_params, dict):
        return cleaned
    caller_last4 = str(session_params.get("caller_provided_phone_last4") or "").strip()
    profile_last4 = str(session_params.get("phone_last4") or "").strip()
    card_last4 = str(session_params.get("card_last4") or "").strip()
    bank_last4 = str(session_params.get("bank_last4") or "").strip()

    if len(caller_last4) == 4 and caller_last4.isdigit():
        if (
            len(profile_last4) == 4
            and profile_last4 != caller_last4
            and profile_last4 != card_last4
            and profile_last4 != bank_last4
            and profile_last4 in cleaned
        ):
            cleaned = re.sub(rf"\b{re.escape(profile_last4)}\b", caller_last4, cleaned)

        def _replace_non_card_last4(m: re.Match[str]) -> str:
            prefix = cleaned[max(0, m.start() - 35) : m.start()].lower()
            if any(
                w in prefix
                for w in (
                    "card",
                    "carte",
                    "tarjeta",
                    "visa",
                    "mastercard",
                    "amex",
                    "crédit",
                    "credit",
                    "débit",
                    "debit",
                )
            ):
                return (
                    f"{m.group(1)}{card_last4}"
                    if (len(card_last4) == 4 and card_last4.isdigit())
                    else m.group(0)
                )
            if any(
                w in prefix
                for w in (
                    "bank",
                    "bancaire",
                    "checking",
                    "chequing",
                    "chèques",
                    "chèque",
                    "savings",
                    "épargne",
                    "routing",
                    "transit",
                    "compte",
                    "account",
                    "cuenta",
                )
            ):
                return (
                    f"{m.group(1)}{bank_last4}"
                    if (len(bank_last4) == 4 and bank_last4.isdigit())
                    else m.group(0)
                )
            if len(card_last4) == 4 and m.group(2) == card_last4:
                return m.group(0)
            if len(bank_last4) == 4 and m.group(2) == bank_last4:
                return m.group(0)
            return f"{m.group(1)}{caller_last4}"

        cleaned = _LAST4_CONTEXT_RE.sub(_replace_non_card_last4, cleaned)
    return cleaned


def enforce_handover_utterance(
    text: str,
    session_params: dict[str, Any] | None = None,
    called_tools: tuple[str, ...] = (),
    tool_args_list: tuple[dict[str, Any], ...] = (),
) -> str:
    """Ensure a handover turn produces a valid localized transfer line."""
    if (text or "").strip():
        return text
    params = session_params if isinstance(session_params, dict) else {}
    if params.get("handover_complete") and params.get("handoff_message"):
        handoff_msg = str(params["handoff_message"]).strip()
        if handoff_msg:
            return handoff_msg

    if any(name in ("handover_to_person", "execute_live_agent_handover") for name in called_tools):
        reason = ""
        target_queue = ""
        lang = params.get("language")
        for args in tool_args_list:
            if isinstance(args, dict):
                if args.get("reason"):
                    reason = str(args["reason"]).lower()
                if args.get("target_queue"):
                    target_queue = str(args["target_queue"]).lower()
                if args.get("language"):
                    lang = args["language"]
        loc = resolve_copy_locale(lang)
        if "business" in reason:
            return spoken_line("business_handoff", loc)
        if "fraud" in reason:
            return f"{spoken_line('empathy_protocol', loc)} {spoken_line('live_agent_handoff', loc)}"
        if (
            "refund_threshold" in reason
            or "specialist" in reason
            or target_queue == "billing_specialist"
        ):
            return spoken_line("transfer_to_specialist", loc)
        return spoken_line("live_agent_handoff", loc)

    return text
