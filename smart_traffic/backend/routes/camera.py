import os
import threading
from flask import Blueprint, Response, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models.models import Camera, DashboardAlert, AccidentLog, Violation, EmissionRecord, Detection
from ..services.video_analysis import analyze_video_file, generate_live_stream, get_live_frame
from datetime import datetime
import random

camera_bp = Blueprint('camera', __name__)

ALLOWED = {'mp4', 'avi', 'mov', 'mkv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


@camera_bp.route('/list', methods=['GET'])
@jwt_required()
def list_cameras():
    cameras = Camera.query.all()
    if not cameras:
        # Seed demo cameras
        demo = [
            Camera(camera_id='CAM-001', name='North Junction A', intersection_id='INT-001',
                   location_name='MG Road & Brigade Road', lat=12.9716, lng=77.5946,
                   stream_url='0', is_active=True, status='online', resolution='1080p'),
            Camera(camera_id='CAM-002', name='South Gate Cam', intersection_id='INT-002',
                   location_name='Residency Road & Richmond', lat=12.9656, lng=77.6010,
                   stream_url='', is_active=True, status='online', resolution='1080p'),
            Camera(camera_id='CAM-003', name='East Corridor', intersection_id='INT-003',
                   location_name='Old Airport Road', lat=12.9780, lng=77.6090,
                   stream_url='', is_active=True, status='maintenance', resolution='720p'),
            Camera(camera_id='CAM-004', name='West Ring Road', intersection_id='INT-004',
                   location_name='Outer Ring Road Junction', lat=12.9600, lng=77.5800,
                   stream_url='', is_active=True, status='online', resolution='4K'),
        ]
        for c in demo:
            db.session.add(c)
        db.session.commit()
        cameras = Camera.query.all()
    return jsonify({'success': True, 'cameras': [c.to_dict() for c in cameras]})


@camera_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_video():
    """Upload a video for AI analysis"""
    if 'video' not in request.files:
        return jsonify({'success': False, 'message': 'No video file provided'}), 400

    file = request.files['video']
    intersection_id = request.form.get('intersection_id', 'INT-001')
    camera_id = request.form.get('camera_id', 'CAM-001')

    if not file or not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400

    upload_dir = os.path.join(current_app.root_path, '..', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    # Run analysis (blocking for now; use Celery for production)
    result = analyze_video_file(filepath, intersection_id, camera_id)

    # Persist to DB
    _persist_analysis_results(result, intersection_id, camera_id)

    return jsonify({'success': True, 'analysis': result})


@camera_bp.route('/analyze-frame', methods=['POST'])
@jwt_required()
def analyze_single_frame():
    """Analyze a single uploaded image frame"""
    from ai_models.vit_detection import detect_traffic
    import cv2
    import numpy as np

    intersection_id = request.form.get('intersection_id', 'INT-001')
    camera_id = request.form.get('camera_id', 'CAM-001')

    frame = None
    if 'image' in request.files:
        img_file = request.files['image']
        img_array = np.frombuffer(img_file.read(), dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    result = detect_traffic(frame, intersection_id)
    result.pop('annotated_frame', None)

    # Persist alerts
    _create_alerts(result.get('dashboard_alerts', []), intersection_id, camera_id)

    return jsonify({'success': True, 'result': result})


@camera_bp.route('/live-stream/<camera_id>')
def live_stream(camera_id):
    """MJPEG live stream with AI overlay"""
    camera = Camera.query.filter_by(camera_id=camera_id).first()
    intersection_id = camera.intersection_id if camera else 'INT-001'
    cam_index = int(camera.stream_url) if camera and camera.stream_url.isdigit() else 0

    return Response(
        generate_live_stream(cam_index, intersection_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@camera_bp.route('/snapshot/<camera_id>')
@jwt_required()
def snapshot(camera_id):
    """Single annotated snapshot from camera"""
    camera = Camera.query.filter_by(camera_id=camera_id).first()
    intersection_id = camera.intersection_id if camera else 'INT-001'
    cam_index = int(camera.stream_url) if camera and camera.stream_url and camera.stream_url.isdigit() else 0

    jpeg_bytes, result = get_live_frame(cam_index, intersection_id)

    if jpeg_bytes:
        return Response(jpeg_bytes, mimetype='image/jpeg')
    return jsonify({'success': False, 'message': 'No frame available'}), 503


@camera_bp.route('/detection-result/<camera_id>', methods=['GET'])
@jwt_required()
def get_detection_result(camera_id):
    """Get latest AI detection result for camera (JSON, no frame)"""
    from ai_models.vit_detection import detect_traffic
    camera = Camera.query.filter_by(camera_id=camera_id).first()
    intersection_id = camera.intersection_id if camera else 'INT-001'

    result = detect_traffic(None, intersection_id)
    result.pop('annotated_frame', None)

    return jsonify({'success': True, 'camera_id': camera_id, 'result': result})


def _persist_analysis_results(analysis, intersection_id, camera_id):
    """Save analysis results to DB"""
    try:
        # Save detection summary
        last = analysis.get('last_frame_result', {})
        counts = last.get('counts', {})
        det = Detection(
            intersection_id=intersection_id,
            camera_id=camera_id,
            vehicle_count=last.get('total', 0),
            cars=counts.get('car', 0),
            buses=counts.get('bus', 0),
            trucks=counts.get('truck', 0),
            bikes=counts.get('bike', 0),
            emergency=counts.get('emergency', 0),
            congestion_level=last.get('congestion'),
            confidence=last.get('confidence'),
            fps=last.get('fps')
        )
        db.session.add(det)

        # Save accidents
        for acc in analysis.get('severe_accidents', []):
            al = AccidentLog(
                intersection_id=intersection_id,
                camera_id=camera_id,
                severity=acc.get('severity'),
                accident_type=acc.get('type'),
                confidence=acc.get('confidence'),
                description=acc.get('message'),
                status='open'
            )
            db.session.add(al)

        # Save violations
        for v in analysis.get('severe_violations', []):
            viol = Violation(
                intersection_id=intersection_id,
                camera_id=camera_id,
                violation_type=v.get('type'),
                severity=v.get('severity'),
                vehicle_plate=v.get('plate'),
                description=v.get('description'),
                is_severe=True,
                status='pending'
            )
            db.session.add(viol)

        # Save alerts
        _create_alerts(analysis.get('dashboard_alerts', []), intersection_id, camera_id)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f'DB persist error: {e}')


def _create_alerts(alerts, intersection_id, camera_id):
    for a in alerts:
        alert = DashboardAlert(
            alert_type=a.get('type'),
            severity=a.get('severity'),
            intersection_id=intersection_id,
            camera_id=camera_id,
            message=a.get('message'),
            action_required=a.get('action_required', False)
        )
        db.session.add(alert)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
