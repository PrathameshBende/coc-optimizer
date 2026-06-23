# optimizer/models.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class ResourceType(Enum):
    BUILDER = "BUILDER"
    LAB = "LAB"
    PET = "PET"

@dataclass
class Task:
    id: str
    duration: int
    deps: list[str]
    resource: ResourceType
    release_time: int = 0

@dataclass
class TaskSchedule:
    task_id: str
    machine_id: int
    start_time: int
    end_time: int

@dataclass
class NormalizedLevel:
    level: int
    duration_seconds: int
    town_hall_required: Optional[int] = None
    hero_hall_required: Optional[int] = None
    lab_required: Optional[int] = None
    pet_house_required: Optional[int] = None
    spell_factory_required: Optional[int] = None
    dark_spell_factory_required: Optional[int] = None
    workshop_required: Optional[int] = None
    barracks_required: Optional[int] = None         # NEW
    dark_barracks_required: Optional[int] = None    # NEW
    supercharge: bool = False

@dataclass
class NormalizedTaskMetadata:
    data_id: str
    name: str
    resource: ResourceType
    count_by_th: Optional[dict[int, int]] = None
    levels: list[NormalizedLevel] = field(default_factory=list)