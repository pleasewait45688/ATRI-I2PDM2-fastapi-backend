# app/db/models/user_profile.py

from sqlalchemy import Column, String, Integer, DateTime, func
from app.db.database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id           = Column(Integer, primary_key=True, index=True)
    line_user_id  = Column(String(255), unique=True, index=True, nullable=False)
    name         = Column(String(100), nullable=False)
    phone        = Column(String(20), nullable=False)
    location     = Column(String(100), nullable=False)
    farm_name    = Column(String(100), nullable=False)
    service_unit = Column(String(100), nullable=False)
    created_at   = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at   = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
