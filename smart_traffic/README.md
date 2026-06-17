# 🚦 SmartTraffic AI — Urban Traffic Management System v4

A full-stack AI-powered urban traffic management platform with real-time monitoring,
computer vision, adaptive signal control, and comprehensive analytics.

---

## 🚀 Quick Start

### Option A — Docker (recommended)
```bash
docker-compose up -d
```
Then open: http://localhost (served by Nginx)
API available at: http://localhost/api/

### Option B — Local Dev
```bash
cd backend
pip install -r requirements.txt
cd ..
python app.py
```
Then open `frontend/index.html` in a browser (or use Live Server).

---

## 🔐 Demo Credentials

| Role       | Email                       | Password   |
|------------|-----------------------------|------------|
| Admin      | admin@smarttraffic.ai       | admin123   |
| Supervisor | supervisor@smarttraffic.ai  | super123   |
| Operator   | operator@smarttraffic.ai    | oper123    |

---

## 📁 Project Structure

```
smart_traffic_v4/
├── app.py                        # Flask entry point (port 5000)
├── Dockerfile                    # Production container
├── docker-compose.yml            # Flask + Nginx orchestration
├── backend/
│   ├── __init__.py               # App factory + blueprint registration
│   ├── config.py                 # Dev/Prod config
│   ├── extensions.py             # db, bcrypt, jwt, cors, socketio
│   ├── requirements.txt          # Python dependencies
│   ├── models/
│   │   └── models.py             # All SQLAlchemy models (25+ tables)
│   ├── routes/
│   │   ├── auth.py               # Login / register / logout
│   │   ├── dashboard.py          # Role-based dashboard data
│   │   ├── traffic.py            # Signal control + prediction
│   │   ├── congestion.py         # Congestion + emission analysis
│   │   ├── camera.py             # Camera feeds + upload
│   │   └── features.py           # All 50+ new feature routes (1300+ lines)
│   ├── modules/
│   │   └── congestion_emission.py
│   └── services/
│       └── video_analysis.py
├── ai_models/
│   ├── vit_detection.py          # Vision Transformer vehicle detection
│   └── tcn_prediction.py         # Temporal CNN traffic prediction
├── frontend/
│   ├── index.html                # Main dashboard (all 3 roles)
│   ├── congestion_emission.html  # Congestion & emission module
│   └── features.html             # ⭐ Feature Centre (9 categories, 50+ tools)
├── database/
│   └── schema.sql                # Reference schema (all tables)
└── nginx/
    └── nginx.conf                # HTTPS, rate limiting, SocketIO proxy
```

---

## ⚙️ Feature Centre — `/frontend/features.html`

### 🤖 AI & Detection
- **License Plate Recognition** — EasyOCR simulation, logs to DB, searchable history
- **Speed Estimation** — Frame-displacement pixel analysis, auto-creates violations
- **Helmet Detection** — Secondary classifier for no-helmet riders
- **Pedestrian & Cyclist Detection** — Safety zone alerts
- **Queue Length Estimation** — Per-direction vehicle count (N/S/E/W)
- **Night Vision Mode** — CLAHE auto-enhancement status
- **Wrong-Way Detection** — Optical flow analysis

### 📊 Analytics
- **Carbon Credit Calculator** — CO₂ savings → market credits → USD value
- **Weekly Trend Charts** — 4-week rolling congestion + CO₂ plots
- **Monthly Summary** — 6-month signal efficiency + congestion bars
- **Hotspot Prediction** — Tomorrow's congestion map (TCN-powered)
- **Comparative Analysis** — Intersection performance rankings
- **CSV Export** — Violations, detections, emissions

### 🚦 Traffic Control
- **Green Wave Corridor** — Sync offsets across 2–4 intersections
- **School Zone Mode** — Extended pedestrian phases, speed reduction
- **Incident Signal Hold** — Freeze signal state on accident
- **Diversion Suggestions** — Alternate routes when congestion > 75
- **Webster Adaptive Cycle** — Formula-based cycle length optimization

### 📱 Notifications
- **Multi-Channel Dispatch** — Email / Telegram / WhatsApp / Push
- **Test All Channels** — One-click channel health check
- **Escalation Engine** — Auto-escalate unacknowledged alerts > 5 min
- **Notification History** — Full dispatch log with filter

### 🗺️ Maps
- **Custom Zone Drawing** — Monitoring / School / Restricted / Alert zones
- **Route Playback** — 24h historical traffic animation (Leaflet)
- **Isochrone Generator** — Reachability polygon with congestion factor

### 👤 Users & Shifts
- **Audit Log** — Full action history with user/role/resource
- **Officer Shift Manager** — Set on-duty times, mark active
- **Case Assignment** — Assign violations/accidents to officers
- **2FA Setup** — TOTP secret generation for authenticator apps
- **Activity Dashboard** — Per-user action counts + duty status

### 📷 Cameras
- **Health Monitor** — Uptime %, FPS, offline alerts, heartbeat
- **PTZ Control** — Pan/Tilt/Zoom with on-screen D-pad
- **Save Video Clip** — 30s incident clip trigger
- **Video Clip Gallery** — Browse saved clips by trigger type
- **Camera Grid View** — Multi-feed metadata overlay

### 🌐 Integrations
- **Weather API** — OpenWeatherMap congestion factor injection
- **EV Charger Overlay** — Nearby chargers with availability
- **Police/Fire Dispatch** — Critical-accident auto-dispatch REST call
- **City Open Data Feed** — Anonymized public API (CC-BY 4.0)

### 🔐 Security
- **API Key Management** — Create/revoke scoped keys with rate limits
- **Rate Limit Monitor** — Per-IP request tracking (Flask-Limiter)
- **System Health Report** — DB, CPU, memory, JWT, connections
- **Docker + HTTPS** — Production-ready containerised deployment

---

## 🛠 Environment Variables (`.env`)

```env
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
DATABASE_URL=sqlite:///smart_traffic.db   # or postgresql://...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASS=your-app-password
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
OPENWEATHER_API_KEY=your-key
TWILIO_SID=your-sid
TWILIO_TOKEN=your-token
```

---

## 🎨 Themes
Three built-in themes selectable from any page:
- 🌙 **Dark** — Deep navy (default)
- ☀️ **Light** — Clean white
- ⚡ **Neon** — Cyberpunk magenta/cyan

Theme persists across all pages via `localStorage`.

---

## 🌐 API Endpoints Summary

| Prefix | Description |
|--------|-------------|
| `/api/auth/` | Login, register, logout, me |
| `/api/dashboard/` | Role-based dashboard data |
| `/api/traffic/` | Signal control, prediction, congestion |
| `/api/camera/` | Camera list, upload, live stream |
| `/api/features/ai/` | LPR, speed, helmet, pedestrian, queue, night vision |
| `/api/features/analytics/` | Carbon credits, trends, hotspots, CSV export |
| `/api/features/traffic-control/` | Green wave, school zone, incident hold, diversion |
| `/api/features/notifications/` | Send, test, escalation, history |
| `/api/features/maps/` | Custom zones, route playback, isochrone |
| `/api/features/users/` | Audit log, shifts, 2FA, assignments |
| `/api/features/cameras/` | PTZ, health, clips, grid |
| `/api/features/integrations/` | Weather, EV, dispatch, open-data |
| `/api/features/security/` | API keys, rate limits, system health |

---

## 📦 Tech Stack

**Backend:** Flask 3 · SQLAlchemy · Flask-JWT-Extended · Flask-SocketIO · Flask-Limiter · OpenCV · NumPy  
**Frontend:** Vanilla JS · Chart.js 4 · Leaflet.js · Space Grotesk font · JetBrains Mono  
**AI Models:** Vision Transformer (ViT) detection simulation · Temporal CNN (TCN) prediction  
**Infrastructure:** Docker · Nginx (HTTPS + rate limiting) · SQLite (dev) / PostgreSQL (prod)

