from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
import logging
from typing import Any

from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics, get_last_statistics
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

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
    READING_TYPE_STATE_CONSUMPTION,
    READING_TYPE_STATE_EXPORT,
)


LOGGER = logging.getLogger(__name__)
MAX_API_INTERVAL_DAYS = 35


@dataclass(frozen=True)
class MojelektroData:
    daily_import_kwh: Decimal | None
    daily_export_kwh: Decimal | None
    daily_balance_kwh: Decimal | None
    today_consumption_kwh: Decimal | None
    today_export_kwh: Decimal | None
    today_balance_kwh: Decimal | None
    month_import_kwh: Decimal | None
    month_export_kwh: Decimal | None
    month_balance_kwh: Decimal | None
    year_import_kwh: Decimal | None
    year_export_kwh: Decimal | None
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


@dataclass(frozen=True)
class HistoryData:
    daily_import_series: dict[date, Decimal]
    daily_export_series: dict[date, Decimal]
    daily_balance_series: dict[date, Decimal]
    month_import_kwh: Decimal | None
    month_export_kwh: Decimal | None
    month_balance_kwh: Decimal | None
    year_import_kwh: Decimal | None
    year_export_kwh: Decimal | None
    year_balance_kwh: Decimal | None


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
        self._daily_series: dict[str, dict[date, Decimal]] = {}
        self._daily_stat_entities: dict[str, tuple[str, str]] = {}
        self._history_cache_day: date | None = None
        self._history_cache: HistoryData | None = None
        self._agreed_power_cache_day: date | None = None
        self._agreed_power_cache: tuple[
            Decimal | None,
            Decimal | None,
            Decimal | None,
            Decimal | None,
            Decimal | None,
        ] | None = None

    async def _async_update_data(self) -> MojelektroData:
        today = date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        today_reading_types = [
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
                today_reading_types,
            )
            history = await self._async_get_history_data(today, month_start, year_start)
            agreed_power = await self._async_get_agreed_power_cached(today)
        except MojelektroApiError as err:
            raise UpdateFailed(str(err)) from err

        today_consumption = _sum(today_readings.get(READING_TYPE_CONSUMPTION))
        today_export = _sum(today_readings.get(READING_TYPE_EXPORT))
        self._daily_series = {
            "daily_import_kwh": history.daily_import_series,
            "daily_export_kwh": history.daily_export_series,
            "daily_balance_kwh": history.daily_balance_series,
        }
        await self._async_import_missing_daily_statistics()
        latest_completed_day = _latest_completed_day(today)

        return MojelektroData(
            daily_import_kwh=history.daily_import_series.get(latest_completed_day),
            daily_export_kwh=history.daily_export_series.get(latest_completed_day),
            daily_balance_kwh=history.daily_balance_series.get(latest_completed_day),
            today_consumption_kwh=today_consumption,
            today_export_kwh=today_export,
            today_balance_kwh=_balance(today_consumption, today_export),
            month_import_kwh=history.month_import_kwh,
            month_export_kwh=history.month_export_kwh,
            month_balance_kwh=history.month_balance_kwh,
            year_import_kwh=history.year_import_kwh,
            year_export_kwh=history.year_export_kwh,
            year_balance_kwh=history.year_balance_kwh,
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

    async def _async_get_history_data(
        self,
        today: date,
        month_start: date,
        year_start: date,
    ) -> HistoryData:
        if self._history_cache_day == today and self._history_cache is not None:
            return self._history_cache

        year_state_readings = await self._async_get_meter_readings_chunked(
            self.entry.data[CONF_USAGE_POINT],
            year_start,
            today,
            [
                READING_TYPE_STATE_CONSUMPTION,
                READING_TYPE_STATE_EXPORT,
            ],
        )
        daily_import_series = _daily_totals_from_state(
            year_state_readings.get(READING_TYPE_STATE_CONSUMPTION)
        )
        daily_export_series = _daily_totals_from_state(
            year_state_readings.get(READING_TYPE_STATE_EXPORT)
        )
        daily_balance_series = _daily_balance_series(daily_import_series, daily_export_series)
        month_import = _sum_series_from(daily_import_series, month_start)
        month_export = _sum_series_from(daily_export_series, month_start)
        year_import = _sum_series_from(daily_import_series, year_start)
        year_export = _sum_series_from(daily_export_series, year_start)
        history = HistoryData(
            daily_import_series=daily_import_series,
            daily_export_series=daily_export_series,
            daily_balance_series=daily_balance_series,
            month_import_kwh=month_import,
            month_export_kwh=month_export,
            month_balance_kwh=_balance(month_import, month_export),
            year_import_kwh=year_import,
            year_export_kwh=year_export,
            year_balance_kwh=_balance(year_import, year_export),
        )
        self._history_cache_day = today
        self._history_cache = history
        return history

    async def _async_get_agreed_power_cached(
        self,
        today: date,
    ) -> tuple[
        Decimal | None,
        Decimal | None,
        Decimal | None,
        Decimal | None,
        Decimal | None,
    ]:
        if self._agreed_power_cache_day == today and self._agreed_power_cache is not None:
            return self._agreed_power_cache

        agreed_power = await self._async_get_agreed_power()
        self._agreed_power_cache_day = today
        self._agreed_power_cache = agreed_power
        return agreed_power

    @property
    def daily_series(self) -> dict[str, dict[date, Decimal]]:
        return self._daily_series

    async def async_register_daily_statistic_entity(
        self,
        key: str,
        entity_id: str,
        name: str,
    ) -> None:
        self._daily_stat_entities[key] = (entity_id, name)
        await self._async_import_missing_daily_statistics()

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

    async def _async_get_meter_readings_chunked(
        self,
        usage_point: str,
        start: date,
        end: date,
        reading_types: list[str],
    ) -> dict[str, list[ReadingPoint]]:
        merged: dict[str, list[ReadingPoint]] = {}

        for chunk_start, chunk_end in _iter_date_chunks(start, end, MAX_API_INTERVAL_DAYS):
            payload = await self.client.async_get_meter_readings(
                usage_point,
                chunk_start,
                chunk_end,
                reading_types,
            )
            for reading_type, points in payload.items():
                merged.setdefault(reading_type, []).extend(points)

        return merged

    async def _async_import_missing_daily_statistics(self) -> None:
        if not self._daily_series or not self._daily_stat_entities:
            return

        for key, series in self._daily_series.items():
            entity_meta = self._daily_stat_entities.get(key)
            if entity_meta is None or not series:
                continue

            entity_id, name = entity_meta
            imported_from = await self.hass.async_add_executor_job(
                _last_imported_day,
                self.hass,
                entity_id,
            )
            statistics: list[StatisticData] = []

            for day in sorted(series):
                if imported_from is not None and day <= imported_from:
                    continue
                statistics.append(
                    {
                        "start": _day_start_local(day),
                        "state": float(series[day]),
                    }
                )

            if not statistics:
                continue

            metadata: StatisticMetaData = {
                "has_sum": False,
                "mean_type": StatisticMeanType.NONE,
                "name": name,
                "source": "recorder",
                "statistic_id": entity_id,
                "unit_class": None,
                "unit_of_measurement": "kWh",
            }
            async_import_statistics(self.hass, metadata, statistics)


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


def _total_from_state(points: list[ReadingPoint] | None) -> Decimal | None:
    valid = sorted(_valid_points(points), key=lambda point: point.timestamp)
    if len(valid) < 2:
        return None

    total = Decimal("0")
    previous = valid[0].value

    for point in valid[1:]:
        if point.value >= previous:
            total += point.value - previous
        else:
            total += point.value
        previous = point.value

    return total


def _daily_totals_from_state(points: list[ReadingPoint] | None) -> dict[date, Decimal]:
    valid = sorted(_valid_points(points), key=lambda point: point.timestamp)
    if len(valid) < 2:
        return {}

    totals: dict[date, Decimal] = {}
    previous = valid[0].value

    for point in valid[1:]:
        if point.value >= previous:
            delta = point.value - previous
        else:
            delta = point.value

        day = _bucket_day(point.timestamp)
        totals[day] = totals.get(day, Decimal("0")) + delta
        previous = point.value

    return totals


def _daily_balance_series(
    import_series: dict[date, Decimal],
    export_series: dict[date, Decimal],
) -> dict[date, Decimal]:
    days = set(import_series) | set(export_series)
    return {
        day: export_series.get(day, Decimal("0")) - import_series.get(day, Decimal("0"))
        for day in days
    }


def _sum_series_from(series: dict[date, Decimal], start_day: date) -> Decimal | None:
    values = [value for day, value in series.items() if day >= start_day]
    if not values:
        return None
    return sum(values, Decimal("0"))


def _iter_date_chunks(
    start: date,
    end: date,
    max_days: int,
) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    current = start
    max_span = timedelta(days=max_days - 1)

    while current <= end:
        chunk_end = min(current + max_span, end)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)

    return chunks


def _bucket_day(timestamp: str) -> date:
    moment = datetime.fromisoformat(timestamp)
    local_day = moment.date()
    if moment.timetz().replace(tzinfo=None) == time.min:
        return local_day - timedelta(days=1)
    return local_day


def _latest_completed_day(today: date) -> date:
    return today - timedelta(days=1)


def _day_start_local(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=dt_util.DEFAULT_TIME_ZONE)


def _last_imported_day(hass: HomeAssistant, statistic_id: str) -> date | None:
    rows = get_last_statistics(hass, 1, statistic_id, False, {"state"}).get(statistic_id)
    if not rows:
        return None

    start = rows[0].get("start")
    if isinstance(start, datetime):
        return start.date()
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
