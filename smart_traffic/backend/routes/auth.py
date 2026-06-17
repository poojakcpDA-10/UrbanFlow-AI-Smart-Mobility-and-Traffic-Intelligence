from flask import Blueprint, request, jsonify, session
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import secrets, re
from ..extensions import db, bcrypt
from ..models.models import User

auth_bp = Blueprint('auth', __name__)

ROLE_REDIRECTS = {
    'admin': '/admin/dashboard',
    'supervisor': '/supervisor/monitoring',
    'operator': '/operator/cameras',
}

def validate_email(email):
    return re.match(r'^[^@]+@[^@]+\.[^@]+$', email)

def validate_password(password):
    return len(password) >= 8

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'operator')

    if role not in ('admin', 'supervisor', 'operator'):
        role = 'operator'
    if not name or len(name) < 2:
        return jsonify({'success': False, 'message': 'Name too short'}), 400
    if not validate_email(email):
        return jsonify({'success': False, 'message': 'Invalid email'}), 400
    if not validate_password(password):
        return jsonify({'success': False, 'message': 'Password min 8 chars'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 409

    from flask_bcrypt import Bcrypt
    bc = Bcrypt()
    user = User(name=name, email=email, role=role)
    user.password_hash = bc.generate_password_hash(password).decode('utf-8')
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({
        'success': True, 'message': 'Registration successful',
        'token': token, 'user': user.to_dict(),
        'redirect': ROLE_REDIRECTS.get(role, '/operator/cameras')
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not validate_email(email):
        return jsonify({'success': False, 'message': 'Invalid email'}), 400
    if not password:
        return jsonify({'success': False, 'message': 'Password required'}), 400

    user = User.query.filter_by(email=email).first()
    from flask_bcrypt import Bcrypt
    bc = Bcrypt()
    if not user or not bc.check_password_hash(user.password_hash, password):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    if not user.is_active:
        return jsonify({'success': False, 'message': 'Account deactivated'}), 403

    user.last_login = datetime.utcnow()
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    session['user_id'] = user.id

    return jsonify({
        'success': True, 'message': 'Login successful',
        'token': token, 'user': user.to_dict(),
        'redirect': ROLE_REDIRECTS.get(user.role, '/operator/cameras'),
        'role': user.role
    }), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'}), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'success': False, 'message': 'Not found'}), 404
    return jsonify({'success': True, 'user': user.to_dict()}), 200

@auth_bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'Smart Traffic System'}), 200
