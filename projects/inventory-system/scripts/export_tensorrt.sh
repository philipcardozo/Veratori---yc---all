#!/usr/bin/env bash
# Build a TensorRT-optimized yolov8n.engine from yolov8n.pt.
#
# WHERE TO RUN THIS:
#   Run on the *exact* machine that will serve inference (the Jetson box).
#   TensorRT engines are non-portable — they're compiled for one specific
#   GPU + CUDA + TensorRT combo. Re-export after firmware/CUDA upgrades.
#
# WHAT IT PRODUCES:
#   models/yolov8n.engine — picked up automatically by camera_server.py on
#   next start (see MODEL_PATH logic).
#
# REQUIREMENTS (Jetson):
#   - JetPack 5.x or 6.x with CUDA + TensorRT installed
#   - `pip install ultralytics` in the same venv camera_server uses
#
# EXPECTED SPEEDUP on Jetson Orin Nano (yolov8n @ 416×416):
#   PyTorch FP32 ~45 ms/frame   →  TensorRT FP16 ~12 ms   →  TensorRT INT8 ~7 ms
#
# Usage:  bash scripts/export_tensorrt.sh           # FP16 (recommended)
#         bash scripts/export_tensorrt.sh int8      # INT8 (fastest, ~1% accuracy hit)

set -e

cd "$(dirname "$0")/.."

if [[ ! -f models/yolov8n.pt ]]; then
  echo "models/yolov8n.pt not found" >&2
  exit 1
fi

PRECISION="${1:-fp16}"

case "$PRECISION" in
  fp16)
    echo "[export] Building FP16 TensorRT engine…"
    yolo export model=models/yolov8n.pt format=engine half=True device=0 imgsz=416
    ;;
  int8)
    echo "[export] Building INT8 TensorRT engine (requires calibration images)…"
    yolo export model=models/yolov8n.pt format=engine int8=True device=0 imgsz=416
    ;;
  *)
    echo "Unknown precision '$PRECISION'. Use fp16 or int8." >&2
    exit 2
    ;;
esac

if [[ -f models/yolov8n.engine ]]; then
  echo "[export] ✓ models/yolov8n.engine ready"
  echo "[export] Restart the camera server to pick it up:"
  echo "         launchctl unload ~/Library/LaunchAgents/com.veratori.camera-server.plist"
  echo "         launchctl load   ~/Library/LaunchAgents/com.veratori.camera-server.plist"
else
  echo "[export] Engine file not produced — check ultralytics output above" >&2
  exit 3
fi
