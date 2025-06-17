# Hazard Analysis Platform

## Quick Start

```bash
# Install task if you do not have it
brew install go-task

# Start all services
task up

# Seed database with initial data
task seed
```

## Common Commands

```bash
task stop           # Stop all containers
task psql           # Open PostgreSQL shell
task shell          # Open Python shell in backend
task lint           # Format backend code
task migrate:upgrade # Apply database migrations
```

## Development

- Backend API: http://localhost:8000/api
- Frontend UI: http://localhost:3000
- All commands managed through `task` (see Taskfile.yml)
