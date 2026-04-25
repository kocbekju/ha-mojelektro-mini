from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PRODUCTION_URL, TEST_URL, MojelektroApiError, MojelektroClient, ReadingPoint
from .const import (
    CONF_ALLOWED_EXPORT_POWER,
    CONF_API_ENVIRONMENT,
    CONF_INSTALLED_PRODUCTION_POWER,
    CONF_OMTO_GSRN,
    CONF_POLL_INTERVAL_MINUTES,
    CONF_USAGE_POINT,
    DEFAULT_POLL_INTERVAL_MINUTES,
    DOMAIN,
    READING_TYPE_CONSUMPTION,
    READING_TYPE_EXPORT,
    READING_TYPE_MAX_EXPORT_POWER,
    READING_TYPE_MAX_IMPORT_POWER,
)


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class MojelektroData:
    today_consumption_kwh: Decimal | None
    today_export_kwh: Decimal | None
    today_balance_kwh: Decimal | None
    month_balance_kwh: Decimal | None
    year_balance_kwh: Decimal | None
    max_import_power_kw: Decimal | None
    max_export_power_kw: Decimal | None
    agreed_power_block_1_kw: Decimal | None
    agreed_power_block_2_kw: Decimal | None
    agreed_power_block_3_kw: Decimal | None
    agreed_power_block_4_kw: Decimal | None
    agreed_power_block_5_kw: Decimal | None
    max_agreed_power_kw: Decimal | None
    allowed_export_power_kw: Decimal | None
    installed_production_power_kw: Decimal | None


class MojelektroCoordinator(DataUpdateCoordinator[MojelektroData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=entry.options.get(
                    CONF_POLL_INTERVAL_MINUTES,
                    DEFAULT_POLL_INTERVAL_MINUTES,
                )
            ),
        )
        self.entry = entry
        base_url = TEST_URL if entry.data[CONF_API_ENVIRONMENT] == "test" else PRODUCTION_URL
        self.client = MojelektroClient(
            async_get_clientsession(hass),
            entry.data[CONF_API_TOKEN],
            base_url,
        )

    async def _async_update_data(self) -> MojelektroData:
        today = date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        reading_types = [
            READING_TYPE_CONSUMPTION,
            READING_TYPE_EXPORT,
            READING_TYPE_MAX_IMPORT_POWER,
            READING_TYPE_MAX_EXPORT_POWER,
        ]

        try:
            today_readings = await self.client.async_get_meter_readings(
                self.entry.data[CONF_USAGE_POINT],
                today,
                today,
                reading_types,
            )
            month_readings = await self.client.async_get_meter_readings(
                self.entry.data[CONF_USAGE_POINT],
                month_start,
                today,
                reading_types,
            )
            year_readings = await self.client.async_get_meter_readings(
                self.entry.data[CONF_USAGE_POINT],
                year_start,
                today,
                reading_types,
            )
            agreed_power = await self._async_get_agreed_power()
        except MojelektroApiError as err:
            raise UpdateFailed(str(err)) from err

        today_consumption = _sum(today_readings.get(READING_TYPE_CONSUMPTION))
        today_export = _sum(today_readings.get(READING_TYPE_EXPORT))
        month_consumption = _sum(month_readings.get(READING_TYPE_CONSUMPTION))
        month_export = _sum(month_readings.get(READING_TYPE_EXPORT))
        year_consumption = _sum(year_readings.get(READING_TYPE_CONSUMPTION))
        year_export = _sum(year_readings.get(READING_TYPE_EXPORT))

        return MojelektroData(
            today_consumption_kwh=today_consumption,
            today_export_kwh=today_export,
            today_balance_kwh=_balance(today_consumption, today_export),
            month_balance_kwh=_balance(month_consumption, month_export),
            year_balance_kwh=_balance(year_consumption, year_export),
            max_import_power_kw=_max(today_readings.get(READING_TYPE_MAX_IMPORT_POWER)),
            max_export_power_kw=_max(today_readings.get(READING_TYPE_MAX_EXPORT_POWER)),
            agreed_power_block_1_kw=agreed_power[0],
            agreed_power_block_2_kw=agreed_power[1],
            agreed_power_block_3_kw=agreed_power[2],
            agreed_power_block_4_kw=agreed_power[3],
            agreed_power_block_5_kw=agreed_power[4],
            max_agreed_power_kw=_max_values(agreed_power),
            allowed_export_power_kw=_decimal(self.entry.data.get(CONF_ALLOWED_EXPORT_POWER)),
            installed_production_power_kw=_decimal(self.entry.data.get(CONF_INSTALLED_PRODUCTION_POWER)),
        )

    async def _async_get_agreed_power(self) -> tuple[
        Decimal | None,
        Decimal | None,
        Decimal | None,
        Decimal | None,
        Decimal | None,
    ]:
        payload = await self.client.async_get_merilna_tocka(self.entry.data[CONF_OMTO_GSRN])
        dogovorjene_moci = payload.get("dogovorjeneMoci") or []
        active = _select_active_agreed_power(dogovorjene_moci, date.today())
        if active is None and dogovorjene_moci:
            active = dogovorjene_moci[0]
        if active is None:
            return (None, None, None, None, None)

        return (
            _decimal(active.get("casovniBlok1")),
            _decimal(active.get("casovniBlok2")),
            _decimal(active.get("casovniBlok3")),
            _decimal(active.get("casovniBlok4")),
            _decimal(active.get("casovniBlok5")),
        )


def _valid_points(points: list[ReadingPoint] | None) -> list[ReadingPoint]:
    invalid_quality_types = {
        "1.5.257",
        "1.5.259",
        "3.5.259",
        "3.7.3",
    }
    return [
        point
        for point in points or []
        if not any(quality in invalid_quality_types for quality in point.qualities)
    ]


def _sum(points: list[ReadingPoint] | None) -> Decimal | None:
    valid = _valid_points(points)
    if not valid:
        return None
    return sum((point.value for point in valid), Decimal("0"))


def _max(points: list[ReadingPoint] | None) -> Decimal | None:
    valid = _valid_points(points)
    if not valid:
        return None
    return max(point.value for point in valid)


def _max_values(values: tuple[Decimal | None, ...]) -> Decimal | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return max(present)


def _balance(consumption: Decimal | None, export: Decimal | None) -> Decimal | None:
    if consumption is not None and export is not None:
        return export - consumption
    return None


def _select_active_agreed_power(
    values: list[dict[str, Any]],
    current_day: date,
) -> dict[str, Any] | None:
    dated_matches: list[tuple[date, dict[str, Any]]] = []
    for value in values:
        if value.get("veljavnost") is not True:
            continue

        start_day = _parse_date(value.get("datumOd"))
        end_day = _parse_date(value.get("datumDo"))
        if start_day is None or end_day is None:
            continue

        if start_day <= current_day <= end_day:
            dated_matches.append((start_day, value))

    if dated_matches:
        dated_matches.sort(key=lambda item: item[0], reverse=True)
        return dated_matches[0][1]

    return next((value for value in values if value.get("veljavnost") is True), None)


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None

    raw = str(value).split("T", maxsplit=1)[0]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except InvalidOperation:
        return None
