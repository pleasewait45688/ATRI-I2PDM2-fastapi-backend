# app/schemas.py

from pydantic import BaseModel
from datetime import datetime

class UserProfileCreate(BaseModel):
    name: str
    phone: str
    location: str
    farm_name: str
    service_unit: str

class UserProfileRead(UserProfileCreate):
    id: int
    line_user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
