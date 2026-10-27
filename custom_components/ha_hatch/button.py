from __future__ import annotations

from hatch_rest_api import RestoreV5
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .const import DOMAIN
from .hatch_entity import HatchEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    entities: list[ButtonEntity] = []
    for rest_device in coordinator.rest_devices:
        if not isinstance(rest_device, RestoreV5):
            continue
        # Published API versions may not include the routine controls yet.
        for button_type, method, state_attributes in (
            (HatchStopRoutineButton, "stop_routine", ("current_playing",)),
            (HatchSnoozeAlarmButton, "snooze_alarm", ("current_playing", "is_snoozed")),
            (HatchAdvanceStepButton, "advance_step", ("can_advance_step",)),
            (HatchSwapRoutineButton, "swap_routine", ("can_swap_routine",)),
        ):
            if callable(getattr(rest_device, method, None)) and all(
                hasattr(rest_device, attribute) for attribute in state_attributes
            ):
                entities.append(
                    button_type(
                        coordinator=coordinator, thing_name=rest_device.thing_name
                    )
                )
    async_add_entities(entities)


class HatchStopRoutineButton(HatchEntity, ButtonEntity):
    entity_description = ButtonEntityDescription(
        key="stop_routine",
        icon="mdi:stop",
    )

    def __init__(
        self, coordinator: HatchDataUpdateCoordinator, thing_name: str
    ):
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Stop Routine",
        )

    @property
    def available(self) -> bool:
        device = self.rest_device
        return device is not None and device.current_playing != "none"

    def press(self) -> None:
        self.rest_device.stop_routine()


class HatchSnoozeAlarmButton(HatchEntity, ButtonEntity):
    entity_description = ButtonEntityDescription(
        key="snooze_alarm",
        icon="mdi:alarm-snooze",
    )

    def __init__(
        self, coordinator: HatchDataUpdateCoordinator, thing_name: str
    ):
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Snooze Alarm",
        )

    @property
    def available(self) -> bool:
        device = self.rest_device
        if device is None:
            return False
        return device.current_playing == "routine" and not device.is_snoozed

    def press(self) -> None:
        self.rest_device.snooze_alarm()


class HatchAdvanceStepButton(HatchEntity, ButtonEntity):
    entity_description = ButtonEntityDescription(
        key="advance_step",
        icon="mdi:skip-next",
    )

    def __init__(
        self, coordinator: HatchDataUpdateCoordinator, thing_name: str
    ):
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Advance Step",
        )

    @property
    def available(self) -> bool:
        device = self.rest_device
        return device is not None and device.can_advance_step

    def press(self) -> None:
        self.rest_device.advance_step()


class HatchSwapRoutineButton(HatchEntity, ButtonEntity):
    entity_description = ButtonEntityDescription(
        key="swap_routine",
        icon="mdi:swap-horizontal",
    )

    def __init__(
        self, coordinator: HatchDataUpdateCoordinator, thing_name: str
    ):
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Swap Routine",
        )

    @property
    def available(self) -> bool:
        device = self.rest_device
        return device is not None and device.can_swap_routine

    async def async_press(self) -> None:
        await self.rest_device.swap_routine()
        self.schedule_update_ha_state()
