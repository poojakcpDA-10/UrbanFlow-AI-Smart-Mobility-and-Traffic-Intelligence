from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.models import SignalTiming, EmergencyLog, TrafficHistory
from ai_models.tcn_prediction import predict_traffic, get_adaptive_signal
from backend.modules.congestion_emission import (
    generate_congestion_report,
    simulate_live_report,
    simulate_history,
    build_heatmap_data,
    aggregate_historical,
)
from datetime import datetime, timedelta
import random

traffic_bp = Blueprint('traffic', __name__)


@traffic_bp.route('/signal/<intersection_id>', methods=['GET'])
@jwt_required()
def get_signal(intersection_id):
    signal = SignalTiming.query.filter_by(intersection_id=intersection_id).first()
    if not signal:
        signal = SignalTiming(
            intersection_id=intersection_id,
            cycle_length=90.0,
            north_green=30, south_green=30,
            east_green=25, west_green=25,
            mode='adaptive'
        )
        db.session.add(signal)
        db.session.commit()
    return jsonify({'success': True, 'signal': signal.to_dict()})


@traffic_bp.route('/signal/<intersection_id>', methods=['POST'])
@jwt_required()
def update_signal(intersection_id):
    """Manual signal update by operator"""
    data = request.get_json()
    signal = SignalTiming.query.filter_by(intersection_id=intersection_id).first()
    if not signal:
        signal = SignalTiming(intersection_id=intersection_id)
        db.session.add(signal)

    signal.north_green = data.get('north_green', signal.north_green)
    signal.south_green = data.get('south_green', signal.south_green)
    signal.east_green = data.get('east_green', signal.east_green)
    signal.west_green = data.get('west_green', signal.west_green)
    signal.cycle_length = data.get('cycle_length', signal.cycle_length)
    signal.mode = data.get('mode', 'manual')
    signal.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'signal': signal.to_dict()})


@traffic_bp.route('/signal/<intersection_id>/emergency-override', methods=['POST'])
@jwt_required()
def emergency_override(intersection_id):
    """Emergency vehicle signal override"""
    data = request.get_json()
    direction = data.get('direction', 'North')
    duration = data.get('duration', 60)
    vehicle_type = data.get('vehicle_type', 'Ambulance')

    signal = SignalTiming.query.filter_by(intersection_id=intersection_id).first()
    if not signal:
        signal = SignalTiming(intersection_id=intersection_id)
        db.session.add(signal)

    signal.is_emergency_override = True
    signal.override_direction = direction
    signal.override_expires_at = datetime.utcnow() + timedelta(seconds=duration)
    signal.mode = 'emergency'
    # Set all green to override direction
    for d in ['north', 'south', 'east', 'west']:
        setattr(signal, f'{d}_green', duration if d.lower() == direction.lower() else 5)

    # Log emergency
    log = EmergencyLog(
        intersection_id=intersection_id,
        vehicle_type=vehicle_type,
        direction=direction,
        override_duration=duration,
        response_time=round(random.uniform(2, 8), 2)
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Emergency override active for {duration}s toward {direction}',
        'signal': signal.to_dict()
    })


@traffic_bp.route('/signal/<intersection_id>/adaptive', methods=['POST'])
@jwt_required()
def apply_adaptive_signal(intersection_id):
    """Apply TCN-optimized adaptive signal timing"""
    data = request.get_json()
    lane_counts = data.get('lane_counts', {
        'north': random.randint(5, 30),
        'south': random.randint(5, 30),
        'east': random.randint(5, 30),
        'west': random.randint(5, 30),
    })

    plan = get_adaptive_signal(lane_counts)
    adaptive = plan['adaptive_plan']

    signal = SignalTiming.query.filter_by(intersection_id=intersection_id).first()
    if not signal:
        signal = SignalTiming(intersection_id=intersection_id)
        db.session.add(signal)

    signal.north_green = adaptive.get('north', {}).get('green_seconds', 30)
    signal.south_green = adaptive.get('south', {}).get('green_seconds', 30)
    signal.east_green = adaptive.get('east', {}).get('green_seconds', 25)
    signal.west_green = adaptive.get('west', {}).get('green_seconds', 25)
    signal.cycle_length = plan['total_cycle']
    signal.mode = 'adaptive'
    signal.is_emergency_override = False
    signal.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Adaptive signal plan applied',
        'signal': signal.to_dict(),
        'adaptive_plan': plan
    })


@traffic_bp.route('/predict/<intersection_id>', methods=['GET'])
@jwt_required()
def predict(intersection_id):
    horizon = int(request.args.get('horizon', 12))
    current = request.args.get('current_count')
    current_count = int(current) if current else None

    result = predict_traffic(intersection_id, horizon, current_count)
    return jsonify({'success': True, 'prediction': result})


@traffic_bp.route('/history/<intersection_id>', methods=['GET'])
@jwt_required()
def get_history(intersection_id):
    hours = int(request.args.get('hours', 24))
    since = datetime.utcnow() - timedelta(hours=hours)
    records = TrafficHistory.query.filter(
        TrafficHistory.intersection_id == intersection_id,
        TrafficHistory.timestamp >= since
    ).order_by(TrafficHistory.timestamp.asc()).all()
    return jsonify({'success': True, 'history': [r.to_dict() for r in records]})


# ─────────────────────────────────────────────────────────────────────────────
# CONGESTION & EMISSION ANALYSIS ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@traffic_bp.route('/congestion-report', methods=['GET', 'POST'])
@jwt_required()
def congestion_report():
    """
    GET  /api/traffic/congestion-report?intersection_id=INT-001
         Returns live simulated congestion report.

    POST /api/traffic/congestion-report
         Body: { intersection_id, vehicle_counts, predicted_load,
                 time_window_minutes, lanes, avg_speed_kmh }
         Returns computed report from provided ViT detection data.
    """
    if request.method == 'POST':
        data            = request.get_json() or {}
        intersection_id = data.get('intersection_id', 'INT-001')
        vehicle_counts  = data.get('vehicle_counts', {
            'car': random.randint(5, 20), 'bus': random.randint(0, 4),
            'truck': random.randint(0, 3), 'bike': random.randint(1, 8),
            'emergency': 0,
        })
        predicted_load  = data.get('predicted_load', random.uniform(10, 35))
        time_window     = float(data.get('time_window_minutes', 1.0))
        lanes           = int(data.get('lanes', 4))
        avg_speed       = data.get('avg_speed_kmh')
        current_green   = int(data.get('current_green', 30))

        report = generate_congestion_report(
            intersection_id     = intersection_id,
            vehicle_counts      = vehicle_counts,
            predicted_load      = predicted_load,
            time_window_minutes = time_window,
            lanes               = lanes,
            avg_speed_kmh       = avg_speed,
            current_green       = current_green,
        )
    else:
        intersection_id = request.args.get('intersection_id', 'INT-001')
        report = simulate_live_report(intersection_id)

    d = report.to_dict()

    # Flatten top-level for easy dashboard consumption
    return jsonify({
        'success': True,
        'vehicles_per_minute': d['vehicles_per_minute'],
        'lane_density':        d['lane_density'],
        'lane_density_pct':    d['lane_density_pct'],
        'congestion_score':    d['congestion_score'],
        'congestion_status':   d['congestion_status'],
        'congestion_color':    d['congestion_color'],
        'alert_triggered':     d['alert_triggered'],
        'alert_message':       d['alert_message'],
        'co2_emission':        f"{d['emission']['co2_kg_per_min']:.3f} kg/min",
        'co2_kg_per_hour':     d['emission']['co2_kg_per_hour'],
        'aqi':                 d['emission']['aqi_estimate'],
        'aqi_level':           d['emission']['aqi_level'],
        'nox_mg_per_min':      d['emission']['nox_mg_per_min'],
        'pm25_ug_per_min':     d['emission']['pm25_ug_per_min'],
        'status':              d['congestion_status'],
        'signal_action':       d['signal_action'],
        'signal_detail':       d['signal_detail'],
        'green_adjustment':    d['green_adjustment'],
        'env_rating':          d['env_rating'],
        'trees_needed':        d['trees_needed'],
        'emission_breakdown':  d['emission']['breakdown'],
        'vehicle_counts':      d['vehicle_counts'],
        'timestamp':           d['timestamp'],
        'intersection_id':     d['intersection_id'],
        'full_report':         d,
    })


@traffic_bp.route('/congestion-report/all', methods=['GET'])
@jwt_required()
def congestion_all_intersections():
    """Live congestion snapshot for all 4 intersections — used by heatmap"""
    intersections = ['INT-001', 'INT-002', 'INT-003', 'INT-004']
    reports = []
    for iid in intersections:
        r = simulate_live_report(iid).to_dict()
        reports.append(r)

    heatmap = build_heatmap_data(reports)

    return jsonify({
        'success':  True,
        'reports':  reports,
        'heatmap':  heatmap,
        'summary': {
            'avg_score':    round(sum(r['congestion_score'] for r in reports) / len(reports), 1),
            'worst':        max(reports, key=lambda r: r['congestion_score'])['intersection_id'],
            'alerts_active': sum(1 for r in reports if r['alert_triggered']),
            'total_vehicles': sum(r['total_vehicles'] for r in reports),
            'total_co2_kg_min': round(sum(r['emission']['co2_kg_per_min'] for r in reports), 4),
        }
    })


@traffic_bp.route('/congestion-history/<intersection_id>', methods=['GET'])
@jwt_required()
def congestion_history(intersection_id):
    """24-hour historical congestion + emission analytics"""
    hours = int(request.args.get('hours', 24))
    history = simulate_history(intersection_id, hours)
    analytics = aggregate_historical(history)

    # Chart-ready arrays
    labels        = [h['timestamp'][11:16] for h in history]
    scores        = [h['congestion_score']          for h in history]
    vpms          = [h['vehicles_per_minute']        for h in history]
    co2s          = [h['emission']['co2_kg_per_min'] for h in history]
    densities     = [h['lane_density_pct']           for h in history]

    return jsonify({
        'success':   True,
        'intersection_id': intersection_id,
        'analytics': analytics,
        'chart_data': {
            'labels':           labels,
            'congestion_scores': scores,
            'vehicles_per_min': vpms,
            'co2_kg_per_min':   co2s,
            'lane_density_pct': densities,
        },
        'history': history,
    })


@traffic_bp.route('/emission-report/<intersection_id>', methods=['GET'])
@jwt_required()
def emission_report(intersection_id):
    """Environmental impact report for an intersection"""
    history  = simulate_history(intersection_id, 24)
    analytics = aggregate_historical(history)

    total_co2   = analytics.get('total_co2_kg', 0)
    avg_aqi     = round(sum(h['emission']['aqi_estimate'] for h in history) / len(history))
    worst_hour  = max(history, key=lambda h: h['emission']['co2_kg_per_min'])
    best_hour   = min(history, key=lambda h: h['emission']['co2_kg_per_min'])

    return jsonify({
        'success': True,
        'intersection_id': intersection_id,
        'period_hours': 24,
        'total_co2_kg':       round(total_co2, 2),
        'avg_aqi':            avg_aqi,
        'aqi_level':          history[-1]['emission']['aqi_level'],
        'worst_hour': {
            'time':   worst_hour['timestamp'][11:16],
            'co2_kg': worst_hour['emission']['co2_kg_per_min'],
            'score':  worst_hour['congestion_score'],
        },
        'best_hour': {
            'time':   best_hour['timestamp'][11:16],
            'co2_kg': best_hour['emission']['co2_kg_per_min'],
            'score':  best_hour['congestion_score'],
        },
        'env_rating':  history[-1]['env_rating'],
        'trees_needed_to_offset': round(total_co2 / 0.021),
        'equivalent_cars_off_road': round(total_co2 / 2.4),
        'chart_data': {
            'labels':          [h['timestamp'][11:16] for h in history],
            'co2':             [h['emission']['co2_kg_per_min'] for h in history],
            'aqi':             [h['emission']['aqi_estimate']   for h in history],
            'nox':             [h['emission']['nox_mg_per_min'] for h in history],
        },
        'breakdown_by_vehicle': history[-1]['emission']['breakdown'],
    })
