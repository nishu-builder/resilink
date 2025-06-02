# System Descriptions

This document provides a comprehensive overview of two flood risk analysis systems: the existing hazard analysis backend and the flood-risk-app frontend mockup, along with a detailed comparison of their features.

## Hazard Codebase

### Overview

The hazard system is a backend-focused flood damage analysis platform built with modern Python technologies. It processes geospatial hazard data and building information to calculate expected damage states based on fragility curves.

### Technology Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL with PostGIS extension
- **ORM**: SQLModel/SQLAlchemy
- **Containerization**: Docker Compose
- **Python Libraries**:
  - rasterio (for raster data processing)
  - geopandas (for geospatial operations)
  - scipy (for statistical calculations)

### Core Models

- **Hazard**: Stores water surface elevation (WSE) raster data paths
- **FragilityCurve**: JSON-based fragility curve definitions (DFR3 format)
- **MappingSet**: Maps building characteristics to appropriate fragility curves
- **BuildingDataset**: Shapefile data containing building locations and attributes
- **Run**: Analysis execution tracking with status and results

### Key Functionality

1. **Data Ingestion**:

   - Upload and store WSE raster files (TIF format)
   - Import building datasets (shapefiles in ZIP format)
   - Load fragility curves and mapping sets (JSON format)

2. **Analysis Pipeline**:

   - Extract building locations from shapefiles
   - Sample WSE values at building locations
   - Map buildings to appropriate fragility curves based on attributes
   - Calculate limit state exceedance probabilities using lognormal CDFs
   - Generate damage state probabilities (DS0-DS3)

3. **Output**:
   - GeoJSON FeatureCollection with building geometries
   - Calculated probabilities for each damage state
   - Effective flood depth for each building

### API Endpoints

- `/hazards`: Manage hazard datasets
- `/building-datasets`: Upload and manage building data
- `/fragility-curves`: Manage fragility curve definitions
- `/mapping-sets`: Configure building-to-fragility mappings
- `/runs`: Execute and monitor analysis runs

## Flood-Risk-App Codebase

### Overview

The flood-risk-app is a modern web application mockup that provides a user-friendly interface for flood resilience planning. It focuses on intervention planning, financial analysis, and visualization of flood mitigation strategies.

### Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **UI Library**: shadcn/ui (Radix UI + Tailwind CSS)
- **State Management**: React hooks
- **Charts**: Recharts
- **Maps**: Custom map components (likely placeholder for Mapbox/Leaflet)

### Key Features

1. **Portfolio Management**:

   - Upload custom portfolios (CSV/JSON)
   - Pre-built demo portfolios (Sacramento, Houston, Tampa)
   - Visual preview of building locations on interactive maps
   - Building metadata management (type, address, risk level)

2. **Planning Workflows**:

   - **Manual Planning**: Step-by-step intervention selection
   - **Optimized Planning**: AI-powered optimization with budget constraints
   - Guided wizard interface with progress tracking

3. **Intervention Types**:

   - **Asset-level**:
     - Structure elevation (customizable height)
     - Flood vents installation
     - Dry floodproofing
     - HVAC system elevation
     - Water-resistant materials
     - Deployable flood barriers
   - **Hazard-level**:
     - Levee construction
     - Flood bypass channels
     - Green infrastructure
     - Detention basins

4. **Financial Analysis**:

   - Cost estimation for each intervention
   - ROI calculation
   - Expected Annual Loss (EAL) reduction
   - Insurance premium impact analysis

5. **Visualization & Reporting**:
   - Interactive maps with risk overlays
   - Scenario comparison charts
   - Fragility curve visualization
   - Export capabilities for reports

### Page Structure

- `/`: Landing page with product overview
- `/portfolio-selection`: Portfolio upload and selection interface
- `/simulator`: Main analysis workflow
- `/dashboard`: Comprehensive analysis dashboard (alternate view)

## Differences and Feature Gaps

### Features Present in Flood-Risk-App but NOT in Hazard System

#### 1. **Intervention Modeling**

- **Gap**: Hazard system only calculates baseline damage states
- **Flood-risk-app**: Models how interventions modify risk
- **Details**:
  - No mechanism to adjust fragility curves based on interventions
  - No elevation adjustment calculations
  - No hazard modification modeling

#### 2. **Financial Analysis Capabilities**

- **Gap**: Hazard system has no financial modeling
- **Flood-risk-app Features**:
  - Intervention cost tracking
  - ROI calculations
  - Expected Annual Loss (EAL) calculations
  - Budget optimization

#### 5. **User Experience Features**

- **Gap**: Hazard system is API-only
- **Flood-risk-app Features**:
  - Guided workflow wizard

### Integration Opportunities

To converge these systems, the following integration points should be considered:

1. **Extend Models**: Add intervention, scenario, and portfolio models to the backend
2. **Financial Engine**: Implement cost and benefit calculation services
5. **Result Enhancement**: Extend analysis results to include financial metrics and intervention impacts
6. **Frontend Integration**: Connect flood-risk-app UI to the hazard backend APIs

This convergence would create a comprehensive flood risk management platform that combines rigorous hazard analysis with user-friendly planning tools and financial decision support.
