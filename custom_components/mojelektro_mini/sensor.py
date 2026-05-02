from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_METERING_POINT_NAME, CONF_USAGE_POINT, DOMAIN
from .coordinator import MojelektroCoordinator, MojelektroData


@dataclass(frozen=True)
class SensorDescription:
    key: str
    name: str
    unit: str
    device_class: SensorDeviceClass
    state_class: SensorStateClass | None


SENSORS = (
    SensorDescription(
        "daily_import_kwh",
        "Daily grid consumption",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        None,
    ),
    SensorDescription(
        "daily_export_kwh",
        "Daily grid export",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        None,
    ),
    SensorDescription(
        "daily_balance_kwh",
        "Daily balance",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        None,
    ),
    SensorDescription(
        "today_consumption_kwh",
        "Today grid consumption",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL,
    ),
    SensorDescription(
        "today_export_kwh",
        "Today grid export",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL,
    ),
    SensorDescription(
        "today_balance_kwh",
        "Today balance",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "month_import_kwh",
        "Month grid consumption",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "month_export_kwh",
        "Month grid export",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "month_balance_kwh",
        "Month balance",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "year_import_kwh",
        "Year grid consumption",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "year_export_kwh",
        "Year grid export",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "year_balance_kwh",
        "Year balance",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "max_import_power_kw",
        "Max import power today",
        UnitOfPower.KILO_WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "max_export_power_kw",
        "Max export power today",
        UnitOfPower.KILO_WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "agreed_power_block_1_kw",
        "Agreed power block 1",
        UnitOfPower.KILO_WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "agreed_power_block_2_kw",
        "Agreed power block 2",
        UnitOfPower.KILO_WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "agreed_power_block_3_kw",
        "Agreed power block 3",
        UnitOfPower.KILO_WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "agreed_power_block_4_kw",
        "Agreed power block 4",
        UnitOfPower.KILO_WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "agreed_power_block_5_kw",
        "Agreed power block 5",
        UnitOfPower.KILO_WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "max_agreed_power_kw",
        "Max agreed power",
        UnitOfPower.KILO_WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "allowed_export_power_kw",
        "Allowed export power",
        UnitOfPower.KILO_WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDescription(
        "installed_production_power_kw",
        "Installed production power",
        UnitOfPower.KILO_WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MojelektroCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(MojelektroSensor(coordinator, entry, description) for description in SENSORS)


class MojelektroSensor(CoordinatorEntity[MojelektroCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MojelektroCoordinator,
        entry: ConfigEntry,
        description: SensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.key
        self._attr_name = description.name
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data[CONF_USAGE_POINT])},
            "name": entry.data.get(CONF_METERING_POINT_NAME, f"Mojelektro {entry.data[CONF_USAGE_POINT]}"),
            "manufacturer": "Moj Elektro",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._description.key.startswith("daily_"):
            await self.coordinator.async_register_daily_statistic_entity(
                self._description.key,
                self.entity_id,
                self.name,
            )

    @property
    def native_value(self) -> Decimal | None:
        data: MojelektroData | None = self.coordinator.data
        if data is None:
            return None
        return getattr(data, self._description.key)
