#!/usr/bin/env python3
"""
System Validation Script
Performs comprehensive checks before production deployment
"""

import sys
import os
from pathlib import Path
import sqlite3
import yaml

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

def check_file_exists(path, description):
    """Check if a file exists"""
    if Path(path).exists():
        print(f"✓ {description}: {path}")
        return True
    else:
        print(f"✗ {description} MISSING: {path}")
        return False

def check_config_file(config_path):
    """Validate configuration file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        required_sections = ['camera', 'detector', 'inventory', 'server', 'stream']
        optional_sections = ['alerts']
        
        all_good = True
        for section in required_sections:
            if section in config:
                print(f"✓ Config section '{section}' present")
            else:
                print(f"✗ Config section '{section}' MISSING")
                all_good = False
        
        for section in optional_sections:
            if section in config:
                print(f"✓ Optional config section '{section}' present")
            else:
                print(f"  Optional config section '{section}' not present (will use defaults)")
        
        return all_good
    
    except Exception as e:
        print(f"✗ Config validation failed: {e}")
        return False

def check_database_schema():
    """Check database schema if database exists"""
    db_path = Path('data/inventory.db')
    if not db_path.exists():
        print("  Database not yet created (will be created on first run)")
        return True
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        required_tables = ['inventory_snapshots', 'product_freshness', 'sales_log', 'alerts_log']
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        all_good = True
        for table in required_tables:
            if table in existing_tables:
                print(f"✓ Database table '{table}' exists")
            else:
                print(f"✗ Database table '{table}' MISSING")
                all_good = False
        
        # Check WAL mode
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        if journal_mode.upper() == 'WAL':
            print(f"✓ Database WAL mode enabled")
        else:
            print(f"  Database journal mode: {journal_mode} (WAL recommended)")
        
        conn.close()
        return all_good
    
    except Exception as e:
        print(f"✗ Database check failed: {e}")
        return False

def check_python_imports():
    """Check if all required Python modules can be imported"""
    required_modules = [
        ('cv2', 'opencv-python'),
        ('yaml', 'PyYAML'),
        ('aiohttp', 'aiohttp'),
        ('numpy', 'numpy'),
    ]
    
    all_good = True
    for module_name, package_name in required_modules:
        try:
            __import__(module_name)
            print(f"✓ Python module '{module_name}' available")
        except ImportError:
            print(f"✗ Python module '{module_name}' MISSING (install: pip install {package_name})")
            all_good = False
    
    # Check for ultralytics (YOLO)
    try:
        import ultralytics
        print(f"✓ Python module 'ultralytics' available")
    except ImportError:
        print(f"✗ Python module 'ultralytics' MISSING (install: pip install ultralytics)")
        all_good = False
    
    return all_good

def check_permissions():
    """Check file permissions"""
    checks = [
        ('data', 'Data directory writable'),
        ('.', 'Project root readable'),
    ]
    
    all_good = True
    for path, description in checks:
        p = Path(path)
        if p.exists():
            if os.access(p, os.W_OK if 'writable' in description else os.R_OK):
                print(f"✓ {description}")
            else:
                print(f"✗ {description} - Permission denied")
                all_good = False
        else:
            if 'data' in path:
                # Data directory will be created
                print(f"  Data directory will be created on first run")
            else:
                print(f"✗ {description} - Path does not exist")
                all_good = False
    
    return all_good

def main():
    """Run all validation checks"""
    print("=" * 60)
    print("Jetson Orin Inventory Vision System v2.0")
    print("System Validation")
    print("=" * 60)
    print()
    
    all_checks_passed = True
    
    # Check critical files
    print("1. Critical Files Check")
    print("-" * 60)
    critical_files = [
        ('models/best.pt', 'YOLO model'),
        ('backend/main.py', 'Main application'),
        ('backend/camera.py', 'Camera module'),
        ('backend/detector.py', 'Detector module'),
        ('backend/inventory.py', 'Inventory module'),
        ('backend/inventory_persistent.py', 'Persistent inventory module'),
        ('backend/persistence.py', 'Persistence module'),
        ('backend/sales_attribution.py', 'Sales attribution module'),
        ('backend/alerts.py', 'Alerts module'),
        ('backend/server.py', 'Server module'),
        ('apps/web-frontend/index.html', 'Frontend UI'),
        ('config/config.yaml', 'Jetson configuration'),
        ('tests/pc_config.yaml', 'PC webcam configuration'),
        ('tests/phone_config.yaml', 'Phone camera configuration'),
    ]
    
    for path, desc in critical_files:
        if not check_file_exists(path, desc):
            all_checks_passed = False
    print()
    
    # Check Python dependencies
    print("2. Python Dependencies Check")
    print("-" * 60)
    if not check_python_imports():
        all_checks_passed = False
    print()
    
    # Check configuration files
    print("3. Configuration Validation")
    print("-" * 60)
    for config_file in ['config/config.yaml', 'tests/pc_config.yaml', 'tests/phone_config.yaml']:
        print(f"\nValidating {config_file}:")
        if not check_config_file(config_file):
            all_checks_passed = False
    print()
    
    # Check database
    print("4. Database Check")
    print("-" * 60)
    if not check_database_schema():
        all_checks_passed = False
    print()
    
    # Check permissions
    print("5. Permissions Check")
    print("-" * 60)
    if not check_permissions():
        all_checks_passed = False
    print()
    
    # Summary
    print("=" * 60)
    if all_checks_passed:
        print("✓ ALL CHECKS PASSED - System ready for deployment")
        print("=" * 60)
        return 0
    else:
        print("✗ SOME CHECKS FAILED - Please address issues before deployment")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())

