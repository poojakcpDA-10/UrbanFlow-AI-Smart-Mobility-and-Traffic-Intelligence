"""
Congestion & Emission Analysis API Routes
==========================================
All endpoints for the new Congestion & Emission module.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..modules.congestion_emission import (
    generate_congestion_report,
    simulate_live_report,
    simulate_history,
    aggregate_historical,
    build_heatmap_data,
    calculate_vehicle_flow,
    calculate_lane_density,
    calculate_congestion_score,
    estimate_co2_emission,
    INTERSECTION_COORDS,
)
from ..models.models import SignalTiming
from ..extensions import db
from datetime import datetime, timedelta
import random

congestion_bp = Blueprint('congestion', __name__)


# ── /api/traffic/congestion-report ─────────────────────────────────────────
@congestion_bp.route('/congestion-report', methods=['GET', 'POST'])
@jwt_required()
def congestion_report():
    """
    GET  → simulate a live report for a given intersection
    POST → accept ViT detection output + TCN prediction and compute report
    Returns the standard CongestionReport JSON.
    """
    if request.method == 'POST':
        data = request.get_json() or {}
        intersection_id     = data.get('intersection_id', 'INT-001')
        vehicle_counts      = data.get('vehicle_counts', {})
        predicted_load      = float(data.get('predicted_load', 18))
        time_window_minutes = float(data.get('time_window_minutes', 1.0))
        lanes               = int(data.get('lanes', 4))
        avg_speed_kmh       = data.get('avg_speed_kmh')
        current_green       = int(data.get('current_green', 30))

        if not vehicle_counts:
            # fallback to simulation
            report = simulate_live_report(intersection_id)
        else:
            report = generate_congestion_report(
                intersection_id=intersection_id,
                vehicle_counts=vehicle_counts,
                predicted_load=predicted_load,
                time_window_minutes=time_window_minutes,
                lanes=lanes,
                avg_speed_kmh=avg_speed_kmh,
                current_green=current_green,
            )
    else:
        intersection_id = request.args.get('intersection_id', 'INT-001')
        report = simulate_live_report(intersection_id)

    d = report.to_dict()

    # Flatten for convenience
    return jsonify({
        'success': True,
        'vehicles_per_minute': d['vehicles_per_minute'],
        'lane_density':        d['lane_density'],
        'lane_density_pct':    d['lane_density_pct'],
        'congestion_score':    d['congestion_score'],
        'congestion_status':   d['congestion_status'],
        'congestion_color':    d['congestion_color'],
        'co2_emission':        f"{d['emission']['co2_kg_per_min']:.3f} kg/min",
        'co2_kg_per_min':      d['emission']['co2_kg_per_min'],
        'co2_kg_per_hour':     d['emission']['co2_kg_per_hour'],
        'aqi':                 d['emission']['aqi_estimate'],
        'aqi_level':           d['emission']['aqi_level'],
        'nox_mg_per_min':      d['emission']['nox_mg_per_min'],
        'pm25_ug_per_min':     d['emission']['pm25_ug_per_min'],
        'status':              d['congestion_status'],
        'alert_triggered':     d['alert_triggered'],
        'alert_message':       d['alert_message'],
        'signal_action':       d['signal_action'],
        'signal_detail':       d['signal_detail'],
        'green_adjustment':    d['green_adjustment'],
        'vehicle_counts':      d['vehicle_counts'],
        'total_vehicles':      d['total_vehicles'],
        'trees_needed':        d['trees_needed'],
        'env_rating':          d['env_rating'],
        'emission_breakdown':  d['emission']['breakdown'],
        'intersection_id':     d['intersection_id'],
        'timestamp':           d['timestamp'],
    })


# ── /api/traffic/congestion-history ─────────────────────────────────────────
@congestion_bp.route('/congestion-history', methods=['GET'])
@jwt_required()
def congestion_history():
    """24-hour historical congestion & emission data for charts."""
    intersection_id = request.args.get('intersection_id', 'INT-001')
    hours = int(request.args.get('hours', 24))
    history = simulate_history(intersection_id, hours)
    analytics = aggregate_historical(history)

    return jsonify({
        'success': True,
        'intersection_id': intersection_id,
        'history': history,
        'analytics': analytics,
        'chart_data': {
            'labels':        [h['timestamp'][11:16] for h in history],
            'scores':        [h['congestion_score'] for h in history],
            'vpm':           [h['vehicles_per_minute'] for h in history],
            'co2':           [h['emission']['co2_kg_per_min'] for h in history],
            'aqi':           [h['emission']['aqi_estimate'] for h in history],
            'density':       [h['lane_density_pct'] for h in history],
        },
    })


# ── /api/traffic/heatmap ─────────────────────────────────────────────────────
@congestion_bp.route('/heatmap', methods=['GET'])
@jwt_required()
def heatmap():
    """Leaflet heatmap data for all intersections."""
    reports = [simulate_live_report(iid).to_dict()
               for iid in ['INT-001', 'INT-002', 'INT-003', 'INT-004']]
    heatmap_points = build_heatmap_data(reports)

    # Pollution zones
    zones = []
    for r in reports:
        iid = r['intersection_id']
        co2 = r['emission']['co2_kg_per_min']
        if co2 > 0.5:
            zone, zone_color = 'Zone A – High CO₂', '#ff3c5f'
        elif co2 > 0.2:
            zone, zone_color = 'Zone B – Moderate', '#ff8c00'
        else:
            zone, zone_color = 'Zone C – Safe', '#00ff88'
        lat, lng = INTERSECTION_COORDS.get(iid, (12.97, 77.59))
        zones.append({
            'intersection_id': iid,
            'lat': lat, 'lng': lng,
            'zone': zone,
            'zone_color': zone_color,
            'co2_kg_per_min': co2,
            'aqi': r['emission']['aqi_estimate'],
        })

    return jsonify({'success': True, 'heatmap': heatmap_points, 'pollution_zones': zones})


# ── /api/traffic/all-intersections ──────────────────────────────────────────
@congestion_bp.route('/all-intersections', methods=['GET'])
@jwt_required()
def all_intersections():
    """Live congestion report for all 4 intersections."""
    results = []
    for iid in ['INT-001', 'INT-002', 'INT-003', 'INT-004']:
        r = simulate_live_report(iid)
        d = r.to_dict()
        results.append({
            'intersection_id':   iid,
            'congestion_score':  d['congestion_score'],
            'congestion_status': d['congestion_status'],
            'congestion_color':  d['congestion_color'],
            'vehicles_per_minute': d['vehicles_per_minute'],
            'total_vehicles':    d['total_vehicles'],
            'co2_kg_per_min':    d['emission']['co2_kg_per_min'],
            'aqi':               d['emission']['aqi_estimate'],
            'aqi_level':         d['emission']['aqi_level'],
            'alert_triggered':   d['alert_triggered'],
            'signal_action':     d['signal_action'],
            'env_rating':        d['env_rating'],
            'lat': INTERSECTION_COORDS.get(iid, (12.97, 77.59))[0],
            'lng': INTERSECTION_COORDS.get(iid, (12.97, 77.59))[1],
        })
    return jsonify({'success': True, 'intersections': results})


# ── /api/traffic/emission-report ─────────────────────────────────────────────
@congestion_bp.route('/emission-report', methods=['GET'])
@jwt_required()
def emission_report():
    """Daily environmental impact report — exportable."""
    intersection_id = request.args.get('intersection_id', 'INT-001')
    history = simulate_history(intersection_id, 24)
    total_co2  = sum(h['emission']['co2_kg_per_min'] * 60 for h in history)
    avg_aqi    = int(sum(h['emission']['aqi_estimate'] for h in history) / len(history))
    worst_hour = max(history, key=lambda h: h['emission']['co2_kg_per_min'])
    best_hour  = min(history, key=lambda h: h['emission']['co2_kg_per_min'])
    total_veh  = sum(h['total_vehicles'] for h in history)

    return jsonify({
        'success': True,
        'report_date':   datetime.utcnow().strftime('%Y-%m-%d'),
        'intersection_id': intersection_id,
        'total_vehicles': total_veh,
        'congestion_hours': round(sum(1 for h in history if h['alert_triggered']) * 1.0, 1),
        'total_co2_kg':    round(total_co2, 2),
        'total_co2_tons':  round(total_co2 / 1000, 4),
        'avg_aqi':         avg_aqi,
        'aqi_level':       history[-1]['emission']['aqi_level'],
        'env_rating':      history[-1]['env_rating'],
        'trees_to_offset': round(total_co2 / 0.021),
        'cars_equivalent': round(total_co2 / 2.4),
        'worst_hour': {
            'time': worst_hour['timestamp'][11:16],
            'co2_kg_per_hour': worst_hour['emission']['co2_kg_per_hour'],
            'congestion_score': worst_hour['congestion_score'],
        },
        'best_hour': {
            'time': best_hour['timestamp'][11:16],
            'co2_kg_per_hour': best_hour['emission']['co2_kg_per_hour'],
            'congestion_score': best_hour['congestion_score'],
        },
        'chart_data': {
            'labels': [h['timestamp'][11:16] for h in history],
            'co2':    [round(h['emission']['co2_kg_per_min'] * 60, 3) for h in history],
            'aqi':    [h['emission']['aqi_estimate'] for h in history],
            'nox':    [h['emission']['nox_mg_per_min'] for h in history],
        },
        'breakdown_by_vehicle': history[-1]['emission']['breakdown'],
    })


# ── /api/traffic/smart-city-report ───────────────────────────────────────────
@congestion_bp.route('/smart-city-report', methods=['GET'])
@jwt_required()
def smart_city_report():
    """Full smart city daily report across all intersections."""
    all_histories = {
        iid: simulate_history(iid, 24)
        for iid in ['INT-001', 'INT-002', 'INT-003', 'INT-004']
    }

    total_vehicles  = sum(sum(h['total_vehicles'] for h in hist) for hist in all_histories.values())
    total_co2       = sum(sum(h['emission']['co2_kg_per_min']*60 for h in hist) for hist in all_histories.values())
    congestion_hours = sum(sum(1 for h in hist if h['alert_triggered']) for hist in all_histories.values())

    worst_int = max(all_histories.items(),
                    key=lambda kv: max(h['congestion_score'] for h in kv[1]))

    return jsonify({
        'success': True,
        'report_date':       datetime.utcnow().strftime('%Y-%m-%d'),
        'total_vehicles':    total_vehicles,
        'congestion_hours':  round(congestion_hours * 0.25, 1),
        'estimated_co2_kg':  round(total_co2, 1),
        'estimated_co2_tons': round(total_co2 / 1000, 3),
        'worst_intersection': {
            'id':   worst_int[0],
            'peak_score': round(max(h['congestion_score'] for h in worst_int[1]), 1),
        },
        'intersections_summary': [
            {
                'id':   iid,
                'avg_score': round(sum(h['congestion_score'] for h in hist) / len(hist), 1),
                'total_co2_kg': round(sum(h['emission']['co2_kg_per_min']*60 for h in hist), 2),
                'total_vehicles': sum(h['total_vehicles'] for h in hist),
                'alerts': sum(1 for h in hist if h['alert_triggered']),
            }
            for iid, hist in all_histories.items()
        ],
    })
