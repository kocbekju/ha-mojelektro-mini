# Moj Elektro API Notes

Source: https://docs.informatika.si/mojelektro/api/

The Swagger UI loads `mojelektro-openapi.yaml`.

## Servers

- test: `https://api-test.informatika.si/mojelektro/v1`
- production: `https://api.informatika.si/mojelektro/v1`

## Authentication

All API calls use an API key header:

```http
X-API-TOKEN: <token>
```

The OpenAPI spec does not describe username/password login.

## Relevant Endpoints

### `GET /reading-type`

Returns available reading type definitions.

For the current integration, the live API was used to confirm these fixed mappings:

- `A+` grid consumption energy
- `A-` grid export energy
- `P+` import power
- `P-` export power

### `GET /reading-qualities`

Returns reading quality/status definitions. If a reading has no qualities, the OpenAPI description says the reading is considered valid.

### `GET /meter-readings`

Returns 15-minute readings and daily states.

Query parameters:

- `usagePoint`
- `startTime` as `YYYY-MM-DD`
- `endTime` as `YYYY-MM-DD`
- repeated `option`, for example `ReadingType=...`

Response shape:

- `usagePoint`
- `messageCreated`
- `intervalBlocks[]`
  - `readingType`
  - `intervalReadings[]`
    - `timestamp`
    - `value`
    - `readingQualities[]`

### `GET /merilno-mesto/{identifikator}`

Returns metering place details.

### `GET /merilna-tocka/{gsrn}`

Returns metering point contract data, including agreed power values when present.

## Integration Inputs

Known required inputs:

- API token
- metering place identifier `EIMM`

Resolved automatically during setup:

- `usagePoint` / `GSRN MM`
- `OMTO GSRN`
- fixed ReadingType mappings
