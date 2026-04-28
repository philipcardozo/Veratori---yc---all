#!/usr/bin/env python3
"""
Launch the inventory system with a non-webcam camera and open Chrome.

This script:
1. Starts the backend server
2. Enumerates available cameras
3. Finds the first camera that's not the webcam (index > 0)
4. Switches to that camera via API
5. Launches Chrome browser
"""

import sys
import os
import time
import subprocess
import signal
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List, Dict

# Add parent directory to path
PARENT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PARENT_DIR / 'backend'))

# Colors for output
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_info(msg):
    print(f"{BLUE}ℹ{NC} {msg}")

def print_success(msg):
    print(f"{GREEN}✓{NC} {msg}")

def print_warning(msg):
    print(f"{YELLOW}⚠{NC} {msg}")

def print_error(msg):
    print(f"{RED}✗{NC} {msg}")

def enumerate_cameras() -> List[Dict]:
    """Enumerate available cameras using OpenCV."""
    import cv2
    cameras = []
    
    print_info("Scanning for available cameras...")
    for i in range(10):
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    backend = cap.getBackendName() if hasattr(cap, 'getBackendName') else 'unknown'
                    cameras.append({
                        'index': i,
                        'name': f'Camera {i} ({backend} {width}x{height})',
                        'width': width,
                        'height': height
                    })
                    print_success(f"Found camera {i}: {width}x{height}")
                cap.release()
        except Exception as e:
            continue
    
    return cameras

def find_non_webcam_camera(cameras: List[Dict]) -> Optional[Dict]:
    """Find the first camera that's not index 0 (webcam)."""
    for cam in cameras:
        if cam['index'] > 0:
            return cam
    return None

def wait_for_server(url: str, max_wait: int = 30) -> bool:
    """Wait for the server to be ready."""
    print_info(f"Waiting for server at {url}...")
    for i in range(max_wait):
        try:
            req = urllib.request.Request(f"{url}/health")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.getcode() == 200:
                    print_success(f"Server is ready at {url}")
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
        print(".", end="", flush=True)
    
    print()
    print_warning(f"Server did not become ready within {max_wait} seconds")
    return False

def switch_camera(url: str, camera_index: int) -> bool:
    """Switch to the specified camera via API."""
    print_info(f"Switching to camera {camera_index}...")
    try:
        data = json.dumps({"index": camera_index}).encode('utf-8')
        req = urllib.request.Request(
            f"{url}/api/camera/switch",
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() == 200:
                response_data = json.loads(response.read().decode('utf-8'))
                if response_data.get('success'):
                    print_success(f"Switched to camera {camera_index}: {response_data.get('message', '')}")
                    return True
                else:
                    print_error(f"Switch failed: {response_data.get('message', 'Unknown error')}")
                    return False
            else:
                print_error(f"HTTP {response.getcode()}")
                return False
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
        print_error(f"HTTP {e.code}: {error_body}")
        return False
    except (urllib.error.URLError, OSError) as e:
        print_error(f"Failed to switch camera: {e}")
        return False

def launch_chrome(url: str):
    """Launch Chrome browser with the specified URL."""
    print_info(f"Launching Chrome with {url}...")
    
    # Detect OS
    import platform
    system = platform.system()
    
    try:
        if system == 'Darwin':  # macOS
            subprocess.Popen(['open', '-a', 'Google Chrome', url])
            print_success("Chrome launched (macOS)")
        elif system == 'Linux':
            # Try chromium-browser first, then chromium
            if subprocess.run(['which', 'chromium-browser'], capture_output=True).returncode == 0:
                subprocess.Popen(['chromium-browser', url])
            elif subprocess.run(['which', 'chromium'], capture_output=True).returncode == 0:
                subprocess.Popen(['chromium', url])
            else:
                subprocess.Popen(['xdg-open', url])
            print_success("Browser launched (Linux)")
        elif system == 'Windows':
            subprocess.Popen(['start', 'chrome', url], shell=True)
            print_success("Chrome launched (Windows)")
        else:
            print_warning(f"Unknown OS: {system}, trying default browser")
            subprocess.Popen(['xdg-open', url] if system == 'Linux' else ['open', url])
    except Exception as e:
        print_error(f"Failed to launch browser: {e}")
        print_info(f"Please open manually: {url}")

def main():
    """Main function."""
    print("=" * 60)
    print("  Launch Inventory System with Non-Webcam Camera")
    print("=" * 60)
    print()
    
    # Step 1: Enumerate cameras
    cameras = enumerate_cameras()
    
    if not cameras:
        print_error("No cameras found!")
        return 1
    
    print()
    print_info(f"Found {len(cameras)} camera(s):")
    for cam in cameras:
        marker = " (webcam)" if cam['index'] == 0 else " (non-webcam)"
        print(f"  - Camera {cam['index']}: {cam['name']}{marker}")
    print()
    
    # Step 2: Find non-webcam camera
    non_webcam = find_non_webcam_camera(cameras)
    
    if not non_webcam:
        print_warning("No non-webcam camera found (only camera 0 available)")
        print_info("Starting with webcam (camera 0)")
        target_camera_index = 0
    else:
        target_camera_index = non_webcam['index']
        print_success(f"Will use camera {target_camera_index}: {non_webcam['name']}")
    
    print()
    
    # Step 3: Start the server
    print_info("Starting backend server...")
    
    # Import the run script
    test_dir = Path(__file__).parent
    run_script = test_dir / 'run_pc_switchable.py'
    
    if not run_script.exists():
        print_error(f"Run script not found: {run_script}")
        return 1
    
    # Start server in background
    server_process = subprocess.Popen(
        [sys.executable, str(run_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(test_dir)
    )
    
    print_success(f"Server started (PID: {server_process.pid})")
    print()
    
    # Give server a moment to start
    time.sleep(3)
    
    # Step 4: Wait for server to be ready
    url = "http://127.0.0.1:8080"
    if not wait_for_server(url):
        print_error("Server failed to start")
        server_process.terminate()
        return 1
    
    print()
    
    # Step 5: Switch to non-webcam camera (if not already using it)
    if target_camera_index > 0:
        # Check current camera first
        try:
            response = requests.get(f"{url}/api/cameras", timeout=5)
            if response.status_code == 200:
                data = response.json()
                current_index = data.get('active_index', 0)
                
                if current_index != target_camera_index:
                    if not switch_camera(url, target_camera_index):
                        print_warning("Failed to switch camera, but continuing...")
                    print()
                else:
                    print_success(f"Already using camera {target_camera_index}")
                    print()
        except Exception as e:
            print_warning(f"Could not check current camera: {e}")
            print_info("Attempting to switch anyway...")
            switch_camera(url, target_camera_index)
            print()
    
    # Step 6: Launch Chrome
    launch_chrome(url)
    print()
    
    print("=" * 60)
    print_success("System is running!")
    print("=" * 60)
    print()
    print_info(f"Web interface: {url}")
    print_info(f"Active camera: Camera {target_camera_index}")
    print_info("Press Ctrl+C to stop the server")
    print()
    
    # Wait for interrupt
    try:
        server_process.wait()
    except KeyboardInterrupt:
        print()
        print_info("Shutting down...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print_success("Server stopped")
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

