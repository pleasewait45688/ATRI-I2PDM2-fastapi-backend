from fastapi import APIRouter

from app.api.routes import pest_detect
from app.api.routes import db

api_router = APIRouter()

api_router.include_router(
    pest_detect.router, prefix="/pest-detect", tags=["pest-detect"]
)

#add db router
api_router.include_router(db.router, prefix="/db", tags=["db"])