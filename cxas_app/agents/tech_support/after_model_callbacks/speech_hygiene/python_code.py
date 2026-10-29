from __future__ import annotations

from types import SimpleNamespace
from typing import Optional



def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Clean speech, mask long numbers, and ensure valid handover lines."""
    state = getattr(callback_context, "state", None)
    state_dict = state if isinstance(state, dict) else {}
    content = getattr(llm_response, "content", None)
    parts = getattr(content, "parts", None) if content is not None else None
    if content is None or parts is None:
        return None

    changed = False
    has_spoken_text = False
    called_tools: list[str] = []
    tool_args_list: list[dict] = []

    for part in parts:
        fc = getattr(part, "function_call", None)
        if fc is not None:
            fc_name = getattr(fc, "name", None)
            if fc_name:
                called_tools.append(str(fc_name))
            fc_args = getattr(fc, "args", None)
            if fc_args is not None:
                tool_args_list.append(dict(fc_args))

    for part in parts:
        text = getattr(part, "text", None)
        if isinstance(text, str) and text.strip():
            has_spoken_text = True
            cleaned = clean_agent_speech(text, state_dict)
            if "handover_to_person" in called_tools:
                cleaned = enforce_handover_utterance(
                    cleaned,
                    state_dict,
                    called_tools=called_tools,
                    tool_args_list=tool_args_list,
                )
            if cleaned != text:
                part.text = cleaned
                changed = True

    if not has_spoken_text:
        msg = enforce_handover_utterance(
            "",
            state_dict,
            called_tools=called_tools,
            tool_args_list=tool_args_list,
        ).strip()
        if msg and isinstance(parts, list):
            cleaned_msg = clean_agent_speech(msg, state_dict)
            if (
                parts
                and getattr(parts[0], "text", None) == ""
                and not getattr(parts[0], "function_call", None)
            ):
                parts.pop(0)
            _part_cls = globals().get("Part")
            new_part = (
                _part_cls.from_text(text=cleaned_msg)
                if _part_cls is not None and hasattr(_part_cls, "from_text")
                else SimpleNamespace(text=cleaned_msg)
            )
            parts.insert(0, new_part)
            changed = True

    return llm_response if changed else None


# --- BEGIN GENERATED SHARED BUNDLE (edit lib/, then run `make bundle`) ---
# uses: from lib.speech import clean_agent_speech, enforce_handover_utterance
from pathlib import Path
from typing import Any
import re
import sys

_LAST4_CONTEXT_RE = re.compile(  # pragma: no cover
    r"((?:ending\s+in|terminant\s+par|termina\s+en|number\s+is|num[eé]ro\s+est|n[uú]mero\s+es)\s+)(\d{4})\b",
    re.IGNORECASE,
)

NUMBER_RUN_RE = re.compile(r"\(?\d+\)?(?:[-.]\(?\d+\)?|\s\(?\d{3,}\)?)*")  # pragma: no cover

SPEAKABLE_NUMBERS: frozenset[str] = frozenset()  # pragma: no cover

def mask_long_numbers(text: str, min_digits: int = 9) -> str:  # pragma: no cover
    """Replace every number of min_digits or more digits by its last 4 digits."""

    def _mask(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) < min_digits or digits in SPEAKABLE_NUMBERS:
            return match.group(0)
        return digits[-4:]

    return NUMBER_RUN_RE.sub(_mask, text)

MARKDOWN_RE = re.compile(r"\*+|`+|^#+[ \t]*", re.MULTILINE)  # pragma: no cover

def strip_markdown(text: str) -> str:  # pragma: no cover
    """Drop markdown formatting characters from spoken text."""
    return MARKDOWN_RE.sub("", text)

def clean_speech(text: str) -> str:  # pragma: no cover
    """Clean markdown formatting and long numbers from spoken text."""
    return mask_long_numbers(strip_markdown(text))

def clean_agent_speech(  # pragma: no cover
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

def resolve_locale(language: str | None) -> str:  # pragma: no cover
    """Normalize a language tag, name, or code into a canonical BCP-47 locale."""
    raw = str(language or "").strip()
    if not raw:
        return "en-US"
    low = raw.lower().replace("_", "-")
    if low in ("primary",) or low.startswith(("en", "english", "anglais")):
        return "en-US"
    if low in ("secondary",) or low.startswith(("fr", "french", "francais", "français")):
        return "fr-CA"
    if low.startswith(("es", "spanish", "espanol", "español")):
        return "es-US"
    if low.startswith(("pt", "portug")):
        return "pt-BR"
    if low.startswith(("de", "german", "deutsch")):
        return "de-DE"
    if low.startswith(("it", "ital")):
        return "it-IT"
    if low.startswith(("zh", "chin", "mandarin")):
        return "zh-CN"
    if low.startswith(("hi", "hindi")):
        return "hi-IN"
    if low.startswith(("ar", "arab")):
        return "ar-XA"
    if low.startswith(("ja", "japan")):
        return "ja-JP"
    if low.startswith(("ko", "korean")):
        return "ko-KR"
    m = re.match(r"^([a-zA-Z]{2,3})-([a-zA-Z0-9]{2,4})$", raw)
    if m:
        return f"{m.group(1).lower()}-{m.group(2).upper()}"
    return "en-US"

def resolve_copy_locale(language: str | None) -> str:  # pragma: no cover
    """Pick one of the three primary supported copy locales."""
    loc = resolve_locale(language)
    if loc == "fr-CA":
        return "fr-CA"
    if loc == "es-US":
        return "es-US"
    return "en-US"

SPOKEN_LINES: dict[str, dict[str, str]] = {  # pragma: no cover
    "greeting": {
        "en-US": "Hello, thanks for calling. Which phone number or account number can I look up for you?",
        "fr-CA": "Bonjour, merci de votre appel. Quel numéro de téléphone ou numéro de compte puis-je rechercher pour vous?",
        "es-US": "Hola, gracias por su llamada. ¿Qué número de teléfono o número de cuenta puedo buscar para usted?",
    },
    "code_sent": {
        "en-US": "I've sent a login code to the phone number ending in [destination_last4]. Please read it to me when it arrives.",
        "fr-CA": "J'ai envoyé un code de connexion au numéro se terminant par [destination_last4]. Lisez-le-moi dès que vous le recevez.",
        "es-US": "Envié un código de acceso al número que termina en [destination_last4]. Léamelo cuando lo reciba.",
    },
    "handover": {
        "en-US": "I'm transferring you to a member of our team now. Thank you for your patience.",
        "fr-CA": "Je vous transfère maintenant à un membre de notre équipe. Merci de votre patience.",
        "es-US": "Le transfiero ahora con un miembro de nuestro equipo. Gracias por su paciencia.",
    },
    "greeting_main": {
        "en-US": "Welcome to Telco. I can help with billing, technical support, or managing your account. To get started, could you tell me the phone number or account number associated with your service?",
        "fr-CA": "Bienvenue chez Telco. Je peux vous aider avec la facturation, le soutien technique ou la gestion de votre compte. Pour commencer, pourriez-vous m'indiquer le numéro de téléphone ou le numéro de compte associé à votre service?",
        "es-US": "Bienvenido a Telco. Puedo ayudarle con facturación, soporte técnico o la gestión de su cuenta. Para comenzar, ¿podría indicarme el número de teléfono o el número de cuenta asociado a su servicio?",
    },
    "recording_notice": {
        "en-US": "This call may be recorded for quality and training purposes.",
        "fr-CA": "Cet appel peut être enregistré à des fins de qualité et de formation.",
        "es-US": "Esta llamada puede ser grabada con fines de calidad y capacitación.",
    },
    "id_verification_otp": {
        "en-US": "For your security, I just sent a 6-digit code to that number — please read it back to me.",
        "fr-CA": "Pour votre sécurité, je viens d'envoyer un code à 6 chiffres à ce numéro — veuillez me le lire.",
        "es-US": "Por su seguridad, acabo de enviar un código de 6 dígitos a ese número; por favor léamelo.",
    },
    "id_verification_email_otp": {
        "en-US": "For your security, I just sent a 6-digit verification code to your backup email address on file — please read it back to me.",
        "fr-CA": "Pour votre sécurité, je viens d'envoyer un code de vérification à 6 chiffres à votre adresse courriel de secours au dossier — veuillez me le lire.",
        "es-US": "Por su seguridad, acabo de enviar un código de verificación de 6 dígitos a su correo electrónico de respaldo registrado; por favor léamelo.",
    },
    "id_verification_pin": {
        "en-US": "For your security, I'll need to verify your identity. Please enter the 4-digit PIN you set up.",
        "fr-CA": "Pour votre sécurité, je dois vérifier votre identité. Veuillez composer le NIP à 4 chiffres que vous avez configuré.",
        "es-US": "Por su seguridad, necesito verificar su identidad. Por favor ingrese el PIN de 4 dígitos que configuró.",
    },
    "live_agent_handoff": {
        "en-US": "I'll connect you to a representative who can help. Please hold.",
        "fr-CA": "Je vais vous mettre en communication avec un représentant qui pourra vous aider. Veuillez patienter.",
        "es-US": "Le comunicaré con un representante que pueda ayudarle. Por favor espere.",
    },
    "business_handoff": {
        "en-US": "To get you the best support for your business account, I'll transfer you to an agent. You'll need to use your phone keypad instead of talking to the virtual assistant. Just a moment while I connect you.",
        "fr-CA": "Pour vous offrir le meilleur soutien pour votre compte affaires, je vais vous transférer à un agent. Vous devrez utiliser le clavier de votre téléphone plutôt que de parler à l'assistant virtuel. Un instant pendant que je vous transfère.",
        "es-US": "Para brindarle la mejor asistencia con su cuenta comercial, le transferiré con un agente. Deberá usar el teclado de su teléfono en lugar de hablar con el asistente virtual. Un momento mientras le comunico.",
    },
    "payment_method_preamble": {
        "en-US": "For your security, please do not read your full card number or security code out loud; we only confirm the last four digits on file.",
        "fr-CA": "Pour votre sécurité, veuillez ne pas lire votre numéro de carte complet ni votre code de sécurité à haute voix; nous confirmons uniquement les quatre derniers chiffres au dossier.",
        "es-US": "Por su seguridad, no lea en voz alta el número completo de su tarjeta ni el código de seguridad; solo confirmamos los últimos cuatro dígitos registrados.",
    },
    "contract_cancellation_fee_disclosure": {
        "en-US": "Please note that cancelling or transferring your line ends any active term agreement, and any applicable early cancellation fee and prorated charges from your account terms will appear on your final statement.",
        "fr-CA": "Veuillez noter que l'annulation ou le transfert de votre ligne met fin à toute entente active, et que les frais de résiliation anticipée applicables ainsi que le solde calculé au prorata figureront sur votre dernière facture.",
        "es-US": "Tenga en cuenta que cancelar o transferir su línea finaliza cualquier contrato vigente, y cualquier cargo aplicable por cancelación anticipada y cargos prorrateados aparecerán en su estado de cuenta final.",
    },
    "refund_confirmation_pattern": {
        "en-US": "Your refund of $[amount] will appear on your next statement within [days] business days.",
        "fr-CA": "Votre remboursement de [amount] $ figurera sur votre prochain relevé d'ici [days] jours ouvrables.",
        "es-US": "Su reembolso de $[amount] aparecerá en su próximo estado de cuenta dentro de [days] días hábiles.",
    },
    "empathy_protocol": {
        "en-US": "I'm very sorry to hear that you are facing challenges. I will ensure we handle your request with the utmost care.",
        "fr-CA": "Je suis vraiment désolé d'apprendre que vous rencontrez ces difficultés. Je veillerai à ce que nous traitions votre demande avec le plus grand soin.",
        "es-US": "Lamento mucho saber que está pasando por dificultades. Me aseguraré de que atendamos su solicitud con el mayor cuidado.",
    },
    "outage_active": {
        "en-US": "I see there's an active outage in your area. We're working on it. Would you like me to text you when it's restored?",
        "fr-CA": "Je constate qu'une panne est en cours dans votre secteur. Nous travaillons à la résoudre. Voulez-vous que je vous envoie un texto dès que le service sera rétabli?",
        "es-US": "Veo que hay una interrupción activa en su área. Estamos trabajando para resolverla. ¿Desea que le envíe un mensaje de texto cuando se restablezca el servicio?",
    },
    "transfer_to_specialist": {
        "en-US": "I'll connect you to a billing specialist now — they'll have everything we've already discussed.",
        "fr-CA": "Je vous mets maintenant en communication avec un spécialiste de la facturation — il aura déjà tout ce dont nous avons discuté.",
        "es-US": "Le comunicaré ahora con un especialista de facturación; tendrá toda la información que ya conversamos.",
    },
    "service_alert_banner": {
        "en-US": "Please note: there is an active regional service advisory in parts of Montreal today.",
        "fr-CA": "Veuillez noter qu'un avis de service régional est actuellement en vigueur dans certains secteurs de Montréal.",
        "es-US": "Tenga en cuenta que hoy hay un aviso de servicio regional activo en partes de Montreal.",
    },
    "blocked_caller_deflection": {
        "en-US": "We're unable to complete this call from your current number. Please visit telco.example.com/support for assistance. Goodbye.",
        "fr-CA": "Nous ne sommes pas en mesure de traiter cet appel à partir de ce numéro. Veuillez consulter telco.example.com/support pour obtenir de l'aide. Au revoir.",
        "es-US": "No podemos completar esta llamada desde este número. Visite telco.example.com/support para recibir asistencia. Hasta luego.",
    },
    "malicious_closing": {
        "en-US": "I'm only able to assist with Telco telecommunications services and account requests. Thank you for calling, goodbye.",
        "fr-CA": "Je peux uniquement vous aider avec les services de télécommunications et les demandes de compte Telco. Merci de votre appel, au revoir.",
        "es-US": "Solo puedo ayudarle con servicios de telecomunicaciones y solicitudes de cuenta de Telco. Gracias por llamar, hasta luego.",
    },
}

def spoken_line(key: str, language: str | None = "en-US", **slots: object) -> str:  # pragma: no cover
    """Return the spoken template for key and language, formatting all placeholders."""
    locale = resolve_copy_locale(language)
    table = SPOKEN_LINES.get(key, {})
    template = table.get(locale) or table.get("en-US") or ""
    for slot_name, slot_val in slots.items():
        if isinstance(slot_val, float) and slot_val.is_integer():
            val_str = str(int(slot_val))
        elif slot_name == "days" and isinstance(slot_val, (int, float, str)):
            try:
                val_str = str(int(float(slot_val)))
            except (ValueError, TypeError):
                val_str = str(slot_val)
        else:
            val_str = str(slot_val)
        template = template.replace(f"[{slot_name}]", val_str).replace(f"{{{slot_name}}}", val_str)
    return template

def enforce_handover_utterance(  # pragma: no cover
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
# --- END GENERATED SHARED BUNDLE ---
