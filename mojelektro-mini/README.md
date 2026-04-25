# Mojelektro Mini

Minimal Home Assistant add-on shell for Mojelektro data.

## Current Status

This add-on is installable and starts a small HTTP service exposed through Home Assistant Ingress.

It does not yet fetch Mojelektro data. The next implementation step is to add the real Mojelektro client and decide how entities should be published into Home Assistant.

## Options

| Option | Description |
| --- | --- |
| `mojelektro_username` | Mojelektro username. |
| `mojelektro_password` | Mojelektro password. |
| `poll_interval_minutes` | Planned polling interval. |
| `log_level` | Add-on log level. |
