import pytest
import numpy as np
from app.face.detector import detect_single_face, detect_all_faces, check_image_quality

def test_single_face_detection():
    """Validates face detection returns count=1 for valid sample input image."""
    result = detect_single_face("samples/input.jpg")
    assert result["face_count"] == 1
    assert "facial_area" in result
    assert "face_crop" in result

def test_detect_all_faces():
    """Validates detect_all_faces returns list of face dicts."""
    faces = detect_all_faces("samples/input.jpg")
    assert isinstance(faces, list)
    assert len(faces) >= 1

def test_missing_image_rejection():
    """Validates missing file raises ValueError."""
    with pytest.raises(ValueError):
        detect_single_face("samples/non_existent_file.jpg")

def test_image_quality_gating():
    """Validates image quality and blur check function."""
    tiny_crop = np.zeros((30, 30, 3), dtype=np.uint8)
    is_ok, reason = check_image_quality(tiny_crop)
    assert is_ok is False
    assert "too small" in reason

