from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO

db       = SQLAlchemy()
bcrypt   = Bcrypt()
jwt      = JWTManager()
cors     = CORS()
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
