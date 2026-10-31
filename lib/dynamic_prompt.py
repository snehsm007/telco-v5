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
        "aimerais",
        "habite",
        "adresse",
        "déménage",
        "vérifier",
        "disponibilité",
        "élevée",
        "trop",
        "besoin",
        "aide",
        "problème",
        "connexion",
        "fonctionne",
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
        "is",
        "am",
        "at",
        "address",
        "moving",
        "availability",
    }
)

_DP_GERMAN_MARKERS = frozenset(
    {
        "guten",
        "hallo",
        "morgen",
        "abend",
        "sprechen",
        "deutsch",
        "ich",
        "brauche",
        "hilfe",
        "helfen",
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
        "möchte",
        "funktioniert",
        "nicht",
        "haben",
        "habe",
        "kann",
        "können",
    }
)

_DP_PORTUGUESE_MARKERS = frozenset(
    {
        "olá",
        "oi",
        "bom",
        "boa",
        "noite",
        "preciso",
        "ajuda",
        "minha",
        "minhas",
        "meu",
        "meus",
        "fatura",
        "conta",
        "plano",
        "quero",
        "gostaria",
        "não",
        "tenho",
        "estou",
        "obrigado",
        "obrigada",
        "você",
        "vocês",
        "atendente",
        "cartão",
        "ligação",
        "português",
        "senha",
        "aparelho",
    }
)

_DP_ITALIAN_MARKERS = frozenset(
    {
        "buongiorno",
        "buonasera",
        "salve",
        "ciao",
        "parla",
        "italiano",
        "perché",
        "bisogno",
        "aiuto",
        "aiutarmi",
        "aiutare",
        "vorrei",
        "potete",
        "bolletta",
        "fattura",
        "connessione",
        "funziona",
        "disdire",
        "abbonamento",
        "cellulare",
        "guasto",
        "grazie",
        "favore",
        "mia",
        "mio",
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


_DP_STREET_ADDRESS_TOKENS = frozenset(
    {
        "rue",
        "boulevard",
        "boul",
        "blvd",
        "avenue",
        "ave",
        "av",
        "chemin",
        "ch",
        "route",
        "rte",
        "rang",
        "place",
        "côte",
        "cote",
        "impasse",
        "croissant",
        "allée",
        "allee",
        "terrasse",
        "promenade",
        "montée",
        "montee",
        "appartement",
        "apt",
        "street",
        "road",
        "rd",
        "drive",
        "dr",
        "qc",
    }
)

_DP_CANADIAN_POSTAL_RE = re.compile(
    r"\b[a-z]\d[a-z]\s*-?\s*\d[a-z]\d\b",
    re.IGNORECASE,
)
_DP_STREET_NUMBER_RE = re.compile(r"\b\d{1,5}\b")

_DP_NEGATED_SWITCH_PREFIX_RE = re.compile(
    r"(?:"
    r"\b(?:don't|do\s+not|dont|cannot|can't|cant|not)\s+"
    r"(?:want\s+to\s+|know\s+how\s+to\s+)?(?:speak\s+|talk\s+|switch\s+to\s+)?"
    r"|\b(?:pas|jamais)\s+(?:parler\s+|continuer\s+)?"
    r"|\bno\s+(?:hablo|habla|hablas|hablamos|puedo|podemos|quiero)\s+(?:hablar\s+)?"
    r")$",
    re.IGNORECASE,
)

_DP_EXPLICIT_SWITCH_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "fr-CA",
        (
            "en français",
            "en francais",
            "parler en français",
            "parler en francais",
            "switch to french",
            "french please",
            "in french",
            "speak french",
            "passer au français",
            "passer au francais",
        ),
    ),
    (
        "en-US",
        (
            "in english",
            "switch to english",
            "speak english",
            "english please",
            "en anglais",
            "parler en anglais",
            "passer à l'anglais",
            "passer a l'anglais",
            "en inglés",
            "en ingles",
            "hablar inglés",
            "hablar ingles",
            "habla inglés",
            "habla ingles",
        ),
    ),
    (
        "es-US",
        (
            "en español",
            "en espanol",
            "hablar en español",
            "hablar en espanol",
            "hablar español",
            "hablar espanol",
            "habla español",
            "habla espanol",
            "switch to spanish",
            "spanish please",
            "in spanish",
            "speak spanish",
            "en espagnol",
            "parler en espagnol",
        ),
    ),
    (
        "pt-BR",
        (
            "em português",
            "em portugues",
            "fala português",
            "fala portugues",
            "in portuguese",
            "do you speak portuguese",
            "speak portuguese",
            "switch to portuguese",
            "portuguese please",
        ),
    ),
    (
        "de-DE",
        (
            "auf deutsch",
            "sprechen sie deutsch",
            "in german",
            "do you speak german",
            "speak german",
            "switch to german",
            "german please",
        ),
    ),
    (
        "it-IT",
        (
            "in italiano",
            "parla italiano",
            "in italian",
            "do you speak italian",
            "speak italian",
            "switch to italian",
            "italian please",
        ),
    ),
    (
        "zh-CN",
        (
            "in mandarin",
            "in chinese",
            "do you speak mandarin",
            "do you speak chinese",
            "speak mandarin",
            "speak chinese",
            "mandarin please",
            "switch to mandarin",
        ),
    ),
    (
        "hi-IN",
        (
            "in hindi",
            "do you speak hindi",
            "speak hindi",
            "hindi please",
            "switch to hindi",
        ),
    ),
    (
        "ar-XA",
        (
            "in arabic",
            "do you speak arabic",
            "speak arabic",
            "arabic please",
            "switch to arabic",
        ),
    ),
    (
        "ja-JP",
        (
            "in japanese",
            "do you speak japanese",
            "speak japanese",
            "japanese please",
            "switch to japanese",
        ),
    ),
    (
        "ko-KR",
        (
            "in korean",
            "do you speak korean",
            "speak korean",
            "korean please",
            "switch to korean",
        ),
    ),
)


def _dp_match_explicit_switch(low: str) -> str:
    """Return target locale for the last non-negated explicit switch term in `low`."""
    best_end = -1
    best_locale = ""
    for target_locale, terms in _DP_EXPLICIT_SWITCH_TERMS:
        for term in terms:
            for m in re.finditer(rf"(?<!\w){re.escape(term)}(?!\w)", low):
                if _DP_NEGATED_SWITCH_PREFIX_RE.search(low[: m.start()]):
                    continue
                if m.end() > best_end:
                    best_end = m.end()
                    best_locale = target_locale
    return best_locale


def detect_utterance_language(utterance: str, current_language: str = "en-US") -> str:
    """Detect language from an utterance with contextual inertia on silence and numbers."""
    raw = str(utterance or "").strip()
    if re.fullmatch(
        r"(?:\[?(?:dtmf|touch-?tone|keypad|option|choice|touche|user)?\s*[:#-]?\s*)?2(?:[.#*]|\]|\s)*",
        raw,
        re.IGNORECASE,
    ):
        return "fr-CA"
    if re.fullmatch(
        r"(?:\[?(?:dtmf|touch-?tone|keypad|option|choice|touche|user)?\s*[:#-]?\s*)?1(?:[.#*]|\]|\s)*",
        raw,
        re.IGNORECASE,
    ):
        return "en-US"

    cleaned = re.sub(r"\[(?:pause|silence)\]", " ", str(utterance or ""), flags=re.IGNORECASE)
    cleaned = re.sub(r"[0-9\W_]+", " ", cleaned).strip()
    if not cleaned:
        return resolve_locale(current_language)

    low = str(utterance or "").lower()

    explicit_switch = _dp_match_explicit_switch(low)
    if explicit_switch:
        return explicit_switch

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
        1 if re.search(r"[äöüß]", low) else 0
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
    is_en_address_turn = resolve_locale(current_language) == "en-US" and (
        bool(_DP_CANADIAN_POSTAL_RE.search(low))
        or (
            bool(_DP_STREET_NUMBER_RE.search(low))
            and bool(_DP_STREET_ADDRESS_TOKENS.intersection(words))
        )
    )
    has_french_accents = (
        False
        if is_en_address_turn
        else bool(re.search(r"[éèêëàâùûîïôçœ]", non_place_text))
    )
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


_RE_RELAY_PREFIX = re.compile(
    r"^(?:For context|\s*\[[^\]]+\]\s*(?:said:|thought:|called tool |`[^`]*` tool returned result:))",
    re.IGNORECASE,
)
_RE_QUOTED_AGENT_BLOCK = re.compile(
    r"<<<BEGIN_QUOTED_AGENT_CONTENT>>>[\s\S]*?<<<END_QUOTED_AGENT_CONTENT>>>"
)
_RE_RELAY_ACTIVE_LANG = re.compile(
    r"['\"]active_language['\"]\s*:\s*['\"]([a-zA-Z]{2}(?:-[a-zA-Z]{2})?)['\"]"
)


def _is_relay_or_quoted_part(txt: str) -> bool:
    """Return True if txt is an ADK relay part, agent event, or quoted content block."""
    s = txt.strip()
    if not s:
        return True
    if _RE_RELAY_PREFIX.match(s):
        return True
    cleaned = _RE_QUOTED_AGENT_BLOCK.sub("", s).strip()
    if not cleaned:
        return True
    if _RE_RELAY_PREFIX.match(cleaned):
        return True
    return False


def _extract_relayed_active_language(llm_request: Any) -> str:
    """Extract the most recent active_language from relayed tool results in contents."""
    contents = getattr(llm_request, "contents", None)
    if not contents or not isinstance(contents, (list, tuple)):
        return ""
    last_lang = ""
    for item in contents:
        parts = getattr(item, "parts", None)
        if parts and isinstance(parts, (list, tuple)):
            for part in parts:
                txt = getattr(part, "text", None)
                if txt and isinstance(txt, str):
                    matches = _RE_RELAY_ACTIVE_LANG.findall(txt)
                    if matches:
                        last_lang = matches[-1]
                fn_resp = getattr(part, "function_response", None)
                if fn_resp:
                    resp = getattr(fn_resp, "response", None)
                    if isinstance(resp, dict):
                        al = resp.get("active_language")
                        if not al and isinstance(resp.get("result"), dict):
                            al = resp["result"].get("active_language")
                        if al and isinstance(al, str):
                            last_lang = al
        elif isinstance(getattr(item, "text", None), str):
            matches = _RE_RELAY_ACTIVE_LANG.findall(item.text)
            if matches:
                last_lang = matches[-1]
    if last_lang:
        return resolve_locale(last_lang)
    return ""


def extract_user_utterances(llm_request: Any) -> list[str]:
    """Safely extract genuine user utterance strings from LLM request contents, skipping relay parts."""
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
                        s = txt.strip()
                        if s.lower() == _PRE_GREETING_CONNECT_TOKEN:
                            continue
                        if not _is_relay_or_quoted_part(txt):
                            utterances.append(s)
            elif isinstance(getattr(item, "text", None), str):
                t = item.text.strip()
                if t and t.lower() != _PRE_GREETING_CONNECT_TOKEN and not _is_relay_or_quoted_part(t):
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
    if locked:
        locked = resolve_locale(locked)
    else:
        relayed = _extract_relayed_active_language(llm_request)
        if relayed:
            locked = relayed

    if locked and locked != "en-US":
        current = locked
        for utt in user_utterances:
            switch = _dp_match_explicit_switch(utt.lower())
            if switch:
                current = switch
        return current

    current = resolve_locale(locked) if locked else "en-US"
    for utt in user_utterances:
        if current != "en-US":
            switch = _dp_match_explicit_switch(utt.lower())
            if switch:
                current = switch
        else:
            current = detect_utterance_language(utt, current_language=current)

    return current


_PRE_GREETING_CONNECT_TOKEN = "[call connected]"

_EARLY_SILENCE_SUPPRESSED_TOOLS: frozenset[str] = frozenset(
    {
        "end_session",
        "handover_to_person",
    }
)

_SILENCE_TOKENS: frozenset[str] = frozenset(
    {
        "[silence]",
        "<silence>",
        "(silence)",
        "silence",
        "no input",
        "[no input]",
    }
)


def _is_silent_utterance(stripped: str) -> bool:
    """Return True when stripped user text represents silence or punctuation-only noise."""
    if not stripped:
        return True
    if stripped.lower() in _SILENCE_TOKENS:
        return True
    return bool(re.fullmatch(r"[.\s…\-_?!]+", stripped))


def _normalize_pre_greeting_connect_silence(llm_request: Any) -> None:
    """Replace pre-greeting silent connect turns with '[call connected]' in-place."""
    contents = getattr(llm_request, "contents", None)
    if not contents or not isinstance(contents, (list, tuple)):
        return None

    for item in contents:
        role = getattr(item, "role", "")
        parts = getattr(item, "parts", None)
        if role == "model":
            if parts and isinstance(parts, (list, tuple)):
                for part in parts:
                    if getattr(part, "thought", False):
                        continue
                    txt = getattr(part, "text", None)
                    if isinstance(txt, str) and txt.strip():
                        return None
            elif isinstance(getattr(item, "text", None), str) and item.text.strip():
                return None
        elif role == "user":
            if parts and isinstance(parts, (list, tuple)):
                for part in parts:
                    if getattr(part, "function_response", None) is not None:
                        continue
                    if getattr(part, "function_call", None) is not None:
                        continue
                    txt = getattr(part, "text", None)
                    if isinstance(txt, str) and _is_silent_utterance(txt.strip()):
                        try:
                            part.text = _PRE_GREETING_CONNECT_TOKEN
                        except Exception:  # pragma: no cover
                            pass
            elif isinstance(getattr(item, "text", None), str) and _is_silent_utterance(item.text.strip()):
                try:
                    item.text = _PRE_GREETING_CONNECT_TOKEN
                except Exception:  # pragma: no cover
                    pass
    return None


def _suppress_escalation_tools_on_early_silence(config: Any) -> None:
    """Filter end_session and handover_to_person from config.tools during silent turns 1-2."""
    tools = getattr(config, "tools", None)
    if not isinstance(tools, (list, tuple)):
        return None

    filtered_tools: list[Any] = []
    for t in tools:
        if isinstance(t, dict):
            if t.get("name", "") in _EARLY_SILENCE_SUPPRESSED_TOOLS:
                continue
            fds_dict = t.get("function_declarations")
            if isinstance(fds_dict, (list, tuple)):
                fds_kept = [
                    fd
                    for fd in fds_dict
                    if (fd.get("name", "") if isinstance(fd, dict) else getattr(fd, "name", ""))
                    not in _EARLY_SILENCE_SUPPRESSED_TOOLS
                ]
                other_keys = {k: v for k, v in t.items() if k != "function_declarations" and v}
                if fds_kept or other_keys:
                    filtered_tools.append({**t, "function_declarations": fds_kept})
                continue
            filtered_tools.append(t)
            continue

        if (
            getattr(t, "name", "") in _EARLY_SILENCE_SUPPRESSED_TOOLS
            or getattr(t, "__name__", "") in _EARLY_SILENCE_SUPPRESSED_TOOLS
        ):
            continue

        fds_raw = getattr(t, "function_declarations", None)
        if isinstance(fds_raw, (list, tuple)) and fds_raw:
            fds = [
                fd
                for fd in fds_raw
                if (fd.get("name", "") if isinstance(fd, dict) else getattr(fd, "name", ""))
                not in _EARLY_SILENCE_SUPPRESSED_TOOLS
            ]
            if len(fds) == len(fds_raw):
                filtered_tools.append(t)
                continue
            if hasattr(t, "model_dump"):
                other_fields = {
                    k: v
                    for k, v in t.model_dump(exclude_none=True).items()
                    if k != "function_declarations" and v
                }
            elif hasattr(t, "__dict__"):
                other_fields = {
                    k: v for k, v in vars(t).items() if k != "function_declarations" and v
                }
            else:  # pragma: no cover
                other_fields = {}
            if not fds and not other_fields:
                continue
            try:
                if callable(getattr(t, "model_copy", None)):
                    filtered_tools.append(t.model_copy(update={"function_declarations": fds or None}))
                elif hasattr(t, "__dict__") and other_fields:
                    filtered_tools.append(type(t)(**{**vars(t), "function_declarations": fds}))
                else:
                    filtered_tools.append(type(t)(function_declarations=fds))
            except Exception:  # pragma: no cover
                try:
                    clone = object.__new__(type(t))
                    clone.__dict__.update(t.__dict__)
                    clone.function_declarations = fds
                    filtered_tools.append(clone)
                except Exception:
                    filtered_tools.append(t)
            continue

        filtered_tools.append(t)

    try:
        config.tools = filtered_tools
    except Exception:  # pragma: no cover
        pass
    return None


def count_post_greeting_silent_turns(llm_request: Any) -> int:
    """Count consecutive post-greeting silent user turns from LLM request contents."""
    contents = getattr(llm_request, "contents", None)
    if not contents or not isinstance(contents, (list, tuple)):
        return 0

    agent_has_spoken = False
    consecutive_silent = 0

    for item in contents:
        role = getattr(item, "role", "")
        parts = getattr(item, "parts", None)
        if role == "model":
            if parts and isinstance(parts, (list, tuple)):
                for part in parts:
                    if getattr(part, "thought", False):
                        continue
                    txt = getattr(part, "text", None)
                    if isinstance(txt, str) and txt.strip():
                        agent_has_spoken = True
                        break
            elif isinstance(getattr(item, "text", None), str) and item.text.strip():
                agent_has_spoken = True
        elif role == "user":
            user_texts: list[str] = []
            if parts and isinstance(parts, (list, tuple)):
                for part in parts:
                    if getattr(part, "function_response", None) is not None:
                        continue
                    if getattr(part, "function_call", None) is not None:
                        continue
                    txt = getattr(part, "text", None)
                    if txt is None or not isinstance(txt, str):
                        continue
                    s = txt.strip()
                    if s and _is_relay_or_quoted_part(txt):
                        continue
                    user_texts.append(s)
            elif isinstance(getattr(item, "text", None), str):
                raw_t = item.text
                s = raw_t.strip()
                if not (s and _is_relay_or_quoted_part(raw_t)):
                    user_texts.append(s)

            if not user_texts:
                continue

            stripped = " ".join(t for t in user_texts if t).strip()
            if not agent_has_spoken and stripped.lower() == _PRE_GREETING_CONNECT_TOKEN:
                continue
            if _is_silent_utterance(stripped):
                if agent_has_spoken:
                    consecutive_silent += 1
            elif any(c.isalnum() for c in stripped):
                consecutive_silent = 0

    return consecutive_silent


def build_language_sheet(
    locale: str,
    agent_name: str = "router",
    silent_turns: int = 0,
) -> str:
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

    if 1 <= silent_turns < 3:
        lines.append(
            f"Post-greeting consecutive silent turns: {silent_turns} of 3 — politely check in and ask the caller to repeat; do NOT call handover_to_person or end_session yet."
        )
    elif silent_turns >= 3:
        lines.append(
            f'Post-greeting consecutive silent turns: {silent_turns} of 3 — 3rd consecutive silent turn reached; speak verbatim live_agent_handoff and call handover_to_person(reason="no_input_escalation") and end_session(reason="no_input_escalation").'
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
    silent_turns = count_post_greeting_silent_turns(llm_request)
    if silent_turns >= 1:
        _normalize_pre_greeting_connect_silence(llm_request)
    sheet = build_language_sheet(
        locale,
        agent_name=agent_name,
        silent_turns=silent_turns,
    )

    config = getattr(llm_request, "config", None)
    if config is None:
        return None
    if 1 <= silent_turns < 3:
        _suppress_escalation_tools_on_early_silence(config)
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
