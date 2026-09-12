from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, List
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        # Since you run app/main.py from backend folder, this would be OK
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # add ALLOWED_ORIGINS for local host
    ALLOWED_ORIGINS: str | None
    @property
    def allowed_origins_list(self) -> List[str]:
        if not self.ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
    
    LINE_CHANNEL_SECRET: str | None
    LINE_CHANNEL_ACCESS_TOKEN: str | None
    #add env for db
    DATABASE_URL: str | None

    # base URL for links sent to LINE users (recognition/info/history pages)
    FRONTEND_BASE_URL: str | None

    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"


settings = Settings()  # type: ignore

logdir_path = Path(__file__).parent.parent.parent / "tmp" / "log"
if not logdir_path.exists():
    # Create the directory
    logdir_path.mkdir(parents=True, exist_ok=True)

# Define the path for the log file
logfile_path = Path(__file__).parent.parent.parent / "tmp" / "log" / "app.log"

# Create a rotating file handler
handler = RotatingFileHandler(
    filename=logfile_path,
    mode="a",  # Append mode
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,  # Keep up to 5 backup files
    encoding=None,
    delay=0,
)

# Define the logging format
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Configure the root logger
logging.basicConfig(level=logging.DEBUG, handlers=[handler])
