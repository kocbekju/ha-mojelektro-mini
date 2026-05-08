from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PRODUCTION_URL, TEST_URL, MojelektroApiError, MojelektroClient
from .const import (
    CONF_ALLOWED_EXPORT_POWER,
    CONF_API_ENVIRONMENT,
    CONF_EIMM,
    CONF_INSTALLED_PRODUCTION_POWER,
    CONF_METERING_POINT_NAME,
    CONF_OMTO_GSRN,
    CONF_POLL_INTERVAL_MINUTES,
    CONF_USAGE_POINT,
    DEFAULT_POLL_INTERVAL_MINUTES,
    DOMAIN,
)


class MojelektroConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api_token = user_input[CONF_API_TOKEN]
            eimm = user_input[CONF_EIMM]
            base_url = TEST_URL if user_input[CONF_API_ENVIRONMENT] == "test" else PRODUCTION_URL

            client = MojelektroClient(async_get_clientsession(self.hass), api_token, base_url)
            try:
                merilno_mesto = await client.async_get_merilno_mesto(eimm)
            except MojelektroApiError:
                errors["base"] = "cannot_connect"
            else:
                identifikator = merilno_mesto.get("identifikator") or {}
                usage_point = identifikator.get("gsrn")
                omto_gsrn = next(
                    (
                        merilna_tocka.get("gsrn")
                        for merilna_tocka in merilno_mesto.get("merilneTocke") or []
                        if merilna_tocka.get("vrsta") == "OMTO"
                    ),
                    None,
                )
                pogodbeni_podatki = merilno_mesto.get("pogodbeniPodatki") or {}

                if not usage_point or not omto_gsrn:
                    errors["base"] = "cannot_resolve_metering_point"
                else:
                    await self.async_set_unique_id(usage_point)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=str(merilno_mesto.get("naziv") or f"Mojelektro {eimm}"),
                        data={
                            CONF_API_ENVIRONMENT: user_input[CONF_API_ENVIRONMENT],
                            CONF_API_TOKEN: api_token,
                            CONF_EIMM: eimm,
                            CONF_USAGE_POINT: str(usage_point),
                            CONF_OMTO_GSRN: str(omto_gsrn),
                            CONF_METERING_POINT_NAME: str(merilno_mesto.get("naziv") or eimm),
                            CONF_ALLOWED_EXPORT_POWER: pogodbeni_podatki.get("dovoljenaMocOddaje"),
                            CONF_INSTALLED_PRODUCTION_POWER: pogodbeni_podatki.get("instaliranaMocProizvodnje"),
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_form_schema(user_input),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return MojelektroOptionsFlow(config_entry)


class MojelektroOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL_MINUTES,
                        default=self._config_entry.options.get(
                            CONF_POLL_INTERVAL_MINUTES,
                            DEFAULT_POLL_INTERVAL_MINUTES,
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
                }
            ),
        )


def _form_schema(user_input: dict[str, Any] | None) -> vol.Schema:
    defaults = user_input or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_API_ENVIRONMENT,
                default=defaults.get(CONF_API_ENVIRONMENT, "production"),
            ): vol.In(
                {
                    "production": "Production",
                    "test": "Test",
                }
            ),
            vol.Required(CONF_API_TOKEN, default=defaults.get(CONF_API_TOKEN, "")): str,
            vol.Required(CONF_EIMM, default=defaults.get(CONF_EIMM, "")): str,
        }
    )
