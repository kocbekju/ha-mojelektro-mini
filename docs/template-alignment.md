# Template Alignment

## Transfer

Transferred from `../project-template`:

- `.gitignore` basics
- a compact agent entrypoint
- documentation habit for architecture and decisions

## Do Not Transfer Yet

Not transferred:

- `app/` root
- full initialization workflow
- `docs/arch/` process tree
- review history folders
- local skill copies
- beads/task-tracker requirements
- multi-agent orchestration defaults
- frontend design standards

## Reason

Home Assistant custom integrations have a specific repository shape. A generic standalone app template would make the project harder to install in Home Assistant and would blur the source of truth for integration files.
