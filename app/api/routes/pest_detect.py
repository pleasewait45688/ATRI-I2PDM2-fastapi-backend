import logging
import pillow_heif
import uuid
from pathlib import Path
from PIL import Image
from io import BytesIO
import base64
import gc
from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks, Response
from fastapi.responses import FileResponse
from app.pest.i2pdm2 import YOLOv11Detector, QualityInspection, PieChart
import torch
import GPUtil
import asyncio

from sqlalchemy.orm import Session
from fastapi import Depends
from app.db.dependency import get_db
from app.db.models import PestResult

# Configure logging

logger = logging.getLogger(__name__)


router = APIRouter()

# Determine the path two levels up from the current file
base_dir = Path(__file__).resolve().parents[3]

# Define the path for the 'tmp' directory within this base directory
UPLOAD_DIR = base_dir / "tmp"

# Create the 'tmp' directory if it doesn't already exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

model_dir = base_dir / "app" / "pest" / "model"

yolo_model_path = model_dir / "best.pt"

# ResNet classifier paths (for two-stage classification)
classifier_model_path = model_dir / "resnet18_best_model_513d.pth"
classifier_label_path = model_dir / "labels.json"

svm_model_path = model_dir / "svm_cifar_100.pickle"

# Global variables for models
detect_model = None
quality_model = None

GPUMEM_THRESHOLD = 2048  # mb
reload_lock = asyncio.Lock()


def initialize_models():
    global detect_model, quality_model
    detect_model = YOLOv11Detector(
        yolo_model=yolo_model_path,
        classifier_model_path=classifier_model_path,
        classifier_label_path=classifier_label_path,
    )
    quality_model = QualityInspection(svm_model_path=svm_model_path)


initialize_models()

# TODO: Move model inference to worker, and establish queue in the future.


def image_exists(image_id: str) -> bool:
    image_folder = UPLOAD_DIR / image_id
    return image_folder.exists() and any(image_folder.iterdir())


# TODO: Maybe reload until success.


async def reload_model():
    async with reload_lock:
        global detect_model, quality_model
        logger.info("Starting model reload.")
        try:
            # Cleanup current models
            del detect_model
            del quality_model
            gc.collect()
            torch.cuda.empty_cache()

            # Reinitialize models
            initialize_models()
            logger.info("Model reload successful.")
        except Exception as e:
            logger.error(f"Error during model reload: {e}")
            raise RuntimeError("Model reload failed.") from e


# TODO: use Celery in the future and don't use background task for this....
def gpu_available() -> bool:
    try:
        available_memory = GPUtil.getGPUs()[0].memoryFree
        logger.info(f"Available GPU Memory: {available_memory} MB")
        return available_memory >= GPUMEM_THRESHOLD
    except Exception as e:
        logger.error(f"Error checking GPU availability: {e}")
        return False


@router.get("/")
async def read_main():
    print("====================")
    logger.warning("API PEST DETECT")
    return {"msg": "PEST_DETECT"}


@router.get("/status")
async def check_status(response: Response, background_tasks: BackgroundTasks):
    if reload_lock.locked():
        logger.warning("Server is currently reloading the model.")
        raise HTTPException(
            status_code=503,
            detail="The server is busy. Please try again later.",
        )

    if not gpu_available():
        logger.warning("GPU OOM detected. Initiating model reload.")
        try:
            background_tasks.add_task(reload_model)
            response.status_code = 503
            return {"result": "The server is busy. Please try again later."}
        except RuntimeError as e:
            logger.error(f"Failed to enqueue model reload task: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error occurred while reloading the model.",
            )

    response.status_code = 202
    return {"result": "ready"}


@router.post("/upload/")
async def upload_image(file: UploadFile):
    if reload_lock.locked():
        logger.warning("Server is currently reloading the model.")
        raise HTTPException(
            status_code=503,
            detail="The server is busy. Please try again later.",
        )
    # Validate the uploaded file's content type
    if file.content_type not in ["image/jpeg", "image/png", "image/heic"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, and HEIC are allowed.",
        )

    # Generate a unique ID for the image
    image_id = str(uuid.uuid4())

    # Create a folder inside 'tmp' named after the UUID
    image_folder = UPLOAD_DIR / image_id
    image_folder.mkdir(parents=True, exist_ok=True)

    # Define the path to save the image inside the UUID folder
    # image_filename = file.filename
    image_path = image_folder / f"{image_id}.jpg"

    # Read the uploaded file
    file_content = await file.read()

    # Check if the file is in HEIC format
    if file.content_type == "image/heic":
        # Convert HEIC to JPEG
        heif_file = pillow_heif.read_heif(file_content)
        image = Image.frombytes(
            heif_file.mode, heif_file.size, heif_file.data, "raw", heif_file.mode
        )
        # Save the converted image as JPEG
        image_path = image_path.with_suffix(".jpg")

         # TODO: trying to fix the upload quality
        # image.save(image_path, format="JPEG")
        image.save(image_path, format="JPEG", quality=95, subsampling=0, optimize=True, progressive=True)

    else:
        image = Image.open(BytesIO(file_content))
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(image_path, format="JPEG", quality=95, subsampling=0, optimize=True, progressive=True)

    # Log the dimensions of the uploaded image
    if image:
        width, height = image.size
        logger.info(f"Uploaded image size: Width={width}px, Height={height}px")

    # Return the unique ID as the response
    return {"id": image_id}


@router.get("/preprocess/{image_id}")
async def preprocess(image_id: str):
    if reload_lock.locked():
        logger.warning("Server is currently reloading the model.")
        raise HTTPException(
            status_code=503,
            detail="The server is busy. Please try again later.",
        )
    logger.info(f"Received request to preprocess image with ID: {image_id}")
    # Step 1: Validate the UUID

    try:
        _ = uuid.UUID(image_id, version=4)
        logger.debug(f"Validated image ID as UUID4: {image_id}")
    except ValueError as e:
        logger.warning(
            f"Invalid image ID format received: {image_id} | Error: {str(e)}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image ID format: {image_id}. Expected a valid UUID4.",
        )

    # Step 2: Check if the image exists
    logger.debug(f"Checking existence of image with ID: {image_id}")
    if not image_exists(image_id):
        logger.warning(f"Image not found for ID: {image_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Image with ID {image_id} not found in the upload directory.",
        )
    logger.debug(f"Image found for ID: {image_id}")

    # Define paths for image and processed output
    image_path = UPLOAD_DIR / image_id / f"{image_id}.jpg"
    output_image_path = UPLOAD_DIR / image_id / f"{image_id}_proc.jpg"
    logger.debug(
        f"Paths defined - Original: {image_path}, Processed: {output_image_path}"
    )

    # Step 3: Read and preprocess the image
    logger.info(f"Starting preprocessing for image with ID: {image_id}")
    try:
        result_json, image_after_clip = quality_model.inspect_sticky_trap(image_path)
        logger.debug(f"Preprocessing result: {result_json}")
    except Exception as e:
        logger.error(
            f"Error during preprocessing for image ID: {image_id} | Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during preprocessing: {str(e)}",
        )

    # Step 4: Check preprocessing result
    if result_json.get("result") != "success":
        logger.error(
            f"Preprocessing failed for image ID: {image_id} | Result: {result_json.get('msg')}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Preprocessing failed. Result: {result_json.get('msg')}",
        )

    logger.info(f"Preprocessing successful for image ID: {image_id}")

    # Step 5: Save the image after quality-check preprocessing
    try:
        image_after_clip.save(output_image_path, format="JPEG", quality=95, subsampling=0, optimize=True, progressive=True)
        logger.info(
            f"Processed image saved successfully for ID: {image_id} at {output_image_path}"
        )
    except Exception as e:
        logger.error(
            f"Failed to save processed image for ID: {image_id} | Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save processed image. Error: {str(e)}",
        )

    logger.info(f"Preprocessing completed successfully for image ID: {image_id}")
    return result_json


@router.get("/detect/{image_id}")
async def inference(image_id: str, db: Session = Depends(get_db)):
    if reload_lock.locked():
        logger.warning("Server is currently reloading the model.")
        raise HTTPException(
            status_code=503,
            detail="The server is busy. Please try again later.",
        )

    logger.info(f"Received request for inference on image ID: {image_id}")

    # Validate the UUID
    try:
        uuid_obj = uuid.UUID(image_id, version=4)
        logger.debug(f"Validated image ID as a valid UUID4: {uuid_obj}")
    except ValueError as e:
        logger.warning(f"Invalid image ID format: {image_id}")
        logger.debug(f"Error details: {e}")
        raise HTTPException(status_code=400, detail="Invalid image ID format.")

    # Check if the image exists
    image_path = UPLOAD_DIR / image_id / f"{image_id}_proc.jpg"
    if not image_path.exists():
        logger.warning(f"Processed image not found for ID: {image_id}")
        raise HTTPException(status_code=404, detail="Image not found.")
    logger.debug(f"Image found at path: {image_path}")

    output_image_path = UPLOAD_DIR / image_id / f"{image_id}_inf.jpg"
    logger.debug(f"Output path for inference result set to: {output_image_path}")

    try:
        logger.info(f"Running detection model for image ID: {image_id}")
        result_json, result_image = detect_model.detect(image_path)
        logger.debug(f"Detection model output: {result_json}")

        total_value = sum(result_json.values())

        # Add a new key with the total
        result_json["總數"] = total_value

    except Exception as e:
        logger.error(f"Error during model inference for image ID: {image_id}")
        logger.debug(f"Error details: {e}")
        raise HTTPException(
            status_code=500, detail="An error occurred during model inference."
        )

    logger.info(f"Inference result details: {result_json}")

    # Convert and save the result image
    try:
        # Convert cv2 Mat (BGR) to RGB
        # result_image_rgb = cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB)
        # Create a PIL image from the RGB array
        result_image_array = Image.fromarray(result_image)
        # Save the image to the specified path
        result_image_array.save(output_image_path)
        logger.info(
            f"Saved inference result image for ID: {image_id} at {output_image_path}"
        )

        # Convert the image to Base64
        buffered = BytesIO()
        result_image_array.save(buffered, format="JPEG")
        encoded_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
        logger.debug("Encoded image as Base64 for response.")

    except Exception as e:
        logger.error(
            f"Failed to save and encode inference result image for ID: {image_id}"
        )
        logger.debug(f"Error details: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to save and encode inference result image."
        )
    
    # add the pie chart after detecting
    chart_image_path = UPLOAD_DIR / image_id / f"{image_id}_pie.jpg"
    try:
        logger.info(f"Generating pie chart for image ID: {image_id}")
        pie_chart = PieChart(result_json, title="害蟲比例")
        pie_chart.save_image(chart_image_path, format="jpg")
        logger.info(f"Saved pie chart for image ID: {image_id} at {chart_image_path}")

    except Exception as e:
        logger.error(f"Failed to generate and save pie chart for ID: {image_id}")
        logger.debug(f"Error details: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate and save pie chart."
        )

    logger.info(f"Inference and pie chart generation completed successfully for image ID: {image_id}")

    # 寫入資料庫
    try:
        record = PestResult(
            uuid=image_id,
            image_path=str(output_image_path),
            result=str(result_json)
        )
        db.add(record)
        db.commit()
        logger.info("✅ 寫入資料庫成功")
    except Exception as e:
        logger.error(f"❌ 寫入資料庫失敗: {e}")

    # Include the Base64 image in the response
    response = {
        "result": result_json,
        "image": encoded_image,  # Base64 encoded image
    }

    logger.info(f"Inference completed successfully for image ID: {image_id}")
    return response


@router.get("/chart/{image_id}")
async def get_pie_chart(image_id: str):
    """
    Retrieve and return the Pie Chart image.
    """
    try:
        pie_chart_path = UPLOAD_DIR / image_id / f"{image_id}_pie.jpg"

        # Check if the file exists
        if not pie_chart_path.exists():
            logger.warning(f"Pie Chart not found: {pie_chart_path}")
            raise HTTPException(status_code=404, detail="Pie Chart not found. Please run /detect/{image_id} first.")

        logger.info(f"Returning Pie Chart: {pie_chart_path}")
        return FileResponse(pie_chart_path)

    except Exception as e:
        logger.error(f"Failed to retrieve Pie Chart: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error. Unable to retrieve the Pie Chart.")