"""Tests for lib/speech.py covering speech cleaning, number masking, and handover lines."""

from __future__ import annotations

import lib.speech as speech
from lib.speech import (
    clean_agent_speech,
    clean_speech,
    enforce_handover_utterance,
    mask_long_numbers,
    strip_markdown,
)


def test_long_numbers_keep_only_their_last_4_digits() -> None:
    assert mask_long_numbers("Call 2025550143 now") == "Call 0143 now"
    assert mask_long_numbers("It is (202) 555-0143.") == "It is 0143."
    assert mask_long_numbers("Card 4111 1111 1111 1234 is on file") == "Card 1234 is on file"
    assert mask_long_numbers("10-digit account 1234567890") == "10-digit account 7890"


def test_short_numbers_dates_and_amounts_are_left_alone() -> None:
    text = "Reference R123456, due 2026-10-08 14:30, amount $1,234.56, code 123456."
    assert mask_long_numbers(text) == text
    assert mask_long_numbers("PIN is 1234") == "PIN is 1234"
    assert mask_long_numbers("Port 8080") == "Port 8080"


def test_speakable_numbers_are_kept(monkeypatch) -> None:
    monkeypatch.setattr(speech, "SPEAKABLE_NUMBERS", frozenset({"18005550100"}))
    assert mask_long_numbers("Call 1-800-555-0100.") == "Call 1-800-555-0100."


def test_strip_markdown() -> None:
    assert strip_markdown("**Done.** Use `code`.\n## Next") == "Done. Use code.\nNext"
    assert strip_markdown("Press # to finish") == "Press # to finish"
    assert strip_markdown("# Header 1\n## Header 2\n### Header 3\nText") == "Header 1\nHeader 2\nHeader 3\nText"
    assert strip_markdown("Here is `monospace` and *italics* and ***bold-italics***") == "Here is monospace and italics and bold-italics"


def test_clean_speech() -> None:
    assert clean_speech("**Your number is 2025550143.**") == "Your number is 0143."
    assert clean_speech("`Account 9876543210`") == "Account 3210"


def test_clean_agent_speech_without_dict_params() -> None:
    assert clean_agent_speech("Hello 2025550143", None) == "Hello 0143"
    assert clean_agent_speech("Hello 2025550143", "not a dict") == "Hello 0143"  # type: ignore[arg-type]


def test_clean_agent_speech_caller_last4_and_profile_last4() -> None:
    # When caller gave 0199 but profile says 0143
    params = {"phone_last4": "0143", "caller_provided_phone_last4": "0199"}
    assert (
        clean_agent_speech("Your number ending in 0143 is verified.", params)
        == "Your number ending in 0199 is verified."
    )
    # Profile last4 matches caller last4
    params_same = {"phone_last4": "0143", "caller_provided_phone_last4": "0143"}
    assert (
        clean_agent_speech("Your number ending in 0143 is verified.", params_same)
        == "Your number ending in 0143 is verified."
    )


def test_clean_agent_speech_card_and_bank_last4_en() -> None:
    params = {
        "caller_provided_phone_last4": "0199",
        "phone_last4": "0143",
        "card_last4": "4242",
        "bank_last4": "6789",
    }
    # Credit card context in English
    text_card = "Your Visa credit card ending in 0000 has been charged."
    assert (
        clean_agent_speech(text_card, params)
        == "Your Visa credit card ending in 4242 has been charged."
    )
    # Bank context in English
    text_bank = "Your checking account ending in 0000 has been debited."
    assert (
        clean_agent_speech(text_bank, params)
        == "Your checking account ending in 6789 has been debited."
    )
    # Phone context in English
    text_phone = "Your phone number is 1111."
    assert clean_agent_speech(text_phone, params) == "Your phone number is 0199."


def test_clean_agent_speech_card_and_bank_last4_fr() -> None:
    params = {
        "caller_provided_phone_last4": "0199",
        "phone_last4": "0143",
        "card_last4": "4242",
        "bank_last4": "6789",
    }
    # French carte de crédit context
    text_fr_card = "Votre carte de crédit se terminant par 0000 a été débitée."
    assert (
        clean_agent_speech(text_fr_card, params)
        == "Votre carte de crédit se terminant par 4242 a été débitée."
    )
    # French compte bancaire / chèques context
    text_fr_bank = "Votre compte bancaire chèque se terminant par 0000 est valide."
    assert (
        clean_agent_speech(text_fr_bank, params)
        == "Votre compte bancaire chèque se terminant par 6789 est valide."
    )
    # French phone context
    text_fr_phone = "Votre numéro est 0000."
    assert clean_agent_speech(text_fr_phone, params) == "Votre numéro est 0199."


def test_clean_agent_speech_card_and_bank_last4_es() -> None:
    params = {
        "caller_provided_phone_last4": "0199",
        "phone_last4": "0143",
        "card_last4": "4242",
        "bank_last4": "6789",
    }
    # Spanish tarjeta de débito context
    text_es_card = "Su tarjeta de débito que termina en 0000 ha sido confirmada."
    assert (
        clean_agent_speech(text_es_card, params)
        == "Su tarjeta de débito que termina en 4242 ha sido confirmada."
    )
    # Spanish cuenta bancaria context
    text_es_bank = "Su cuenta bancaria que termina en 0000 está registrada."
    assert (
        clean_agent_speech(text_es_bank, params)
        == "Su cuenta bancaria que termina en 6789 está registrada."
    )
    # Spanish phone context
    text_es_phone = "Su número es 0000."
    assert clean_agent_speech(text_es_phone, params) == "Su número es 0199."


def test_clean_agent_speech_already_matching_last4_kept() -> None:
    params = {
        "caller_provided_phone_last4": "0199",
        "card_last4": "4242",
        "bank_last4": "6789",
    }
    # Card already matches
    assert "4242" in clean_agent_speech("ending in 4242", params)
    # Bank already matches
    assert "6789" in clean_agent_speech("ending in 6789", params)


def test_enforce_handover_utterance_existing_text() -> None:
    # When text is already non-empty, it is returned intact
    assert enforce_handover_utterance("Please wait a moment.") == "Please wait a moment."
    assert enforce_handover_utterance("Hold on.", {"handover_complete": True}) == "Hold on."


def test_enforce_handover_utterance_from_state_handoff_message() -> None:
    msg_en = "I'm transferring you to a member of our team now. Thank you for your patience."
    state = {"handover_complete": True, "handoff_message": msg_en}
    assert enforce_handover_utterance("", state) == msg_en
    assert enforce_handover_utterance("   ", state) == msg_en

    # Incomplete handover in state
    assert enforce_handover_utterance("", {"handover_complete": False, "handoff_message": msg_en}) == ""


def test_enforce_handover_utterance_called_tools_business() -> None:
    # Business transfer in EN, FR, ES
    for lang, phrase in (
        ("en-US", "business account"),
        ("fr-CA", "compte affaires"),
        ("es-US", "cuenta comercial"),
    ):
        line = enforce_handover_utterance(
            "",
            called_tools=("handover_to_person",),
            tool_args_list=({"reason": "business_handoff", "language": lang},),
        )
        assert phrase in line


def test_enforce_handover_utterance_called_tools_fraud() -> None:
    # Fraud transfer has empathy protocol + live agent handoff
    line_en = enforce_handover_utterance(
        "",
        called_tools=("handover_to_person",),
        tool_args_list=({"reason": "suspected_fraud_lockout", "language": "en-US"},),
    )
    assert "facing challenges" in line_en
    assert "representative who can help" in line_en

    line_fr = enforce_handover_utterance(
        "",
        called_tools=("execute_live_agent_handover",),
        tool_args_list=({"reason": "fraud", "language": "fr-CA"},),
    )
    assert "difficultés" in line_fr
    assert "représentant" in line_fr


def test_enforce_handover_utterance_called_tools_specialist_and_refund() -> None:
    # Refund threshold / billing specialist
    line_refund = enforce_handover_utterance(
        "",
        called_tools=("handover_to_person",),
        tool_args_list=({"reason": "refund_threshold_exceeded", "language": "en-US"},),
    )
    assert "billing specialist" in line_refund

    line_queue = enforce_handover_utterance(
        "",
        called_tools=("handover_to_person",),
        tool_args_list=({"target_queue": "billing_specialist", "language": "fr-CA"},),
    )
    assert "spécialiste de la facturation" in line_queue

    line_specialist = enforce_handover_utterance(
        "",
        called_tools=("handover_to_person",),
        tool_args_list=({"reason": "specialist_required", "language": "es-US"},),
    )
    assert "especialista de facturación" in line_specialist


def test_enforce_handover_utterance_called_tools_default_live_agent() -> None:
    line_default = enforce_handover_utterance(
        "",
        called_tools=("handover_to_person",),
        tool_args_list=({"reason": "general_inquiry", "language": "en-US"},),
    )
    assert "representative who can help" in line_default

    line_no_tools = enforce_handover_utterance(
        "",
        called_tools=("lookup_account",),
        tool_args_list=({"identifier": "2025550143"},),
    )
    assert line_no_tools == ""
