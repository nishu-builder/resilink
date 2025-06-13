# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

All development tasks are managed through Task (Taskfile.yml):

### Docker Operations
- `task up` - Start all services (postgres, backend, frontend, nginx)
- `task build` - Build Docker images
- `task stop` - Stop all containers

### Backend Development
- `task lint` - Format Python code with black and ruff
- `task typecheck` - Run pyright type checker
- `task shell` - Open IPython shell in backend container
- `task enter` - Open bash shell in backend container
- `task add_req` - Add Python dependency with uv (e.g., `task add_req requests`)

### Database Operations
- `task psql` - Open PostgreSQL shell
- `task seed` - Seed database with initial data from `/app/seed_data`
- `task migrate:upgrade` - Apply database migrations
- `task migrate:create -- "migration name"` - Create new migration
- `task migrate:downgrade` - Rollback last migration

### Frontend Development
- `npm run dev` - Run frontend development server (inside container)
- `npm run type-check` - TypeScript type checking
- `npm run lint` - Run Next.js linter

## Architecture Overview

### System Design
This is a flood risk analysis platform with three main components:

1. **Backend API (FastAPI)** - `/backend`
   - Processes geospatial hazard data (water surface elevation rasters)
   - Calculates damage probabilities using fragility curves
   - Stores hazards, building datasets, fragility curves, and analysis results
   - PostgreSQL with PostGIS for spatial data

2. **Frontend UI (Next.js)** - `/frontend`
   - Portfolio management and building dataset visualization
   - Analysis run configuration and monitoring
   - Results visualization with maps and charts
   - Uses shadcn/ui components with Tailwind CSS

3. **Infrastructure**
   - Docker Compose orchestration with hot reloading
   - Nginx reverse proxy routing `/api` to backend, `/` to frontend
   - Database migrations with Alembic

### Core Analysis Pipeline
1. Upload water surface elevation (WSE) raster files (TIF format)
2. Import building datasets (shapefiles in ZIP format)
3. Load fragility curves (DFR3 JSON format) and mapping sets
4. Run analysis:
   - Extract building locations from shapefiles
   - Sample WSE values at building coordinates
   - Map buildings to fragility curves based on attributes
   - Calculate damage state probabilities (DS0-DS3) using lognormal CDFs
   - Generate GeoJSON results with probabilities and flood depths

### Key API Endpoints
- `/api/hazards` - Manage hazard datasets
- `/api/building-datasets` - Upload and manage building data
- `/api/fragility-curves` - Manage fragility curve definitions
- `/api/mapping-sets` - Configure building-to-fragility mappings
- `/api/runs` - Execute and monitor analysis runs
- `/api/financial` - Financial analysis endpoints (in development)
- `/api/interventions` - Intervention modeling (in development)

### Data Models
- **Hazard**: Stores WSE raster data paths and metadata
- **BuildingDataset**: Shapefile data with building locations/attributes
- **FragilityCurve**: JSON-based damage probability curves
- **MappingSet**: Rules for mapping buildings to fragility curves
- **Run**: Analysis execution tracking with status and results

### Development Notes
- Backend uses SQLModel (SQLAlchemy + Pydantic) for database models
- Frontend uses SWR for data fetching and Zustand for state management
- All file uploads go to `/app/data/` inside containers
- Environment variables are in `.env` (copy from `.env.example`)
- Database migrations must be created in the container then synced back