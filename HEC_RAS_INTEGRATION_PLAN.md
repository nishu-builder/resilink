# HEC-RAS Integration Implementation Plan for Hazard-Level Interventions

## Executive Summary

This document outlines a comprehensive plan for integrating HEC-RAS capabilities into the existing hazard analysis system to support hazard-level interventions (dams and levees). The integration will enable users to:

1. View flood hazards (WSE rasters) through a web interface
2. Design hazard-level interventions (dam/levee placement)
3. Use HEC-RAS to generate updated hazards based on interventions
4. Incorporate these interventions into analysis runs

## Current System Analysis

### Existing Capabilities

- **Hazard Management**: Upload and store WSE raster files
- **Asset-Level Interventions**: Building elevation modifications
- **Analysis Pipeline**: Calculate damage states using fragility curves
- **Financial Analysis**: EAL calculations and ROI comparisons

### Gaps to Address

1. No hazard visualization capability
2. No support for hazard-level interventions
3. No integration with HEC-RAS for hydraulic modeling
4. No mechanism to update hazards based on interventions

## Proposed Architecture

### System Components

1. **HEC-RAS Service Container**

   - Containerized HEC-RAS installation
   - Python wrapper using `ras-commander` or `raspy`
   - API for model manipulation and execution

2. **Hazard Viewer API**

   - Endpoint to serve raster data as tiles
   - Support for multiple visualization formats
   - Integration with frontend mapping libraries

3. **Intervention Designer API**

   - Store hazard-level intervention geometries
   - Validate intervention placement
   - Generate HEC-RAS model inputs

4. **Updated Analysis Pipeline**
   - Support for dynamic hazard replacement
   - Track intervention-modified hazards
   - Maintain hazard lineage

## Implementation Phases

### Phase 1: Hazard Visualization (Week 1-2)

#### Backend Implementation

```python
# backend/app/api/hazards.py
@router.get("/{hazard_id}/visualize", response_model=HazardVisualization)
async def get_hazard_visualization(
    hazard_id: int,
    bounds: Optional[List[float]] = Query(None),
    resolution: Optional[int] = Query(256),
    colormap: Optional[str] = Query("Blues"),
    db: AsyncSession = Depends(get_async_session)
):
    """Generate visualization data for a hazard raster."""
    hazard = await db.get(Hazard, hazard_id)
    if not hazard:
        raise HTTPException(404, "Hazard not found")

    # Process raster for visualization
    viz_data = await process_raster_for_viz(
        hazard.wse_raster_path,
        bounds=bounds,
        resolution=resolution,
        colormap=colormap
    )
    return viz_data

@router.get("/{hazard_id}/tiles/{z}/{x}/{y}")
async def get_hazard_tile(
    hazard_id: int,
    z: int, x: int, y: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Serve raster tiles for web mapping."""
    # Implementation for tile generation
    pass
```

#### Frontend Implementation

- Integrate Mapbox GL JS or Leaflet
- Add hazard layer visualization
- Color ramp for water depth display
- Interactive legend

### Phase 2: HEC-RAS Service Setup (Week 2-3)

#### Docker Container

```dockerfile
# backend/hecras/Dockerfile
FROM python:3.11-slim

# Install HEC-RAS dependencies
RUN apt-get update && apt-get install -y \
    wine \
    wine32 \
    wine64 \
    libwine \
    libwine:i386 \
    fonts-wine

# Install HEC-RAS (using wine)
COPY HEC-RAS_6.6_Setup.exe /tmp/
RUN wine /tmp/HEC-RAS_6.6_Setup.exe /S

# Install Python dependencies
RUN pip install ras-commander pyrasfile h5py geopandas

# Copy service code
COPY hecras_service/ /app/

WORKDIR /app
CMD ["python", "service.py"]
```

#### HEC-RAS Service API

```python
# backend/hecras_service/service.py
from fastapi import FastAPI, UploadFile
from ras_commander import RasPrj, RasCmdr, RasPlan
import tempfile
import shutil

app = FastAPI()

@app.post("/setup-model")
async def setup_hecras_model(
    terrain: UploadFile,
    geometry: dict,  # River geometry
    boundary_conditions: dict
):
    """Initialize a HEC-RAS model with base geometry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create HEC-RAS project
        prj = RasPrj()
        prj.create_new_project(tmpdir)

        # Add terrain
        terrain_path = f"{tmpdir}/terrain.tif"
        with open(terrain_path, "wb") as f:
            shutil.copyfileobj(terrain.file, f)

        # Setup geometry
        # ... implementation details

        return {"project_id": project_id}

@app.post("/add-intervention")
async def add_intervention(
    project_id: str,
    intervention_type: str,  # "dam" or "levee"
    geometry: dict  # GeoJSON geometry
):
    """Add a dam or levee to the HEC-RAS model."""
    # Load project
    # Add structure to geometry
    # Return success
    pass

@app.post("/run-simulation")
async def run_hecras_simulation(
    project_id: str,
    output_format: str = "wse_raster"
):
    """Execute HEC-RAS simulation and return results."""
    # Run HEC-RAS
    # Extract WSE results
    # Convert to raster
    # Return result path
    pass
```

### Phase 3: Intervention Models (Week 3-4)

#### Database Models

```python
# backend/app/models.py

class HazardIntervention(Base, table=True):
    __tablename__ = "hazard_interventions"

    name: str = Field(index=True)
    type: str  # "dam", "levee"
    geometry: dict = Field(sa_column=Column(JSON))  # GeoJSON
    parameters: dict = Field(sa_column=Column(JSON))

    # Dam parameters: height, width, spillway_elevation
    # Levee parameters: height, top_width, side_slopes

    created_by: Optional[int] = Field(foreign_key="users.id")
    hazard_id: int = Field(foreign_key="hazards.id")

    hazard: Optional[Hazard] = Relationship(back_populates="interventions")

class ModifiedHazard(Base, table=True):
    __tablename__ = "modified_hazards"

    name: str
    original_hazard_id: int = Field(foreign_key="hazards.id")
    intervention_id: int = Field(foreign_key="hazard_interventions.id")
    wse_raster_path: str
    hecras_project_path: Optional[str]

    original_hazard: Optional[Hazard] = Relationship()
    intervention: Optional[HazardIntervention] = Relationship()
```

#### API Endpoints

```python
# backend/app/api/hazard_interventions.py
@router.post("/hazard-interventions", response_model=HazardInterventionResponse)
async def create_hazard_intervention(
    intervention: HazardInterventionCreate,
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new hazard-level intervention."""
    # Validate geometry
    # Store intervention
    # Return response
    pass

@router.post("/hazard-interventions/{intervention_id}/apply")
async def apply_hazard_intervention(
    intervention_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session)
):
    """Apply intervention and generate modified hazard."""
    intervention = await db.get(HazardIntervention, intervention_id)
    if not intervention:
        raise HTTPException(404)

    # Queue HEC-RAS processing
    background_tasks.add_task(
        process_intervention_with_hecras,
        intervention_id=intervention_id
    )

    return {"status": "processing", "intervention_id": intervention_id}
```

### Phase 4: Integration with Run System (Week 4-5)

#### Updated Run Model

```python
# backend/app/models.py
class Run(Base, table=True):
    # ... existing fields ...

    # Add support for modified hazards
    modified_hazard_id: Optional[int] = Field(
        default=None,
        foreign_key="modified_hazards.id"
    )

    modified_hazard: Optional[ModifiedHazard] = Relationship()
```

#### Analysis Service Updates

```python
# backend/app/services/analysis.py
async def perform_analysis(run_id: int, M_OFFSET: float = 0.0) -> None:
    # ... existing code ...

    # Determine which hazard to use
    if run.modified_hazard_id:
        wse_raster_path = run.modified_hazard.wse_raster_path
    else:
        wse_raster_path = hazard.wse_raster_path

    # Load WSE raster
    wse_ds = rasterio.open(wse_raster_path)

    # ... rest of analysis ...
```

## Python Libraries Selection

### Recommended: ras-commander

- **Pros**:
  - Comprehensive API for HEC-RAS 6.x
  - Active development
  - Good documentation
  - Handles both model setup and execution
- **Cons**:
  - Newer library, less battle-tested
  - Requires HEC-RAS 6.x

### Alternative: raspy

- **Pros**:
  - More established
  - Supports multiple HEC-RAS versions
  - Used in production systems
- **Cons**:
  - Less comprehensive than ras-commander
  - Primarily focused on parameter modification

### For HDF Reading: rashdf

- Use for reading HEC-RAS output files
- Developed by FEMA, well-maintained
- Good for extracting results

## Technical Considerations

### Performance

1. **HEC-RAS Processing**:

   - Use Celery for async processing
   - Cache results for repeated simulations
   - Consider parallel processing for multiple scenarios

2. **Raster Processing**:
   - Use Cloud Optimized GeoTIFF (COG) format
   - Implement tile caching for visualization
   - Consider using PostGIS for spatial queries

### Storage

1. **HEC-RAS Projects**:

   - Store in dedicated directory structure
   - Implement cleanup for old projects
   - Consider compression for archival

2. **Modified Hazards**:
   - Track lineage (original → intervention → modified)
   - Version control for interventions
   - Efficient storage of large rasters

### Security

1. **Input Validation**:

   - Validate intervention geometries
   - Limit HEC-RAS model complexity
   - Sanitize file uploads

2. **Resource Limits**:
   - Set timeouts for HEC-RAS runs
   - Limit concurrent simulations
   - Monitor disk usage

## Frontend Components

### Hazard Viewer

```typescript
// frontend/components/HazardViewer.tsx
import { useEffect, useState } from "react";
import mapboxgl from "mapbox-gl";

export function HazardViewer({ hazardId }: { hazardId: number }) {
  // Initialize map
  // Load hazard tiles
  // Add controls for visualization
  // Display legend
}
```

### Intervention Designer

```typescript
// frontend/components/InterventionDesigner.tsx
import { DrawControl } from "@mapbox/mapbox-gl-draw";

export function InterventionDesigner({
  hazardId,
  onSave,
}: {
  hazardId: number;
  onSave: (intervention: Intervention) => void;
}) {
  // Map with drawing tools
  // Intervention type selector
  // Parameter inputs
  // Save/cancel buttons
}
```

## Testing Strategy

### Unit Tests

- Raster processing functions
- Intervention validation
- HEC-RAS input generation

### Integration Tests

- Full HEC-RAS workflow
- API endpoint testing
- Database operations

### Performance Tests

- Large raster handling
- Concurrent HEC-RAS runs
- Visualization performance

## Deployment Considerations

### Docker Compose Updates

```yaml
services:
  # ... existing services ...

  hecras:
    build: ./backend/hecras
    volumes:
      - hecras-projects:/projects
      - hazard-data:/data
    environment:
      - HECRAS_LICENSE=${HECRAS_LICENSE}
    depends_on:
      - rabbitmq

  hazard-tiles:
    image: titiler/titiler:latest
    environment:
      - TITILER_API_URL=/api/tiles
    volumes:
      - hazard-data:/data:ro
```

### Resource Requirements

- Additional CPU cores for HEC-RAS
- ~50GB storage for HEC-RAS projects
- GPU optional but beneficial for large models

## Timeline Summary

- **Week 1-2**: Hazard visualization
- **Week 2-3**: HEC-RAS service setup
- **Week 3-4**: Intervention models and API
- **Week 4-5**: Integration and testing
- **Week 5-6**: Frontend development
- **Week 6-7**: Testing and refinement
- **Week 7-8**: Documentation and deployment

## Next Steps

1. **Immediate Actions**:

   - Set up development environment with HEC-RAS
   - Create proof-of-concept HEC-RAS service
   - Implement basic hazard visualization

2. **Technical Decisions**:

   - Choose between ras-commander and raspy
   - Select mapping library (Mapbox vs Leaflet)
   - Determine HEC-RAS licensing approach

3. **Team Coordination**:
   - Assign frontend/backend responsibilities
   - Schedule design reviews
   - Plan user testing sessions

This implementation plan provides a roadmap for successfully integrating HEC-RAS capabilities while maintaining the existing system's functionality and extending it with powerful hazard-level intervention modeling.
