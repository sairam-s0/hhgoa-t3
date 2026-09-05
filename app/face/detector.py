import os
import io
import cv2
import numpy as np
from PIL import Image, ImageOps

def detect_single_face(image_input: str | bytes | np.ndarray) -> dict:
    """
    Detects a single face in an input image for primary target verification.
    Enforces exactly 1 face constraint.
    
    Returns:
        dict: {
            "face_count": 1,
            "facial_area": (x, y, w, h),
            "img_array": np.ndarray,
            "face_crop": np.ndarray  # Aligned facial BGR image
        }
    """
    faces = detect_all_faces(image_input)
    face_count = len(faces)

    if face_count == 0:
        raise ValueError("0 faces detected. Input image must contain exactly one face.")
    if face_count > 1:
        raise ValueError(f"{face_count} faces detected. Target image must contain exactly one face (rejected group photo).")

    return {
        "face_count": 1,
        "facial_area": faces[0]["facial_area"],
        "img_array": faces[0]["img_array"],
        "face_crop": faces[0]["face_crop"],
        "confidence": faces[0]["confidence"]
    }


# Alias for backward compatibility
detect_faces = detect_single_face


def detect_all_faces(image_input: str | bytes | np.ndarray) -> list[dict]:
    """
    Detects and extracts ALL aligned faces in an image for web candidate matching.
    Does NOT reject multi-face group photos.
    
    Returns:
        List of dicts: [
            {
                "facial_area": (x, y, w, h),
                "confidence": float,
                "img_array": np.ndarray,
                "face_crop": np.ndarray  # Aligned facial BGR image
            }
        ]
    """
    img_array = _to_opencv_image(image_input)
    if img_array is None:
        return []

    # Primary: DeepFace / RetinaFace face extraction with alignment
    faces = _detect_deepface_aligned(img_array)
    if not faces:
        # Secondary fallback: OpenCV face detection
        faces = _detect_opencv_crop(img_array)

    # Filter faces by quality and blur level
    valid_faces = []
    for face in faces:
        is_ok, reason = check_image_quality(face["face_crop"])
        if is_ok:
            valid_faces.append(face)
        else:
            print(f"[Detector Gating] Rejecting face crop: {reason}")

    return valid_faces


def check_image_quality(face_crop: np.ndarray, min_size: int = 40, min_blur_var: float = 15.0) -> tuple[bool, str]:
    """
    Validates face crop dimensions and blur level using Laplacian variance.
    """
    if face_crop is None or face_crop.size == 0:
        return False, "Empty face crop"

    h, w = face_crop.shape[:2]
    if h < min_size or w < min_size:
        return False, f"Crop size too small ({w}x{h}px < {min_size}px)"

    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if len(face_crop.shape) == 3 else face_crop
    blur_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_var < min_blur_var:
        return False, f"Crop heavily blurred (Laplacian variance {blur_var:.2f} < {min_blur_var})"

    return True, "OK"



def _to_opencv_image(image_input: str | bytes | np.ndarray) -> np.ndarray | None:
    """Converts input (path, bytes, ndarray) into an EXIF-oriented OpenCV BGR numpy array."""
    if isinstance(image_input, np.ndarray):
        return image_input

    try:
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return None
            pil_img = Image.open(image_input)
        elif isinstance(image_input, bytes):
            pil_img = Image.open(io.BytesIO(image_input))
        else:
            return None

        # Auto-rotate based on EXIF orientation tags
        pil_img = ImageOps.exif_transpose(pil_img).convert("RGB")
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        # Fallback to direct OpenCV decode
        if isinstance(image_input, str) and os.path.exists(image_input):
            return cv2.imread(image_input)
        if isinstance(image_input, bytes):
            nparr = np.frombuffer(image_input, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return None


def _detect_deepface_aligned(img_array: np.ndarray) -> list[dict]:
    """
    Detects and extracts aligned faces using DeepFace (RetinaFace / OpenCV backend).
    Returns landmark-aligned BGR face crops.
    """
    # Try RetinaFace first, fallback to opencv backend
    backends = ["retinaface", "opencv"]
    for backend in backends:
        try:
            from deepface import DeepFace
            results = DeepFace.extract_faces(
                img_path=img_array,
                detector_backend=backend,
                align=True,
                enforce_detection=False
            )
            detected = []
            for r in results:
                area = r.get("facial_area", {})
                confidence = r.get("confidence", 0.0)
                w = area.get("w", 0)
                h = area.get("h", 0)

                # Confidence threshold >= 0.70 for RetinaFace, 0.50 for OpenCV
                min_conf = 0.70 if backend == "retinaface" else 0.50
                if confidence >= min_conf and w >= 30 and h >= 30:
                    raw_face = r.get("face")
                    if raw_face is not None:
                        # DeepFace aligned face is RGB float [0..1], convert to BGR uint8 [0..255]
                        if raw_face.dtype != np.uint8:
                            face_bgr = cv2.cvtColor((raw_face * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
                        else:
                            face_bgr = cv2.cvtColor(raw_face, cv2.COLOR_RGB2BGR)
                    else:
                        x_c, y_c = max(0, area["x"]), max(0, area["y"])
                        face_bgr = img_array[y_c:y_c+h, x_c:x_c+w]

                    detected.append({
                        "facial_area": (area["x"], area["y"], area["w"], area["h"]),
                        "confidence": confidence,
                        "img_array": img_array,
                        "face_crop": face_bgr
                    })
            if detected:
                return detected
        except Exception as e:
            print(f"[DeepFace {backend} Detector Info] {e}")
            continue

    return []


def _detect_opencv_crop(img_array: np.ndarray) -> list[dict]:
    """Detects faces using OpenCV Cascade classifier."""
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.05,
        minNeighbors=7,
        minSize=(50, 50)
    )

    results = []
    img_h, img_w = img_array.shape[:2]
    for (x, y, w, h) in faces:
        x_c, y_c = max(0, int(x)), max(0, int(y))
        w_c, h_c = min(img_w - x_c, int(w)), min(img_h - y_c, int(h))
        crop = img_array[y_c:y_c+h_c, x_c:x_c+w_c]
        results.append({
            "facial_area": (x_c, y_c, w_c, h_c),
            "confidence": 0.85,
            "img_array": img_array,
            "face_crop": crop
        })

    return results






