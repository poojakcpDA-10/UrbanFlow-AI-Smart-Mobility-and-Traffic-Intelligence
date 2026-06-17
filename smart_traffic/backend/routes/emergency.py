"""
Emergency Detection Routes
Features: 5 (Smart Trigger), 7 (Dashboard), 8 (Event Logging), 2 (Audio fusion)
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from ai_models.vit_detection import (
    get_emergency_log,
    get_active_override,
    activate_priority,
    ACTIVE_SIGNAL_OVERRIDES,
    CONFIDENCE_HISTORY,
    detect_traffic,
    fuse_emergency_score,
    EMERGENCY_CONFIRM_THRESHOLD,
)
from datetime import datetime

emergency_bp = Blueprint('emergency', __name__)


# ──────────────────────────────────────────────────────────────
# Feature 8 – Emergency Event Log
# ──────────────────────────────────────────────────────────────
@emergency_bp.route('/log', methods=['GET'])
@jwt_required()
def get_log():
    """Return recent emergency detection events."""
    limit = int(request.args.get('limit', 50))
    logs  = get_emergency_log(limit)
    return jsonify({'success': True, 'count': len(logs), 'events': logs})


# ──────────────────────────────────────────────────────────────
# Feature 5 – Active Signal Overrides
# ──────────────────────────────────────────────────────────────
@emergency_bp.route('/signal-overrides', methods=['GET'])
@jwt_required()
def get_signal_overrides():
    """Return all currently active signal overrides."""
    return jsonify({
        'success':   True,
        'overrides': list(ACTIVE_SIGNAL_OVERRIDES.values()),
        'count':     len(ACTIVE_SIGNAL_OVERRIDES),
    })


@emergency_bp.route('/signal-override/<intersection_id>', methods=['GET'])
@jwt_required()
def get_override(intersection_id):
    override = get_active_override(intersection_id)
    return jsonify({'success': True, 'intersection_id': intersection_id, 'override': override})


@emergency_bp.route('/signal-override/<intersection_id>/activate', methods=['POST'])
@jwt_required()
def manual_activate(intersection_id):
    """
    Feature 5: Manually trigger a priority signal for an intersection.
    Body: { "direction": "North", "duration": 60, "vehicle_type": "Ambulance" }
    """
    data         = request.get_json() or {}
    direction    = data.get('direction', 'North')
    duration     = int(data.get('duration', 60))
    vehicle_type = data.get('vehicle_type', 'Manual Override')

    override = activate_priority(intersection_id, direction, duration, vehicle_type)
    return jsonify({'success': True, 'override': override})


@emergency_bp.route('/signal-override/<intersection_id>/clear', methods=['POST'])
@jwt_required()
def clear_override(intersection_id):
    """Remove an active signal override."""
    ACTIVE_SIGNAL_OVERRIDES.pop(intersection_id, None)
    return jsonify({'success': True, 'message': f'Override cleared for {intersection_id}'})


# ──────────────────────────────────────────────────────────────
# Feature 3 – Temporal Confidence History
# ──────────────────────────────────────────────────────────────
@emergency_bp.route('/confidence/<intersection_id>', methods=['GET'])
@jwt_required()
def confidence_history(intersection_id):
    """
    Feature 3: Return rolling confidence scores for an intersection.
    Useful for the dashboard graph.
    """
    hist = list(CONFIDENCE_HISTORY.get(intersection_id, []))
    avg  = round(sum(hist) / len(hist), 4) if hist else 0.0
    return jsonify({
        'success':           True,
        'intersection_id':   intersection_id,
        'history':           hist,
        'avg_confidence':    avg,
        'threshold':         EMERGENCY_CONFIRM_THRESHOLD,
        'confirmed':         avg >= EMERGENCY_CONFIRM_THRESHOLD,
    })


# ──────────────────────────────────────────────────────────────
# Feature 2 – Siren + Visual Fusion endpoint
# ──────────────────────────────────────────────────────────────
@emergency_bp.route('/fuse-score', methods=['POST'])
@jwt_required()
def fuse_score():
    """
    Feature 2: Accept a vision score and an audio siren score,
    return the fused emergency probability.
    Body: { "vision_score": 0.8, "audio_score": 0.6 }
    """
    data         = request.get_json() or {}
    vision_score = float(data.get('vision_score', 0.0))
    audio_score  = float(data.get('audio_score', 0.0))
    fused        = fuse_emergency_score(vision_score, audio_score)
    return jsonify({
        'success':       True,
        'vision_score':  vision_score,
        'audio_score':   audio_score,
        'fused_score':   fused,
        'formula':       'emergency_score = 0.7 * vision + 0.3 * audio',
        'confirmed':     fused >= EMERGENCY_CONFIRM_THRESHOLD,
    })


# ──────────────────────────────────────────────────────────────
# Feature 7 – Emergency Detection Dashboard Stats
# ──────────────────────────────────────────────────────────────
@emergency_bp.route('/dashboard-stats', methods=['GET'])
@jwt_required()
def dashboard_stats():
    """
    Feature 7: Aggregated dashboard statistics for the emergency module.
    Returns recent events, active overrides, confidence averages.
    """
    logs      = get_emergency_log(100)
    overrides = list(ACTIVE_SIGNAL_OVERRIDES.values())

    # Confidence summary across all known intersections
    conf_summary = {}
    for iid, hist in CONFIDENCE_HISTORY.items():
        h   = list(hist)
        avg = round(sum(h) / len(h), 4) if h else 0.0
        conf_summary[iid] = {
            'history':   h,
            'avg':       avg,
            'confirmed': avg >= EMERGENCY_CONFIRM_THRESHOLD,
        }

    # Event counts by vehicle type
    vehicle_counts = {}
    for ev in logs:
        vt = ev.get('vehicle_type', 'Unknown')
        vehicle_counts[vt] = vehicle_counts.get(vt, 0) + 1

    return jsonify({
        'success':               True,
        'generated_at':          datetime.utcnow().isoformat(),
        'total_events_logged':   len(logs),
        'recent_events':         logs[-10:],
        'active_overrides_count': len(overrides),
        'active_overrides':      overrides,
        'confidence_by_intersection': conf_summary,
        'vehicle_type_breakdown': vehicle_counts,
        'threshold':             EMERGENCY_CONFIRM_THRESHOLD,
    })
