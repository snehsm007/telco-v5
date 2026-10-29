"""Dynamic multilingual prompt injection via read-only before_model_callback."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any

if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.copy import (
    AGENT_VERBATIM_KEYS,
    SPOKEN_LINES,
    WORLD_LANGUAGE_NAMES,
    resolve_copy_locale,
    resolve_locale,
    spoken_line,
)

LANGUAGE_SHEET_SENTINEL = "<!-- ACTIVE_LANGUAGE_SHEET -->"

SHARED_COGNATES: frozenset[str] = frozenset(
    {
        "internet",
        "mobile",
        "mobility",
        "sim",
        "tv",
        "wifi",
        "wi-fi",
        "fibe",
        "bell",
        "telco",
        "pin",
        "otp",
        "mfa",
        "sms",
        "ok",
        "okay",
        "agent",
        "service",
        "support",
        "plan",
        "menu",
        "code",
        "cable",
        "modem",
        "router",
        "app",
        "streaming",
        "satellite",
    }
)

_FRENCH_MARKERS = frozenset(
    {
        "bonjour",
        "bonsoir",
        "salut",
        "oui",
        "merci",
        "svp",
        "je",
        "j'ai",
        "j'aimerais",
        "mon",
        "ma",
        "mes",
        "votre",
        "notre",
        "pour",
        "avec",
        "dans",
        "sur",
        "facture",
        "forfait",
        "compte",
        "numéro",
        "annuler",
        "désactiver",
        "remboursement",
        "garantie",
        "clavier",
        "paiement",
        "panne",
        "réseau",
        "téléphone",
        "courriel",
        "veuillez",
        "pouvez",
        "voudrais",
        "veux",
    }
)

_SPANISH_MARKERS = frozenset(
    {
        "hola",
        "buenos",
        "buenas",
        "quiero",
        "necesito",
        "factura",
        "cuenta",
        "gracias",
        "por",
        "favor",
        "ayuda",
        "servicio",
        "tarjeta",
        "reembolso",
        "cancelar",
    }
)

_ENGLISH_MARKERS = frozenset(
    {
        "hello",
        "hi",
        "my",
        "want",
        "need",
        "bill",
        "account",
        "please",
        "help",
        "cancel",
        "reset",
        "password",
        "outage",
        "upgrade",
        "refund",
        "dispute",
        "payment",
        "phone",
        "the",
        "with",
        "have",
        "your",
        "this",
        "that",
        "would",
        "could",
        "check",
        "issue",
        "working",
        "down",
    }
)

_DP_GERMAN_MARKERS = frozenset(
    {
        "guten",
        "sprechen",
        "deutsch",
        "ich",
        "brauche",
        "hilfe",
        "meiner",
        "meine",
        "mein",
        "rechnung",
        "bitte",
        "danke",
        "konto",
        "vertrag",
        "störung",
        "kündigen",
    }
)

_DP_PORTUGUESE_MARKERS = frozenset(
    {
        "olá",
        "preciso",
        "ajuda",
        "minha",
        "meu",
        "fatura",
        "obrigado",
        "obrigada",
        "você",
        "atendente",
        "cartão",
        "ligação",
        "português",
    }
)

_DP_ITALIAN_MARKERS = frozenset(
    {
        "buongiorno",
        "buonasera",
        "parla",
        "italiano",
        "perché",
        "bisogno",
        "aiuto",
        "vorrei",
        "bolletta",
        "fattura",
        "grazie",
        "favore",
    }
)

_DP_QUEBEC_PLACE_TOKENS = frozenset(
    {
        "montréal",
        "montreal",
        "québec",
        "quebec",
        "laval",
        "longueuil",
        "gatineau",
        "sherbrooke",
        "lévis",
        "levis",
        "trois",
        "rivières",
        "rivieres",
        "saguenay",
        "terrebonne",
        "brossard",
        "repentigny",
        "saint",
        "sainte",
        "st",
        "ste",
        "laurent",
        "catherine",
        "denis",
        "hubert",
        "jean",
        "baptiste",
        "honoré",
        "honore",
        "rené",
        "rene",
        "lévesque",
        "levesque",
        "côte",
        "cote",
        "neiges",
        "île",
        "ile",
        "boulevard",
        "boul",
        "rue",
        "avenue",
        "ave",
        "chemin",
        "ch",
        "appartement",
        "apt",
        "suite",
        "qc",
    }
)


def detect_utterance_language(utterance: str, current_language: str = "en-US") -> str:
    """Detect language from an utterance with contextual inertia on silence and numbers."""
    cleaned = re.sub(r"\[(?:pause|silence)\]", " ", str(utterance or ""), flags=re.IGNORECASE)
    cleaned = re.sub(r"[0-9\W_]+", " ", cleaned).strip()
    if not cleaned:
        return resolve_locale(current_language)

    low = str(utterance or "").lower()

    if any(
        p in low
        for p in (
            "en français",
            "parler en français",
            "switch to french",
            "french please",
            "in french",
            "passer au français",
        )
    ):
        return "fr-CA"
    if any(
        p in low
        for p in (
            "in english",
            "switch to english",
            "parler en anglais",
            "english please",
            "passer à l'anglais",
        )
    ):
        return "en-US"
    if any(
        p in low
        for p in (
            "en español",
            "hablar en español",
            "switch to spanish",
            "spanish please",
            "en espanol",
        )
    ):
        return "es-US"
    if any(
        p in low
        for p in (
            "em português",
            "em portugues",
            "fala português",
            "fala portugues",
            "in portuguese",
            "do you speak portuguese",
            "switch to portuguese",
            "portuguese please",
        )
    ):
        return "pt-BR"
    if any(
        p in low
        for p in (
            "auf deutsch",
            "sprechen sie deutsch",
            "in german",
            "do you speak german",
            "switch to german",
            "german please",
        )
    ):
        return "de-DE"
    if any(
        p in low
        for p in (
            "in italiano",
            "parla italiano",
            "in italian",
            "do you speak italian",
            "switch to italian",
            "italian please",
        )
    ):
        return "it-IT"
    if any(
        p in low
        for p in (
            "in mandarin",
            "in chinese",
            "do you speak mandarin",
            "do you speak chinese",
            "mandarin please",
            "switch to mandarin",
        )
    ):
        return "zh-CN"
    if any(
        p in low
        for p in ("in hindi", "do you speak hindi", "hindi please", "switch to hindi")
    ):
        return "hi-IN"
    if any(
        p in low
        for p in ("in arabic", "do you speak arabic", "arabic please", "switch to arabic")
    ):
        return "ar-XA"
    if any(
        p in low
        for p in (
            "in japanese",
            "do you speak japanese",
            "japanese please",
            "switch to japanese",
        )
    ):
        return "ja-JP"
    if any(
        p in low
        for p in ("in korean", "do you speak korean", "korean please", "switch to korean")
    ):
        return "ko-KR"

    if re.search(r"[\u0600-\u06ff]", utterance):
        return "ar-XA"
    if re.search(r"[\u0900-\u097f]", utterance):
        return "hi-IN"
    if re.search(r"[\u3040-\u30ff]", utterance):
        return "ja-JP"
    if re.search(r"[\uac00-\ud7af]", utterance):
        return "ko-KR"
    if re.search(r"[\u4e00-\u9fff]", utterance):
        return "zh-CN"

    words = [w.lower() for w in cleaned.split()]

    if words == ["merci"] and resolve_locale(current_language) == "en-US":
        return "en-US"
    if words == ["gracias"] and resolve_locale(current_language) == "en-US":
        return "en-US"

    german_score = sum(1 for w in words if w in _DP_GERMAN_MARKERS) + (
        1 if re.search(r"[äöß]", low) else 0
    )
    portuguese_score = sum(1 for w in words if w in _DP_PORTUGUESE_MARKERS) + (
        1 if re.search(r"[ãõ]", low) else 0
    )
    italian_score = sum(1 for w in words if w in _DP_ITALIAN_MARKERS)

    if (
        german_score >= 2
        and german_score >= portuguese_score
        and german_score >= italian_score
    ):
        return "de-DE"
    if (
        portuguese_score >= 2
        and portuguese_score > german_score
        and portuguese_score >= italian_score
    ):
        return "pt-BR"
    if (
        italian_score >= 2
        and italian_score > german_score
        and italian_score > portuguese_score
    ):
        return "it-IT"

    non_place_text = " ".join(w for w in words if w not in _DP_QUEBEC_PLACE_TOKENS)
    has_french_accents = bool(re.search(r"[éèêëàâùûîïôçœ]", non_place_text))
    french_words = sum(1 for w in words if w in _FRENCH_MARKERS)
    french_score = french_words + (1 if has_french_accents else 0)

    has_spanish_punct = bool(re.search(r"[¿¡ñ]", low))
    spanish_words = sum(1 for w in words if w in _SPANISH_MARKERS)
    spanish_score = spanish_words + (1 if has_spanish_punct else 0)

    english_words = sum(1 for w in words if w in _ENGLISH_MARKERS)

    if french_score > 0 and french_score >= spanish_score and french_score >= english_words:
        return "fr-CA"
    if spanish_score > 0 and spanish_score > french_score and spanish_score >= english_words:
        return "es-US"
    if english_words >= 3 and french_score == 0 and spanish_score == 0:
        return "en-US"

    return resolve_locale(current_language)


def extract_user_utterances(llm_request: Any) -> list[str]:
    """Safely extract user utterance strings from LLM request contents."""
    utterances: list[str] = []
    contents = getattr(llm_request, "contents", None)
    if not contents or not isinstance(contents, (list, tuple)):
        return utterances
    for item in contents:
        if getattr(item, "role", "") == "user":
            parts = getattr(item, "parts", None)
            if parts and isinstance(parts, (list, tuple)):
                for part in parts:
                    txt = getattr(part, "text", None)
                    if txt and isinstance(txt, str) and txt.strip():
                        utterances.append(txt.strip())
            elif isinstance(getattr(item, "text", None), str):
                t = item.text.strip()
                if t:
                    utterances.append(t)
    return utterances


def detect_active_call_language(state_dict: Any, llm_request: Any) -> str:
    """Determine the active conversation language from state and user turns."""
    user_utterances = extract_user_utterances(llm_request)
    locked = (
        str(state_dict.get("language") or "").strip()
        if callable(getattr(state_dict, "get", None))
        else ""
    )

    current = resolve_locale(locked) if locked else "en-US"
    for utt in user_utterances:
        current = detect_utterance_language(utt, current_language=current)

    return current


def build_language_sheet(locale: str, agent_name: str = "router") -> str:
    """Generate dynamic language sheet containing localized rules and verbatim lines."""
    loc = resolve_locale(locale)
    lang_name = WORLD_LANGUAGE_NAMES.get(loc, loc)
    keys = AGENT_VERBATIM_KEYS.get(agent_name, AGENT_VERBATIM_KEYS["router"])

    lines = [
        LANGUAGE_SHEET_SENTINEL,
        f'<active_language_sheet locale="{loc}" language="{lang_name}">',
    ]

    if loc in ("en-US", "fr-CA", "es-US"):
        lines.append("### Required Disclosures & Spoken Lines (Emit Exact Wording):")
        for k in keys:
            line_text = spoken_line(k, loc)
            lines.append(f'- {k}: "{line_text}"')
        lines.append("")
        lines.append("### Mandatory Conversational Rules:")
        lines.append(
            f"1. Speak 100% in {lang_name} ({loc}). Never mix languages or repeat lines in another language."
        )
        lines.append(
            f'2. Always pass language="{loc}" when calling tools (and write any free-text reason/summary in {lang_name} while keeping structural enum values unchanged).'
        )
        lines.append(
            "3. Emit the verbatim lines above word-for-word whenever their trigger fires, filling [amount] and [days] from tool output only."
        )
    else:
        lines.append("### Canonical Templates:")
        for k in keys:
            line_text = spoken_line(k, "en-US")
            lines.append(f'- {k}: "{line_text}"')
        lines.append("")
        lines.append("### Mandatory Conversational Rules:")
        lines.append(
            f"1. Speak 100% natively and fluently in {lang_name} ({loc}), translating the canonical Telco disclosures faithfully into {lang_name} with zero English mixing."
        )
        lines.append(
            f'2. Pass language="{loc}" to tools; if a request cannot be completed accurately without language degradation, politely offer to connect a specialist via handover_to_person(reason="secondary_language_live_agent", language="{loc}").'
        )

    lines.append("</active_language_sheet>")
    return "\n".join(lines)


def apply_language_prompt_filter(
    callback_context: Any,
    llm_request: Any,
    agent_name: str = "router",
) -> None:
    """Inject language rules and verbatim lines into system instruction in-place."""
    state = getattr(callback_context, "state", None)
    state_dict = state if callable(getattr(state, "get", None)) else {}
    locale = detect_active_call_language(state_dict, llm_request)
    sheet = build_language_sheet(locale, agent_name=agent_name)

    config = getattr(llm_request, "config", None)
    if config is None:
        return None
    sys_inst = getattr(config, "system_instruction", None)
    if sys_inst is None:
        return None

    def _update_text(text: str) -> str:
        if LANGUAGE_SHEET_SENTINEL in text:
            text = text.split(LANGUAGE_SHEET_SENTINEL, 1)[0].rstrip()
        return f"{text}\n\n{sheet}"

    if isinstance(sys_inst, str):
        config.system_instruction = _update_text(sys_inst)
    elif hasattr(sys_inst, "parts"):
        parts = getattr(sys_inst, "parts", None)
        if parts and len(parts) > 0:
            first = parts[0]
            if hasattr(first, "text") and isinstance(first.text, str):
                first.text = _update_text(first.text)
    elif isinstance(sys_inst, list) and len(sys_inst) > 0:
        if isinstance(sys_inst[0], str):
            sys_inst[0] = _update_text(sys_inst[0])
        elif hasattr(sys_inst[0], "text") and isinstance(sys_inst[0].text, str):
            sys_inst[0].text = _update_text(sys_inst[0].text)

    return None
