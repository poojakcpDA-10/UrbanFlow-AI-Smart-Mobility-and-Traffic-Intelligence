"""
Video Analysis Service
Processes uploaded/live video, runs ViT+TCN, saves results, emits socket alerts.

Enhancements:
  - Feature 1/6: Frame buffer fed into multi-frame emergency scoring
  - Feature 2:   audio_score parameter passthrough (siren fusion)
  - Feature 9:   configurable FRAME_SKIP
"""

import cv2
import os
import sys
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ai_models.vit_detection import detect_traffic
from ai_models.tcn_prediction import predict_traffic

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Feature 9: process every Nth frame for performance
FRAME_SKIP = 3


def analyze_video_file(video_path, intersection_id='INT-001', camera_id='CAM-001',
                        socketio=None, app=None, audio_score=0.0):
    """
    Analyze a video file frame by frame.
    audio_score – Feature 2: pass siren detection probability to fuse with vision.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {'error': f'Cannot open video: {video_path}'}

    fps          = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_idx    = 0
    frame_results = []
    all_alerts    = []
    accidents_detected   = []
    violations_detected  = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % FRAME_SKIP != 0:
            continue

        # Feature 2: pass audio_score through to fuse with vision
        result = detect_traffic(frame, intersection_id, audio_score=audio_score)
        if result.get('skipped'):
            continue

        result['camera_id']     = camera_id
        result['frame_idx']     = frame_idx
        result['video_time_sec'] = round(frame_idx / fps, 2)
        frame_results.append(result)

        if result.get('dashboard_alerts'):
            all_alerts.extend(result['dashboard_alerts'])

        if result.get('accident', {}).get('detected'):
            accidents_detected.append({
                **result['accident'],
                'frame_idx': frame_idx,
                'timestamp': datetime.utcnow().isoformat(),
            })

        if result.get('violations'):
            for v in result['violations']:
                if v.get('severe'):
                    violations_detected.append({
                        **v, 'frame_idx': frame_idx,
                        'timestamp': datetime.utcnow().isoformat(),
                    })

        if socketio and result.get('dashboard_alerts'):
            try:
                socketio.emit('analysis_update', {
                    'intersection_id': intersection_id,
                    'camera_id':       camera_id,
                    'frame_idx':       frame_idx,
                    'alerts':          result['dashboard_alerts'],
                    'counts':          result.get('counts', {}),
                    'congestion':      result.get('congestion'),
                    'emergency_vehicle': result.get('emergency_vehicle', {}),
                    # Feature 3/7: include confidence history for live graph
                    'confidence_history': result.get('confidence_history', []),
                    # Feature 4: motion tracking
                    'motion_tracking': result.get('motion_tracking', {}),
                    # Feature 5: active override
                    'active_signal_override': result.get('active_signal_override', {}),
                })
            except Exception:
                pass

    cap.release()
    if not frame_results:
        return {'error': 'No frames processed'}

    last       = frame_results[-1]
    avg_count  = sum(r.get('total', 0) for r in frame_results) / max(len(frame_results), 1)
    prediction = predict_traffic(intersection_id, horizon=12, current_count=int(avg_count))

    return {
        'video_path':                video_path,
        'intersection_id':           intersection_id,
        'camera_id':                 camera_id,
        'frames_analyzed':           len(frame_results),
        'total_frames':              total_frames,
        'duration_seconds':          round(total_frames / fps, 1),
        'avg_vehicle_count':         round(avg_count, 1),
        'peak_vehicle_count':        max(r.get('total', 0) for r in frame_results),
        'congestion_summary':        _congestion_summary(frame_results),
        'total_violations_detected': len(violations_detected),
        'severe_violations':         [v for v in violations_detected if v.get('severe')],
        'accidents_detected':        accidents_detected,
        'severe_accidents':          [a for a in accidents_detected
                                      if a.get('severity') in ('high', 'critical')],
        'emission_summary':          _emission_summary(frame_results),
        'prediction':                prediction,
        'dashboard_alerts':          all_alerts[:20],
        # Feature 7: include final confidence history & signal override state
        'confidence_history':        last.get('confidence_history', []),
        'active_signal_override':    last.get('active_signal_override', {}),
        'motion_tracking':           last.get('motion_tracking', {}),
        'last_frame_result':         {k: v for k, v in last.items() if k != 'annotated_frame'},
        'analyzed_at':               datetime.utcnow().isoformat(),
    }


def _congestion_summary(frame_results):
    counts  = {'Low': 0, 'Medium': 0, 'High': 0}
    for r in frame_results:
        lvl = r.get('congestion', 'Low')
        counts[lvl] = counts.get(lvl, 0) + 1
    dominant = max(counts, key=counts.get)
    return {'distribution': counts, 'dominant': dominant}


def _emission_summary(frame_results):
    if not frame_results:
        return {}
    emissions = [r.get('emission_data', {}).get('co2_kg', 0) for r in frame_results]
    aqis      = [r.get('emission_data', {}).get('aqi',    0) for r in frame_results]
    return {
        'avg_co2_kg': round(sum(emissions) / len(emissions), 3),
        'max_co2_kg': round(max(emissions), 3),
        'avg_aqi':    round(sum(aqis) / len(aqis)),
        'max_aqi':    max(aqis),
    }


def get_live_frame(camera_index=0, intersection_id='INT-001', audio_score=0.0):
    cap = cv2.VideoCapture(camera_index)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        frame = None

    result    = detect_traffic(frame, intersection_id, audio_score=audio_score)
    annotated = result.get('annotated_frame')

    if annotated is not None:
        _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        jpeg_bytes = buffer.tobytes()
    else:
        jpeg_bytes = b''

    return jpeg_bytes, {k: v for k, v in result.items() if k != 'annotated_frame'}


def generate_live_stream(camera_index=0, intersection_id='INT-001', audio_score=0.0):
    cap         = cv2.VideoCapture(camera_index)
    frame_count = 0

    while True:
        success, frame = cap.read()
        if not success:
            frame = None

        frame_count += 1
        result    = detect_traffic(frame, intersection_id, audio_score=audio_score)
        annotated = result.get('annotated_frame')

        if annotated is not None:
            _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
            jpeg_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')

    cap.release()
