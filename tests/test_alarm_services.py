from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.ha_hatch.const import DOMAIN
from custom_components.ha_hatch.hatch_data_update_coordinator import (
    HatchDataUpdateCoordinator,
)
from custom_components.ha_hatch.services import (
    SERVICE_SET_ALARM_WEEKDAYS,
    async_register_services,
)


class AlarmServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        config_dir = TemporaryDirectory()
        self.addCleanup(config_dir.cleanup)
        self.hass = HomeAssistant(config_dir.name)
        self.addAsyncCleanup(self.hass.async_stop)
        self.device = SimpleNamespace(set_alarm_weekdays=AsyncMock())
        coordinator = Mock(spec=HatchDataUpdateCoordinator)
        coordinator.rest_device_by_thing_name.return_value = self.device
        self.hass.config_entries = Mock()
        self.hass.config_entries.async_get_entry.return_value = SimpleNamespace(
            runtime_data=coordinator
        )
        self.hass.data[dr.DATA_REGISTRY] = dr.DeviceRegistry(self.hass)
        await dr.async_get(self.hass).async_load()
        registry = er.async_get(self.hass)
        await registry.async_load()
        self.alarm = registry.async_get_or_create(
            "switch", DOMAIN, "thing_alarm_42_switch"
        ).entity_id
        self.unrelated = registry.async_get_or_create(
            "light", "other", "unrelated"
        ).entity_id
        self.hass.states.async_set(
            "group.bedroom", "on", {"entity_id": [self.alarm, self.unrelated]}
        )
        async_register_services(self.hass)

    async def set_weekdays(self, entity_ids):
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_SET_ALARM_WEEKDAYS,
            {"entity_id": entity_ids, "weekdays": ["monday"]},
            blocking=True,
        )

    async def test_explicit_alarm_updates_weekdays(self):
        await self.set_weekdays(self.alarm)
        self.device.set_alarm_weekdays.assert_awaited_once_with("42", ["monday"])

    async def test_mixed_group_updates_only_the_alarm(self):
        await self.set_weekdays("group.bedroom")
        self.device.set_alarm_weekdays.assert_awaited_once_with("42", ["monday"])

    async def test_explicit_unrelated_entity_is_rejected_even_with_a_group(self):
        for entity_ids in (self.unrelated, ["group.bedroom", self.unrelated]):
            with self.subTest(entity_ids=entity_ids):
                with self.assertRaisesRegex(ServiceValidationError, "not a Hatch alarm"):
                    await self.set_weekdays(entity_ids)
                self.device.set_alarm_weekdays.assert_not_awaited()

    async def test_group_and_explicit_alarm_are_deduplicated(self):
        await self.set_weekdays(["group.bedroom", self.alarm])
        self.device.set_alarm_weekdays.assert_awaited_once_with("42", ["monday"])


if __name__ == "__main__":
    unittest.main()
