from fastapi import FastAPI
from app.api.main import api_router

# from app.api.routes import pest-detect
from app.core.config import settings
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

from fastapi.middleware.cors import CORSMiddleware #this is for local host to connect to backend
# from app.db.database import Base, engine
# import app.db.models  # init table cannot be deleted

# Base.metadata.create_all(bind=engine)

app = FastAPI(openapi_url=f"{settings.API_V1_STR}/openapi.json")
# Define the path for the log file
logfile_path = Path(__file__).parent / "app.log"

# Create a rotating file handler
handler = RotatingFileHandler(
    filename=logfile_path,
    mode="a",  # Append mode
    maxBytes=20 * 1024 * 1024,  # 20 MB
    backupCount=30,  # Keep up to 5 backup files
    encoding=None,
    delay=0,
)

# Define the logging format
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

#CORS middleware
if settings.allowed_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/")
async def read_main():
    # TODO: warning or informative messages for user
    return {"msg": "NTU Pest Demo"}


app.include_router(api_router, prefix=settings.API_V1_STR)
