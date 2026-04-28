# Project Reorganization Summary

This document summarizes the reorganization of the Veratori project structure to improve organization and maintainability.

## New Directory Structure

### Apps (`apps/`)
All application frontends and mobile apps are now organized under `apps/`:
- **`apps/web-frontend/`** - Web frontend (previously `frontend/`)
  - HTML files, CSS, JavaScript
- **`apps/mobile-app/`** - React Native mobile app (previously `mobile-app/`)
- **`apps/flutter-restock/`** - Flutter restock app (previously `veratori_restock_flutter/`)

### Models (`models/`)
All model files are centralized:
- **`models/best.pt`** - Trained YOLO model (previously at root)
- **`models/yolov8n.pt`** - Base YOLO model (previously at root)

### Scripts (`scripts/`)
All shell scripts and utility scripts are organized by purpose:
- **`scripts/setup/`** - Setup and installation scripts
  - `generate_password_hash.py`
  - `setup_auth.sh`
  - `start_auth_server.sh`
- **`scripts/management/`** - System management scripts
  - `start.sh`
  - `stop.sh`
  - `restart.sh`
  - `status.sh`
- **`scripts/testing/`** - Testing utilities
  - `Py/py.py`
- **`scripts/common.sh`** - Shared functions for scripts

### Tests (`tests/`)
All test files and PC testing code:
- **`tests/`** - All test files (previously `Testing On Pc/`)
  - Test scripts (`test_*.py`, `validate_system.py`)
  - PC testing launchers (`run_pc_*.py`, `run_phone_camera.py`)
  - Test configurations (`pc_config.yaml`, `phone_config.yaml`)
  - Test documentation

### Training (`training/`)
All training-related files:
- **`training/`** - Training scripts and data
  - `train_pokebowl_model.ipynb` - Training notebook
  - `migrate_dataset.py` - Dataset migration script
  - `minimal_training_config.py` - Training configuration
  - `products_list.txt` - Product list
  - `training/images/` - Training images (previously `Images/`)
  - `class_distribution.png`, `sample_images.png` - Training visualizations

## Updated File References

### Backend Code
- **`backend/main.py`**:
  - Model path: `best.pt` → `models/best.pt`
  - Frontend path: `frontend/` → `apps/web-frontend/`

- **`backend/server.py`**:
  - Frontend path: `frontend/` → `apps/web-frontend/`

### Configuration Files
- **`config/config.yaml`**:
  - Model path: `best.pt` → `models/best.pt`

- **`tests/pc_config.yaml`**:
  - Model path: `best.pt` → `models/best.pt`

- **`tests/phone_config.yaml`**:
  - Model path: `best.pt` → `models/best.pt`

### Scripts
- **`scripts/common.sh`**:
  - Test paths: `Testing On Pc/` → `tests/`

- **`deployment/quick_test.sh`**:
  - Model path: `best.pt` → `models/best.pt`

### Test Files
- **`tests/run_pc_webcam.py`**:
  - Model path: `best.pt` → `models/best.pt`
  - Frontend path: `frontend/` → `apps/web-frontend/`

- **`tests/run_phone_camera.py`**:
  - Model path: `best.pt` → `models/best.pt`
  - Frontend path: `frontend/` → `apps/web-frontend/`

- **`tests/run_pc_switchable.py`**:
  - Model path: `best.pt` → `models/best.pt`
  - Frontend path: `frontend/` → `apps/web-frontend/`

- **`tests/validate_system.py`**:
  - Model path: `best.pt` → `models/best.pt`
  - Frontend path: `frontend/` → `apps/web-frontend/`
  - Test config paths: `Testing On Pc/` → `tests/`

## Unchanged Directories

The following directories remain in their original locations:
- **`backend/`** - Backend Python code
- **`config/`** - Configuration files
- **`data/`** - Runtime data (databases)
- **`dataset/`** - Training dataset
- **`deployment/`** - Deployment scripts and service files
- **`docs/`** - Documentation
- **`run/`** - Runtime files (logs, PIDs)
- **`restock_photos/`** - Restock photo uploads

## Benefits of Reorganization

1. **Better Organization**: Related files are grouped together logically
2. **Clearer Structure**: Easy to find files by purpose
3. **Scalability**: Easy to add new apps, models, or scripts
4. **Maintainability**: Clear separation of concerns
5. **Developer Experience**: Intuitive navigation

## Migration Notes

- All code references have been updated to use new paths
- Configuration files have been updated
- Scripts have been updated to use new paths
- No functionality has been changed, only file locations

## Verification

To verify the reorganization:
1. Run `python3 tests/validate_system.py` to check all paths
2. Run `bash deployment/quick_test.sh` to verify system components
3. Test starting the system: `bash scripts/management/start.sh`

