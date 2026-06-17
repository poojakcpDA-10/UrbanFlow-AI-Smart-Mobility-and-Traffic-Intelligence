"""
License Plate Recognition (LPR) Service
========================================
Real OCR-based plate reading using EasyOCR + OpenCV.

Pipeline:
  1. Capture frame from camera (live webcam or uploaded image/video frame)
  2. Pre-process: CLAHE → grayscale → denoise → threshold
  3. Detect plate region via contour filtering (aspect ratio + area heuristics)
  4. Run EasyOCR on the cropped region
  5. Post-process: clean text, apply Indian/generic plate regex validation
  6. Return plate number, confidence, bounding box, annotated frame

Falls back gracefully when:
  - No camera connected (uses provided image bytes)
  - EasyOCR not installed (returns install instructions)
  - No plate found in frame (returns None with reason)
"""

import cv2
import numpy as np
import re
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── EasyOCR lazy-load (heavy model, load once) ────────────────────────────────
_reader = None
_reader_error = None

def _get_reader():
    global _reader, _reader_error
    if _reader is not None:
        return _reader, None
    if _reader_error is not None:
        return None, _reader_error
    try:
        import easyocr
        logger.info("Loading EasyOCR model (first run may take ~30s)...")
        _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        logger.info("EasyOCR ready.")
        return _reader, None
    except ImportError:
        _reader_error = (
            "EasyOCR not installed. Run: pip install easyocr --break-system-packages"
        )
        return None, _reader_error
    except Exception as e:
        _reader_error = f"EasyOCR init error: {e}"
        return None, _reader_error


# ── Plate regex patterns ───────────────────────────────────────────────────────
# Indian format: KA01AB1234, MH12CD5678, DL3CAF3456 etc.
PLATE_PATTERNS = [
    re.compile(r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$'),      # KA01AB1234
    re.compile(r'^[A-Z]{2}\d{2}[A-Z]{1,3}\d{3,4}$'),    # KA01ABC123
    re.compile(r'^[A-Z]{2}\d{1,2}[A-Z]{2,3}\d{4}$'),    # DL3CAF3456
    re.compile(r'^[A-Z0-9]{5,12}$'),                      # Generic fallback
]

def _is_valid_plate(text: str) -> bool:
    text = text.upper().replace(' ', '').replace('-', '')
    return any(p.match(text) for p in PLATE_PATTERNS)

def _clean_plate(text: str) -> str:
    """Normalize OCR output to plate format."""
    text = text.upper()
    # Common OCR misreads on plates
    text = text.replace('O', '0').replace('I', '1').replace('Q', '0')
    # Keep only alphanumeric
    text = re.sub(r'[^A-Z0-9]', '', text)
    return text


# ── Image pre-processing ──────────────────────────────────────────────────────
def _preprocess_frame(frame: np.ndarray) -> np.ndarray:
    """Enhance frame for better plate detection."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # CLAHE for contrast normalisation (helps in low-light)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    # Bilateral filter — removes noise while preserving edges
    denoised = cv2.bilateralFilter(enhanced, 11, 17, 17)
    return denoised


def _find_plate_regions(frame: np.ndarray, preprocessed: np.ndarray):
    """
    Detect candidate plate regions using edge detection + contour filtering.
    Returns list of (x, y, w, h) bounding boxes sorted by confidence score.
    """
    edges = cv2.Canny(preprocessed, 30, 200)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]

    h_frame, w_frame = frame.shape[:2]
    candidates = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = w / float(h) if h > 0 else 0
        area = w * h
        area_ratio = area / (h_frame * w_frame)

        # Plate aspect ratio: typically 2:1 to 5:1, area: 0.3%–8% of frame
        if 1.5 <= aspect_ratio <= 6.0 and 0.003 <= area_ratio <= 0.08:
            # Add padding around the region
            pad = 5
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(w_frame, x + w + pad)
            y2 = min(h_frame, y + h + pad)
            candidates.append((x1, y1, x2 - x1, y2 - y1, aspect_ratio))

    return candidates


# ── Core OCR function ─────────────────────────────────────────────────────────
def read_plate_from_frame(frame: np.ndarray, camera_id: str = 'CAM-001'):
    """
    Main entry: detect and read plate from a BGR OpenCV frame.

    Returns dict:
        plate_number  : str or None
        confidence    : float 0–1
        bbox          : (x, y, w, h) or None
        annotated     : np.ndarray with box drawn
        raw_results   : list of all OCR hits
        method        : 'region_ocr' | 'full_frame_ocr' | 'none'
        error         : str or None
    """
    reader, err = _get_reader()
    if err:
        return {
            'plate_number': None, 'confidence': 0.0,
            'bbox': None, 'annotated': frame,
            'raw_results': [], 'method': 'none',
            'error': err
        }

    result = {
        'plate_number': None, 'confidence': 0.0,
        'bbox': None, 'annotated': frame.copy(),
        'raw_results': [], 'method': 'none',
        'error': None
    }

    preprocessed = _preprocess_frame(frame)
    candidates = _find_plate_regions(frame, preprocessed)

    best_plate = None
    best_conf = 0.0
    best_bbox = None

    # ── Strategy 1: OCR on detected plate regions ─────────────────────────
    for (x, y, w, h, _) in candidates[:8]:
        crop = frame[y:y+h, x:x+w]
        if crop.size == 0:
            continue

        # Upscale small crops for better OCR
        scale = max(1, int(200 / h))
        if scale > 1:
            crop = cv2.resize(crop, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

        ocr_results = reader.readtext(crop, detail=1, paragraph=False,
                                       allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ')
        for (_, text, conf) in ocr_results:
            cleaned = _clean_plate(text)
            if len(cleaned) >= 5 and conf > best_conf:
                if _is_valid_plate(cleaned) or (len(cleaned) >= 6 and conf > 0.7):
                    best_plate = cleaned
                    best_conf = conf
                    best_bbox = (x, y, w, h)
                    result['raw_results'].append({'text': text, 'cleaned': cleaned, 'conf': round(conf, 3), 'region': (x,y,w,h)})

    if best_plate:
        result['method'] = 'region_ocr'
    else:
        # ── Strategy 2: Full-frame OCR fallback ───────────────────────────
        # Resize to manageable size
        max_dim = 1280
        fh, fw = frame.shape[:2]
        scale = min(1.0, max_dim / max(fw, fh))
        small = cv2.resize(frame, (int(fw * scale), int(fh * scale)))

        ocr_results = reader.readtext(small, detail=1, paragraph=False,
                                       allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ')
        for (pts, text, conf) in ocr_results:
            cleaned = _clean_plate(text)
            if _is_valid_plate(cleaned) and conf > best_conf:
                best_plate = cleaned
                best_conf = conf
                result['raw_results'].append({'text': text, 'cleaned': cleaned, 'conf': round(conf, 3)})

        if best_plate:
            result['method'] = 'full_frame_ocr'

    # ── Annotate frame ─────────────────────────────────────────────────────
    annotated = frame.copy()
    if best_bbox:
        x, y, w, h = best_bbox
        cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 3)
        label = f"{best_plate}  {best_conf*100:.1f}%"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(annotated, (x, y - th - 14), (x + tw + 8, y), (0, 255, 0), -1)
        cv2.putText(annotated, label, (x + 4, y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    elif best_plate:
        label = f"PLATE: {best_plate}  {best_conf*100:.1f}%"
        cv2.putText(annotated, label, (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)

    result.update({
        'plate_number': best_plate,
        'confidence': round(best_conf, 4),
        'bbox': best_bbox,
        'annotated': annotated,
    })
    return result


# ── Frame acquisition ─────────────────────────────────────────────────────────
def capture_frame_from_camera(camera_id: str, stream_url: str = None) -> np.ndarray:
    """
    Grab a single frame from a camera.
    stream_url can be: '0' (webcam), RTSP URL, video file path.
    Returns BGR numpy array or None.
    """
    src = 0  # default: first webcam
    if stream_url:
        if stream_url.isdigit():
            src = int(stream_url)
        elif os.path.exists(stream_url):
            src = stream_url
        elif stream_url.startswith('rtsp://') or stream_url.startswith('http://'):
            src = stream_url

    cap = cv2.VideoCapture(src)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    # Grab a few frames to flush buffer lag
    for _ in range(3):
        cap.grab()
    ret, frame = cap.retrieve()
    cap.release()

    return frame if ret else None


def read_plate_from_image_bytes(image_bytes: bytes, camera_id: str = 'CAM-001'):
    """
    Read plate from raw image bytes (from multipart upload or base64).
    """
    np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        return {'plate_number': None, 'confidence': 0.0, 'error': 'Cannot decode image', 'method': 'none'}
    return read_plate_from_frame(frame, camera_id)


def encode_annotated_frame(annotated: np.ndarray) -> bytes:
    """Convert annotated frame to JPEG bytes for API response."""
    if annotated is None:
        return b''
    _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes()


# ── Batch plate scan on video ─────────────────────────────────────────────────
def scan_video_for_plates(video_path: str, camera_id: str = 'CAM-001',
                           sample_every_n: int = 30, max_plates: int = 50):
    """
    Scan every Nth frame of a video file for plates.
    Useful for post-processing uploaded footage.
    Returns list of unique detected plates with timestamps.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    results = []
    seen_plates = set()
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % sample_every_n == 0:
            r = read_plate_from_frame(frame, camera_id)
            plate = r.get('plate_number')
            conf = r.get('confidence', 0)
            if plate and plate not in seen_plates and conf > 0.5:
                seen_plates.add(plate)
                timestamp_sec = frame_idx / fps
                results.append({
                    'plate_number': plate,
                    'confidence': conf,
                    'timestamp_sec': round(timestamp_sec, 2),
                    'timestamp_hms': str(datetime.utcfromtimestamp(timestamp_sec).strftime('%H:%M:%S')),
                    'frame_index': frame_idx,
                })
                if len(results) >= max_plates:
                    break
        frame_idx += 1

    cap.release()
    return results
