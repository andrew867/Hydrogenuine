"""Budget governor tests."""

import os

from hg_runtime.cloud_browser_governance.budget import ProviderBudgetGovernor


def test_budget_hard_stop():
    os.environ["HG_CLOUD_PROVIDERS_ENABLED"] = "true"
    gov = ProviderBudgetGovernor()
    gov.token_ledger.hourly_limit = 50
    gov.check_budget(tokens=50, cost_usd=0.0)
    gov.release_request()
    stop = gov.check_budget(tokens=1, cost_usd=0.0)
    assert stop.get("hard_stop") or stop.get("reason") == "budget_hard_stop"


def test_cloud_disabled_by_default():
    os.environ["HG_CLOUD_PROVIDERS_ENABLED"] = "false"
    gov = ProviderBudgetGovernor()
    assert gov.check_budget().get("allowed") is False
