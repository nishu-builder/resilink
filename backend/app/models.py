from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship, Column, JSON, MetaData

metadata_obj = MetaData(schema="public")


class Base(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class Hazard(Base, table=True):
    __tablename__ = "hazards"

    name: str = Field(index=True)
    wse_raster_path: str  # stored path on disk

    runs: list["Run"] = Relationship(back_populates="hazard")


class FragilityCurve(Base, table=True):
    __tablename__ = "fragility_curves"

    name: str = Field(index=True)
    json_path: str


class MappingSet(Base, table=True):
    __tablename__ = "mapping_sets"

    name: str = Field(index=True)
    json_path: str


class BuildingDataset(Base, table=True):
    __tablename__ = "building_datasets"

    name: str = Field(index=True)
    shp_path: str
    bbox: Optional[str] = Field(default=None, sa_column=Column(JSON))  # GeoJSON bbox array
    feature_count: Optional[int] = None

    runs: list["Run"] = Relationship(back_populates="building_dataset")
    buildings: list["Building"] = Relationship(back_populates="dataset")


class Building(Base, table=True):
    __tablename__ = "buildings"
    
    guid: str = Field(index=True)  # Building identifier from shapefile
    dataset_id: int = Field(foreign_key="building_datasets.id")
    geometry: dict = Field(sa_column=Column(JSON))  # GeoJSON geometry
    properties: dict = Field(sa_column=Column(JSON))  # All shapefile properties
    asset_value: Optional[float] = None  # User-assigned asset value
    
    dataset: Optional[BuildingDataset] = Relationship(back_populates="buildings")


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

    run: Optional["Run"] = Relationship(back_populates="interventions")
    intervention: Optional[Intervention] = Relationship(back_populates="run_interventions")


class RunGroup(Base, table=True):
    __tablename__ = "run_groups"
    
    name: str = Field(index=True)
    description: Optional[str] = None
    
    runs: list["Run"] = Relationship(back_populates="run_group")


class Run(Base, table=True):
    __tablename__ = "runs"

    name: str = Field(index=True)

    hazard_id: int = Field(foreign_key="hazards.id")
    mapping_set_id: int = Field(foreign_key="mapping_sets.id")
    building_dataset_id: int = Field(foreign_key="building_datasets.id")
    run_group_id: Optional[int] = Field(default=None, foreign_key="run_groups.id")

    status: str = Field(default="PENDING")  # Could be Enum later
    result_path: Optional[str] = None
    finished_at: Optional[datetime] = None
    
    # Financial analysis results
    total_eal: Optional[float] = None
    buildings_analyzed: Optional[int] = None
    buildings_with_values: Optional[int] = None
    total_asset_value: Optional[float] = None

    hazard: Optional[Hazard] = Relationship(back_populates="runs")
    building_dataset: Optional[BuildingDataset] = Relationship(back_populates="runs")
    interventions: list[RunIntervention] = Relationship(back_populates="run")
    run_group: Optional[RunGroup] = Relationship(back_populates="runs")
