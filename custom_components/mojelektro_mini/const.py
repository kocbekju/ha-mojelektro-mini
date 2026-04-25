from __future__ import annotations

from homeassistant.const import Platform


DOMAIN = "mojelektro_mini"
PLATFORMS = [Platform.SENSOR]

CONF_API_ENVIRONMENT = "api_environment"
CONF_EIMM = "eimm"
CONF_METERING_POINT_NAME = "metering_point_name"
CONF_OMTO_GSRN = "omto_gsrn"
CONF_ALLOWED_EXPORT_POWER = "allowed_export_power_kw"
CONF_INSTALLED_PRODUCTION_POWER = "installed_production_power_kw"
CONF_POLL_INTERVAL_MINUTES = "poll_interval_minutes"
CONF_USAGE_POINT = "usage_point"

DEFAULT_POLL_INTERVAL_MINUTES = 15

READING_TYPE_CONSUMPTION = "32.0.2.4.1.2.12.0.0.0.0.0.0.0.0.3.72.0"
READING_TYPE_EXPORT = "32.0.2.4.19.2.12.0.0.0.0.0.0.0.0.3.72.0"
READING_TYPE_MAX_IMPORT_POWER = "32.0.2.4.1.2.37.0.0.0.0.0.0.0.0.3.38.0"
READING_TYPE_MAX_EXPORT_POWER = "32.0.2.4.19.2.37.0.0.0.0.0.0.0.0.3.38.0"
