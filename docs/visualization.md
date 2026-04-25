# Visualization

The most practical visualization path for this integration is a Lovelace dashboard.

Use [`lovelace-dashboard.yaml`](./lovelace-dashboard.yaml) as a starting point.

## Notes

- Entity IDs in the example are placeholders. Replace them with the actual entity IDs created by Home Assistant.
- The gauge limit `14` is only an example based on your current allowed export range. Adjust it if needed.
- `history-graph` works best for values that change over time and are written into recorder history.
- `statistics-graph` is useful for comparing daily import/export sums.

## Recommended layout

- One summary card for daily, monthly, and yearly saldo
- One graph for import vs export
- One power graph or gauge for grid power peaks
- One limits card for agreed power blocks and allowed export power
