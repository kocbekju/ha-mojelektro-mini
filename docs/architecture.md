# Architecture

## Shape

This repository is a Home Assistant custom integration repository.

```text
.
├── custom_components/mojelektro_mini/
│   ├── manifest.json
│   ├── config_flow.py
│   ├── api.py
│   ├── coordinator.py
│   └── sensor.py
├── mojelektro-mini/
│   └── legacy add-on scaffold
└── docs/
```

## Runtime

Home Assistant loads the integration from `custom_components/mojelektro_mini`.

The integration uses:

- config flow for API token and `EIMM`
- options flow for fetch interval
- Home Assistant `DataUpdateCoordinator` with a 15-minute polling interval
- sensor platform for energy and power values

## Boundaries

Moj Elektro API:

- production: `https://api.informatika.si/mojelektro/v1`
- test: `https://api-test.informatika.si/mojelektro/v1`
- authentication: `X-API-TOKEN`

Current API calls:

- `GET /merilno-mesto/{identifikator}` during setup validation
- `GET /meter-readings` during coordinator refresh
- `GET /merilna-tocka/{gsrn}` for agreed power and related contract data

## Discovery Rules

The current integration uses fixed Moj Elektro reading types discovered from the live API:

- `A+` for grid consumption
- `A-` for grid export
- `P+` for import power
- `P-` for export power

The integration resolves `usagePoint` and `OMTO GSRN` automatically from `EIMM`.

## Saldo

There are two useful balances:

- self-consumption surplus balance: `production - export - import`
- net grid balance: `export - import`

The user's example says `import=10`, `production=60`, `export=45`, expected saldo `35`. That matches net grid balance, not production-minus-export-minus-import.

The integration currently exposes the net grid balance for daily/monthly/yearly saldo.

## Visualization

Visualization is expected to live in Home Assistant Lovelace, not inside a custom frontend bundled with the integration.

See:

- [`visualization.md`](./visualization.md)
- [`lovelace-dashboard.yaml`](./lovelace-dashboard.yaml)
