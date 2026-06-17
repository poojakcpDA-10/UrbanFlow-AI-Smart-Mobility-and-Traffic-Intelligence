import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-traffic-secret-2024')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///smart_traffic.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-traffic-secret-2024')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'jpg', 'jpeg', 'png'}
    SOCKETIO_PING_INTERVAL = 10
    SOCKETIO_PING_TIMEOUT = 5

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
