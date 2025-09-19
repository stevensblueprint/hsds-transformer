from pydantic import BaseModel
from typing import List

class Location(BaseModel):
    address: str

class Organization(BaseModel):
    id: str
    name: str
    description: str
    locations: List[Location]
    location: Location
