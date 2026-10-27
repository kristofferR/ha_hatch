import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from hatch_rest_api import RestoreV5
from homeassistant.components.media_player.const import MediaPlayerEntityFeature
from homeassistant.const import STATE_IDLE, STATE_PAUSED, STATE_PLAYING

from custom_components.ha_hatch.button import async_setup_entry
from custom_components.ha_hatch.const import DOMAIN
from custom_components.ha_hatch.hatch_data_update_coordinator import (
    HatchDataUpdateCoordinator,
)
from custom_components.ha_hatch.media_riot_entity import MediaRiotEntity
from custom_components.ha_hatch.sensor import HatchPlaybackState


class RoutineControlsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Use the installed API's class without opening an MQTT connection.
        self.device = RestoreV5.__new__(RestoreV5)
        self.device.device_name = "Restore"
        self.device.thing_name = "restore"
        self.device.mac = "001122334455"
        self.device.sounds_by_name = {}
        self.coordinator = Mock(spec=HatchDataUpdateCoordinator)
        self.coordinator.rest_devices = [self.device]
        self.coordinator.rest_device_by_thing_name.return_value = self.device
        self.hass = SimpleNamespace(data={DOMAIN: self.coordinator})

    async def test_published_api_keeps_playback_working_without_routine_controls(self):
        entities = []
        await async_setup_entry(self.hass, Mock(), entities.extend)
        self.assertEqual(entities, [])

        player = MediaRiotEntity(self.coordinator, "restore")
        sensor = HatchPlaybackState(self.coordinator, "restore")
        self.assertFalse(player.supported_features & MediaPlayerEntityFeature.PAUSE)
        self.assertEqual(player.state, STATE_IDLE)
        self.assertEqual(sensor.native_value, "idle")
        player.media_pause()

        self.device.sound_id = 42
        self.assertEqual(player.state, STATE_PLAYING)
        self.assertEqual(sensor.native_value, "playing")
        player.media_play()

    async def test_compatible_api_exposes_routine_controls_and_pause_resume(self):
        self.device.is_paused = True
        self.device.is_snoozed = False
        self.device.current_playing = "routine"
        self.device.can_advance_step = True
        self.device.can_swap_routine = True
        self.device.stop_routine = Mock()
        self.device.snooze_alarm = Mock()
        self.device.advance_step = Mock()
        self.device.swap_routine = AsyncMock()
        self.device.pause_routine = Mock()
        self.device.resume_routine = Mock()

        entities = []
        await async_setup_entry(self.hass, Mock(), entities.extend)
        self.assertEqual(len(entities), 4)
        self.assertTrue(all(entity.available for entity in entities))

        player = MediaRiotEntity(self.coordinator, "restore")
        sensor = HatchPlaybackState(self.coordinator, "restore")
        self.assertTrue(player.supported_features & MediaPlayerEntityFeature.PAUSE)
        self.assertEqual(player.state, STATE_PAUSED)
        self.assertEqual(sensor.native_value, "paused")
        player.media_pause()
        player.media_play()
        self.device.pause_routine.assert_called_once_with()
        self.device.resume_routine.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
