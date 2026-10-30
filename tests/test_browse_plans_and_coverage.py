from types import SimpleNamespace
import pytest

import cxas_app.tools.browse_plans_and_coverage.python_function.python_code as tool


def test_browse_plans_and_coverage_internet_happy_path(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.browse_plans_and_coverage(category="internet", postal_code="H3Z 2Y7", max_budget="80")
    assert res["status"] == "ok"
    assert res["data"]["category"] == "internet"
    assert len(res["data"]["shortlisted_plans"]) > 0
    assert res["data"]["fiber_coverage_available"] is True
    assert session.state["postal_code"] == "H3Z 2Y7"


def test_browse_plans_and_coverage_tv_with_dict_context(monkeypatch) -> None:
    session_dict = {}
    monkeypatch.setattr(tool, "context", session_dict, raising=False)
    res = tool.browse_plans_and_coverage(category="tv", service_address="123 Main St")
    assert res["status"] == "ok"
    assert res["data"]["category"] == "tv"
    assert len(res["data"]["shortlisted_plans"]) > 0
    assert session_dict["service_address"] == "123 Main St"


def test_browse_plans_and_coverage_mobility_without_context(monkeypatch) -> None:
    monkeypatch.setattr(tool, "context", None, raising=False)
    res = tool.browse_plans_and_coverage(category="mobility")
    assert res["status"] == "ok"
    assert res["data"]["category"] == "mobility"
    assert res["data"]["five_g_coverage_available"] is True


def test_browse_plans_and_coverage_localization_french(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.browse_plans_and_coverage(category="internet", language="fr-CA")
    assert res["status"] == "ok"
    assert len(res["data"]["shortlisted_plans"]) > 0


def test_browse_plans_and_coverage_localization_spanish(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.browse_plans_and_coverage(category="internet", language="es-US")
    assert res["status"] == "ok"
    assert len(res["data"]["shortlisted_plans"]) > 0


def test_browse_plans_and_coverage_french_comma_max_budget(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res_dot = tool.browse_plans_and_coverage(
        category="internet", postal_code="H3Z 2Y7", max_budget="60.00", language="fr-CA"
    )
    res_comma = tool.browse_plans_and_coverage(
        category="internet", postal_code="H3Z 2Y7", max_budget="60,00 $", language="fr-CA"
    )
    ids_dot = [p["id"] for p in res_dot["data"]["shortlisted_plans"]]
    ids_comma = [p["id"] for p in res_comma["data"]["shortlisted_plans"]]
    assert ids_comma == ids_dot == ["NET-STARTER"]
    assert all(float(p["monthly_price"]) <= 60.0 for p in res_comma["data"]["shortlisted_plans"])


def test_browse_plans_and_coverage_catalog_coherence_tax_speed_addons(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.browse_plans_and_coverage(category="internet", postal_code="H3Z 2Y7")
    assert res["status"] == "ok"
    plans = res["data"]["shortlisted_plans"]
    assert len(plans) >= 2
    for p in plans:
        assert "estimated_tax" in p
        assert "estimated_total_monthly" in p
        assert "monthly_total_with_tax" in p
        assert "download_speed" in p
        assert "upload_speed" in p
        assert "modem_compatibility" in p
        assert "included_modem" in p
        assert p["contract_required"] is False
        price = float(p["monthly_price"])
        tax = float(p["estimated_tax"])
        total = float(p["monthly_total_with_tax"])
        assert round(price + tax, 2) == round(total, 2)

    # Addons must be present with contract_required: False
    addons = res["data"].get("available_add_ons") or res["data"].get("add_ons")
    assert addons is not None and len(addons) > 0
    for a in addons:
        assert a["contract_required"] is False
        assert "estimated_tax" in a
        assert "monthly_total_with_tax" in a


@pytest.mark.parametrize(
    "lang,expected_feature_prefix,expected_desc_prefix,expected_modem",
    [
        ("en-US", "Unlimited downloads", "Full access", "Wi-Fi 6 Gateway (included at $0/month)"),
        ("fr-CA", "Téléchargements illimités", "Accès complet", "Borne Wi-Fi 6 (incluse à 0 $/mois)"),
        ("es-US", "Descargas ilimitadas", "Acceso completo", "Módem Wi-Fi 6 (incluido a $0/mes)"),
    ],
)
def test_browse_plans_and_coverage_single_language_replies(
    monkeypatch, lang: str, expected_feature_prefix: str, expected_desc_prefix: str, expected_modem: str
) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.browse_plans_and_coverage(category="internet", language=lang)
    assert res["status"] == "ok"
    plans = res["data"]["shortlisted_plans"]
    assert len(plans) >= 2
    for p in plans:
        assert "features" in p
        assert "features_en" not in p
        assert "features_fr" not in p
        assert "features_es" not in p
    assert plans[0]["features"].startswith(expected_feature_prefix)
    assert plans[0]["included_modem"] == expected_modem

    addons = res["data"].get("available_add_ons") or res["data"].get("add_ons")
    assert addons is not None and len(addons) > 0
    for a in addons:
        assert "description" in a
        assert "description_en" not in a
        assert "description_fr" not in a
        assert "description_es" not in a
    sports_addon = next((a for a in addons if a["id"] == "ADDON-SPORTS"), None)
    if sports_addon:
        assert sports_addon["description"].startswith(expected_desc_prefix)


def test_browse_plans_and_coverage_tv_sports_addon_channels_and_combined_monthly(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.browse_plans_and_coverage(category="tv")
    assert res["status"] == "ok"
    data = res["data"]
    assert data["category"] == "tv"
    assert "included_channels" in data
    assert "TSN 1-5" in data["included_channels"]
    assert "ESPN" in data["included_channels"]
    assert data["combined_monthly_with_tv_starter"] == "43.00"
    assert data["combined_monthly_with_tv_starter_with_tax"] == "49.45"

    addons = data.get("available_add_ons") or data.get("add_ons")
    sports_addon = next((a for a in addons if a["id"] == "ADDON-SPORTS"), None)
    assert sports_addon is not None
    assert "TSN 1-5" in sports_addon["included_channels"]
    assert "Sportsnet" in sports_addon["included_channels"]
    assert "ESPN" in sports_addon["included_channels"]
    assert sports_addon["combined_monthly_with_tv_starter"] == "43.00"
    assert sports_addon["combined_monthly_with_tv_starter_with_tax"] == "49.45"
    assert "TSN 1-5" in sports_addon["description"]


def test_browse_plans_and_coverage_internet_wfh_technical_specifications(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)
    res = tool.browse_plans_and_coverage(category="internet", postal_code="H3Z 2Y7")
    assert res["status"] == "ok"
    data = res["data"]
    assert data["category"] == "internet"
    assert "latency" in data
    assert "sub-15ms" in data["latency"]
    assert "<2ms jitter" in data["latency"]
    assert "technical_specifications" in data
    assert "Pure fiber symmetrical bandwidth" in data["technical_specifications"]
    assert "99.9% uptime" in data["technical_specifications"]
    assert "sla_or_guarantee" in data
    assert "work_from_home_recommended_tier" in data
    assert "Fiber Internet 500 or Gigabit Fiber" in data["work_from_home_recommended_tier"]

    plans = data["shortlisted_plans"]
    assert len(plans) >= 2
    for p in plans:
        assert "latency" in p
        assert "sub-15ms" in p["latency"]
        assert "technical_specifications" in p
        assert "sla_or_guarantee" in p
        assert "99.9%" in p["sla_or_guarantee"]


def test_browse_plans_and_coverage_current_plan_internet_en_fr_es(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)

    # English
    res_en = tool.browse_plans_and_coverage(category="internet", language="en-US")
    assert res_en["status"] == "ok"
    assert "current_plan" in res_en["data"]
    cp_en = res_en["data"]["current_plan"]
    assert cp_en["plan_name"] == "Fiber Internet 100"
    assert cp_en["monthly_price"] == "$45.00/month"
    assert cp_en["monthly_rate"] == "45.00"
    assert "100 Mbps" in cp_en["speed"]
    assert "Fiber Internet 100" in cp_en["spoken_summary"]
    assert res_en["data"]["current_plan_name"] == "Fiber Internet 100"
    assert res_en["data"]["current_plan_price"] == "$45.00/month"

    # French
    session_fr = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session_fr, raising=False)
    res_fr = tool.browse_plans_and_coverage(category="internet", language="fr-CA")
    assert res_fr["status"] == "ok"
    cp_fr = res_fr["data"]["current_plan"]
    assert cp_fr["plan_name"] == "Internet Fibre 100"
    assert cp_fr["monthly_price"] == "45.00 $/mois"
    assert "100 Mbps" in cp_fr["speed"]
    assert "Internet Fibre 100" in cp_fr["spoken_summary"]
    assert res_fr["data"]["current_plan_name"] == "Internet Fibre 100"
    assert res_fr["data"]["current_plan_price"] == "45.00 $/mois"

    # Spanish
    session_es = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session_es, raising=False)
    res_es = tool.browse_plans_and_coverage(category="internet", language="es-US")
    assert res_es["status"] == "ok"
    cp_es = res_es["data"]["current_plan"]
    assert cp_es["plan_name"] == "Internet Fibra 100"
    assert cp_es["monthly_price"] == "$45.00/mes"
    assert "100 Mbps" in cp_es["speed"]
    assert "Internet Fibra 100" in cp_es["spoken_summary"]


def test_browse_plans_and_coverage_current_plan_mobility_and_tv(monkeypatch) -> None:
    session = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session, raising=False)

    # Mobility
    res_mob = tool.browse_plans_and_coverage(category="mobility", language="en-US")
    assert res_mob["status"] == "ok"
    cp_mob = res_mob["data"]["current_plan"]
    assert cp_mob["plan_name"] == "Mobility Essential Plan"
    assert cp_mob["monthly_price"] == "$55.00/month"
    assert "20 GB" in cp_mob["speed"]
    assert "20 GB" in cp_mob["data"]
    assert res_mob["data"]["current_plan_name"] == "Mobility Essential Plan"
    assert res_mob["data"]["current_plan_price"] == "$55.00/month"

    # Mobility French
    session_fr = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session_fr, raising=False)
    res_mob_fr = tool.browse_plans_and_coverage(category="mobility", language="fr-CA")
    assert res_mob_fr["status"] == "ok"
    cp_mob_fr = res_mob_fr["data"]["current_plan"]
    assert cp_mob_fr["plan_name"] == "Forfait Mobilité Essentiel"
    assert cp_mob_fr["monthly_price"] == "55.00 $/mois"
    assert "20 Go" in cp_mob_fr["speed"]

    # TV
    session_tv = SimpleNamespace(state={})
    monkeypatch.setattr(tool, "context", session_tv, raising=False)
    res_tv = tool.browse_plans_and_coverage(category="tv", language="en-US")
    assert res_tv["status"] == "ok"
    cp_tv = res_tv["data"]["current_plan"]
    assert cp_tv["plan_name"] == "TV Starter"
    assert cp_tv["monthly_price"] == "$25.00/month"





