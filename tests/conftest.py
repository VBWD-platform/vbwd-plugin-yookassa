"""Shared fixtures for YooKassa plugin tests."""
from unittest.mock import MagicMock

import pytest

from vbwd.sdk.interface import SDKConfig
from vbwd.plugins.config_store import PluginConfigEntry


@pytest.fixture
def fake_lifecycle():
    """Register a spy ISubscriptionLifecycle (the webhook write port).

    YooKassa webhooks delegate recurring link/fail to this port; the test
    asserts the right port call instead of the old subscription-repo seam.
    """
    from vbwd.services.subscription_lifecycle import (
        ISubscriptionLifecycle,
        register_subscription_lifecycle,
        clear_subscription_lifecycle,
    )

    lifecycle = MagicMock(spec=ISubscriptionLifecycle)
    register_subscription_lifecycle(lifecycle)
    yield lifecycle
    clear_subscription_lifecycle()


@pytest.fixture
def recurring_registry():
    """Line-item registry carrying a fake handler that reports a line item as
    recurring iff the test attached a ``_recurring_spec`` to it (the seam
    ``determine_session_mode`` now uses). Saves + restores the singleton."""
    from vbwd.events.line_item_registry import (
        line_item_registry,
        ILineItemHandler,
        LineItemResult,
    )

    class _FakeRecurringHandler(ILineItemHandler):
        def can_handle_line_item(self, line_item, context):
            return True

        def activate_line_item(self, line_item, context):
            return LineItemResult.skip()

        def reverse_line_item(self, line_item, context):
            return LineItemResult.skip()

        def restore_line_item(self, line_item, context):
            return LineItemResult.skip()

        def is_recurring_line_item(self, line_item):
            return getattr(line_item, "_recurring_spec", None) is not None

        def recurring_billing_spec(self, line_item):
            return getattr(line_item, "_recurring_spec", None)

    saved = line_item_registry.handlers
    line_item_registry.clear()
    line_item_registry.register(_FakeRecurringHandler())
    yield line_item_registry
    line_item_registry.clear()
    for handler in saved:
        line_item_registry.register(handler)


@pytest.fixture
def yookassa_config():
    """YooKassa plugin configuration dict."""
    return {
        "test_shop_id": "test_shop_123",
        "test_secret_key": "test_secret_456",
        "test_webhook_secret": "whsec_test_789",
        "sandbox": True,
    }


@pytest.fixture
def sdk_config(yookassa_config):
    """SDKConfig instance built from yookassa_config."""
    return SDKConfig(
        api_key=yookassa_config["test_shop_id"],
        api_secret=yookassa_config["test_secret_key"],
        sandbox=yookassa_config["sandbox"],
    )


@pytest.fixture
def mock_yookassa_api(mocker):
    """Mock requests module for YooKassa API calls.

    Returns the mock so tests can configure specific responses.
    """
    mock = mocker.patch("plugins.yookassa.yookassa.sdk_adapter.requests")
    # Default: successful payment creation
    default_resp = mocker.MagicMock()
    default_resp.status_code = 200
    default_resp.json.return_value = {
        "id": "pay_default",
        "status": "pending",
        "confirmation": {"confirmation_url": "https://yookassa.ru/pay/default"},
    }
    mock.post.return_value = default_resp
    mock.get.return_value = default_resp
    return mock


@pytest.fixture
def mock_config_store(mocker, yookassa_config):
    """Mock PluginConfigStore with enabled YooKassa entry."""
    store = mocker.MagicMock()
    store.get_by_name.return_value = PluginConfigEntry(
        plugin_name="yookassa",
        status="enabled",
        config=yookassa_config,
    )
    store.get_config.return_value = yookassa_config
    return store


@pytest.fixture
def mock_config_store_disabled(mocker):
    """Config store returning disabled YooKassa plugin."""
    store = mocker.MagicMock()
    store.get_by_name.return_value = PluginConfigEntry(
        plugin_name="yookassa", status="disabled"
    )
    return store
