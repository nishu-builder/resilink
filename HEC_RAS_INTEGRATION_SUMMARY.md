# HEC-RAS Integration Summary

## Overview

This plan outlines how to integrate HEC-RAS for hazard-level interventions (dams/levees) into your existing flood hazard analysis system. The integration will enable users to design interventions and generate updated flood hazards using HEC-RAS hydraulic modeling.

## Key Components

### 1. **Hazard Visualization** (Not currently supported)

- Web-based raster tile serving using TiTiler
- Interactive map display with Mapbox/Leaflet
- Color-coded depth visualization

### 2. **HEC-RAS Python Libraries**

#### Recommended: **ras-commander**

- Modern, comprehensive API for HEC-RAS 6.x
- Full model creation and manipulation
- Easy installation: `pip install ras-commander`

#### Alternative: **raspy**

- More established, supports HEC-RAS 5.x and 6.x
- Better for modifying existing models
- Installation: `pip install raspy-auto`

#### For Results: **rashdf**

- FEMA-developed library for reading HEC-RAS HDF files
- Installation: `pip install rashdf`

### 3. **Architecture Updates**

```
Current Flow:
Upload Hazard → Run Analysis → Calculate Damage

New Flow:
Upload Hazard → View Hazard → Design Intervention →
Run HEC-RAS → Generate Updated Hazard → Run Analysis
```

## Implementation Steps

### Phase 1: Hazard Visualization (15 min setup)

```python
# Add to backend/app/api/hazards.py
@router.get("/{hazard_id}/tiles/{z}/{x}/{y}")
async def get_hazard_tile(hazard_id: int, z: int, x: int, y: int):
    # Serve raster tiles for web mapping
```

### Phase 2: HEC-RAS Service Container

```dockerfile
FROM python:3.11
RUN pip install ras-commander rashdf
# Install HEC-RAS (Windows container or Wine on Linux)
```

### Phase 3: Intervention Models

```python
class HazardIntervention(Base):
    type: str  # "dam", "levee"
    geometry: dict  # GeoJSON
    parameters: dict  # height, width, etc.
```

### Phase 4: Processing Pipeline

1. User designs intervention on map
2. System creates HEC-RAS project
3. Adds intervention to model
4. Runs simulation
5. Extracts updated WSE raster
6. Uses new hazard in damage analysis

## Quick Start Example

```python
from ras_commander import init_ras_project, RasGeo, RasCmdr

# Create HEC-RAS project
init_ras_project("/path/to/project", "6.6")

# Add dam
RasGeo.add_inline_structure(
    river="MainRiver",
    station=1500,
    structure_data={
        "type": "dam",
        "spillway_elevation": 94.0,
        "spillway_width": 50.0
    }
)

# Run simulation
RasCmdr.compute_plan("DamScenario")
```

## Benefits

- **Visual feedback**: Users can see hazards before/after interventions
- **Accurate modeling**: HEC-RAS provides industry-standard hydraulic calculations
- **Integrated workflow**: Seamlessly combines with existing damage analysis
- **Scalable**: Containerized approach allows parallel processing

## Challenges & Solutions

- **HEC-RAS licensing**: Use command-line version, consider cloud licensing
- **Performance**: Cache results, use async processing with Celery
- **Large rasters**: Use Cloud Optimized GeoTIFF (COG) format
- **Windows dependency**: Use Wine in Linux containers or Windows containers

## Timeline

- Week 1-2: Hazard visualization
- Week 2-3: HEC-RAS service setup
- Week 3-4: Intervention models
- Week 4-5: Integration testing
- Week 5-6: Frontend development

## Next Steps

1. Install `ras-commander`: `pip install ras-commander`
2. Test HEC-RAS automation with the provided POC example
3. Implement hazard visualization endpoint
4. Create Docker container for HEC-RAS service

This integration will transform your system from analyzing static hazards to dynamically modeling intervention impacts, providing powerful decision support for flood mitigation planning.
