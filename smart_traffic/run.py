"""
SmartTraffic AI — Safe Startup Script
Run this instead of app.py for better error messages.
Usage: python run.py
"""
import sys
import os

print("=" * 55)
print("  🚦 SmartTraffic AI — Starting up")
print("=" * 55)

# ── Check Python version ──────────────────────────────────
print(f"\n📌 Python: {sys.version}")
if sys.version_info < (3, 8):
    print("❌ Python 3.8+ required. Please upgrade Python.")
    sys.exit(1)

# ── Check each required package individually ─────────────
REQUIRED = [
    ("flask",               "Flask"),
    ("flask_sqlalchemy",    "Flask-SQLAlchemy"),
    ("flask_jwt_extended",  "Flask-JWT-Extended"),
    ("flask_bcrypt",        "Flask-Bcrypt"),
    ("flask_cors",          "Flask-CORS"),
    ("flask_socketio",      "Flask-SocketIO"),
    ("flask_session",       "Flask-Session"),
    ("sqlalchemy",          "SQLAlchemy"),
    ("cv2",                 "opencv-python-headless"),
    ("numpy",               "numpy"),
    ("eventlet",            "eventlet"),
]

OPTIONAL = [
    ("easyocr",   "easyocr  (only needed for License Plate Recognition)"),
    ("reportlab", "reportlab  (only needed for PDF export via backend)"),
    ("openpyxl",  "openpyxl  (only needed for Excel export)"),
    ("pyotp",     "pyotp  (only needed for 2FA)"),
]

print("\n📦 Checking required packages...")
missing = []
for mod, pkg in REQUIRED:
    try:
        __import__(mod)
        print(f"  ✅ {pkg}")
    except ImportError:
        print(f"  ❌ {pkg}  ← MISSING")
        missing.append(pkg)

print("\n📦 Checking optional packages...")
for mod, pkg in OPTIONAL:
    try:
        __import__(mod)
        print(f"  ✅ {pkg}")
    except ImportError:
        print(f"  ⚠️  {pkg}  ← not installed (optional)")

if missing:
    print(f"\n❌ Missing {len(missing)} required package(s).")
    print("   Run this command to install them:\n")
    pkgs = " ".join(p.lower().replace("-", "_").replace(" ", "") for p in missing)
    print(f"   pip install {' '.join(missing)}\n")
    print("   Or install everything at once:")
    print("   pip install flask flask-sqlalchemy flask-jwt-extended flask-bcrypt flask-cors flask-socketio flask-session opencv-python-headless numpy eventlet\n")
    sys.exit(1)

# ── Try importing the app ─────────────────────────────────
print("\n🔧 Loading application...")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from backend import create_app
    from backend.extensions import socketio
except Exception as e:
    print(f"\n❌ Import error: {e}")
    print("\n   Make sure you are running this from the smart_traffic_v4 folder:")
    print("   cd smart_traffic_v4")
    print("   python run.py\n")
    import traceback; traceback.print_exc()
    sys.exit(1)

try:
    app = create_app('development')
    print("✅ App created successfully")
except Exception as e:
    print(f"\n❌ App creation failed: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# ── Start server ──────────────────────────────────────────
print("\n" + "=" * 55)
print("  ✅ SmartTraffic AI is running!")
print("=" * 55)
print("""
  🌐 Open in browser:
     http://localhost:5000

  📄 Frontend pages (if using http.server separately):
     http://localhost:8000/frontend/index.html
     http://localhost:8000/frontend/congestion_emission.html
     http://localhost:8000/frontend/features.html

  🔐 Login credentials:
     admin@smarttraffic.ai     / admin123
     supervisor@smarttraffic.ai / super123
     operator@smarttraffic.ai   / oper123

  Press Ctrl+C to stop
""")

try:
    socketio.run(
        app,
        debug=False,
        host='0.0.0.0',
        port=5000,
        allow_unsafe_werkzeug=True
    )
except OSError as e:
    if "Address already in use" in str(e) or "10048" in str(e):
        print("❌ Port 5000 is already in use.")
        print("   Kill the existing process or use a different port:")
        print("   python run.py --port 5001\n")
    else:
        print(f"❌ Server error: {e}")
        import traceback; traceback.print_exc()
except KeyboardInterrupt:
    print("\n👋 Server stopped.")
