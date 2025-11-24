#!/usr/bin/env python3
"""
yolo_demo.py

Run YOLOv8 on a webcam or video, show annotated frames, save annotated video,
and write detection CSV.

Usage:
  python3 yolo_demo.py --source 0 --model yolov8n.pt --out annotated.mp4 --csv detections.csv --display
  python3 yolo_demo.py --source /path/to/video.mp4 --model yolov8n.pt --out annotated.mp4 --csv detections.csv --display
"""
import argparse
import time
import csv
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

def parse_args():
    p = argparse.ArgumentParser(description="YOLO demo: annotate + save video + CSV")
    p.add_argument("--source", default="0",
                   help="Camera index (0,1,...) or path to video file. Default=0")
    p.add_argument("--model", default="yolov8n.pt", help="Path to YOLO model (weights)")
    p.add_argument("--imgsz", type=int, default=640, help="Inference image size")
    p.add_argument("--conf", type=float, default=0.35, help="Confidence threshold")
    p.add_argument("--out", default="annotated_output.mp4", help="Annotated output video path")
    p.add_argument("--csv", default="detections.csv", help="CSV output path for detections")
    p.add_argument("--display", action="store_true", help="Show live display window")
    p.add_argument("--save", action="store_true", help="Save annotated video (default: enabled)")
    p.add_argument("--fps", type=float, default=20.0, help="Output video FPS (if saving)")
    return p.parse_args()

def draw_boxes(frame, xyxy, confs, class_ids, names=None):
    h, w = frame.shape[:2]
    for i, box in enumerate(xyxy):
        x1, y1, x2, y2 = map(int, box)
        cls = int(class_ids[i]) if len(class_ids)>0 else -1
        conf = float(confs[i]) if len(confs)>0 else 0.0
        label = f'{cls}:{conf:.2f}' if names is None else f'{names.get(cls, str(cls))} {conf:.2f}'
        cv2.rectangle(frame, (x1, y1), (x2, y2), (10, 200, 255), 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), (10,200,255), -1)
        cv2.putText(frame, label, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1, cv2.LINE_AA)
    return frame

def main():
    args = parse_args()
    src = args.source
    try:
        src_idx = int(src)
    except Exception:
        src_idx = src

    model = YOLO(args.model)

    cap = cv2.VideoCapture(src_idx)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open source: {src}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

    writer = None
    save_video = bool(args.out)
    out_path = Path(args.out)
    if save_video:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_path), fourcc, args.fps, (width, height))
        print(f"[INFO] Writing annotated video to: {out_path} (fps={args.fps})")

    csv_path = Path(args.csv)
    csv_file = open(csv_path, "w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["frame", "class", "conf", "cx", "cy", "w", "h"])

    frame_id = 0
    t0 = time.time()
    names = getattr(model, "names", None) or {}

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            t1 = time.time()
            results = model.predict(frame, imgsz=args.imgsz, conf=args.conf, verbose=False)
            if len(results) > 0:
                r = results[0]
                boxes = getattr(r, "boxes", None)
                if boxes is not None and len(boxes):
                    xyxy = boxes.xyxy.cpu().numpy()
                    confs = boxes.conf.cpu().numpy().flatten()
                    cls = boxes.cls.cpu().numpy().astype(int).flatten()
                    h_frame, w_frame = frame.shape[:2]
                    for i in range(len(confs)):
                        x1,y1,x2,y2 = xyxy[i]
                        cx = ((x1 + x2)/2.0) / w_frame
                        cy = ((y1 + y2)/2.0) / h_frame
                        bw = (x2 - x1) / w_frame
                        bh = (y2 - y1) / h_frame
                        csv_writer.writerow([frame_id, int(cls[i]), float(confs[i]), float(cx), float(cy), float(bw), float(bh)])
                    draw_boxes(frame, xyxy, confs, cls, names)
            elapsed = time.time() - t1
            fps = 1.0 / elapsed if elapsed > 0 else 0.0
            cv2.putText(frame, f"Frame:{frame_id} FPS:{fps:.1f}", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200,200,20), 2)
            if args.display:
                cv2.imshow("YOLO Demo", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            if writer is not None:
                writer.write(frame)
            frame_id += 1
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        csv_file.close()
        if args.display:
            cv2.destroyAllWindows()
        total_time = time.time() - t0
        print(f"[INFO] Done. Processed {frame_id} frames in {total_time:.1f}s ({frame_id/total_time:.1f} FPS avg)")
        print(f"[INFO] CSV saved to: {csv_path}")
        if writer is not None:
            print(f"[INFO] Video saved to: {out_path}")

if __name__ == "__main__":
    main()
