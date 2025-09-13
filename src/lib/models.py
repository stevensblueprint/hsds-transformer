from pydantic import BaseModel


class Organization(BaseModel):
    id: str
    name: str
    description: str
