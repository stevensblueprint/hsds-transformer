from pydantic import BaseModel
from typing import List

class Address(BaseModel):
    id: str
    address_1: str
    city: str
    region: str
    state_province: str
    postal_code: str
    address_type: str

class Location(BaseModel):
    addresses: List[Address]

class Phone(BaseModel):
    number: str

class Organization(BaseModel):
    id: str
    name: str
    locations: List[Location]
    phones: List[Phone]
