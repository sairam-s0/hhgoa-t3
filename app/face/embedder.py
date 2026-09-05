import os
import cv2
import numpy as np

def generate_embedding(image_input: str | bytes | np.ndarray, model_name: str = "ArcFace") -> np.ndarray:
    """
    Generates a L2-normalized ArcFace embedding vector for an input image.
    
    Args:
        image_input: File path, raw bytes, or numpy array.
        model_name: Model architecture to use (default: ArcFace).
        
    Returns:
        np.ndarray: Normalized 1D embedding vector (norm = 1.0).
    """
    img_array = _to_bgr_array(image_input)
    if img_array is None:
        raise ValueError("Invalid image input for embedding generation.")

    try:
        from deepface import DeepFace
        # Run DeepFace.represent with ArcFace
        results = DeepFace.represent(
            img_path=img_array,
            model_name=model_name,
            enforce_detection=False
        )
        if results and len(results) > 0:
            raw_vector = np.array(results[0]["embedding"], dtype=np.float32)
            # L2 Normalize: embedding = embedding / np.linalg.norm(embedding)
            norm = np.linalg.norm(raw_vector)
            if norm > 0:
                return raw_vector / norm
            return raw_vector
        raise RuntimeError(f"{model_name} returned no embedding representation for image.")
    except Exception as e:
        raise RuntimeError(f"ArcFace embedding generation failed: {e}")


def generate_dual_embedding(image_input: str | bytes | np.ndarray) -> dict[str, np.ndarray]:
    """
    Generates L2-normalized embeddings for both ArcFace and Facenet512 models to ensure redundancy.
    
    Returns:
        dict: {
            "arcface": np.ndarray,
            "facenet512": np.ndarray
        }
    """
    arcface_vec = generate_embedding(image_input, model_name="ArcFace")
    try:
        facenet_vec = generate_embedding(image_input, model_name="Facenet512")
    except Exception as e:
        print(f"[Facenet512 Embedding Info] {e}, continuing with ArcFace vector")
        facenet_vec = arcface_vec

    return {
        "arcface": arcface_vec,
        "facenet512": facenet_vec
    }


def _to_bgr_array(image_input: str | bytes | np.ndarray) -> np.ndarray | None:
    if isinstance(image_input, np.ndarray):
        return image_input
    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            return None
        return cv2.imread(image_input)
    if isinstance(image_input, bytes):
        nparr = np.frombuffer(image_input, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return None


