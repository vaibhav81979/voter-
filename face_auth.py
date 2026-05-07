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

# LBPHFaceRecognizer for face recognition
_recognizer = None
_recognizer_trained = False


def _base64_to_cv2(base64_str: str) -> np.ndarray:
    """Convert a base64-encoded image to an OpenCV image (BGR)."""
    # Strip data URL prefix if present
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
    """
    Detect faces in a base64-encoded image.
    Returns dict with 'found' (bool), 'count' (int), 'face_region' (cropped face as base64).
    """
    img = _base64_to_cv2(image_b64)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )

    if len(faces) == 0:
        return {"found": False, "count": 0, "face_region": None}

    # Take the largest face
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_crop = img[y : y + h, x : x + w]

    return {
        "found": True,
        "count": len(faces),
        "face_region": _cv2_to_base64(face_crop),
        "bbox": [int(x), int(y), int(w), int(h)],
    }


def encode_face(image_b64: str) -> bytes | None:
    """
    Create a face encoding (histogram) from a base64 image.
    Returns pickled encoding bytes, or None if no face found.
    """
    img = _base64_to_cv2(image_b64)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )

    if len(faces) == 0:
        return None

    # Take the largest face
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_crop = gray[y : y + h, x : x + w]

    # Resize to standard size for consistent encoding
    face_resized = cv2.resize(face_crop, (200, 200))

    # Create LBPH histogram as the face encoding
    lbph = _compute_lbph(face_resized)
    return pickle.dumps(lbph)


def verify_face(stored_encoding_bytes: bytes, live_image_b64: str, threshold: float = 40.0) -> dict:
    """
    Compare a stored face encoding with a live image.
    Returns dict with 'match' (bool), 'confidence' (float 0-100), 'message'.
    """
    if stored_encoding_bytes is None:
        return {"match": False, "confidence": 0, "message": "No stored face encoding found."}

    stored_hist = pickle.loads(stored_encoding_bytes)

    img = _base64_to_cv2(live_image_b64)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )

    if len(faces) == 0:
        return {"match": False, "confidence": 0, "message": "No face detected in live image."}

    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_crop = gray[y : y + h, x : x + w]
    face_resized = cv2.resize(face_crop, (200, 200))

    live_hist = _compute_lbph(face_resized)

    # Compare histograms using correlation
    similarity = cv2.compareHist(
        stored_hist.astype(np.float32),
        live_hist.astype(np.float32),
        cv2.HISTCMP_CORREL,
    )

    # Convert correlation (-1 to 1) to confidence (0 to 100)
    confidence = max(0, min(100, (similarity + 1) * 50))

    match = confidence >= threshold

    return {
        "match": match,
        "confidence": round(confidence, 2),
        "message": "Face verified successfully!" if match else "Face did not match.",
    }


def check_liveness(image_b64: str) -> dict:
    """
    Basic liveness detection.
    Checks for reasonable face proportions and image quality.
    """
    img = _base64_to_cv2(image_b64)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )

    if len(faces) == 0:
        return {"alive": False, "message": "No face detected."}

    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

    # Basic checks
    aspect_ratio = w / h if h > 0 else 0
    img_area = img.shape[0] * img.shape[1]
    face_area = w * h
    face_ratio = face_area / img_area if img_area > 0 else 0

    # Check image isn't too blurry
    face_crop = gray[y : y + h, x : x + w]
    laplacian_var = cv2.Laplacian(face_crop, cv2.CV_64F).var()

    checks = {
        "face_detected": True,
        "aspect_ratio_ok": 0.5 < aspect_ratio < 2.0,
        "face_size_ok": face_ratio > 0.01,
        "image_quality_ok": laplacian_var > 5,
    }

    is_alive = all(checks.values())

    return {
        "alive": is_alive,
        "checks": checks,
        "message": "Liveness check passed." if is_alive else "Liveness check failed. Please ensure good lighting and face the camera directly.",
    }


def save_face_image(image_b64: str, upload_dir: str, filename: str) -> str:
    """Save a base64 face image to disk. Returns the file path."""
    os.makedirs(upload_dir, exist_ok=True)
    img = _base64_to_cv2(image_b64)
    filepath = os.path.join(upload_dir, f"{filename}.jpg")
    cv2.imwrite(filepath, img)
    return filepath


def _compute_lbph(gray_face: np.ndarray) -> np.ndarray:
    """Compute Local Binary Pattern Histogram for a grayscale face image."""
    radius = 1
    n_points = 8 * radius
    h, w = gray_face.shape
    lbp = np.zeros_like(gray_face, dtype=np.uint8)

    for i in range(radius, h - radius):
        for j in range(radius, w - radius):
            center = gray_face[i, j]
            code = 0
            code |= (gray_face[i - 1, j - 1] >= center) << 7
            code |= (gray_face[i - 1, j] >= center) << 6
            code |= (gray_face[i - 1, j + 1] >= center) << 5
            code |= (gray_face[i, j + 1] >= center) << 4
            code |= (gray_face[i + 1, j + 1] >= center) << 3
            code |= (gray_face[i + 1, j] >= center) << 2
            code |= (gray_face[i + 1, j - 1] >= center) << 1
            code |= (gray_face[i, j - 1] >= center) << 0
            lbp[i, j] = code

    # Compute histogram
    hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
    hist = hist.astype(np.float64)
    hist /= hist.sum() + 1e-7  # Normalize
    return hist
