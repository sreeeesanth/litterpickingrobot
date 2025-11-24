# LitterBot – Vision-Based Litter Detection Dashboard

A lightweight, fast, and modern system for detecting newly placed litter objects using a webcam feed. Built using:

* **FastAPI** backend
* **OpenCV** diff-based detection
* **WebSockets** for live video streaming & trigger events
* **Next.js (App Router)** frontend dashboard
* **TailwindCSS** for clean, futuristic UI

Designed to be simple, portable, and competition-ready.

---

## 📦 Project Structure

```
litter_picking_robot/
│
├── backend/
│   ├── app.py          # FastAPI + WebSocket backend
│   ├── snapshots/      # Auto-saved detection snapshots
│   └── ...
│
├── litter_ui/
│   ├── app/
│   │   └── page.tsx    # Main dashboard UI
│   ├── public/
│   └── ...
│
└── venv/ (optional)    # Python virtual environment
```

---

## ⚙️ Backend Setup (FastAPI + OpenCV)

### 1. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install backend dependencies

```bash
pip install fastapi uvicorn opencv-python numpy
```

### 3. Run backend

```bash
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000 --ws websockets
```

Backend runs at:

```
http://localhost:8000
```

Live WebSocket stream:

```
ws://localhost:8000/ws
```

Snapshots accessible at:

```
http://localhost:8000/snapshots/<filename>
```

---

## 🖥️ Frontend Setup (Next.js + Tailwind)

### 1. Install dependencies

```bash
cd litter_ui
npm install
```

### 2. Start development server

```bash
npm run dev
```

Frontend runs at:

```
http://localhost:3000
```

Make sure the backend is running so the dashboard can stream frames and receive triggers.

---

## 🎯 Features

### ✔ Live camera feed

Streams raw frames over WebSockets in real-time.

### ✔ Automatic litter detection

Uses background subtraction & contour persistence to detect new objects.

### ✔ Auto snapshot saving

When a new object is detected:

* snapshot is saved to `backend/snapshots/`
* frontend receives a `trigger` event

### ✔ Futuristic, clean dashboard

Includes:

* live video panel
* recent events list
* saved snapshots grid
* robot status (battery/state)
* a minimal map panel with robot location

---

## 📡 WebSocket Protocol

Backend sends two types of messages:

### **1. Binary JPEG frame**

Raw live camera feed, encoded as JPEG.

### **2. JSON event**

```json
{
  "type": "trigger",
  "payload": {
    "file": "snapshots/snap_1700843002.jpg",
    "ts": 1700843002
  }
}
```

Frontend uses this to display alerts and load the screenshot.

---

## 🧪 Manual Snapshot

The dashboard includes a button for manually saving a snapshot.

---

## 🔧 Customization

### Change robot map position

Edit inside `page.tsx`:

```ts
setRobotPos({ lat: XX.XXXX, lng: YY.YYYY })
```

### Adjust detection sensitivity

Inside `backend/app.py`:

* `MIN_AREA_RATIO`
* `PERSISTENCE_FRAMES`
* `COOLDOWN_SECONDS`

---

## 🚀 Deployment

* Backend can run via `pm2`, Docker, or systemd
* Next.js can be built and exported for production
* WebSocket works behind Nginx reverse proxy

---

## 🏁 Conclusion

LitterBot is a compact and powerful vision-based litter detection system designed for competitions and demos. Its clean architecture makes it easy to extend with real robotics features like autonomous navigation, robotic arms, ROS bridges, GPS, etc.

If you want, I can generate a:

* production build guide
* Docker Compose setup
* hardware expansion (robot arm / gripper)
* real GPS map integration (Mapbox/Leaflet)
* cloud dashboard version
