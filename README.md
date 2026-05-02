# Stanje net metering SLO

Home Assistant integration repository for Moj Elektro 15-minute readings and solar/grid balance sensors.

## Direction

The primary implementation is now a custom Home Assistant integration in [`custom_components/mojelektro_mini/`](./custom_components/mojelektro_mini/).

This is the right Home Assistant shape for the target workflow:

- add integration from the Home Assistant UI
- enter API token and metering identifiers in the config flow
- create a Home Assistant device for the metering point
- expose sensors directly in Home Assistant

The older [`mojelektro-mini/`](./mojelektro-mini/) add-on scaffold is kept for now, but it is no longer the preferred direction for sensors and devices.

## Current Integration Inputs

The Moj Elektro API documentation shows token authentication via `X-API-TOKEN`.

The config flow currently asks for:

- API environment: production or test
- API token
- metering place identifier `EIMM`

From that, the integration resolves:

- `usagePoint` / `GSRN MM`
- `OMTO GSRN`
- fixed Moj Elektro `ReadingType` values for:
  - grid consumption
  - grid export
  - max import power
  - max export power

The fetch interval is configurable later in Home Assistant via the integration `Configure` action.

For monthly and yearly saldo, the integration automatically splits API requests into chunks because Moj Elektro limits a single date interval request to 35 days.

## Target Sensors

Planned first sensors:

- daily grid consumption in kWh
- daily grid export in kWh
- daily balance in kWh
- today's grid consumption in kWh
- today's grid export in kWh
- today's balance in kWh
- month balance in kWh
- year balance in kWh
- max import power today in kW
- max export power today in kW
- agreed power blocks 1-5 in kW
- max agreed power in kW
- allowed export power in kW
- installed production power in kW

Balance rule:

```text
balance = exported_to_grid - imported_from_grid
```

With the example `imported=10 kWh`, `production=60 kWh`, `exported=45 kWh`, the daily balance is `35 kWh`.

For monthly and yearly saldo, the integration prefers Moj Elektro `24 h` state readings with reset handling so the result matches the portal more closely than a plain sum of `15-min` intervals.

Home Assistant records long-term statistics for the daily import, daily export, and daily balance sensors from the time the integration is installed.

## Visualization

The integration does not ship a custom frontend yet, but Home Assistant Lovelace is a good fit here.

Prepared dashboard examples:

- [`docs/lovelace-dashboard.yaml`](./docs/lovelace-dashboard.yaml)
- [`docs/visualization.md`](./docs/visualization.md)

## Template Alignment

This repository intentionally uses only a small subset of `../project-template`.

Carried over:

- practical `.gitignore` coverage for OS/editor noise, Python caches, logs, and build output
- a short `AGENTS.md` as the future agent entrypoint
- compact docs for project intent and architecture

Not carried over:

- `app/` split, because Home Assistant custom integrations live under `custom_components/`
- full process-first init flow, because this is a small Home Assistant integration repository
- repo-local skill copies, because `../jurek` remains the external source of truth
- beads, multi-agent orchestration, review history, and broad frontend docs until the project actually needs them
