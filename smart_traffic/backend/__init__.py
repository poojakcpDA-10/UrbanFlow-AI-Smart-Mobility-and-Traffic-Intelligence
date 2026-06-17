# import os
# import sys

# # Ensure project root is in path for ai_models imports
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from flask import Flask
# from flask_session import Session
# from .extensions import db, bcrypt, jwt, cors, socketio
# from .config import config
# from .models.models import (User, Detection, EmissionRecord, Violation, AccidentLog,
#                              EmergencyLog, SignalTiming, TrafficHistory, Camera,
#                              DashboardAlert, Prediction,
#                              AuditLog, LicensePlateLog, NotificationLog, CarbonCreditRecord,
#                              WeatherRecord, ApiKey, VideoClip, CustomZone, OfficerShift)


# def create_app(config_name='development'):
#     app = Flask(__name__, instance_relative_config=True)
#     app.config.from_object(config[config_name])
#     app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, '..', 'flask_sessions')

#     os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
#     os.makedirs(os.path.join(app.root_path, '..', 'uploads'), exist_ok=True)

#     # Init extensions
#     db.init_app(app)
#     bcrypt.init_app(app)
#     jwt.init_app(app)
#     cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
#     socketio.init_app(app)

#     try:
#         Session(app)
#     except Exception:
#         pass

#     # Register blueprints
#     from .routes.auth import auth_bp
#     from .routes.camera import camera_bp
#     from .routes.dashboard import dashboard_bp
#     from .routes.traffic import traffic_bp
#     from .routes.congestion import congestion_bp
#     from .routes.emergency import emergency_bp

#     app.register_blueprint(auth_bp,       url_prefix='/api/auth')
#     app.register_blueprint(camera_bp,     url_prefix='/api/camera')
#     app.register_blueprint(dashboard_bp,  url_prefix='/api/dashboard')
#     app.register_blueprint(traffic_bp,    url_prefix='/api/traffic')
#     app.register_blueprint(congestion_bp, url_prefix='/api/traffic')
#     app.register_blueprint(emergency_bp,  url_prefix='/api/emergency')

#     # SocketIO events
#     @socketio.on('connect')
#     def handle_connect():
#         print('Client connected')
#         socketio.emit('connected', {'status': 'SmartTraffic WS ready'})

#     @socketio.on('subscribe_intersection')
#     def handle_subscribe(data):
#         intersection_id = data.get('intersection_id', 'INT-001')
#         socketio.emit('subscribed', {'intersection_id': intersection_id})

#     @socketio.on('request_signal_status')
#     def handle_signal_request(data):
#         from .models.models import SignalTiming
#         intersection_id = data.get('intersection_id', 'INT-001')
#         with app.app_context():
#             signal = SignalTiming.query.filter_by(intersection_id=intersection_id).first()
#             socketio.emit('signal_status', signal.to_dict() if signal else {})

#     # Create tables
#     with app.app_context():
#         db.create_all()
#         _seed_demo_data(app)

#     @app.route("/")
#     def home():
#       return {
#         "message": "🚦 Smart Traffic Backend Running",
#         "api": "/api"
#     }

#     return app


# def _seed_demo_data(app):
#     """Seed demo users and cameras if DB is empty"""
#     from flask_bcrypt import Bcrypt
#     bc = Bcrypt()

#     if User.query.count() == 0:
#         users = [
#             User(name='Admin Officer', email='admin@smarttraffic.ai',
#                  password_hash=bc.generate_password_hash('admin123').decode('utf-8'),
#                  role='admin', is_active=True),
#             User(name='Supervisor Singh', email='supervisor@smarttraffic.ai',
#                  password_hash=bc.generate_password_hash('super123').decode('utf-8'),
#                  role='supervisor', is_active=True),
#             User(name='Operator Kumar', email='operator@smarttraffic.ai',
#                  password_hash=bc.generate_password_hash('oper123').decode('utf-8'),
#                  role='operator', is_active=True, assigned_intersection='INT-001'),
#         ]
#         for u in users:
#             db.session.add(u)

#     if Camera.query.count() == 0:
#         cameras = [
#             Camera(camera_id='CAM-001', name='North Junction A', intersection_id='INT-001',
#                    location_name='MG Road & Brigade Road', lat=12.9716, lng=77.5946,
#                    stream_url='0', status='online', resolution='1080p'),
#             Camera(camera_id='CAM-002', name='South Gate', intersection_id='INT-002',
#                    location_name='Residency Road', lat=12.9656, lng=77.6010,
#                    stream_url='', status='online', resolution='1080p'),
#             Camera(camera_id='CAM-003', name='East Corridor', intersection_id='INT-003',
#                    location_name='Old Airport Road', lat=12.9780, lng=77.6090,
#                    stream_url='', status='maintenance', resolution='720p'),
#             Camera(camera_id='CAM-004', name='West Ring', intersection_id='INT-004',
#                    location_name='Outer Ring Road', lat=12.9600, lng=77.5800,
#                    stream_url='', status='online', resolution='4K'),
#         ]
#         for c in cameras:
#             db.session.add(c)

#     try:
#         db.session.commit()
#     except Exception:
#         db.session.rollback()
import os
import sys

# Ensure project root is in path for ai_models imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify
from flask_session import Session
from .extensions import db, bcrypt, jwt, cors, socketio
from .config import config
from .models.models import (
    User, Detection, EmissionRecord, Violation, AccidentLog,
    EmergencyLog, SignalTiming, TrafficHistory, Camera,
    DashboardAlert, Prediction,
    AuditLog, LicensePlateLog, NotificationLog, CarbonCreditRecord,
    WeatherRecord, ApiKey, VideoClip, CustomZone, OfficerShift
)


def create_app(config_name='development'):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, '..', 'flask_sessions')
    app.config['JSON_AS_ASCII'] = False

    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, '..', 'uploads'), exist_ok=True)

    # Init extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    socketio.init_app(app)

    try:
        Session(app)
    except Exception:
        pass

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.camera import camera_bp
    from .routes.dashboard import dashboard_bp
    from .routes.traffic import traffic_bp
    from .routes.congestion import congestion_bp
    from .routes.emergency import emergency_bp

    app.register_blueprint(auth_bp,       url_prefix='/api/auth')
    app.register_blueprint(camera_bp,     url_prefix='/api/camera')
    app.register_blueprint(dashboard_bp,  url_prefix='/api/dashboard')
    app.register_blueprint(traffic_bp,    url_prefix='/api/traffic')
    app.register_blueprint(congestion_bp, url_prefix='/api/traffic')
    app.register_blueprint(emergency_bp,  url_prefix='/api/emergency')

    # SocketIO events
    @socketio.on('connect')
    def handle_connect():
        print('Client connected')
        socketio.emit('connected', {'status': 'SmartTraffic WS ready'})

    @socketio.on('subscribe_intersection')
    def handle_subscribe(data):
        intersection_id = data.get('intersection_id', 'INT-001')
        socketio.emit('subscribed', {'intersection_id': intersection_id})

    @socketio.on('request_signal_status')
    def handle_signal_request(data):
        from .models.models import SignalTiming
        intersection_id = data.get('intersection_id', 'INT-001')
        with app.app_context():
            signal = SignalTiming.query.filter_by(intersection_id=intersection_id).first()
            socketio.emit('signal_status', signal.to_dict() if signal else {})

    # Create tables
    with app.app_context():
        db.create_all()
        _seed_demo_data(app)

    # ✅ ROOT ROUTE (CORRECTLY INDENTED)
    @app.route("/")
    def home():
        from flask import jsonify
        return jsonify({
            "message": "🚦 Smart Traffic Backend Running",
            "api": "/api"
    })

    return app


def _seed_demo_data(app):
    """Seed demo users and cameras if DB is empty"""
    from flask_bcrypt import Bcrypt
    bc = Bcrypt()

    if User.query.count() == 0:
        users = [
            User(
                name='Admin Officer',
                email='admin@smarttraffic.ai',
                password_hash=bc.generate_password_hash('admin123').decode('utf-8'),
                role='admin',
                is_active=True
            ),
            User(
                name='Supervisor Singh',
                email='supervisor@smarttraffic.ai',
                password_hash=bc.generate_password_hash('super123').decode('utf-8'),
                role='supervisor',
                is_active=True
            ),
            User(
                name='Operator Kumar',
                email='operator@smarttraffic.ai',
                password_hash=bc.generate_password_hash('oper123').decode('utf-8'),
                role='operator',
                is_active=True,
                assigned_intersection='INT-001'
            ),
        ]
        for u in users:
            db.session.add(u)

    if Camera.query.count() == 0:
        cameras = [
            Camera(
                camera_id='CAM-001',
                name='North Junction A',
                intersection_id='INT-001',
                location_name='MG Road & Brigade Road',
                lat=12.9716,
                lng=77.5946,
                stream_url='0',
                status='online',
                resolution='1080p'
            ),
            Camera(
                camera_id='CAM-002',
                name='South Gate',
                intersection_id='INT-002',
                location_name='Residency Road',
                lat=12.9656,
                lng=77.6010,
                stream_url='',
                status='online',
                resolution='1080p'
            ),
            Camera(
                camera_id='CAM-003',
                name='East Corridor',
                intersection_id='INT-003',
                location_name='Old Airport Road',
                lat=12.9780,
                lng=77.6090,
                stream_url='',
                status='maintenance',
                resolution='720p'
            ),
            Camera(
                camera_id='CAM-004',
                name='West Ring',
                intersection_id='INT-004',
                location_name='Outer Ring Road',
                lat=12.9600,
                lng=77.5800,
                stream_url='',
                status='online',
                resolution='4K'
            ),
        ]
        for c in cameras:
            db.session.add(c)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
