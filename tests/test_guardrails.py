import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_default_prompt_guardrail_language_aware() -> None:
    path = REPO_ROOT / "cxas_app" / "guardrails" / "Default_Prompt_Guardrail" / "Default_Prompt_Guardrail.json"
    assert path.is_file(), f"Missing {path}"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("enabled") is True
    assert "generativeAnswer" in data.get("action", {})
    prompt = data["action"]["generativeAnswer"].get("prompt", "")
    assert len(prompt) > 0
    # Must instruct the model to respond in the caller's language with {language} interpolation
    prompt_lower = prompt.lower()
    assert any(
        term in prompt_lower
        for term in ("same language", "caller is using", "exact language", "caller's language")
    ), f"Prompt guardrail answer prompt must be language-aware: {prompt!r}"
    assert "{language}" in prompt
    assert "cannot fulfill that request" in prompt_lower

    sec = data.get("llmPromptSecurity", {})
    assert sec.get("failOpen") is True
    assert "defaultSettings" not in sec
    cp = sec.get("customPolicy", {})
    assert cp.get("policyScope") == "USER_QUERY"
    assert cp.get("maxConversationMessages") == 6
    assert cp.get("allowShortUtterance") is False
    assert cp.get("failOpen") is True
    assert "Telecom Customer Service Requests in Any Language" in cp.get("prompt", "")


def test_default_safety_guardrail_language_aware() -> None:
    path = REPO_ROOT / "cxas_app" / "guardrails" / "Default_Safety_Guardrail" / "Default_Safety_Guardrail.json"
    assert path.is_file(), f"Missing {path}"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("enabled") is True
    assert "generativeAnswer" in data.get("action", {})
    prompt = data["action"]["generativeAnswer"].get("prompt", "")
    assert len(prompt) > 0
    # Must instruct the model to respond in the caller's language with {language} interpolation
    prompt_lower = prompt.lower()
    assert any(
        term in prompt_lower
        for term in ("same language", "caller is using", "exact language", "caller's language")
    ), f"Safety guardrail answer prompt must be language-aware: {prompt!r}"
    assert "{language}" in prompt

    app_json = json.loads((REPO_ROOT / "cxas_app" / "app.json").read_text(encoding="utf-8"))
    decls = {v["name"]: v["schema"] for v in app_json.get("variableDeclarations", [])}
    assert decls["language"]["default"] == ""
