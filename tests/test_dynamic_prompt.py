"""Tests for lib/dynamic_prompt.py covering language detection and dynamic prompt filter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
import pytest

from lib.dynamic_prompt import (
    LANGUAGE_SHEET_SENTINEL,
    SHARED_COGNATES,
    apply_language_prompt_filter,
    build_language_sheet,
    detect_active_call_language,
    detect_utterance_language,
    extract_user_utterances,
)


def test_shared_cognates_set() -> None:
    assert "internet" in SHARED_COGNATES
    assert "wifi" in SHARED_COGNATES
    assert "router" in SHARED_COGNATES
    assert len(SHARED_COGNATES) > 20


def test_detect_utterance_language_empty_and_digits_inertia() -> None:
    assert detect_utterance_language("", "en-US") == "en-US"
    assert detect_utterance_language("[pause]", "fr-CA") == "fr-CA"
    assert detect_utterance_language("[silence] 123456 [pause]", "es-US") == "es-US"
    assert detect_utterance_language("123-456-7890", "fr-CA") == "fr-CA"
    assert detect_utterance_language("... --- ...", "en-US") == "en-US"


def test_detect_utterance_language_explicit_switches() -> None:
    # French
    assert detect_utterance_language("je voudrais parler en français", "en-US") == "fr-CA"
    assert detect_utterance_language("switch to french please", "en-US") == "fr-CA"
    assert detect_utterance_language("passer au français svp", "en-US") == "fr-CA"
    assert detect_utterance_language("in french", "en-US") == "fr-CA"

    # English
    assert detect_utterance_language("in english please", "fr-CA") == "en-US"
    assert detect_utterance_language("switch to english", "es-US") == "en-US"
    assert detect_utterance_language("parler en anglais", "fr-CA") == "en-US"
    assert detect_utterance_language("passer à l'anglais", "fr-CA") == "en-US"

    # Spanish
    assert detect_utterance_language("en español por favor", "en-US") == "es-US"
    assert detect_utterance_language("hablar en español", "en-US") == "es-US"
    assert detect_utterance_language("switch to spanish", "en-US") == "es-US"
    assert detect_utterance_language("en espanol", "en-US") == "es-US"

    # Other world languages
    assert detect_utterance_language("em português por favor", "en-US") == "pt-BR"
    assert detect_utterance_language("switch to portuguese", "en-US") == "pt-BR"
    assert detect_utterance_language("auf deutsch bitte", "en-US") == "de-DE"
    assert detect_utterance_language("switch to german", "en-US") == "de-DE"
    assert detect_utterance_language("in italiano per favore", "en-US") == "it-IT"
    assert detect_utterance_language("switch to italian", "en-US") == "it-IT"
    assert detect_utterance_language("in mandarin please", "en-US") == "zh-CN"
    assert detect_utterance_language("switch to mandarin", "en-US") == "zh-CN"
    assert detect_utterance_language("in hindi please", "en-US") == "hi-IN"
    assert detect_utterance_language("switch to hindi", "en-US") == "hi-IN"
    assert detect_utterance_language("in arabic please", "en-US") == "ar-XA"
    assert detect_utterance_language("switch to arabic", "en-US") == "ar-XA"
    assert detect_utterance_language("in japanese please", "en-US") == "ja-JP"
    assert detect_utterance_language("switch to japanese", "en-US") == "ja-JP"
    assert detect_utterance_language("in korean please", "en-US") == "ko-KR"
    assert detect_utterance_language("switch to korean", "en-US") == "ko-KR"


def test_detect_utterance_language_scripts() -> None:
    # Arabic script
    assert detect_utterance_language("مرحبا كيف حالك", "en-US") == "ar-XA"
    # Devanagari script (Hindi)
    assert detect_utterance_language("नमस्ते आप कैसे हैं", "en-US") == "hi-IN"
    # Japanese kana
    assert detect_utterance_language("こんにちは", "en-US") == "ja-JP"
    # Korean hangul
    assert detect_utterance_language("안녕하세요", "en-US") == "ko-KR"
    # Chinese CJK
    assert detect_utterance_language("你好我想查账单", "en-US") == "zh-CN"


def test_detect_utterance_language_isolated_courtesy_words_keep_inertia() -> None:
    assert detect_utterance_language("merci", "en-US") == "en-US"
    assert detect_utterance_language("gracias", "en-US") == "en-US"


def test_detect_utterance_language_markers_and_scoring() -> None:
    # French markers and accents
    assert detect_utterance_language("Bonjour j'aimerais voir ma facture", "en-US") == "fr-CA"
    assert detect_utterance_language("J'ai une panne de réseau", "en-US") == "fr-CA"

    # Spanish markers and punctuation
    assert detect_utterance_language("Hola necesito ayuda con mi cuenta", "en-US") == "es-US"
    assert detect_utterance_language("¿Cuánto debo en mi tarjeta?", "en-US") == "es-US"

    # English markers (at least 3 markers with no fr/es score)
    assert detect_utterance_language("Hello I want help with my account", "fr-CA") == "en-US"
    assert detect_utterance_language("Need to reset password please", "es-US") == "en-US"

    # Ambiguous or cognates fall back to current language
    assert detect_utterance_language("router modem wifi", "fr-CA") == "fr-CA"


def test_extract_user_utterances() -> None:
    # None and empty
    assert extract_user_utterances(None) == []
    assert extract_user_utterances(SimpleNamespace(contents=None)) == []
    assert extract_user_utterances(SimpleNamespace(contents=[])) == []

    # Non-user roles ignored
    req1 = SimpleNamespace(
        contents=[
            SimpleNamespace(role="model", parts=[SimpleNamespace(text="Hello")]),
            SimpleNamespace(role="system", parts=[SimpleNamespace(text="System instructions")]),
        ]
    )
    assert extract_user_utterances(req1) == []

    # User role with parts list
    req2 = SimpleNamespace(
        contents=[
            SimpleNamespace(
                role="user",
                parts=[
                    SimpleNamespace(text="My bill is high"),
                    SimpleNamespace(text="  "),
                    SimpleNamespace(text=None),
                ],
            ),
            SimpleNamespace(
                role="user",
                parts=[SimpleNamespace(text="Can you check it?")],
            ),
        ]
    )
    assert extract_user_utterances(req2) == ["My bill is high", "Can you check it?"]

    # User role with direct text attribute
    req3 = SimpleNamespace(
        contents=[
            SimpleNamespace(role="user", text="I need tech support"),
            SimpleNamespace(role="user", text="   "),
        ]
    )
    assert extract_user_utterances(req3) == ["I need tech support"]


def test_detect_active_call_language() -> None:
    req_fr = SimpleNamespace(
        contents=[
            SimpleNamespace(
                role="user",
                parts=[SimpleNamespace(text="Bonjour j'aimerais de l'aide pour ma facture")],
            )
        ]
    )
    # No locked language -> detects fr-CA
    assert detect_active_call_language({}, req_fr) == "fr-CA"

    # Locked language fr-CA
    assert detect_active_call_language({"language": "fr-CA"}, SimpleNamespace(contents=[])) == "fr-CA"

    # Locked en-US switches if caller speaks French
    assert detect_active_call_language({"language": "en-US"}, req_fr) == "fr-CA"

    # Locked en-US remains en-US if user utterance is English
    req_en = SimpleNamespace(
        contents=[
            SimpleNamespace(
                role="user",
                parts=[SimpleNamespace(text="Hello I want help with my account bill")],
            )
        ]
    )
    assert detect_active_call_language({"language": "en-US"}, req_en) == "en-US"


def test_build_language_sheet_supported_locales() -> None:
    for loc in ("en-US", "fr-CA", "es-US"):
        sheet = build_language_sheet(loc, agent_name="router")
        assert LANGUAGE_SHEET_SENTINEL in sheet
        assert f'<active_language_sheet locale="{loc}"' in sheet
        assert "### Required Disclosures & Spoken Lines" in sheet
        assert "### Mandatory Conversational Rules:" in sheet
        assert "</active_language_sheet>" in sheet


def test_build_language_sheet_world_languages() -> None:
    sheet_de = build_language_sheet("de-DE", agent_name="billing")
    assert LANGUAGE_SHEET_SENTINEL in sheet_de
    assert 'locale="de-DE"' in sheet_de
    assert "German" in sheet_de
    assert "### Canonical Templates:" in sheet_de
    assert "secondary_language_live_agent" in sheet_de
    assert "</active_language_sheet>" in sheet_de


def test_build_language_sheet_agents() -> None:
    for agent in ("router", "billing", "tech_support", "sales_equipment", "account"):
        sheet = build_language_sheet("fr-CA", agent_name=agent)
        assert LANGUAGE_SHEET_SENTINEL in sheet


def test_apply_language_prompt_filter_zero_writes_to_state() -> None:
    state_original = {"account_id": "A1001", "phone_last4": "0143", "auth_status": "pass"}
    state_copy = dict(state_original)
    context = SimpleNamespace(state=state_copy)

    req = SimpleNamespace(
        config=SimpleNamespace(system_instruction="Base agent instructions."),
        contents=[
            SimpleNamespace(
                role="user",
                parts=[SimpleNamespace(text="Bonjour j'ai une question sur ma facture")],
            )
        ],
    )

    result = apply_language_prompt_filter(context, req, agent_name="billing")
    assert result is None
    # Crucial assertion: ZERO writes to state!
    assert state_copy == state_original
    assert req.config.system_instruction.startswith("Base agent instructions.\n\n")
    assert LANGUAGE_SHEET_SENTINEL in req.config.system_instruction
    assert 'locale="fr-CA"' in req.config.system_instruction


def test_apply_language_prompt_filter_idempotence() -> None:
    context = SimpleNamespace(state={"language": "es-US"})
    req = SimpleNamespace(
        config=SimpleNamespace(system_instruction="Instructions here"),
        contents=[],
    )

    # First call
    apply_language_prompt_filter(context, req, agent_name="router")
    inst1 = req.config.system_instruction
    assert inst1.count(LANGUAGE_SHEET_SENTINEL) == 1

    # Second call - should not duplicate the sentinel or sheet!
    apply_language_prompt_filter(context, req, agent_name="router")
    inst2 = req.config.system_instruction
    assert inst2.count(LANGUAGE_SHEET_SENTINEL) == 1
    assert inst1 == inst2


def test_apply_language_prompt_filter_instruction_variants() -> None:
    context = SimpleNamespace(state={})

    # Case 1: config is None
    req_no_config = SimpleNamespace(config=None, contents=[])
    assert apply_language_prompt_filter(context, req_no_config) is None

    # Case 2: system_instruction is None
    req_no_sys = SimpleNamespace(config=SimpleNamespace(system_instruction=None), contents=[])
    assert apply_language_prompt_filter(context, req_no_sys) is None

    # Case 3: system_instruction has parts attribute with text
    part = SimpleNamespace(text="Instructions with parts")
    req_parts = SimpleNamespace(
        config=SimpleNamespace(system_instruction=SimpleNamespace(parts=[part])),
        contents=[],
    )
    apply_language_prompt_filter(context, req_parts)
    assert LANGUAGE_SHEET_SENTINEL in part.text

    # Case 4: system_instruction is list of strings
    sys_list_str = ["Instructions in list string"]
    req_list_str = SimpleNamespace(
        config=SimpleNamespace(system_instruction=sys_list_str),
        contents=[],
    )
    apply_language_prompt_filter(context, req_list_str)
    assert LANGUAGE_SHEET_SENTINEL in sys_list_str[0]

    # Case 5: system_instruction is list of objects with text attribute
    part_in_list = SimpleNamespace(text="Instructions in list object")
    sys_list_obj = [part_in_list]
    req_list_obj = SimpleNamespace(
        config=SimpleNamespace(system_instruction=sys_list_obj),
        contents=[],
    )
    apply_language_prompt_filter(context, req_list_obj)
    assert LANGUAGE_SHEET_SENTINEL in part_in_list.text


def test_multiturn_chronology_switches() -> None:
    # state has language en-US, turn 1 is French, turn 2 is English switch
    req_en = SimpleNamespace(
        contents=[
            SimpleNamespace(role="user", parts=[SimpleNamespace(text="Bonjour, j'ai besoin d'aide")]),
            SimpleNamespace(role="user", parts=[SimpleNamespace(text="Actually, switch to English please")]),
        ]
    )
    assert detect_active_call_language({"language": "en-US"}, req_en) == "en-US"

    # state has language en-US, turn 1 is French, turn 2 is Spanish switch
    req_es = SimpleNamespace(
        contents=[
            SimpleNamespace(role="user", parts=[SimpleNamespace(text="Bonjour, j'ai besoin d'aide")]),
            SimpleNamespace(role="user", parts=[SimpleNamespace(text="En español por favor")]),
        ]
    )
    assert detect_active_call_language({"language": "en-US"}, req_es) == "es-US"


def test_english_call_with_quebec_address_stays_english() -> None:
    req = SimpleNamespace(
        contents=[
            SimpleNamespace(role="user", parts=[SimpleNamespace(text="Hello, I need help with my internet plan")]),
            SimpleNamespace(role="user", parts=[SimpleNamespace(text="123 Rue Saint-Laurent, Montréal, Québec")]),
            SimpleNamespace(role="user", parts=[SimpleNamespace(text="Which plan is fastest?")]),
        ]
    )
    assert detect_active_call_language({"language": "en-US"}, req) == "en-US"


def test_native_turn1_german_portuguese_italian_classification() -> None:
    de_utt = "Guten Tag, sprechen Sie Deutsch? Ich brauche Hilfe mit meiner Rechnung."
    assert detect_utterance_language(de_utt, "en-US") == "de-DE"

    pt_utt = "Olá, preciso de ajuda com a minha fatura por favor."
    assert detect_utterance_language(pt_utt, "en-US") == "pt-BR"

    it_utt = "Buongiorno, parla italiano? Perché ho bisogno di aiuto."
    assert detect_utterance_language(it_utt, "en-US") == "it-IT"

