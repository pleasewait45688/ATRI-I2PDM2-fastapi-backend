import logging
import importlib.util
from pathlib import Path
import sys


# Configure logging
logging.basicConfig(
    filename="app.log",  # Log file name
    level=logging.DEBUG,  # Set logging level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def import_pest_module():
    # Determine the path to the 'pest' module
    project_root = Path(__file__).resolve().parents[1]
    pest_module_path = project_root / "app" / "pest"

    # Check if the 'pest' module path exists
    if not pest_module_path.exists() or not pest_module_path.is_dir():
        logger.error(
            f"Module path '{pest_module_path}' does not exist or is not a directory."
        )
        return None

    # Add the parent directory of 'pest' to sys.path
    if str(pest_module_path.parent) not in sys.path:
        sys.path.append(str(pest_module_path.parent))
        logger.info(f"Added '{pest_module_path.parent}' to sys.path.")

    # Attempt to import the 'pest' module
    try:
        spec = importlib.util.find_spec("pest")
        if spec is None:
            logger.error("Module 'pest' not found.")
            return None
        pest = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pest)
        logger.info("Module 'pest' imported successfully.")
        return pest
    except ImportError as e:
        logger.error(f"Failed to import module 'pest': {e}")
        return None
