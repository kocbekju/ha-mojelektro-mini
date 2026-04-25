from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from aiohttp import ClientError, ClientSession


PRODUCTION_URL = "https://api.informatika.si/mojelektro/v1"
TEST_URL = "https://api-test.informatika.si/mojelektro/v1"


class MojelektroApiError(Exception):
    """Raised when the Mojelektro API request fails."""


@dataclass(frozen=True)
class ReadingPoint:
    timestamp: str
    value: Decimal
    qualities: tuple[str, ...]


class MojelektroClient:
    def __init__(self, session: ClientSession, api_token: str, base_url: str = PRODUCTION_URL) -> None:
        self._session = session
        self._api_token = api_token
        self._base_url = base_url.rstrip("/")

    async def async_get_reading_types(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/reading-type")

    async def async_get_merilno_mesto(self, identifikator: str) -> dict[str, Any]:
        return await self._request("GET", f"/merilno-mesto/{identifikator}")

    async def async_get_merilna_tocka(self, gsrn: str) -> dict[str, Any]:
        return await self._request("GET", f"/merilna-tocka/{gsrn}")

    async def async_get_meter_readings(
        self,
        usage_point: str,
        start: date,
        end: date,
        reading_types: list[str],
    ) -> dict[str, list[ReadingPoint]]:
        params: list[tuple[str, str]] = [
            ("usagePoint", usage_point),
            ("startTime", start.isoformat()),
            ("endTime", end.isoformat()),
        ]
        for reading_type in reading_types:
            if reading_type:
                params.append(("option", f"ReadingType={reading_type}"))

        payload = await self._request("GET", "/meter-readings", params=params)
        blocks = payload.get("intervalBlocks") or []
        readings: dict[str, list[ReadingPoint]] = {}

        for block in blocks:
            reading_type = block.get("readingType")
            if not reading_type:
                continue

            points: list[ReadingPoint] = []
            for item in block.get("intervalReadings") or []:
                value = _parse_decimal(item.get("value"))
                if value is None:
                    continue

                qualities = tuple(
                    quality.get("readingQualityType")
                    for quality in item.get("readingQualities") or []
                    if quality.get("readingQualityType")
                )
                points.append(
                    ReadingPoint(
                        timestamp=str(item.get("timestamp", "")),
                        value=value,
                        qualities=qualities,
                    )
                )

            readings[str(reading_type)] = points

        return readings

    async def _request(
        self,
        method: str,
        path: str,
        params: list[tuple[str, str]] | None = None,
    ) -> Any:
        headers = {"X-API-TOKEN": self._api_token}
        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                params=params,
                timeout=30,
            ) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise MojelektroApiError(f"Mojelektro API returned {response.status}: {text}")
                return await response.json()
        except ClientError as err:
            raise MojelektroApiError(f"Mojelektro API request failed: {err}") from err


def _parse_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None

    try:
        return Decimal(str(value).replace(",", "."))
    except InvalidOperation:
        return None
