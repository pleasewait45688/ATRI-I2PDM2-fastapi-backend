import pytest
from pathlib import Path
from PIL import Image
from app.pest.i2pdm2 import QualityInspection  # Adjust import path


@pytest.fixture
def svm_model_path():
    """Fixture to provide the path to a real SVM model file."""
    basePath = Path(__file__).parent.parent / "model"
    model_path = basePath / "svm_cifar_100.pickle"
    assert model_path.exists(), f"SVM model file not found at {model_path}"
    return model_path


@pytest.fixture
def good_image_path():
    """Fixture to provide the path to a positive test image (expected success)."""
    image_path = Path(__file__).parent / "test_data" / "test_image.jpg"
    assert image_path.exists(), f"Test image file not found at {image_path}"
    return image_path


@pytest.fixture
def bad_image_path():
    """Fixture to provide the path to a negative test image (expected fail)."""
    image_path = Path(__file__).parent / "test_data" / "test_image_bad.jpg"
    assert image_path.exists(), f"Test image file not found at {image_path}"
    return image_path


def test_initialization_success(svm_model_path):
    """Test successful initialization of QualityInspection with real model."""
    quality_inspection = QualityInspection(svm_model_path=svm_model_path)

    # Assert that the CLIP model and processor are loaded
    assert quality_inspection.model is not None
    assert quality_inspection.processor is not None

    # Assert that the SVM model is loaded
    assert quality_inspection.svm_model is not None


def test_inspect_sticky_trap_success(svm_model_path, good_image_path):
    """Test the inspect_sticky_trap method for a Sticky Trap image (expected success)."""
    quality_inspection = QualityInspection(svm_model_path=svm_model_path)

    # Run the method on the positive test image
    result, processed_image = quality_inspection.inspect_sticky_trap(
        image_path=good_image_path
    )

    # Validate the result
    assert "result" in result
    assert result["result"] == "success"  # Expected outcome for the good image
    assert isinstance(processed_image, Image.Image)


def test_inspect_sticky_trap_failure(svm_model_path, bad_image_path):
    """Test the inspect_sticky_trap method for a non-Sticky Trap image (expected fail)."""
    quality_inspection = QualityInspection(svm_model_path=svm_model_path)

    # Run the method on the negative test image
    result, processed_image = quality_inspection.inspect_sticky_trap(
        image_path=bad_image_path
    )

    # Validate the result
    assert "result" in result
    assert result["result"] == "fail"  # Expected outcome for the bad image
    assert isinstance(processed_image, Image.Image)


def test_inspect_sticky_trap_invalid_image(svm_model_path):
    """Test failure when a non-existent image path is provided."""
    quality_inspection = QualityInspection(svm_model_path=svm_model_path)

    invalid_image_path = "invalid_image_path.jpg"
    with pytest.raises(RuntimeError, match="Error loading image."):
        quality_inspection.inspect_sticky_trap(image_path=invalid_image_path)
