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


class Run(Base, table=True):
    __tablename__ = "runs"

    name: str = Field(index=True)

    hazard_id: int = Field(foreign_key="hazards.id")
    mapping_set_id: int = Field(foreign_key="mapping_sets.id")
    building_dataset_id: int = Field(foreign_key="building_datasets.id")

    status: str = Field(default="PENDING")  # Could be Enum later
    result_path: Optional[str] = None
    finished_at: Optional[datetime] = None

    hazard: Optional[Hazard] = Relationship(back_populates="runs")
    building_dataset: Optional[BuildingDataset] = Relationship(back_populates="runs")
