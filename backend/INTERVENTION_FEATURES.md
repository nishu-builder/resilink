# Intervention Features Documentation

This document describes the new intervention modeling and financial analysis features added to the hazard backend system.

## Overview

The intervention system allows you to:

- Model building-level interventions (e.g., elevation, flood vents)
- Group related runs for scenario comparison
- Calculate Expected Annual Loss (EAL) and ROI for interventions
- Track intervention costs and parameters
- Compare any two runs to analyze financial impact

## Setup

1. First, ensure the Docker containers are running:

   ```bash
   task up
   ```

2. Install/update dependencies and run migrations:
   ```bash
   task enter
   cd /app
   uv sync  # Updates dependencies including Alembic
   alembic upgrade head  # Apply database migrations
   python scripts/seed_interventions.py  # Seed intervention types
   ```

## Key Concepts

### Run Groups

Run Groups allow you to organize related scenarios for comparison. A typical workflow:

1. Create a Run Group (e.g., "Sacramento Flood Mitigation Study")
2. Add multiple runs to the group:
   - Baseline run (no interventions)
   - Various intervention scenarios
3. Compare any runs within the group

### Interventions

Interventions are modifications applied to buildings to reduce flood risk. Currently supported:

- Building elevation
- Flood vents (defined but not yet affecting analysis)
- Other types can be added

## API Endpoints

### Run Group Management

#### Create a run group

```bash
POST /runs/groups
{
  "name": "Sacramento Flood Study",
  "description": "Comparing various flood mitigation strategies"
}
```

#### List run groups

```bash
GET /runs/groups
```

### Run Management with Groups

#### Create a baseline run

```bash
POST /runs
{
  "name": "Baseline Analysis",
  "hazard_id": 1,
  "mapping_set_id": 1,
  "building_dataset_id": 1,
  "run_group_id": 1
}
```

#### Create an intervention run

```bash
POST /runs
{
  "name": "Building Elevation Scenario",
  "hazard_id": 1,
  "mapping_set_id": 1,
  "building_dataset_id": 1,
  "run_group_id": 1,
  "interventions": [
    {
      "building_id": "B001",
      "intervention_id": 1,
      "parameters": {"elevation_ft": 2.0},
      "cost": 80000
    },
    {
      "building_id": "B002",
      "intervention_id": 1,
      "parameters": {"elevation_ft": 3.0},
      "cost": 120000
    }
  ]
}
```

### Financial Analysis

#### Calculate Expected Annual Loss (EAL)

```bash
GET /financial/runs/{run_id}/eal
```

Response:

```json
{
  "total_eal": 125000.5,
  "building_eals": {
    "B001": 45000.0,
    "B002": 80000.5
  },
  "building_count": 2
}
```

#### Compare any two runs

```bash
POST /financial/compare-runs
{
  "run_id_1": 1,
  "run_id_2": 2
}
```

Response:

```json
{
  "run_1": {
    "id": 1,
    "eal": 500000.0,
    "intervention_cost": 0.0
  },
  "run_2": {
    "id": 2,
    "eal": 250000.0,
    "intervention_cost": 200000.0
  },
  "comparison": {
    "eal_reduction": 250000.0,
    "eal_reduction_percent": 50.0,
    "incremental_cost": 200000.0,
    "roi": 1.25,
    "payback_years": 0.8
  }
}
```

## Example Workflow

1. **Create a run group** for your analysis:

   ```bash
   curl -X POST http://localhost:8000/runs/groups \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Downtown Flood Study",
       "description": "Analyzing flood mitigation options for downtown area"
     }'
   ```

2. **Create a baseline run** in the group:

   ```bash
   curl -X POST http://localhost:8000/runs \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Current State",
       "hazard_id": 1,
       "mapping_set_id": 1,
       "building_dataset_id": 1,
       "run_group_id": 1
     }'
   ```

3. **Create intervention scenarios** in the same group:

   ```bash
   curl -X POST http://localhost:8000/runs \
     -H "Content-Type: application/json" \
     -d '{
       "name": "2ft Elevation Scenario",
       "hazard_id": 1,
       "mapping_set_id": 1,
       "building_dataset_id": 1,
       "run_group_id": 1,
       "interventions": [
         {
           "building_id": "B001",
           "intervention_id": 1,
           "parameters": {"elevation_ft": 2.0},
           "cost": 80000
         }
       ]
     }'
   ```

4. **Compare scenarios**:
   ```bash
   curl -X POST http://localhost:8000/financial/compare-runs \
     -H "Content-Type: application/json" \
     -d '{
       "run_id_1": 1,
       "run_id_2": 2
     }'
   ```

## Database Schema

### New Tables

- `run_groups`: Groups related runs for scenario comparison
- `interventions`: Stores intervention types
- `run_interventions`: Links interventions to specific runs and buildings

### Updated Tables

- `runs`: Added `run_group_id` field (removed `baseline_run_id` and `is_baseline`)

## Technical Details

### Alembic Migrations

The project now uses Alembic for database migrations:

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### How Interventions Work

1. When creating a run with interventions:

   - Intervention parameters are stored in the database
   - During analysis, elevation adjustments are applied to buildings
   - Damage probabilities are recalculated with modified elevations

2. Financial calculations:
   - Use damage state probabilities and predefined damage ratios
   - Calculate expected losses for each building
   - Compare any two runs to determine ROI and other metrics

### Current Limitations

- Building values are mocked (future: store in database)
- Only building elevation interventions affect the analysis
- Simple ROI calculation (future: NPV with discount rates)
- Hazard-level interventions are defined but not implemented

## Next Steps

1. Implement building value storage
2. Add support for additional intervention types
3. Implement hazard-level interventions
4. Add more sophisticated financial models (NPV, discount rates)
5. Create UI for intervention planning
