"""
Face detection and embedding package.
"""
from app.face.detector import detect_faces
from app.face.embedder import generate_embedding

__all__ = ["detect_faces", "generate_embedding"]
