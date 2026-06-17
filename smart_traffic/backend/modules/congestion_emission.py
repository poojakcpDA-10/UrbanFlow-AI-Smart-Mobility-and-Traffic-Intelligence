"""
Congestion & Emission Analysis Module
======================================
Integrates with:
  - ViT vehicle detection output  (vehicle counts, classes, lane occupancy)
  - TCN traffic prediction output (predicted_load for next horizons)
  - Timestamped camera data

Computes:
  - Vehicles per minute
  - Lane density ratio
  - Congestion score  (0–100)
  - CO₂ / NOx / PM2.5 emission estimates
  - Signal optimization recommendations
  - Historical analytics aggregates
"""

import math
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional

# ── Emission factors (grams per km per vehicle) ──────────────────────────────
EMISSION_FACTORS = {
    "car":       {"co2": 120,  "nox": 0.06, "pm25": 0.005},
    "bike":      {"co2": 80,   "nox": 0.04, "pm25": 0.003},
    "bus":       {"co2": 1000, "nox": 0.80, "pm25": 0.060},
    "truck":     {"co2": 1300, "nox": 1.10, "pm25": 0.090},
    "emergency": {"co2": 200,  "nox": 0.10, "pm25": 0.008},
}

# ── Lane capacity constants ───────────────────────────────────────────────────
MAX_LANE_CAPACITY   = 40   # vehicles per lane per minute (saturation flow)
MAX_LANES_PER_INT   = 4    # typical intersection lanes

# ── Congestion thresholds ─────────────────────────────────────────────────────
CONGESTION_LEVELS = [
    (0,  30,  "Free Flow",     "green",  False),
    (30, 55,  "Moderate",      "yellow", False),
    (55, 75,  "Heavy",         "orange", False),
    (75, 90,  "Congested",     "red",    True),
    (90, 101, "Gridlock",      "darkred",True),
]

# ── Signal optimization thresholds ───────────────────────────────────────────
SIGNAL_EXTENSION_THRESHOLD = 75   # extend green when score > this
SIGNAL_REDUCTION_THRESHOLD = 30   # reduce cycle when score < this
GREEN_EXTENSION_SECONDS     = 15
GREEN_REDUCTION_SECONDS     = 10
MAX_GREEN_TIME              = 90
MIN_GREEN_TIME              = 15


@dataclass
class EmissionResult:
    co2_g_per_min:   float
    co2_kg_per_min:  float
    nox_mg_per_min:  float
    pm25_ug_per_min: float
    co2_kg_per_hour: float
    aqi_estimate:    int
    aqi_level:       str
    breakdown:       Dict[str, float] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class CongestionReport:
    intersection_id:     str
    timestamp:           str
    time_window_minutes: float

    # Flow
    total_vehicles:      int
    vehicles_per_minute: float

    # Density
    lane_density:        float
    lane_density_pct:    float
    lanes_active:        int

    # Score
    congestion_score:    float
    congestion_status:   str
    congestion_color:    str
    alert_triggered:     bool
    alert_message:       Optional[str]

    # Emission
    emission:            EmissionResult

    # Signal recommendation
    signal_action:       str
    signal_detail:       str
    green_adjustment:    int   # seconds to add (+) or remove (-)

    # Vehicle breakdown
    vehicle_counts:      Dict[str, int]

    # Env impact
    trees_needed:        float   # trees needed to offset hourly CO2
    env_rating:          str     # A–F

    def to_dict(self):
        d = asdict(self)
        d["emission"] = self.emission.to_dict()
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Core calculation functions
# ─────────────────────────────────────────────────────────────────────────────

def calculate_vehicle_flow(
    total_detected_vehicles: int,
    time_window_minutes: float = 1.0
) -> float:
    """
    Vehicles per minute = total_detected_vehicles / time_window_minutes
    """
    if time_window_minutes <= 0:
        return 0.0
    return round(total_detected_vehicles / time_window_minutes, 2)


def calculate_lane_density(
    vehicles_in_lane: int,
    max_lane_capacity: int = MAX_LANE_CAPACITY
) -> float:
    """
    density = vehicles_in_lane / max_lane_capacity
    Returns value 0.0 – 1.0 (clamped)
    """
    if max_lane_capacity <= 0:
        return 0.0
    return round(min(1.0, vehicles_in_lane / max_lane_capacity), 4)


def calculate_congestion_score(
    vehicle_counts: Dict[str, int],
    predicted_load: float,
    time_window_minutes: float = 1.0,
    lanes: int = 4,
    avg_speed_kmh: Optional[float] = None
) -> float:
    """
    congestion_score = (density * 0.6 + predicted_load_norm * 0.4) * 100

    density         — lane occupancy ratio (0–1)
    predicted_load  — TCN forecast normalised to 0–1 (vehicle count / saturation)
    avg_speed_kmh   — optional: if provided, blends speed factor in
    """
    total = sum(vehicle_counts.values())
    capacity = MAX_LANE_CAPACITY * max(lanes, 1)
    density = min(1.0, total / capacity)

    # Normalise TCN predicted load (saturation = 40 vehicles / min)
    predicted_norm = min(1.0, predicted_load / (MAX_LANE_CAPACITY * lanes))

    if avg_speed_kmh is not None:
        # Speed factor: free-flow ~50 km/h, gridlock ~5 km/h
        speed_factor = max(0.0, 1.0 - (avg_speed_kmh / 50.0))
        score = (density * 0.45 + predicted_norm * 0.35 + speed_factor * 0.20) * 100
    else:
        score = (density * 0.60 + predicted_norm * 0.40) * 100

    return round(min(100.0, max(0.0, score)), 2)


def estimate_co2_emission(
    vehicle_counts: Dict[str, int],
    distance_km: float = 0.1   # default: 100 m road segment
) -> EmissionResult:
    """
    total_emission = Σ(vehicle_count[type] * emission_factor[type] * distance_km)

    Returns EmissionResult per minute.
    """
    co2_total  = 0.0
    nox_total  = 0.0
    pm25_total = 0.0
    breakdown  = {}

    for vtype, count in vehicle_counts.items():
        factor = EMISSION_FACTORS.get(vtype, EMISSION_FACTORS["car"])
        co2  = count * factor["co2"]  * distance_km
        nox  = count * factor["nox"]  * distance_km
        pm25 = count * factor["pm25"] * distance_km
        co2_total  += co2
        nox_total  += nox
        pm25_total += pm25
        if count > 0:
            breakdown[vtype] = round(co2, 2)

    co2_kg  = co2_total / 1000.0
    aqi_est = _estimate_aqi(co2_kg, nox_total, pm25_total)
    aqi_lvl = _aqi_level(aqi_est)

    return EmissionResult(
        co2_g_per_min   = round(co2_total,   2),
        co2_kg_per_min  = round(co2_kg,      4),
        nox_mg_per_min  = round(nox_total,   4),
        pm25_ug_per_min = round(pm25_total,  4),
        co2_kg_per_hour = round(co2_kg * 60, 3),
        aqi_estimate    = aqi_est,
        aqi_level       = aqi_lvl,
        breakdown       = breakdown,
    )


def _estimate_aqi(co2_kg: float, nox_mg: float, pm25_ug: float) -> int:
    """Rough AQI proxy from emissions"""
    raw = (pm25_ug * 200) + (nox_mg * 50) + (co2_kg * 5)
    return min(500, max(0, int(raw)))


def _aqi_level(aqi: int) -> str:
    if aqi < 50:   return "Good"
    if aqi < 100:  return "Moderate"
    if aqi < 150:  return "Unhealthy (Sensitive Groups)"
    if aqi < 200:  return "Unhealthy"
    if aqi < 300:  return "Very Unhealthy"
    return "Hazardous"


def _congestion_label(score: float):
    for lo, hi, label, color, alert in CONGESTION_LEVELS:
        if lo <= score < hi:
            return label, color, alert
    return "Gridlock", "darkred", True


def _signal_recommendation(score: float, current_green: int = 30):
    """
    Auto-adjust green time based on congestion score.
    if congestion_score > 75 → increase_green_time
    if congestion_score < 30 → decrease_green_time
    """
    if score > SIGNAL_EXTENSION_THRESHOLD:
        adj = GREEN_EXTENSION_SECONDS
        new_green = min(MAX_GREEN_TIME, current_green + adj)
        action = "EXTEND_GREEN"
        detail = (f"Congestion {score:.0f} > {SIGNAL_EXTENSION_THRESHOLD} — "
                  f"extend green by {adj}s → {new_green}s")
    elif score < SIGNAL_REDUCTION_THRESHOLD:
        adj = -GREEN_REDUCTION_SECONDS
        new_green = max(MIN_GREEN_TIME, current_green + adj)
        action = "REDUCE_CYCLE"
        detail = (f"Congestion {score:.0f} < {SIGNAL_REDUCTION_THRESHOLD} — "
                  f"reduce cycle by {GREEN_REDUCTION_SECONDS}s → {new_green}s")
    else:
        adj = 0
        action = "NORMAL"
        detail = f"Congestion {score:.0f} — signal timing optimal"
    return action, detail, adj


def _env_rating(co2_kg_per_hour: float) -> str:
    if co2_kg_per_hour < 1:   return "A"
    if co2_kg_per_hour < 3:   return "B"
    if co2_kg_per_hour < 6:   return "C"
    if co2_kg_per_hour < 10:  return "D"
    if co2_kg_per_hour < 20:  return "E"
    return "F"


# ─────────────────────────────────────────────────────────────────────────────
# Main report generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_congestion_report(
    intersection_id: str,
    vehicle_counts: Dict[str, int],
    predicted_load: float,
    time_window_minutes: float = 1.0,
    lanes: int = 4,
    avg_speed_kmh: Optional[float] = None,
    current_green: int = 30,
    distance_km: float = 0.1,
) -> CongestionReport:
    """
    Master function — produces a complete CongestionReport.
    Called by the Flask route and by video_analysis service.
    """
    total = sum(vehicle_counts.values())

    vpm     = calculate_vehicle_flow(total, time_window_minutes)
    density = calculate_lane_density(int(vpm), MAX_LANE_CAPACITY)
    score   = calculate_congestion_score(
                  vehicle_counts, predicted_load,
                  time_window_minutes, lanes, avg_speed_kmh)
    label, color, alert = _congestion_label(score)
    emission = estimate_co2_emission(vehicle_counts, distance_km)
    sig_action, sig_detail, sig_adj = _signal_recommendation(score, current_green)

    alert_msg = None
    if alert:
        if score >= 90:
            alert_msg = ("🚨 GRIDLOCK DETECTED — Immediate signal intervention required. "
                         "Consider activating alternate routes.")
        else:
            alert_msg = ("⚠️ High Congestion Detected – Consider Signal Adjustment. "
                         f"Congestion score: {score:.0f}/100")

    trees = round(emission.co2_kg_per_hour / 0.021, 1)   # avg tree absorbs ~21g CO2/hr
    env_r = _env_rating(emission.co2_kg_per_hour)

    return CongestionReport(
        intersection_id     = intersection_id,
        timestamp           = datetime.utcnow().isoformat(),
        time_window_minutes = time_window_minutes,
        total_vehicles      = total,
        vehicles_per_minute = vpm,
        lane_density        = density,
        lane_density_pct    = round(density * 100, 1),
        lanes_active        = lanes,
        congestion_score    = score,
        congestion_status   = label,
        congestion_color    = color,
        alert_triggered     = alert,
        alert_message       = alert_msg,
        emission            = emission,
        signal_action       = sig_action,
        signal_detail       = sig_detail,
        green_adjustment    = sig_adj,
        vehicle_counts      = vehicle_counts,
        trees_needed        = trees,
        env_rating          = env_r,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Historical analytics helpers
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_historical(records: List[dict]) -> dict:
    """
    Summarise a list of congestion report dicts into analytics.
    Used by /api/traffic/congestion-history endpoint.
    """
    if not records:
        return {}

    scores    = [r["congestion_score"]    for r in records]
    vpms      = [r["vehicles_per_minute"] for r in records]
    densities = [r["lane_density"]        for r in records]
    co2s      = [r["emission"]["co2_kg_per_min"] for r in records]

    peak = max(records, key=lambda r: r["congestion_score"])
    dist = {"Free Flow": 0, "Moderate": 0, "Heavy": 0, "Congested": 0, "Gridlock": 0}
    for r in records:
        dist[r.get("congestion_status", "Moderate")] = \
            dist.get(r.get("congestion_status", "Moderate"), 0) + 1

    return {
        "period_records": len(records),
        "avg_congestion_score": round(sum(scores)    / len(scores),    2),
        "peak_congestion_score": max(scores),
        "min_congestion_score":  min(scores),
        "avg_vehicles_per_min":  round(sum(vpms)     / len(vpms),      2),
        "avg_lane_density":      round(sum(densities) / len(densities), 4),
        "total_co2_kg":          round(sum(co2s),     3),
        "avg_co2_kg_per_min":    round(sum(co2s)      / len(co2s),     4),
        "peak_event": {
            "timestamp":        peak["timestamp"],
            "congestion_score": peak["congestion_score"],
            "status":           peak["congestion_status"],
        },
        "status_distribution": dist,
        "alerts_triggered": sum(1 for r in records if r.get("alert_triggered")),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Heatmap data builder  (Leaflet-compatible)
# ─────────────────────────────────────────────────────────────────────────────

INTERSECTION_COORDS = {
    "INT-001": (12.9716, 77.5946),
    "INT-002": (12.9656, 77.6010),
    "INT-003": (12.9780, 77.6090),
    "INT-004": (12.9600, 77.5800),
}

def build_heatmap_data(reports: List[dict]) -> List[dict]:
    """
    Returns list of {lat, lng, intensity, color, label} for Leaflet heatmap.
    intensity is 0.0 – 1.0.
    """
    result = []
    seen = {}
    for r in reports:
        iid = r.get("intersection_id", "INT-001")
        if iid in seen:
            continue
        seen[iid] = True
        lat, lng = INTERSECTION_COORDS.get(iid, (12.97, 77.59))
        score = r.get("congestion_score", 0)
        color = r.get("congestion_color", "green")
        result.append({
            "intersection_id": iid,
            "lat":   lat,
            "lng":   lng,
            "intensity": round(score / 100, 3),
            "score":     score,
            "status":    r.get("congestion_status", ""),
            "color":     color,
            "label":     f"{iid}: {r.get('congestion_status','')} ({score:.0f})",
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Simulation helper — generates realistic mock data for demo
# ─────────────────────────────────────────────────────────────────────────────

def simulate_live_report(intersection_id: str = "INT-001") -> CongestionReport:
    """Generate a realistic live report (used when no live camera available)."""
    hour = datetime.utcnow().hour
    base = 28 if 7 <= hour <= 9 or 17 <= hour <= 20 else 6 if hour <= 5 else 16
    noise = random.gauss(0, 3)

    cars  = max(0, int(base * 0.55 + noise))
    buses = max(0, int(base * 0.10 + random.gauss(0, 1)))
    trucks= max(0, int(base * 0.08 + random.gauss(0, 1)))
    bikes = max(0, int(base * 0.25 + random.gauss(0, 2)))
    emerg = 1 if random.random() > 0.95 else 0

    counts = {"car": cars, "bus": buses, "truck": trucks,
              "bike": bikes, "emergency": emerg}
    predicted_load = max(3, base + random.gauss(0, 2.232))
    speed = max(5, 50 - (sum(counts.values()) / MAX_LANE_CAPACITY) * 45)

    return generate_congestion_report(
        intersection_id    = intersection_id,
        vehicle_counts     = counts,
        predicted_load     = predicted_load,
        time_window_minutes= 1.0,
        lanes              = 4,
        avg_speed_kmh      = round(speed, 1),
        current_green      = random.randint(20, 40),
        distance_km        = 0.1,
    )


def simulate_history(intersection_id: str, hours: int = 24) -> List[dict]:
    """Simulate hourly history for analytics charts."""
    now = datetime.utcnow()
    history = []
    for h in range(hours, 0, -1):
        ts = now - timedelta(hours=h)
        hour = ts.hour
        base = 28 if 7 <= hour <= 9 or 17 <= hour <= 20 else 6 if hour <= 5 else 16
        counts = {
            "car":   max(0, int(base * 0.55 + random.gauss(0, 2))),
            "bus":   max(0, int(base * 0.10 + random.gauss(0, 1))),
            "truck": max(0, int(base * 0.08 + random.gauss(0, 1))),
            "bike":  max(0, int(base * 0.25 + random.gauss(0, 2))),
            "emergency": 0,
        }
        pred = max(3, base + random.gauss(0, 2.232))
        rpt = generate_congestion_report(
            intersection_id     = intersection_id,
            vehicle_counts      = counts,
            predicted_load      = pred,
            time_window_minutes = 60.0,
        )
        d = rpt.to_dict()
        d["timestamp"] = ts.isoformat()
        history.append(d)
    return history
