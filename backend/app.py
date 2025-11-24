# ~/Desktop/litter_picking_robot/backend/app.py
import asyncio
import io
import json
import os
import time
from typing import List

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

app = FastAPI(title="Litter Placement Detector (diff-based)")

# Config
CAM_SOURCE = 0  # camera index or path
FPS_LIMIT = 15  # best-effort throttle
SNAPSHOT_FOLDER = "snapshots"
MIN_AREA_RATIO = 0.004   # minimal contour area ratio relative to frame (tune)
PERSISTENCE_FRAMES = 3   # require this many consecutive frames of presence before trigger
COOLDOWN_SECONDS = 6     # don't re-trigger within this many seconds
BG_LEARNING_RATE = 0.01  # background running average alpha

# Ensure folders
os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)

# WebSocket manager
class WSMgr:
    def __init__(self):
        self.clients: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket):
        try:
            self.clients.remove(ws)
        except ValueError:
            pass

    async def broadcast_bytes(self, b: bytes):
        dead = []
        for ws in list(self.clients):
            try:
                if ws.client_state.value == 1:  # CONNECTED
                    await ws.send_bytes(b)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def broadcast_json(self, obj):
        txt = json.dumps(obj)
        dead = []
        for ws in list(self.clients):
            try:
                if ws.client_state.value == 1:
                    await ws.send_text(txt)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

ws_mgr = WSMgr()

# background & persistence state
bg_model = None
last_trigger_at = 0.0
present_count = 0

# helper: jpeg encoder
def encode_jpeg(frame: np.ndarray, quality=80) -> bytes:
    ret, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    return buf.tobytes() if ret else b""

async def camera_loop():
    global bg_model, last_trigger_at, present_count
    cap = cv2.VideoCapture(CAM_SOURCE)
    if not cap.isOpened():
        print("Cannot open camera source:", CAM_SOURCE)
        return

    # warm up read
    ret, frame = cap.read()
    if not ret:
        print("Failed to read initial frame")
        cap.release()
        return

    h, w = frame.shape[:2]
    min_area_px = max(10, int(MIN_AREA_RATIO * (w * h)))

    # initialize background as float grayscale image
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    bg_model = gray.astype("float32")

    last_send = 0.0
    while True:
        t0 = time.time()
        ret, frame = cap.read()
        if not ret:
            await asyncio.sleep(0.05)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # update background
        cv2.accumulateWeighted(gray, bg_model, BG_LEARNING_RATE)
        bg_uint8 = cv2.convertScaleAbs(bg_model)

        # compute absolute diff and threshold
        diff = cv2.absdiff(gray, bg_uint8)
        _, th = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        # morphology to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
        th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel)
        th = cv2.morphologyEx(th, cv2.MORPH_DILATE, kernel, iterations=1)

        # find contours (new objects)
        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []
        for cnt in contours:
            x,y,wc,hc = cv2.boundingRect(cnt)
            area = wc*hc
            if area >= min_area_px:
                detections.append({"bbox": [int(x),int(y),int(x+wc),int(y+hc)], "area": int(area)})

        # If any detections -> increase persistence counter, else reset
        if detections:
            present_count += 1
        else:
            present_count = 0

        # Draw boxes for streaming
        vis = frame.copy()
        for d in detections:
            x1,y1,x2,y2 = d["bbox"]
            cv2.rectangle(vis, (x1,y1), (x2,y2), (10,200,255), 2)
            cv2.putText(vis, f"NEW {d['area']}", (x1,y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (10,200,255), 1)

        # If persisted and cooldown passed -> trigger snapshot
        now = time.time()
        if present_count >= PERSISTENCE_FRAMES and (now - last_trigger_at) > COOLDOWN_SECONDS:
            last_trigger_at = now
            present_count = 0
            # crop the largest detection for snapshot (or full frame)
            largest = max(detections, key=lambda x: x["area"]) if detections else None
            if largest:
                x1,y1,x2,y2 = largest["bbox"]
                crop = frame[max(0,y1-10):y2+10, max(0,x1-10):x2+10]
                fname = f"{SNAPSHOT_FOLDER}/snap_{int(now)}.jpg"
                cv2.imwrite(fname, crop if crop.size else frame)
            else:
                fname = f"{SNAPSHOT_FOLDER}/snap_{int(now)}.jpg"
                cv2.imwrite(fname, frame)
            print("Trigger: saved snapshot", fname)
            # notify clients
            payload = {"type":"trigger", "payload": {"file": fname, "ts": now}}
            await ws_mgr.broadcast_json(payload)

        # send annotated frame at limited FPS
        if (now - last_send) >= (1.0 / max(1, FPS_LIMIT)):
            jpg = encode_jpeg(vis, quality=70)
            await ws_mgr.broadcast_bytes(jpg)
            last_send = now

        # small sleep to yield
        await asyncio.sleep(0.01)

@app.on_event("startup")
async def startup():
    print("Starting camera_loop task...")
    asyncio.create_task(camera_loop())

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_mgr.connect(ws)
    try:
        while True:
            # keep connection open; allow client pings
            data = await ws.receive_text()
            # optionally handle client messages here
    except WebSocketDisconnect:
        ws_mgr.disconnect(ws)
    except Exception as e:
        ws_mgr.disconnect(ws)
        print("ws error:", e)

@app.get("/snapshots")
def list_snapshots():
    snaps = sorted(os.listdir(SNAPSHOT_FOLDER), reverse=True)
    return {"ok": True, "snapshots": snaps}

@app.get("/health")
def health():
    return {"ok": True}
