# Hazard Intervention Setup Guide

This guide will help you implement the new hazard visualization and intervention features.

## Features Implemented

✅ **Hazard Visualization**
- View flood hazards as interactive maps
- Multiple color schemes (Blues, Heat, Viridis, etc.)
- Tile-based rendering for performance
- Preview image generation

✅ **Database Models**
- `HazardIntervention`: Store dam/levee designs
- `ModifiedHazard`: Track hydraulically-modified hazards
- Updated `Run` model to support modified hazards

✅ **API Endpoints**
- `/api/datasets/hazards/{id}/info` - Hazard metadata
- `/api/datasets/hazards/{id}/preview` - Preview images
- `/api/datasets/hazards/{id}/tiles/{z}/{x}/{y}` - Map tiles
- `/api/hazard-interventions` - CRUD for interventions

✅ **Frontend Components**
- `HazardViewer` - Interactive map component
- `/datasets/hazards/{id}` - Individual hazard pages
- `/datasets/hazards` - List view with "View" buttons

## Next Steps: Running the System

### 1. Start Services
```bash
task up
```

### 2. Run Database Migration
```bash
task migrate:create -- "add hazard interventions and modified hazards"
task migrate:upgrade
```

### 3. Test Hazard Visualization
1. Upload a hazard raster if you haven't already
2. Navigate to `/datasets/hazards` 
3. Click "View" on any hazard
4. You should see an interactive map!

## Hydraulic Modeling Integration

For Mac compatibility, we recommend **ANUGA** instead of HEC-RAS:

### Install ANUGA
```bash
# In the backend container
task enter
pip install anuga
```

### ANUGA vs HEC-RAS Benefits
- ✅ Runs natively on macOS
- ✅ Pure Python (easy integration)
- ✅ Excellent flood modeling capabilities
- ✅ Dam break and levee modeling
- ✅ Open source and well-documented

### Alternative: Landlab
- Also Python-based
- Good for long-term landscape evolution
- Simpler shallow water flow modeling

## Implementation Details

### Hazard Visualization API
Three new endpoints provide visualization:
- **Info**: Returns metadata, bounds, and statistics
- **Preview**: Generates static preview images
- **Tiles**: Serves map tiles in standard XYZ format

### Intervention Models
- **HazardIntervention**: Stores geometry and parameters
- **ModifiedHazard**: Links original hazards to post-intervention results
- Supports both dam and levee interventions

### Frontend Integration
- Mapbox GL JS for interactive maps
- Configurable color schemes for water depth
- Real-time opacity controls
- Automatic bounds fitting

## Testing the Features

1. **View existing hazards**: Navigate to datasets page
2. **Interactive visualization**: Click any hazard's "View" button
3. **API testing**: Use browser/Postman to test endpoints

## Next Development Phase

Ready to implement the actual hydraulic modeling service! The framework is in place for:
- ANUGA/Landlab integration
- Intervention geometry processing
- Modified hazard generation
- Updated analysis pipeline

The hardest parts (database models, API structure, visualization) are complete!