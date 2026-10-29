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


def test_short_numbers_dates_and_amounts_are_left_alone() -> None:
    text = "Reference R123456, due 2026-10-08 14:30, amount $1,234.56, code 123456."
    assert mask_long_numbers(text) == text


def test_speakable_numbers_are_kept(monkeypatch) -> None:
    monkeypatch.setattr(speech, "SPEAKABLE_NUMBERS", frozenset({"18005550100"}))
    assert mask_long_numbers("Call 1-800-555-0100.") == "Call 1-800-555-0100."


def test_strip_markdown() -> None:
    assert strip_markdown("**Done.** Use `code`.\n## Next") == "Done. Use code.\nNext"
    assert strip_markdown("Press # to finish") == "Press # to finish"


def test_clean_speech_and_caller_last4_preference() -> None:
    assert clean_speech("**Your number is 2025550143.**") == "Your number is 0143."
    params = {"phone_last4": "0143", "caller_provided_phone_last4": "0199"}
    assert (
        clean_agent_speech("Your number ending in 0143 is verified.", params)
        == "Your number ending in 0199 is verified."
    )
    msg = "I'm transferring you to a member of our team now. Thank you for your patience."
    handover_state = {"handover_complete": True, "handoff_message": msg}
    assert enforce_handover_utterance("", handover_state) == msg
    assert enforce_handover_utterance("Hold on.", handover_state) == "Hold on."
    step_line = "I'm transferring you to a billing specialist now."
    assert enforce_handover_utterance(step_line, handover_state) == step_line
    assert enforce_handover_utterance("", {"handover_complete": False, "handoff_message": msg}) == ""
