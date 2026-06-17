import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend import create_app
from backend.extensions import socketio

app = create_app('development')

if __name__ == '__main__':
    print("🚦 Smart Traffic System starting...")
    print("📡 API: http://localhost:5000/api")
    print("🎛  Admin:      admin@smarttraffic.ai / admin123")
    print("👁  Supervisor: supervisor@smarttraffic.ai / super123")
    print("🎮  Operator:   operator@smarttraffic.ai / oper123")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
