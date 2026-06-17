from datetime import datetime
from ..extensions import db


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # Roles: admin | supervisor | operator
    role = db.Column(db.String(20), default='operator')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    reset_token = db.Column(db.String(255))
    reset_token_expiry = db.Column(db.DateTime)
    assigned_intersection = db.Column(db.String(50))  # For operators
    is_on_duty = db.Column(db.Boolean, default=False)
    shift_start = db.Column(db.String(10))
    shift_end = db.Column(db.String(10))
    totp_secret = db.Column(db.String(255))
    two_fa_enabled = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'email': self.email,
            'role': self.role, 'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'assigned_intersection': self.assigned_intersection
        }


class Detection(db.Model):
    __tablename__ = 'detections'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    intersection_id = db.Column(db.String(50), index=True)
    camera_id = db.Column(db.String(50))
    vehicle_count = db.Column(db.Integer, default=0)
    cars = db.Column(db.Integer, default=0)
    buses = db.Column(db.Integer, default=0)
    trucks = db.Column(db.Integer, default=0)
    bikes = db.Column(db.Integer, default=0)
    emergency = db.Column(db.Integer, default=0)
    congestion_level = db.Column(db.String(20))
    congestion_score = db.Column(db.Float)
    confidence = db.Column(db.Float)
    map_score = db.Column(db.Float)
    fps = db.Column(db.Float)
    model_used = db.Column(db.String(50), default='ViT-B/16')
    avg_speed_kmh = db.Column(db.Float)

    def to_dict(self):
        return {
            'id': self.id, 'timestamp': self.timestamp.isoformat(),
            'intersection_id': self.intersection_id, 'camera_id': self.camera_id,
            'vehicle_count': self.vehicle_count,
            'counts': {'car': self.cars, 'bus': self.buses, 'truck': self.trucks,
                       'bike': self.bikes, 'emergency': self.emergency},
            'congestion_level': self.congestion_level,
            'congestion_score': self.congestion_score,
            'confidence': self.confidence, 'fps': self.fps
        }


class EmissionRecord(db.Model):
    __tablename__ = 'emission_records'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    intersection_id = db.Column(db.String(50))
    co2_kg = db.Column(db.Float)
    nox_mg = db.Column(db.Float)
    pm25_ug = db.Column(db.Float)
    aqi = db.Column(db.Integer)
    aqi_level = db.Column(db.String(50))
    vehicle_count = db.Column(db.Integer)
    carbon_credits = db.Column(db.Float, default=0.0)

    def to_dict(self):
        return {
            'id': self.id, 'timestamp': self.timestamp.isoformat(),
            'intersection_id': self.intersection_id,
            'co2_kg': self.co2_kg, 'nox_mg': self.nox_mg,
            'pm25_ug': self.pm25_ug, 'aqi': self.aqi, 'aqi_level': self.aqi_level
        }


class Violation(db.Model):
    __tablename__ = 'violations'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    violation_type = db.Column(db.String(50))
    intersection_id = db.Column(db.String(50))
    camera_id = db.Column(db.String(50))
    severity = db.Column(db.String(20), default='medium')  # low/medium/high/critical
    vehicle_plate = db.Column(db.String(20))
    description = db.Column(db.Text)
    evidence_path = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')  # pending/reviewed/actioned
    officer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_at = db.Column(db.DateTime)
    is_severe = db.Column(db.Boolean, default=False)
    detected_speed_kmh = db.Column(db.Float)
    speed_limit_kmh = db.Column(db.Float)
    no_helmet = db.Column(db.Boolean, default=False)
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def to_dict(self):
        return {
            'id': self.id, 'timestamp': self.timestamp.isoformat(),
            'violation_type': self.violation_type,
            'intersection_id': self.intersection_id, 'camera_id': self.camera_id,
            'severity': self.severity, 'vehicle_plate': self.vehicle_plate,
            'description': self.description, 'status': self.status,
            'is_severe': self.is_severe
        }


class AccidentLog(db.Model):
    __tablename__ = 'accident_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    intersection_id = db.Column(db.String(50))
    camera_id = db.Column(db.String(50))
    severity = db.Column(db.String(20))  # high/critical
    accident_type = db.Column(db.String(50))
    confidence = db.Column(db.Float)
    vehicles_involved = db.Column(db.Integer)
    description = db.Column(db.Text)
    evidence_path = db.Column(db.String(255))
    status = db.Column(db.String(20), default='open')  # open/responded/closed
    emergency_dispatched = db.Column(db.Boolean, default=False)
    officer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_at = db.Column(db.DateTime)
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def to_dict(self):
        return {
            'id': self.id, 'timestamp': self.timestamp.isoformat(),
            'intersection_id': self.intersection_id, 'severity': self.severity,
            'accident_type': self.accident_type, 'confidence': self.confidence,
            'description': self.description, 'status': self.status,
            'emergency_dispatched': self.emergency_dispatched
        }


class EmergencyLog(db.Model):
    __tablename__ = 'emergency_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    intersection_id = db.Column(db.String(50))
    camera_id = db.Column(db.String(50))
    vehicle_type = db.Column(db.String(50))  # Ambulance/Fire/Police
    direction = db.Column(db.String(20))
    response_time = db.Column(db.Float)
    override_duration = db.Column(db.Integer)
    resolved = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id, 'timestamp': self.timestamp.isoformat(),
            'intersection_id': self.intersection_id, 'vehicle_type': self.vehicle_type,
            'direction': self.direction, 'override_duration': self.override_duration,
            'resolved': self.resolved
        }


class SignalTiming(db.Model):
    __tablename__ = 'signal_timings'
    id = db.Column(db.Integer, primary_key=True)
    intersection_id = db.Column(db.String(50), unique=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    cycle_length = db.Column(db.Float)
    north_green = db.Column(db.Integer, default=30)
    south_green = db.Column(db.Integer, default=30)
    east_green = db.Column(db.Integer, default=30)
    west_green = db.Column(db.Integer, default=30)
    is_emergency_override = db.Column(db.Boolean, default=False)
    override_direction = db.Column(db.String(20))
    override_expires_at = db.Column(db.DateTime)
    mode = db.Column(db.String(20), default='adaptive')  # adaptive/manual/emergency
    green_wave_enabled = db.Column(db.Boolean, default=False)
    green_wave_offset = db.Column(db.Integer, default=0)
    school_zone_active = db.Column(db.Boolean, default=False)
    incident_hold_active = db.Column(db.Boolean, default=False)
    incident_hold_reason = db.Column(db.String(200))

    def to_dict(self):
        return {
            'id': self.id, 'intersection_id': self.intersection_id,
            'updated_at': self.updated_at.isoformat(), 'cycle_length': self.cycle_length,
            'green_times': {'north': self.north_green, 'south': self.south_green,
                            'east': self.east_green, 'west': self.west_green},
            'is_emergency_override': self.is_emergency_override,
            'override_direction': self.override_direction, 'mode': self.mode
        }


class TrafficHistory(db.Model):
    __tablename__ = 'traffic_history'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    intersection_id = db.Column(db.String(50))
    vehicle_count = db.Column(db.Integer, default=0)
    vehicles_per_min = db.Column(db.Float, default=0.0)
    congestion_score = db.Column(db.Float, default=0.0)
    avg_delay = db.Column(db.Float, default=0.0)
    co2_emission = db.Column(db.Float, default=0.0)

    def to_dict(self):
        return {
            'id': self.id, 'timestamp': self.timestamp.isoformat(),
            'intersection_id': self.intersection_id,
            'vehicle_count': self.vehicle_count,
            'vehicles_per_min': self.vehicles_per_min,
            'congestion_score': self.congestion_score,
            'avg_delay': self.avg_delay, 'co2_emission': self.co2_emission
        }


class Prediction(db.Model):
    __tablename__ = 'predictions'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    intersection_id = db.Column(db.String(50))
    forecast_hour = db.Column(db.Integer)
    predicted_count = db.Column(db.Float)
    actual_count = db.Column(db.Float)
    rmse = db.Column(db.Float)
    confidence = db.Column(db.Float)

    def to_dict(self):
        return {
            'id': self.id, 'created_at': self.created_at.isoformat(),
            'intersection_id': self.intersection_id,
            'forecast_hour': self.forecast_hour,
            'predicted_count': self.predicted_count,
            'confidence': self.confidence
        }


class Camera(db.Model):
    __tablename__ = 'cameras'
    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(100))
    intersection_id = db.Column(db.String(50))
    location_name = db.Column(db.String(200))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    stream_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='online')  # online/offline/maintenance
    resolution = db.Column(db.String(20), default='1080p')
    fps = db.Column(db.Integer, default=30)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    uptime_pct = db.Column(db.Float, default=99.0)
    last_heartbeat = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id, 'camera_id': self.camera_id, 'name': self.name,
            'intersection_id': self.intersection_id, 'location_name': self.location_name,
            'lat': self.lat, 'lng': self.lng, 'stream_url': self.stream_url,
            'is_active': self.is_active, 'status': self.status,
            'resolution': self.resolution, 'fps': self.fps
        }


class DashboardAlert(db.Model):
    __tablename__ = 'dashboard_alerts'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    alert_type = db.Column(db.String(50))  # ACCIDENT/VIOLATION/EMERGENCY/CONGESTION
    severity = db.Column(db.String(20))
    intersection_id = db.Column(db.String(50))
    camera_id = db.Column(db.String(50))
    message = db.Column(db.Text)
    action_required = db.Column(db.Boolean, default=False)
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    acknowledged_at = db.Column(db.DateTime)
    related_id = db.Column(db.Integer)  # FK to accident_log/violation id
    escalated = db.Column(db.Boolean, default=False)
    escalated_at = db.Column(db.DateTime)
    alert_type_detail = db.Column(db.String(50))

    def to_dict(self):
        return {
            'id': self.id, 'timestamp': self.timestamp.isoformat(),
            'alert_type': self.alert_type, 'severity': self.severity,
            'intersection_id': self.intersection_id, 'message': self.message,
            'action_required': self.action_required,
            'acknowledged': self.acknowledged
        }


# ─────────────────────────────────────────────────────────────────────────────
# NEW FEATURE MODELS
# ─────────────────────────────────────────────────────────────────────────────

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user_name = db.Column(db.String(100))
    user_role = db.Column(db.String(20))
    action = db.Column(db.String(100))
    resource = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    success = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'timestamp': self.timestamp.isoformat(),
            'user_name': self.user_name, 'user_role': self.user_role,
            'action': self.action, 'resource': self.resource,
            'details': self.details, 'ip_address': self.ip_address,
            'success': self.success
        }


class LicensePlateLog(db.Model):
    __tablename__ = 'license_plate_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    plate_number = db.Column(db.String(20), index=True)
    camera_id = db.Column(db.String(50))
    intersection_id = db.Column(db.String(50))
    confidence = db.Column(db.Float)
    vehicle_type = db.Column(db.String(30))
    linked_violation_id = db.Column(db.Integer, db.ForeignKey('violations.id'))
    image_path = db.Column(db.String(255))
    speed_kmh = db.Column(db.Float)
    direction = db.Column(db.String(20))

    def to_dict(self):
        return {
            'id': self.id, 'timestamp': self.timestamp.isoformat(),
            'plate_number': self.plate_number, 'camera_id': self.camera_id,
            'intersection_id': self.intersection_id, 'confidence': self.confidence,
            'vehicle_type': self.vehicle_type, 'speed_kmh': self.speed_kmh,
            'direction': self.direction
        }


class NotificationLog(db.Model):
    __tablename__ = 'notification_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    channel = db.Column(db.String(30))
    recipient = db.Column(db.String(150))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    alert_type = db.Column(db.String(50))
    status = db.Column(db.String(20), default='sent')
    error_msg = db.Column(db.String(255))
    related_alert_id = db.Column(db.Integer)
    escalated = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id, 'timestamp': self.timestamp.isoformat(),
            'channel': self.channel, 'recipient': self.recipient,
            'subject': self.subject, 'status': self.status,
            'alert_type': self.alert_type, 'escalated': self.escalated
        }


class CarbonCreditRecord(db.Model):
    __tablename__ = 'carbon_credit_records'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    intersection_id = db.Column(db.String(50))
    baseline_co2_kg = db.Column(db.Float)
    actual_co2_kg = db.Column(db.Float)
    optimized_co2_kg = db.Column(db.Float)
    co2_saved_kg = db.Column(db.Float)
    carbon_credits = db.Column(db.Float)
    credits_earned = db.Column(db.Float)
    monetary_value_usd = db.Column(db.Float)
    credit_value_usd = db.Column(db.Float)
    period_hours = db.Column(db.Integer, default=24)

    def to_dict(self):
        return {
            'id': self.id,
            'date': (self.timestamp or self.date).isoformat(),
            'intersection_id': self.intersection_id,
            'co2_saved_kg': self.co2_saved_kg,
            'carbon_credits': self.carbon_credits or self.credits_earned,
            'monetary_value_usd': self.monetary_value_usd or self.credit_value_usd
        }


class WeatherRecord(db.Model):
    __tablename__ = 'weather_records'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    location = db.Column(db.String(100))
    temperature_c = db.Column(db.Float)
    humidity_pct = db.Column(db.Float)
    condition = db.Column(db.String(50))   # Clear/Rain/Fog/Storm
    wind_kmh = db.Column(db.Float)
    visibility_km = db.Column(db.Float)
    congestion_factor = db.Column(db.Float, default=1.0)  # multiplier

    def to_dict(self):
        return {
            'id': self.id, 'timestamp': self.timestamp.isoformat(),
            'temperature_c': self.temperature_c, 'humidity_pct': self.humidity_pct,
            'condition': self.condition, 'wind_kmh': self.wind_kmh,
            'visibility_km': self.visibility_km, 'congestion_factor': self.congestion_factor
        }


class ApiKey(db.Model):
    __tablename__ = 'api_keys'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(100))
    key_hash = db.Column(db.String(255), unique=True)
    key_prefix = db.Column(db.String(10))
    scope = db.Column(db.String(200))
    scopes = db.Column(db.String(200))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    last_used = db.Column(db.DateTime)
    requests_today = db.Column(db.Integer, default=0)
    rate_limit = db.Column(db.Integer, default=100)
    expires_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id, 'created_at': self.created_at.isoformat(),
            'name': self.name, 'key_prefix': self.key_prefix,
            'scope': self.scope or self.scopes, 'is_active': self.is_active,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'requests_today': self.requests_today, 'rate_limit': self.rate_limit,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


class VideoClip(db.Model):
    __tablename__ = 'video_clips'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    camera_id = db.Column(db.String(50))
    intersection_id = db.Column(db.String(50))
    trigger_type = db.Column(db.String(50))
    trigger_id = db.Column(db.Integer)
    duration_seconds = db.Column(db.Integer, default=30)
    duration_sec = db.Column(db.Integer, default=30)
    file_path = db.Column(db.String(255))
    file_size_mb = db.Column(db.Float)
    thumbnail_path = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id': self.id, 'created_at': self.created_at.isoformat(),
            'camera_id': self.camera_id, 'intersection_id': self.intersection_id,
            'trigger_type': self.trigger_type,
            'duration_seconds': self.duration_seconds or self.duration_sec,
            'file_size_mb': self.file_size_mb, 'file_path': self.file_path
        }


class CustomZone(db.Model):
    __tablename__ = 'custom_zones'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(100))
    zone_type = db.Column(db.String(30))   # monitoring/school/restricted/alert
    polygon_coords = db.Column(db.Text)    # JSON array of [lat,lng] pairs
    coordinates = db.Column(db.Text)       # alias for polygon_coords
    color = db.Column(db.String(20), default='#00d4ff')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    alert_on_entry = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id, 'created_at': self.created_at.isoformat(),
            'name': self.name, 'zone_type': self.zone_type,
            'polygon_coords': self.polygon_coords,
            'color': self.color, 'is_active': self.is_active
        }


class OfficerShift(db.Model):
    __tablename__ = 'officer_shifts'
    id = db.Column(db.Integer, primary_key=True)
    officer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    shift_date = db.Column(db.DateTime, default=datetime.utcnow)
    shift_start = db.Column(db.String(10))   # "08:00"
    shift_end = db.Column(db.String(10))     # "16:00"
    assigned_intersection = db.Column(db.String(50))
    is_on_duty = db.Column(db.Boolean, default=False)
    cases_handled = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id, 'officer_id': self.officer_id,
            'shift_date': self.shift_date.isoformat(),
            'shift_start': self.shift_start, 'shift_end': self.shift_end,
            'assigned_intersection': self.assigned_intersection,
            'is_on_duty': self.is_on_duty, 'cases_handled': self.cases_handled
        }
