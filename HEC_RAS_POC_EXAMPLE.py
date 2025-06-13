"""
HEC-RAS Integration Proof of Concept
Example showing how to automate HEC-RAS for hazard-level interventions
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Option 1: Using ras-commander (recommended for HEC-RAS 6.x)
try:
    from ras_commander import (
        init_ras_project, RasPrj, RasCmdr, RasPlan, 
        RasGeo, RasUnsteady
    )
    USE_RAS_COMMANDER = True
except ImportError:
    USE_RAS_COMMANDER = False

# Option 2: Using raspy (for HEC-RAS 5.x or 6.x)
try:
    from raspy_auto import Ras, API
    USE_RASPY = True
except ImportError:
    USE_RASPY = False

# For reading results
try:
    from rashdf import RasPlanHdf, RasGeomHdf
    import h5py
    import numpy as np
    import rasterio
    from rasterio.transform import from_bounds
except ImportError:
    print("Warning: rashdf and rasterio not available for reading results")


class HECRASInterventionProcessor:
    """
    Processes hazard-level interventions using HEC-RAS
    """
    
    def __init__(self, hecras_version: str = "6.6"):
        self.hecras_version = hecras_version
        self.project_dir = None
        self.ras_project = None
        
    def create_project_from_hazard(
        self, 
        hazard_raster_path: str,
        river_centerline: List[Tuple[float, float]],
        cross_sections: List[Dict],
        project_name: str = "intervention_analysis"
    ) -> str:
        """
        Create a HEC-RAS project from an existing hazard raster
        """
        # Create temporary project directory
        self.project_dir = Path(tempfile.mkdtemp(prefix=f"hecras_{project_name}_"))
        
        if USE_RAS_COMMANDER:
            return self._create_project_ras_commander(
                hazard_raster_path, river_centerline, cross_sections
            )
        elif USE_RASPY:
            return self._create_project_raspy(
                hazard_raster_path, river_centerline, cross_sections
            )
        else:
            raise RuntimeError("No HEC-RAS Python library available")
    
    def _create_project_ras_commander(
        self, 
        hazard_raster_path: str,
        river_centerline: List[Tuple[float, float]],
        cross_sections: List[Dict]
    ) -> str:
        """Create project using ras-commander"""
        
        # Initialize project
        init_ras_project(str(self.project_dir), self.hecras_version)
        
        # Create geometry
        geometry_data = {
            "river_name": "MainRiver",
            "reach_name": "UpperReach",
            "centerline": river_centerline,
            "cross_sections": cross_sections
        }
        
        # Set up basic geometry
        RasGeo.create_river_reach(
            geometry_data["river_name"],
            geometry_data["reach_name"],
            geometry_data["centerline"]
        )
        
        # Add cross sections
        for xs in cross_sections:
            RasGeo.add_cross_section(
                river=geometry_data["river_name"],
                reach=geometry_data["reach_name"],
                station=xs["station"],
                geometry=xs["geometry"],
                manning_n=xs.get("manning_n", 0.035)
            )
        
        # Set up unsteady flow
        flow_data = {
            "boundary_conditions": [
                {
                    "location": "upstream",
                    "type": "flow_hydrograph",
                    "data": [(0, 1000), (6, 5000), (12, 8000), (24, 3000)]
                },
                {
                    "location": "downstream",
                    "type": "normal_depth",
                    "slope": 0.001
                }
            ]
        }
        
        RasUnsteady.set_boundary_conditions(flow_data["boundary_conditions"])
        
        # Create plan
        RasPlan.create_plan(
            plan_name="BaseConditions",
            geometry_file="base.g01",
            flow_file="base.u01"
        )
        
        return str(self.project_dir)
    
    def _create_project_raspy(
        self, 
        hazard_raster_path: str,
        river_centerline: List[Tuple[float, float]],
        cross_sections: List[Dict]
    ) -> str:
        """Create project using raspy"""
        
        # Create basic project structure
        prj_file = self.project_dir / "intervention.prj"
        
        # Initialize RAS object
        self.ras_project = Ras(str(prj_file), version=self.hecras_version)
        api = API(self.ras_project)
        
        # Open/create project
        api.ops.openProject()
        
        # Add geometry through direct file manipulation
        # (raspy is better for modifying existing projects)
        
        return str(self.project_dir)
    
    def add_dam_intervention(
        self,
        location_station: float,
        dam_height: float,
        spillway_elevation: float,
        spillway_width: float
    ):
        """
        Add a dam structure to the HEC-RAS model
        """
        if USE_RAS_COMMANDER:
            # Using ras-commander
            dam_data = {
                "type": "inline_structure",
                "station": location_station,
                "deck_elevation": spillway_elevation + dam_height,
                "spillway": {
                    "crest_elevation": spillway_elevation,
                    "width": spillway_width,
                    "coefficient": 2.6  # Typical for broad-crested weir
                }
            }
            
            RasGeo.add_inline_structure(
                river="MainRiver",
                reach="UpperReach",
                station=location_station,
                structure_data=dam_data
            )
            
        elif USE_RASPY:
            # Using raspy - would need to modify geometry file directly
            pass
    
    def add_levee_intervention(
        self,
        start_station: float,
        end_station: float,
        levee_elevation: float,
        side: str = "left"  # "left" or "right"
    ):
        """
        Add a levee to the HEC-RAS model
        """
        if USE_RAS_COMMANDER:
            # Using ras-commander
            levee_data = {
                "type": "levee",
                "start_station": start_station,
                "end_station": end_station,
                "elevation": levee_elevation,
                "side": side
            }
            
            RasGeo.add_levee(
                river="MainRiver",
                reach="UpperReach",
                levee_data=levee_data
            )
            
        elif USE_RASPY:
            # Using raspy
            api = API(self.ras_project)
            # Would need to implement levee addition through geometry modification
            pass
    
    def run_simulation(self, plan_name: str = "InterventionPlan") -> Dict:
        """
        Run the HEC-RAS simulation with interventions
        """
        if USE_RAS_COMMANDER:
            # Create new plan with interventions
            RasPlan.create_plan(
                plan_name=plan_name,
                geometry_file="intervention.g01",
                flow_file="base.u01"
            )
            
            # Run simulation
            success = RasCmdr.compute_plan(plan_name)
            
            if success:
                return {
                    "status": "success",
                    "plan_name": plan_name,
                    "output_path": str(self.project_dir / f"{plan_name}.hdf")
                }
            else:
                return {"status": "failed", "error": "Simulation failed"}
                
        elif USE_RASPY:
            api = API(self.ras_project)
            api.ops.compute(wait=True)
            return {"status": "success"}
    
    def extract_wse_raster(
        self, 
        plan_hdf_path: str,
        output_raster_path: str,
        bounds: Tuple[float, float, float, float],
        resolution: float = 10.0
    ) -> str:
        """
        Extract WSE from HEC-RAS results and create raster
        """
        if not os.path.exists(plan_hdf_path):
            raise FileNotFoundError(f"HDF file not found: {plan_hdf_path}")
        
        # Read HDF file using rashdf
        with RasPlanHdf(plan_hdf_path) as plan_hdf:
            # Get 2D flow area results if available
            flow_areas = plan_hdf.mesh_area_names()
            
            if flow_areas:
                # Get maximum WSE for first flow area
                wse_data = plan_hdf.mesh_max_ws(flow_areas[0])
                
                # Convert to raster
                # This is simplified - actual implementation would need proper interpolation
                self._create_raster_from_mesh(
                    wse_data, bounds, resolution, output_raster_path
                )
            else:
                # Handle 1D results
                # Extract cross-section WSE and interpolate
                pass
        
        return output_raster_path
    
    def _create_raster_from_mesh(
        self,
        mesh_data: Dict,
        bounds: Tuple[float, float, float, float],
        resolution: float,
        output_path: str
    ):
        """
        Create a raster from mesh results
        """
        west, south, east, north = bounds
        width = int((east - west) / resolution)
        height = int((north - south) / resolution)
        
        # Create transform
        transform = from_bounds(west, south, east, north, width, height)
        
        # Initialize raster with nodata
        raster_data = np.full((height, width), -9999.0, dtype=np.float32)
        
        # TODO: Interpolate mesh data to raster grid
        # This would involve:
        # 1. Getting mesh cell centers and values
        # 2. Using scipy.interpolate.griddata or similar
        # 3. Filling the raster array
        
        # Write raster
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=raster_data.dtype,
            crs='EPSG:4326',  # Adjust to match input
            transform=transform,
            nodata=-9999.0
        ) as dst:
            dst.write(raster_data, 1)


# Example usage
def example_dam_intervention():
    """
    Example: Add a dam to reduce flood hazard
    """
    
    # Initialize processor
    processor = HECRASInterventionProcessor(hecras_version="6.6")
    
    # Define river geometry (simplified)
    centerline = [
        (-122.5, 38.0),
        (-122.4, 38.1),
        (-122.3, 38.2)
    ]
    
    cross_sections = [
        {
            "station": 0,
            "geometry": {
                "stations": [0, 50, 100, 150, 200],
                "elevations": [100, 95, 90, 95, 100]
            },
            "manning_n": 0.035
        },
        {
            "station": 1000,
            "geometry": {
                "stations": [0, 50, 100, 150, 200],
                "elevations": [98, 93, 88, 93, 98]
            },
            "manning_n": 0.035
        },
        {
            "station": 2000,
            "geometry": {
                "stations": [0, 50, 100, 150, 200],
                "elevations": [96, 91, 86, 91, 96]
            },
            "manning_n": 0.035
        }
    ]
    
    # Create base project
    project_path = processor.create_project_from_hazard(
        hazard_raster_path="/path/to/existing/hazard.tif",
        river_centerline=centerline,
        cross_sections=cross_sections
    )
    
    # Add dam intervention
    processor.add_dam_intervention(
        location_station=1500,  # Between two cross sections
        dam_height=10.0,        # 10 ft high dam
        spillway_elevation=94.0,
        spillway_width=50.0
    )
    
    # Run simulation
    result = processor.run_simulation("DamScenario")
    
    if result["status"] == "success":
        # Extract updated WSE raster
        bounds = (-122.6, 37.9, -122.2, 38.3)  # West, South, East, North
        
        updated_wse_path = processor.extract_wse_raster(
            plan_hdf_path=result["output_path"],
            output_raster_path="/tmp/updated_wse_with_dam.tif",
            bounds=bounds,
            resolution=10.0
        )
        
        print(f"Updated WSE raster created: {updated_wse_path}")
    
    return result


# Example integration with the hazard system
async def integrate_with_hazard_system(
    intervention_id: int,
    original_hazard_path: str,
    db_session
):
    """
    Example of how to integrate HEC-RAS processing with the hazard system
    """
    from app.models import HazardIntervention, ModifiedHazard
    
    # Get intervention from database
    intervention = await db_session.get(HazardIntervention, intervention_id)
    
    # Process with HEC-RAS
    processor = HECRASInterventionProcessor()
    
    # Create project based on intervention type
    if intervention.type == "dam":
        # Add dam based on intervention parameters
        processor.add_dam_intervention(**intervention.parameters)
    elif intervention.type == "levee":
        # Add levee
        processor.add_levee_intervention(**intervention.parameters)
    
    # Run simulation
    result = processor.run_simulation()
    
    # Extract and save updated hazard
    if result["status"] == "success":
        updated_wse_path = f"/data/modified_hazards/{intervention_id}_wse.tif"
        processor.extract_wse_raster(
            result["output_path"],
            updated_wse_path,
            bounds=intervention.geometry["bounds"]
        )
        
        # Create modified hazard record
        modified_hazard = ModifiedHazard(
            name=f"{intervention.name} - Modified Hazard",
            original_hazard_id=intervention.hazard_id,
            intervention_id=intervention_id,
            wse_raster_path=updated_wse_path,
            hecras_project_path=processor.project_dir
        )
        
        db_session.add(modified_hazard)
        await db_session.commit()
        
        return modified_hazard


if __name__ == "__main__":
    # Check available libraries
    print(f"ras-commander available: {USE_RAS_COMMANDER}")
    print(f"raspy available: {USE_RASPY}")
    
    if USE_RAS_COMMANDER or USE_RASPY:
        # Run example
        result = example_dam_intervention()
        print(f"Example result: {result}")
    else:
        print("No HEC-RAS Python library available. Install ras-commander or raspy.") 