#!/usr/bin/env python3
"""
Quick Sales Attribution Test
Tests the fixed sales logging system with simulated inventory changes
"""

import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from sales_attribution import SalesAttributionEngine

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def test_single_product_removal():
    """Test Case 1: Single product removal"""
    print_header("TEST 1: Single Product Removal (5-Second Cadence)")
    
    engine = SalesAttributionEngine(
        confirm_intervals=2,
        min_delta_threshold=1,
        cooldown_seconds=10.0,
        snapshot_interval=5.0
    )
    
    base_time = time.time()
    
    # Snapshot 1 (t=0s): Baseline with 5 mangos
    print(f"\n[t=0s] Snapshot 1: 5 mangos detected")
    events = engine.process_snapshot({'mango': 5}, base_time)
    print(f"  Sales logged: {len(events)}")
    assert len(events) == 0, "Should not log sales on first snapshot"
    
    # Snapshot 2 (t=5s): 1 mango removed
    print(f"\n[t=5s] Snapshot 2: 4 mangos detected (1 removed)")
    events = engine.process_snapshot({'mango': 4}, base_time + 5.0)
    print(f"  Sales logged: {len(events)}")
    print(f"  Status: Decrease detected, pending validation...")
    assert len(events) == 0, "Should not log sale yet (needs confirmation)"
    
    # Snapshot 3 (t=10s): Still 4 mangos (validates decrease)
    print(f"\n[t=10s] Snapshot 3: 4 mangos detected (stable at decreased level)")
    events = engine.process_snapshot({'mango': 4}, base_time + 10.0)
    print(f"  Sales logged: {len(events)}")
    
    if events:
        sale = events[0]
        print(f"\n  ✅ SALE RECORDED:")
        print(f"     Product: {sale['product_name']}")
        print(f"     Quantity: {sale['quantity_delta']}")
        print(f"     Inventory: {sale['inventory_before']} → {sale['inventory_after']}")
        print(f"     Validated: {sale['validated']}")
        
        assert sale['product_name'] == 'mango', "Product name should be 'mango'"
        assert sale['quantity_delta'] == 1, "Quantity should be 1"
        assert sale['validated'] == True, "Sale should be validated"
    else:
        print("  ❌ ERROR: No sale logged!")
        return False
    
    print("\n  ✅ TEST 1 PASSED")
    return True

def test_multiple_products():
    """Test Case 2: Multiple different products"""
    print_header("TEST 2: Multiple Product Sales (Different Products)")
    
    engine = SalesAttributionEngine(
        confirm_intervals=2,
        min_delta_threshold=1,
        cooldown_seconds=10.0,
        snapshot_interval=5.0
    )
    
    base_time = time.time()
    
    # Snapshot 1: Baseline
    print(f"\n[t=0s] Snapshot 1: 3 mangos, 2 watermelons")
    events = engine.process_snapshot({'mango': 3, 'watermelon': 2}, base_time)
    assert len(events) == 0
    
    # Snapshot 2: Remove 1 mango
    print(f"\n[t=5s] Snapshot 2: 2 mangos, 2 watermelons (1 mango removed)")
    events = engine.process_snapshot({'mango': 2, 'watermelon': 2}, base_time + 5.0)
    assert len(events) == 0, "Pending validation"
    
    # Snapshot 3: Stable - validates mango sale
    print(f"\n[t=10s] Snapshot 3: 2 mangos, 2 watermelons (validates mango sale)")
    events = engine.process_snapshot({'mango': 2, 'watermelon': 2}, base_time + 10.0)
    print(f"  Sales logged: {len(events)}")
    
    if events:
        sale = events[0]
        print(f"\n  ✅ SALE 1 RECORDED:")
        print(f"     Product: {sale['product_name']}")
        print(f"     Quantity: {sale['quantity_delta']}")
        assert sale['product_name'] == 'mango'
    
    # Snapshot 4: Remove 1 watermelon
    print(f"\n[t=15s] Snapshot 4: 2 mangos, 1 watermelon (1 watermelon removed)")
    events = engine.process_snapshot({'mango': 2, 'watermelon': 1}, base_time + 15.0)
    assert len(events) == 0, "Pending validation"
    
    # Snapshot 5: Stable - validates watermelon sale
    print(f"\n[t=20s] Snapshot 5: 2 mangos, 1 watermelon (validates watermelon sale)")
    events = engine.process_snapshot({'mango': 2, 'watermelon': 1}, base_time + 20.0)
    print(f"  Sales logged: {len(events)}")
    
    if events:
        sale = events[0]
        print(f"\n  ✅ SALE 2 RECORDED:")
        print(f"     Product: {sale['product_name']}")
        print(f"     Quantity: {sale['quantity_delta']}")
        assert sale['product_name'] == 'watermelon'
    
    print("\n  ✅ TEST 2 PASSED")
    return True

def test_no_false_positives():
    """Test Case 3: Stable inventory = no sales"""
    print_header("TEST 3: No False Positives (Stable Inventory)")
    
    engine = SalesAttributionEngine(
        confirm_intervals=2,
        min_delta_threshold=1,
        cooldown_seconds=10.0,
        snapshot_interval=5.0
    )
    
    base_time = time.time()
    
    # Stable inventory across multiple snapshots
    for i in range(5):
        t = base_time + (i * 5.0)
        print(f"\n[t={i*5}s] Snapshot {i+1}: 5 mangos (stable)")
        events = engine.process_snapshot({'mango': 5}, t)
        print(f"  Sales logged: {len(events)}")
        assert len(events) == 0, f"Should not log sales on stable inventory (snapshot {i+1})"
    
    print("\n  ✅ TEST 3 PASSED - No false positives")
    return True

def test_multiple_quantity():
    """Test Case 4: Multiple items of same product"""
    print_header("TEST 4: Multiple Quantity Sale (Same Product)")
    
    engine = SalesAttributionEngine(
        confirm_intervals=2,
        min_delta_threshold=1,
        cooldown_seconds=10.0,
        snapshot_interval=5.0
    )
    
    base_time = time.time()
    
    # Snapshot 1: 10 mangos
    print(f"\n[t=0s] Snapshot 1: 10 mangos")
    events = engine.process_snapshot({'mango': 10}, base_time)
    assert len(events) == 0
    
    # Snapshot 2: Remove 3 mangos
    print(f"\n[t=5s] Snapshot 2: 7 mangos (3 removed)")
    events = engine.process_snapshot({'mango': 7}, base_time + 5.0)
    assert len(events) == 0
    
    # Snapshot 3: Stable - validates
    print(f"\n[t=10s] Snapshot 3: 7 mangos (validates sale)")
    events = engine.process_snapshot({'mango': 7}, base_time + 10.0)
    print(f"  Sales logged: {len(events)}")
    
    if events:
        sale = events[0]
        print(f"\n  ✅ SALE RECORDED:")
        print(f"     Product: {sale['product_name']}")
        print(f"     Quantity: {sale['quantity_delta']}")
        assert sale['quantity_delta'] == 3, "Should record quantity of 3"
    
    print("\n  ✅ TEST 4 PASSED")
    return True

def main():
    print_header("Sales Attribution System - Automated Test Suite")
    print("\nTesting 5-second snapshot cadence with temporal validation...")
    print("Configuration:")
    print("  - Snapshot Interval: 5.0 seconds")
    print("  - Confirm Intervals: 2 (requires 10s total)")
    print("  - Min Delta: 1 item")
    print("  - Cooldown: 10 seconds")
    
    tests = [
        test_single_product_removal,
        test_multiple_products,
        test_no_false_positives,
        test_multiple_quantity
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n  ❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print_header("TEST SUMMARY")
    print(f"\n  Total Tests: {len(tests)}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    
    if failed == 0:
        print("\n  🎉 ALL TESTS PASSED - System Ready for Production")
        print("\n  Next Steps:")
        print("    1. Run live test: cd 'Testing On Pc' && python3 run_pc_webcam.py")
        print("    2. Open browser: http://localhost:8080")
        print("    3. Test with real objects (see test_sales_fix.md)")
        return 0
    else:
        print("\n  ❌ SOME TESTS FAILED - Review errors above")
        return 1

if __name__ == '__main__':
    sys.exit(main())
