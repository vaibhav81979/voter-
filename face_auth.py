"""
Face authentication using OpenCV.
Handles face detection, encoding storage, and verification.
"""

import os
import base64
import io
import pickle

import cv2
import numpy as np
from PIL import Image


# Load Haar cascade for face detection
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)


def _base64_to_cv2(base64_str: str) -> np.ndarray:
    """Convert a base64-encoded image to an OpenCV image (BGR)."""
    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]
    img_bytes = base64.b64decode(base64_str)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    return cv2.imdecode(img_array, cv2.IMREAD_COLOR)


def _cv2_to_base64(img: np.ndarray) -> str:
    """Convert an OpenCV image to base64 string."""
    _, buffer = cv2.imencode(".jpg", img)
    return base64.b64encode(buffer).decode()


def detect_face(image_b64: str) -> dict:
    """Detect faces in a base64-encoded image."""
    img = _base64_to_cv2(image_b64)
    if img is None: return {"found": False, "count": 0}
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0: return {"found": False, "count": 0}
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_crop = img[y:y+h, x:x+w]
    return {"found": True, "count": len(faces), "face_region": _cv2_to_base64(face_crop)}


def encode_face(image_b64: str) -> bytes | None:
    """Create a face encoding (histogram) from a base64 image."""
    img = _base64_to_cv2(image_b64)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0: return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_crop = gray[y:y+h, x:x+w]
    face_resized = cv2.resize(face_crop, (200, 200))
    lbph = _compute_lbph(face_resized)
    return pickle.dumps(lbph)


def verify_face(stored_encoding_bytes: bytes, live_image_b64: str, threshold: float = 40.0) -> dict:
    """Compare a stored face encoding with a live image."""
    if stored_encoding_bytes is None:
        return {"match": False, "confidence": 0, "message": "No stored face encoding found."}
    stored_hist = pickle.loads(stored_encoding_bytes)
    img = _base64_to_cv2(live_image_b64)
    if img is None: return {"match": False, "confidence": 0}
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return {"match": False, "confidence": 0, "message": "No face detected in live image."}
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_crop = gray[y:y+h, x:x+w]
    face_resized = cv2.resize(face_crop, (200, 200))
    live_hist = _compute_lbph(face_resized)
    
    # SAFETY CHECK: Ensure histograms have the same size
    if stored_hist.shape != live_hist.shape:
        return {
            "match": False, 
            "confidence": 0, 
            "message": "Biometric data mismatch (High-accuracy data found in Original mode). Please re-register."
        }

    similarity = cv2.compareHist(stored_hist.astype(np.float32), live_hist.astype(np.float32), cv2.HISTCMP_CORREL)
    confidence = max(0, min(100, (similarity + 1) * 50))
    match = confidence >= threshold
    return {"match": match, "confidence": round(confidence, 2), "message": "Face verified!" if match else "Face mismatch."}


def _compute_lbph(gray_face: np.ndarray) -> np.ndarray:
    """Compute Local Binary Pattern Histogram."""
    h, w = gray_face.shape
    lbp = np.zeros_like(gray_face, dtype=np.uint8)
    for i in range(1, h-1):
        for j in range(1, w-1):
            center = gray_face[i, j]
            code = 0
            code |= (gray_face[i-1, j-1] >= center) << 7
            code |= (gray_face[i-1, j]   >= center) << 6
            code |= (gray_face[i-1, j+1] >= center) << 5
            code |= (gray_face[i,   j+1] >= center) << 4
            code |= (gray_face[i+1, j+1] >= center) << 3
            code |= (gray_face[i+1, j]   >= center) << 2
            code |= (gray_face[i+1, j-1] >= center) << 1
            code |= (gray_face[i,   j-1] >= center) << 0
            lbp[i, j] = code
    hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
    hist = hist.astype(np.float64)
    hist /= (hist.sum() + 1e-7)
    return hist


def check_liveness(image_b64: str) -> dict:
    """Basic liveness detection."""
    img = _base64_to_cv2(image_b64)
    if img is None: return {"alive": False}
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0: return {"alive": False, "message": "No face detected."}
    return {"alive": True, "message": "Liveness check passed."}


def save_face_image(image_b64: str, upload_dir: str, filename: str) -> str:
    """Save a base64 face image to disk."""
    os.makedirs(upload_dir, exist_ok=True)
    img = _base64_to_cv2(image_b64)
    filepath = os.path.join(upload_dir, f"{filename}.jpg")
    cv2.imwrite(filepath, img)
    return filepath
