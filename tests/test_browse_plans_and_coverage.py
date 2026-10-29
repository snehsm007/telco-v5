from types import SimpleNamespace

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
