# Agent Notes

This is a Home Assistant custom integration repository, not a standalone web app or generic service monorepo.

Default rules:

- keep the primary runtime under `custom_components/mojelektro_mini/`
- use Home Assistant config flow for user-provided settings
- create Home Assistant devices and sensors directly from the integration
- do not introduce an `app/` root
- use `../jurek` as the canonical external skill source when explicit workflow skills are needed
- avoid copying skill packages into this repository
- prefer small, direct docs over the full `../project-template` process model

Before changing integration behavior, check:

- `custom_components/mojelektro_mini/manifest.json`
- `custom_components/mojelektro_mini/config_flow.py`
- `custom_components/mojelektro_mini/api.py`
- `custom_components/mojelektro_mini/coordinator.py`
- `custom_components/mojelektro_mini/sensor.py`

The `mojelektro-mini/` add-on scaffold is secondary and should not drive device/sensor design unless the user explicitly asks for add-on-only behavior.
