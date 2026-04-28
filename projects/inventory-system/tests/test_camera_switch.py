#!/usr/bin/env python3
"""
Test script for camera switching functionality
"""

import requests
import time
import sys

BASE_URL = "http://localhost:8080"

def test_camera_status():
    """Test camera status endpoint"""
    print("Testing camera status endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/camera/status")
        data = response.json()
        
        if data.get('ok'):
            print(f"  ✓ Status: {data}")
            print(f"  ✓ Active source: {data.get('active_source')}")
            print(f"  ✓ Camera index: {data.get('camera_index')}")
            return True
        else:
            print(f"  ✗ Failed: {data}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_camera_switch(target_source):
    """Test camera switch to target source"""
    print(f"\nTesting switch to {target_source}...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/camera/source",
            json={"source": target_source},
            timeout=10
        )
        data = response.json()
        
        if data.get('ok'):
            print(f"  ✓ Switch successful")
            print(f"  ✓ Active source: {data.get('active_source')}")
            print(f"  ✓ Restart time: {data.get('restart_ms')}ms")
            return True
        else:
            print(f"  ✗ Switch failed: {data.get('error')}")
            print(f"  ✓ Active source (rollback): {data.get('active_source')}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("Camera Switch Test Suite")
    print("=" * 60)
    print(f"Testing server at: {BASE_URL}")
    print("\nMake sure the server is running with:")
    print("  cd 'Testing On Pc' && python3 run_pc_switchable.py")
    print()
    
    # Test 1: Check initial status
    print("\n" + "=" * 60)
    print("Test 1: Check Camera Status")
    print("=" * 60)
    if not test_camera_status():
        print("\n✗ Server may not be running. Exiting.")
        sys.exit(1)
    
    time.sleep(1)
    
    # Test 2: Switch to phone camera
    print("\n" + "=" * 60)
    print("Test 2: Switch to Phone Camera")
    print("=" * 60)
    print("Note: This may fail if phone is not connected - that's OK!")
    test_camera_switch("phone")
    
    time.sleep(2)
    
    # Test 3: Check status after switch
    print("\n" + "=" * 60)
    print("Test 3: Check Status After Switch")
    print("=" * 60)
    test_camera_status()
    
    time.sleep(1)
    
    # Test 4: Switch back to webcam
    print("\n" + "=" * 60)
    print("Test 4: Switch to Webcam")
    print("=" * 60)
    test_camera_switch("webcam")
    
    time.sleep(2)
    
    # Test 5: Final status check
    print("\n" + "=" * 60)
    print("Test 5: Final Status Check")
    print("=" * 60)
    test_camera_status()
    
    # Test 6: Invalid source
    print("\n" + "=" * 60)
    print("Test 6: Invalid Source (Should Fail)")
    print("=" * 60)
    print("Testing switch to invalid source...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/camera/source",
            json={"source": "invalid"},
            timeout=10
        )
        data = response.json()
        
        if not data.get('ok'):
            print(f"  ✓ Correctly rejected invalid source")
            print(f"  ✓ Error: {data.get('error')}")
        else:
            print(f"  ✗ Should have rejected invalid source")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Test Suite Complete")
    print("=" * 60)
    print("\nManual Tests:")
    print("1. Open http://localhost:8080 in your browser")
    print("2. Click 'Webcam' button - should see webcam feed")
    print("3. Click 'Phone Camera' button - should switch (if phone connected)")
    print("4. Check status message shows timing and success/failure")
    print("5. Verify video stream continues without page reload")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)





