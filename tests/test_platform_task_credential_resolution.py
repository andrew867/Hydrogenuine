import os
from unittest.mock import patch


def test_fourclaw_load_api_key_uses_task_keystore_for_bayman():
    from hg_platforms.fourclaw.fourclaw_api_client_async import load_api_key

    with patch(
        "hg_platforms.fourclaw.fourclaw_api_client_async.resolve_task_platform_credential",
        return_value="bayman-fourclaw-key",
    ):
        assert load_api_key("newfoundland-bayman-fourclaw-auto-post") == "bayman-fourclaw-key"


def test_fourclaw_sync_load_api_key_uses_task_keystore_for_bayman():
    from hg_platforms.fourclaw.fourclaw_api_client import load_api_key

    with patch(
        "hg_platforms.fourclaw.fourclaw_api_client.resolve_task_platform_credential",
        return_value="bayman-fourclaw-key-sync",
    ):
        assert load_api_key("newfoundland-bayman-fourclaw-engage") == "bayman-fourclaw-key-sync"


def test_moltbook_load_api_key_uses_task_keystore_for_bayman():
    from hg_platforms.moltbook.moltbook_api_client_async import load_api_key

    with patch(
        "hg_platforms.moltbook.moltbook_api_client_async.resolve_task_platform_credential",
        return_value="bayman-moltbook-key",
    ):
        assert load_api_key("newfoundland-bayman-moltbook-engage") == "bayman-moltbook-key"


def test_moltx_load_api_key_prefers_runtime_binding_and_env():
    from skills.automation.moltx.moltx_api_client_async import load_api_key

    with patch.dict(os.environ, {}, clear=True), patch(
        "skills.automation.moltx.moltx_api_client_async.resolve_runtime_task_name",
        return_value="moltx-engage",
    ), patch(
        "skills.automation.moltx.moltx_api_client_async.resolve_task_platform_credential",
        return_value="moltx-runtime-key",
    ):
        assert load_api_key() == "moltx-runtime-key"


def test_moltx_load_api_key_uses_env_over_runtime_binding():
    from skills.automation.moltx.moltx_api_client_async import load_api_key

    with patch.dict(os.environ, {"MOLTX_API_KEY": "moltx-env-key"}, clear=True), patch(
        "skills.automation.moltx.moltx_api_client_async.resolve_task_platform_credential",
        return_value="moltx-runtime-key",
    ):
        assert load_api_key() == "moltx-env-key"
