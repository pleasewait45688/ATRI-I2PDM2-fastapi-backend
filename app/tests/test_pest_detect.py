from fastapi.testclient import TestClient
from app.main import app  # Import the FastAPI app from main.py
import uuid
from pathlib import Path
import pytest
import shutil
from app.core.config import settings


@pytest.fixture
def client():
    return TestClient(app)


UPLOAD_DIR = Path(__file__).parents[2] / "tmp"


@pytest.fixture
def clean_upload_dir():
    """Fixture to clean the upload directory before each test."""
    print("Setup before module")
    yield
    print("Teardown after module")
    if UPLOAD_DIR.exists() and UPLOAD_DIR.is_dir():
        shutil.rmtree(UPLOAD_DIR)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_image_path(filename: str) -> Path:
    """Returns the path to the test image."""
    return Path(__file__).parent / "assets" / filename


def upload_image(client: TestClient, image_path: Path, content_type: str):
    """Uploads an image and returns the response."""
    with image_path.open("rb") as image_file:
        response = client.post(
            f"{settings.API_V1_STR}/pest-detect/upload/",
            files={"file": (image_path.name, image_file, content_type)},
        )
    return response


def validate_uuid4(uuid_string: str):
    """Validates that a string is a valid UUID4."""
    try:
        uuid_obj = uuid.UUID(uuid_string, version=4)
    except ValueError:
        pytest.fail(f"'id' is not a valid UUID4: {uuid_string}")
    assert uuid_obj.version == 4, f"'id' is not a UUID4: {uuid_string}"


def test_pest_detect_root(client):
    response = client.get(f"{settings.API_V1_STR}/pest-detect/")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "image_filename, content_type",
    [
        ("test_image.jpg", "image/jpeg"),
        ("test_image.heic", "image/heic"),
    ],
)
def test_pest_detect_upload(client, image_filename, content_type):
    image_path = get_image_path(image_filename)
    response = upload_image(client, image_path, content_type)

    assert (
        response.status_code == 200
    ), f"Expected status code 200, got {response.status_code}"

    response_json = response.json()
    assert "id" in response_json, "Response JSON does not contain 'id' field"

    image_id = response_json["id"]
    validate_uuid4(image_id)


def test_pest_detect_upload_invalid_file_type(client):
    invalid_file_path = get_image_path("test_invalid_image.txt")
    assert invalid_file_path.exists(), f"Test file not found: {invalid_file_path}"

    with invalid_file_path.open("rb") as invalid_file:
        response = client.post(
            f"{settings.API_V1_STR}/pest-detect/upload/",
            files={"file": ("test_invalid_image.txt", invalid_file, "text/plain")},
        )

    assert (
        response.status_code == 400
    ), f"Expected status code 400, got {response.status_code}"

    response_json = response.json()
    expected_detail = "Invalid file type. Only JPEG, PNG, and HEIC are allowed."
    assert (
        response_json.get("detail") == expected_detail
    ), f"Expected detail message '{expected_detail}', got '{response_json.get('detail')}'"


@pytest.mark.parametrize(
    "image_filename, content_type",
    [
        ("test_image.jpg", "image/jpeg"),
        ("test_image.heic", "image/heic"),
    ],
)
def test_pest_detect_preprocess(client, image_filename, content_type):
    image_path = get_image_path(image_filename)
    upload_response = upload_image(client, image_path, content_type)

    assert (
        upload_response.status_code == 200
    ), f"Expected status code 200, got {upload_response.status_code}"

    image_id = upload_response.json()["id"]
    validate_uuid4(image_id)

    preprocess_response = client.get(
        f"{settings.API_V1_STR}/pest-detect/preprocess/{image_id}"
    )
    assert (
        preprocess_response.status_code == 200
    ), f"Expected status code 200, got {preprocess_response.status_code}"

    preprocess_json = preprocess_response.json()
    assert (
        preprocess_json.get("result") == "success"
    ), f"Expected preprocess result 'success', got: {preprocess_json.get('result')}"


def test_preprocess_invalid_uuid(client):
    response = client.get(f"{settings.API_V1_STR}/pest-detect/preprocess/invalid-uuid")
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid image ID format: invalid-uuid. Expected a valid UUID4."
    }


def test_preprocess_image_not_found(client):
    non_existent_uuid = (
        "711ac0c4-8b0b-4fe4-8b63-ea5fcf72ba7d"  # Replace with a UUID that doesn't exist
    )
    response = client.get(
        f"{settings.API_V1_STR}/pest-detect/preprocess/{non_existent_uuid}"
    )
    assert response.status_code == 404
    assert response.json() == {
        "detail": f"Image with ID {non_existent_uuid} not found in the upload directory."
    }


def test_detect_invalid_uuid(client):
    response = client.get(f"{settings.API_V1_STR}/pest-detect/detect/invalid-uuid")
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid image ID format."}


def test_detect_image_not_found(client):
    non_existent_uuid = (
        "711ac0c4-8b0b-4fe4-8b63-ea5fcf72ba7d"  # Replace with a UUID that doesn't exist
    )
    response = client.get(
        f"{settings.API_V1_STR}/pest-detect/detect/{non_existent_uuid}"
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Image not found."}


@pytest.mark.parametrize(
    "image_filename, content_type",
    [
        ("test_image.jpg", "image/jpeg"),
        ("test_image.heic", "image/heic"),
    ],
)
def test_pest_detect_detect(client, image_filename, content_type):
    image_path = get_image_path(image_filename)
    upload_response = upload_image(client, image_path, content_type)

    assert (
        upload_response.status_code == 200
    ), f"Expected status code 200, got {upload_response.status_code}"

    image_id = upload_response.json()["id"]
    validate_uuid4(image_id)

    preprocess_response = client.get(
        f"{settings.API_V1_STR}/pest-detect/preprocess/{image_id}"
    )
    assert (
        preprocess_response.status_code == 200
    ), f"Expected status code 200, got {preprocess_response.status_code}"

    detect_response = client.get(f"{settings.API_V1_STR}/pest-detect/detect/{image_id}")
    assert (
        detect_response.status_code == 200
    ), f"Expected status code 200, got {detect_response.status_code}"

    detect_json = detect_response.json()
    assert (
        detect_json.get("result") != "failed"
    ), f"Expected detect result not failed, got: {detect_json.get('result')}"
