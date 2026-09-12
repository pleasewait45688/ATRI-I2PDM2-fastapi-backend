from fastapi import APIRouter

from app.api.routes import pest_detect
from app.api.routes import line
from app.api.routes import db
from app.api.routes import profile
from app.api.routes import history

api_router = APIRouter()

api_router.include_router(
    pest_detect.router, prefix="/pest-detect", tags=["pest-detect"]
)
api_router.include_router(line.router, prefix="/line", tags=["line"])

#add db router
api_router.include_router(db.router, prefix="/db", tags=["db"])

api_router.include_router(profile.router, prefix="/profile", tags=["profile"])

api_router.include_router(history.router, prefix="/history", tags=["history"])