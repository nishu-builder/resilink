# Implementation Plan: Intervention Modeling & UI Integration

## Overview

This plan outlines the implementation of building elevation interventions, financial analysis capabilities, and integration of the flood-risk-app UI with the hazard backend system.

## Phase 1: Backend - Intervention Modeling

### 1.1 Database Schema Updates

```sql
-- New tables to add
CREATE TABLE interventions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    name VARCHAR(255),
    type VARCHAR(50), -- 'building_elevation', 'hazard_modification' (future)
    description TEXT
);

CREATE TABLE run_interventions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    run_id INTEGER REFERENCES runs(id),
    building_id VARCHAR(255), -- guid from the shapefile
    intervention_id INTEGER REFERENCES interventions(id),
    parameters JSONB, -- {"elevation_ft": 2.0} for building elevation
    cost DECIMAL(12,2)
);

-- Extend runs table
ALTER TABLE runs ADD COLUMN baseline_run_id INTEGER REFERENCES runs(id);
ALTER TABLE runs ADD COLUMN is_baseline BOOLEAN DEFAULT true;
```

### 1.2 Model Updates

```python
# backend/app/models.py - Add new models

class Intervention(Base, table=True):
    __tablename__ = "interventions"

    name: str = Field(index=True)
    type: str  # 'building_elevation', 'hazard_modification'
    description: Optional[str] = None

    run_interventions: list["RunIntervention"] = Relationship(back_populates="intervention")

class RunIntervention(Base, table=True):
    __tablename__ = "run_interventions"

    run_id: int = Field(foreign_key="runs.id")
    building_id: str  # Building GUID
    intervention_id: int = Field(foreign_key="interventions.id")
    parameters: dict = Field(default={}, sa_column=Column(JSON))
    cost: Optional[float] = None

    run: Optional[Run] = Relationship(back_populates="interventions")
    intervention: Optional[Intervention] = Relationship(back_populates="run_interventions")

# Update Run model
class Run(Base, table=True):
    # ... existing fields ...
    baseline_run_id: Optional[int] = Field(default=None, foreign_key="runs.id")
    is_baseline: bool = Field(default=True)

    interventions: list[RunIntervention] = Relationship(back_populates="run")
    baseline_run: Optional["Run"] = Relationship(
        sa_relationship_kwargs={"remote_side": "Run.id"}
    )
```

### 1.3 Analysis Service Updates

```python
# backend/app/services/analysis.py - Modify perform_analysis

@with_async_session
async def perform_analysis(run_id: int, M_OFFSET: float = 0.0) -> None:
    """Execute full damage-analysis workflow for a Run row with intervention support."""
    session = get_current_session()

    # ... existing code to fetch run and validate ...

    # NEW: Fetch interventions for this run
    interventions_result = await session.execute(
        select(RunIntervention)
        .where(RunIntervention.run_id == run_id)
        .options(selectinload(RunIntervention.intervention))
    )
    run_interventions = interventions_result.scalars().all()

    # Build a map of building_id -> elevation adjustment
    elevation_adjustments = {}
    for ri in run_interventions:
        if ri.intervention.type == 'building_elevation':
            elevation_ft = ri.parameters.get('elevation_ft', 0)
            elevation_adjustments[ri.building_id] = elevation_ft

    # ... existing code to load data ...

    # Modify the building processing loop
    features = []
    for _, b in buildings_gdf.iterrows():
        try:
            guid = b.get('guid') or b.get('id') or _
            # ... existing validation ...

            # NEW: Apply elevation intervention if exists
            elevation_adjustment = elevation_adjustments.get(str(guid), 0)
            ffe_ft = float(b['ffe_elev']) if 'ffe_elev' in b else None
            if ffe_ft is not None:
                ffe_ft += elevation_adjustment  # Add intervention elevation

            # ... rest of existing calculation ...

            features.append({
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": {
                    # ... existing properties ...
                    "elevation_adjustment": elevation_adjustment,  # NEW
                    "original_ffe_m": (float(b['ffe_elev']) * FT_TO_M) if 'ffe_elev' in b else None,  # NEW
                }
            })
```

## Phase 2: Backend - Financial Analysis

### 2.1 Financial Calculation Service

```python
# backend/app/services/financial.py - New file

from typing import Dict, List, Optional
import json
from pathlib import Path

# Damage ratios by damage state (simplified - should come from configuration)
DAMAGE_RATIOS = {
    "DS0": 0.0,    # No damage
    "DS1": 0.02,   # Slight damage - 2% of building value
    "DS2": 0.10,   # Moderate damage - 10% of building value
    "DS3": 0.50,   # Substantial damage - 50% of building value
}

async def calculate_eal(run_id: int, building_values: Dict[str, float]) -> Dict[str, any]:
    """Calculate Expected Annual Loss for a run."""
    results_path = Path(f"/data/results_{run_id}.geojson")

    with open(results_path) as f:
        results = json.load(f)

    total_eal = 0
    building_eals = {}

    for feature in results['features']:
        props = feature['properties']
        building_id = props.get('guid', props.get('arch_flood'))

        # Get probabilities
        p_ds0 = props.get('P_DS0', 0)
        p_ds1 = props.get('P_DS1', 0)
        p_ds2 = props.get('P_DS2', 0)
        p_ds3 = props.get('P_DS3', 0)

        # Get building value (would come from database in real implementation)
        building_value = building_values.get(str(building_id), 1_000_000)  # Default $1M

        # Calculate EAL for this building
        building_eal = (
            p_ds0 * DAMAGE_RATIOS['DS0'] * building_value +
            p_ds1 * DAMAGE_RATIOS['DS1'] * building_value +
            p_ds2 * DAMAGE_RATIOS['DS2'] * building_value +
            p_ds3 * DAMAGE_RATIOS['DS3'] * building_value
        )

        building_eals[building_id] = building_eal
        total_eal += building_eal

    return {
        "total_eal": total_eal,
        "building_eals": building_eals
    }

async def calculate_intervention_roi(
    baseline_run_id: int,
    intervention_run_id: int,
    building_values: Dict[str, float],
    intervention_costs: float
) -> Dict[str, float]:
    """Calculate ROI for interventions."""

    baseline_eal = await calculate_eal(baseline_run_id, building_values)
    intervention_eal = await calculate_eal(intervention_run_id, building_values)

    eal_reduction = baseline_eal['total_eal'] - intervention_eal['total_eal']

    # Simple ROI calculation (annual benefit / one-time cost)
    # In reality, would use NPV with discount rate
    roi = eal_reduction / intervention_costs if intervention_costs > 0 else 0

    return {
        "baseline_eal": baseline_eal['total_eal'],
        "intervention_eal": intervention_eal['total_eal'],
        "eal_reduction": eal_reduction,
        "eal_reduction_percent": (eal_reduction / baseline_eal['total_eal'] * 100) if baseline_eal['total_eal'] > 0 else 0,
        "intervention_cost": intervention_costs,
        "roi": roi,
        "payback_years": intervention_costs / eal_reduction if eal_reduction > 0 else float('inf')
    }
```

### 2.2 Financial API Endpoints

```python
# backend/app/api/financial.py - New file

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from app.db import get_async_session
from app.services.financial import calculate_eal, calculate_intervention_roi

router = APIRouter(prefix="/financial", tags=["Financial Analysis"])

@router.get("/runs/{run_id}/eal")
async def get_run_eal(
    run_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Calculate Expected Annual Loss for a run."""
    # TODO: Get actual building values from database
    # For now, use mock values
    building_values = {f"B{i:03d}": 1_000_000 + i * 100_000 for i in range(1, 20)}

    eal_results = await calculate_eal(run_id, building_values)
    return eal_results

@router.post("/compare-runs")
async def compare_runs(
    baseline_run_id: int,
    intervention_run_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Compare financial metrics between baseline and intervention runs."""
    # Get intervention costs
    result = await session.execute(
        select(RunIntervention).where(RunIntervention.run_id == intervention_run_id)
    )
    interventions = result.scalars().all()
    total_cost = sum(i.cost or 0 for i in interventions)

    # Mock building values
    building_values = {f"B{i:03d}": 1_000_000 + i * 100_000 for i in range(1, 20)}

    roi_results = await calculate_intervention_roi(
        baseline_run_id,
        intervention_run_id,
        building_values,
        total_cost
    )

    return roi_results
```

## Phase 3: API Updates for Intervention Support

### 3.1 Intervention Management Endpoints

```python
# backend/app/api/interventions.py - New file

from fastapi import APIRouter, Depends
from typing import List
from pydantic import BaseModel
from app.db import get_async_session
from app.models import Intervention, RunIntervention

router = APIRouter(prefix="/interventions", tags=["Interventions"])

class InterventionCreate(BaseModel):
    name: str
    type: str
    description: Optional[str] = None

class RunInterventionCreate(BaseModel):
    building_id: str
    intervention_id: int
    parameters: dict
    cost: Optional[float] = None

@router.post("/", response_model=Intervention)
async def create_intervention(
    intervention: InterventionCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new intervention type."""
    db_intervention = Intervention(**intervention.dict())
    session.add(db_intervention)
    await session.commit()
    await session.refresh(db_intervention)
    return db_intervention

@router.get("/", response_model=List[Intervention])
async def list_interventions(
    session: AsyncSession = Depends(get_async_session)
):
    """List all available intervention types."""
    result = await session.execute(select(Intervention))
    return result.scalars().all()

@router.post("/runs/{run_id}/interventions", response_model=RunIntervention)
async def add_run_intervention(
    run_id: int,
    intervention: RunInterventionCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Add an intervention to a run."""
    db_intervention = RunIntervention(
        run_id=run_id,
        **intervention.dict()
    )
    session.add(db_intervention)
    await session.commit()
    await session.refresh(db_intervention)
    return db_intervention
```

### 3.2 Updated Run Creation

```python
# backend/app/api/runs.py - Update existing file

class CreateRunRequest(BaseModel):
    name: str
    hazard_id: int
    mapping_set_id: int
    building_dataset_id: int
    baseline_run_id: Optional[int] = None  # NEW
    interventions: Optional[List[RunInterventionCreate]] = None  # NEW

@router.post("/", response_model=Run)
async def create_run(
    request: CreateRunRequest,
    *,
    session: AsyncSession = Depends(get_async_session),
):
    # ... existing validation ...

    run = Run(
        name=request.name,
        hazard_id=hazard.id,
        mapping_set_id=mapping_set.id,
        building_dataset_id=building_dataset.id,
        baseline_run_id=request.baseline_run_id,  # NEW
        is_baseline=(request.baseline_run_id is None),  # NEW
        status="QUEUED",
    )
    session.add(run)
    await session.commit()

    # NEW: Add interventions if provided
    if request.interventions:
        for intervention_data in request.interventions:
            run_intervention = RunIntervention(
                run_id=run.id,
                **intervention_data.dict()
            )
            session.add(run_intervention)
        await session.commit()

    await session.refresh(run)
    await perform_analysis(run.id)
    await session.refresh(run)
    return run
```

## Phase 4: Frontend Integration: Update hazard frontend with flood-risk-app styling

#### 4.1 Copy UI components and styles

```bash
# Copy the entire flood-risk-app UI system to hazard frontend
cp -r flood-risk-app/components hazard/frontend/components
cp -r flood-risk-app/app/globals.css hazard/frontend/app/
cp -r flood-risk-app/styles hazard/frontend/
cp flood-risk-app/tailwind.config.js hazard/frontend/
cp flood-risk-app/components.json hazard/frontend/
```

#### 4.2 Update hazard frontend to use new components

```typescript
// hazard/frontend/app/analysis/page.tsx - New file

import { useState } from "react";
import { StepIndicator } from "@/components/step-indicator";
import { BuildingSelection } from "@/components/building-selection";
import { ApplyMitigation } from "@/components/apply-mitigation";
import { ResultsOutput } from "@/components/results-output";

export default function AnalysisPage() {
  // Reuse the flood-risk-app workflow but connect to hazard backend
  const [currentStep, setCurrentStep] = useState(1);

  const steps = [
    { id: 1, title: "Select Dataset", icon: Building },
    { id: 2, title: "Apply Interventions", icon: Shield },
    { id: 3, title: "View Results", icon: FileText },
  ];

  return (
    <div className="container py-6">
      <StepIndicator steps={steps} currentStep={currentStep} />

      {currentStep === 1 && <DatasetSelection onSelect={handleDatasetSelect} />}

      {currentStep === 2 && (
        <ApplyMitigation
          selectedBuildings={selectedBuildings}
          onInterventionChange={handleInterventionChange}
        />
      )}

      {currentStep === 3 && (
        <ResultsOutput
          baselineRun={baselineRun}
          interventionRun={interventionRun}
          financialResults={financialResults}
        />
      )}
    </div>
  );
}
```

## Phase 5: Database Migrations & Setup

### 5.1 Create Alembic migrations

```bash
# In backend directory
alembic revision --autogenerate -m "Add interventions and financial tracking"
alembic upgrade head
```

### 5.2 Seed initial intervention types

```python
# backend/scripts/seed_interventions.py

from app.db import get_session
from app.models import Intervention

interventions = [
    {
        "name": "Building Elevation",
        "type": "building_elevation",
        "description": "Raise building above base flood elevation"
    },
    {
        "name": "Flood Vents",
        "type": "flood_vents",
        "description": "Install flood vents to allow water flow"
    },
    # ... more intervention types
]

async def seed_interventions():
    async with get_session() as session:
        for intervention_data in interventions:
            intervention = Intervention(**intervention_data)
            session.add(intervention)
        await session.commit()
```

## Phase 6: Testing & Validation

### 6.1 Backend Tests

```python
# backend/tests/test_interventions.py

async def test_building_elevation_intervention():
    # Create baseline run
    baseline_run = await create_test_run()

    # Create intervention run with 2ft elevation
    intervention_run = await create_test_run(
        baseline_run_id=baseline_run.id,
        interventions=[{
            "building_id": "B001",
            "intervention_id": 1,
            "parameters": {"elevation_ft": 2.0},
            "cost": 80000
        }]
    )

    # Compare results
    baseline_results = await get_run_results(baseline_run.id)
    intervention_results = await get_run_results(intervention_run.id)

    # Building should have lower damage probabilities
    b001_baseline = find_building_result(baseline_results, "B001")
    b001_intervention = find_building_result(intervention_results, "B001")

    assert b001_intervention["P_DS3"] < b001_baseline["P_DS3"]
    assert b001_intervention["ffe_m"] > b001_baseline["ffe_m"]
```

### 6.2 Frontend Tests

```typescript
// flood-risk-app/tests/intervention-flow.test.ts

test("Building elevation reduces damage probability", async () => {
  // Select building
  await selectBuilding("B001");

  // Apply 2ft elevation
  await applyIntervention("B001", "elevate", { height: 2 });

  // Run analysis
  await runAnalysis();

  // Check results
  const results = await getResults();
  expect(results.ealReduction).toBeGreaterThan(0);
  expect(results.roi).toBeGreaterThan(0);
});
```

## Implementation Timeline

1. Backend intervention modeling

   - Database schema updates
   - Model updates
   - Analysis service modifications

2. Financial analysis

   - EAL calculations
   - ROI calculations
   - API endpoints

3. Frontend integration

   - API client setup
   - Component updates
   - State management

4. Testing & refinement
   - Integration tests
   - UI polish
   - Performance optimization
