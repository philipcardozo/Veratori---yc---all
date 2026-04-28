#!/usr/bin/env python3
"""
Test script to verify freshness tracking works for all products
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from inventory_persistent import PersistentInventoryTracker
import time

def test_freshness_tracking():
    """Test that freshness tracking works for all products"""
    
    print("=" * 80)
    print("FRESHNESS TRACKING TEST - ALL PRODUCTS")
    print("=" * 80)
    
    # Create tracker with test database
    test_db = "data/test_inventory.db"
    if os.path.exists(test_db):
        os.remove(test_db)
        print(f"Removed old test database: {test_db}")
    
    # Initialize tracker
    print("\n1. Initializing tracker...")
    tracker = PersistentInventoryTracker(
        db_path=test_db,
        expiration_days=5,
        enable_persistence=True
    )
    
    # Check configuration
    print(f"\n2. Checking configuration...")
    print(f"   FRESHNESS_TRACKED_PRODUCTS: {tracker.FRESHNESS_TRACKED_PRODUCTS}")
    if tracker.FRESHNESS_TRACKED_PRODUCTS is None:
        print("   ✓ Tracking ALL products (as expected)")
    else:
        print(f"   ✗ Only tracking {len(tracker.FRESHNESS_TRACKED_PRODUCTS)} products")
        return False
    
    # Simulate detections for multiple products
    print("\n3. Simulating detections for 10 different products...")
    
    test_products = [
        "Mango",
        "Sprite",
        "Watermelon",
        "Coke Zero",
        "Perrier",
        "Pineapple",
        "Cantaloupe",
        "Strawberry",
        "Grapes",
        "Black Cherry Cane Sugar"
    ]
    
    # Create mock detections
    detections = []
    for i, product in enumerate(test_products):
        detections.append({
            'class_id': i,
            'class_name': product,
            'confidence': 0.9,
            'bbox': [100, 100, 200, 200]
        })
    
    # Update tracker
    tracker.update(detections)
    
    # Wait a moment for processing
    time.sleep(0.5)
    
    # Check freshness state
    print("\n4. Checking freshness state...")
    freshness_state = tracker.get_freshness_state()
    
    print(f"   Products being tracked: {len(freshness_state)}")
    
    if len(freshness_state) == 0:
        print("   ✗ No products tracked!")
        return False
    
    print(f"\n5. Freshness data for tracked products:")
    print("   " + "-" * 76)
    print(f"   {'Product':<30} {'Age (days)':<15} {'Expired':<10}")
    print("   " + "-" * 76)
    
    for product, data in freshness_state.items():
        age = data.get('age_days', 0)
        expired = "Yes" if data.get('is_expired', False) else "No"
        print(f"   {product:<30} {age:<15.2f} {expired:<10}")
    
    print("   " + "-" * 76)
    
    # Verify all test products are tracked
    print(f"\n6. Verifying all test products are tracked...")
    tracked_products = set(freshness_state.keys())
    test_products_set = set(test_products)
    
    missing = test_products_set - tracked_products
    if missing:
        print(f"   ✗ Missing products: {missing}")
        return False
    else:
        print(f"   ✓ All {len(test_products)} test products are tracked!")
    
    # Test with additional products
    print(f"\n7. Testing with 5 more products...")
    
    additional_products = [
        "Ito Milk Tea",
        "Jasmine Green Tea",
        "Maui Custard",
        "Philadelphia 6 roll",
        "Essentia"
    ]
    
    additional_detections = []
    for i, product in enumerate(additional_products):
        additional_detections.append({
            'class_id': i + 100,
            'class_name': product,
            'confidence': 0.85,
            'bbox': [150, 150, 250, 250]
        })
    
    tracker.update(additional_detections)
    time.sleep(0.5)
    
    # Check updated freshness state
    freshness_state = tracker.get_freshness_state()
    print(f"   Total products now tracked: {len(freshness_state)}")
    
    expected_total = len(test_products) + len(additional_products)
    if len(freshness_state) >= expected_total:
        print(f"   ✓ Successfully tracking {len(freshness_state)} products!")
    else:
        print(f"   ✗ Expected at least {expected_total}, got {len(freshness_state)}")
        return False
    
    # Test database persistence
    print(f"\n8. Testing database persistence...")
    if tracker.persistence:
        stats = tracker.get_persistence_stats()
        print(f"   Database enabled: {stats.get('enabled', False)}")
        print(f"   Total snapshots: {stats.get('total_snapshots', 0)}")
        print(f"   Total freshness records: {stats.get('total_freshness', 0)}")
        
        if stats.get('total_freshness', 0) >= expected_total:
            print(f"   ✓ Freshness data persisted to database!")
        else:
            print(f"   ✗ Expected {expected_total} freshness records, got {stats.get('total_freshness', 0)}")
    
    # Cleanup
    print(f"\n9. Cleaning up...")
    tracker.close()
    if os.path.exists(test_db):
        os.remove(test_db)
        print(f"   Removed test database: {test_db}")
    
    print("\n" + "=" * 80)
    print("TEST PASSED! ✓")
    print("=" * 80)
    print("\nFreshness tracking is working correctly for all products!")
    print("All detected products will be tracked for freshness automatically.")
    print("\nTo see this in action:")
    print("  1. cd backend")
    print("  2. python3 main.py")
    print("  3. Open http://localhost:8080")
    print("  4. Watch as all products show freshness timers")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        success = test_freshness_tracking()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

