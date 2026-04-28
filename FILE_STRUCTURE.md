# Veratori Project File Structure

Complete file structure after reorganization.

```
Veratori/
│
├── 📁 projects/
│   └── inventory-system/              # Main inventory management system
│       │
│       ├── 📁 apps/                   # All applications
│       │   ├── web-frontend/          # Web dashboard (HTML/CSS/JS)
│       │   │   ├── index.html
│       │   │   ├── login.html
│       │   │   ├── account.html
│       │   │   ├── analytics.html
│       │   │   ├── upload.html
│       │   │   ├── restock-app.html
│       │   │   ├── home.html
│       │   │   ├── shared.css
│       │   │   └── shared.js
│       │   │
│       │   ├── mobile-app/            # React Native mobile app
│       │   │   ├── App.js
│       │   │   ├── package.json
│       │   │   ├── README.md
│       │   │   └── src/
│       │   │       ├── config/
│       │   │       ├── screens/
│       │   │       └── services/
│       │   │
│       │   └── flutter-restock/       # Flutter restock app
│       │       ├── lib/
│       │       │   ├── main.dart
│       │       │   ├── models/
│       │       │   ├── providers/
│       │       │   ├── screens/
│       │       │   ├── services/
│       │       │   └── widgets/
│       │       ├── pubspec.yaml
│       │       └── README.md
│       │
│       ├── 📁 backend/                # Python backend (12 modules)
│       │   ├── __init__.py
│       │   ├── main.py                 # Application entry point
│       │   ├── server.py               # Web server & WebSocket
│       │   ├── camera.py               # USB camera handler
│       │   ├── detector.py             # YOLO inference
│       │   ├── inventory.py            # Inventory tracking
│       │   ├── inventory_persistent.py # Persistent inventory tracker
│       │   ├── persistence.py          # SQLite database layer
│       │   ├── sales_attribution.py    # Sales detection engine
│       │   ├── alerts.py               # Alert system
│       │   ├── auth.py                 # Authentication
│       │   └── restock_manager.py      # Restock submissions
│       │
│       ├── 📁 models/                  # ML models
│       │   ├── best.pt                 # Trained YOLO model (40 classes)
│       │   └── yolov8n.pt              # Base YOLO model
│       │
│       ├── 📁 config/                  # Configuration files
│       │   └── config.yaml              # Main system configuration
│       │
│       ├── 📁 data/                     # Runtime data
│       │   └── inventory.db             # SQLite database
│       │
│       ├── 📁 dataset/                  # Training dataset
│       │   └── pokebowl_dataset/
│       │       ├── data.yaml
│       │       ├── images/
│       │       │   ├── train/           # 89 training images
│       │       │   └── val/            # 23 validation images
│       │       └── labels/
│       │           ├── train/           # 89 training labels
│       │           └── val/            # 23 validation labels
│       │
│       ├── 📁 deployment/               # Deployment scripts
│       │   ├── pokebowl-inventory.service
│       │   ├── chromium-kiosk.service
│       │   ├── install_service.sh
│       │   ├── setup_autostart.sh
│       │   ├── setup_jetson.sh
│       │   └── quick_test.sh
│       │
│       ├── 📁 docs/                     # Documentation (30+ files)
│       │   ├── ARCHITECTURE.md
│       │   ├── QUICKSTART.md
│       │   ├── DEPLOYMENT_CHECKLIST.md
│       │   ├── RELEASE_NOTES_v2.2.md
│       │   ├── RUN_COMMANDS.md
│       │   ├── TRAINING_ANALYSIS.md
│       │   ├── TRAINING_TROUBLESHOOTING.md
│       │   └── images/                  # Documentation images
│       │
│       ├── 📁 scripts/                  # Utility scripts
│       │   ├── common.sh                # Shared functions
│       │   ├── README.md
│       │   │
│       │   ├── setup/                   # Setup scripts
│       │   │   ├── generate_password_hash.py
│       │   │   ├── setup_auth.sh
│       │   │   └── start_auth_server.sh
│       │   │
│       │   ├── management/               # System management
│       │   │   ├── start.sh            # Start system
│       │   │   ├── stop.sh             # Stop system
│       │   │   ├── restart.sh          # Restart system
│       │   │   └── status.sh           # Check status
│       │   │
│       │   └── testing/                 # Testing utilities
│       │       └── Py/
│       │           └── py.py
│       │
│       ├── 📁 tests/                    # Test files & PC testing
│       │   ├── validate_system.py      # System validation
│       │   ├── test_auth_system.py
│       │   ├── test_freshness_all_products.py
│       │   ├── test_sales_attribution.py
│       │   ├── test_camera_switch.py
│       │   │
│       │   ├── run_pc_webcam.py        # PC webcam launcher
│       │   ├── run_phone_camera.py     # Phone camera launcher
│       │   ├── run_pc_switchable.py    # Switchable camera launcher
│       │   ├── run_pc_test.py
│       │   ├── run_pc_webcam_with_auth.py
│       │   │
│       │   ├── pc_config.yaml          # PC webcam config
│       │   ├── phone_config.yaml       # Phone camera config
│       │   ├── index_switchable.html   # Switchable camera UI
│       │   │
│       │   └── [20+ test documentation files]
│       │
│       ├── 📁 training/                 # Training files
│       │   ├── train_pokebowl_model.ipynb  # Training notebook
│       │   ├── migrate_dataset.py
│       │   ├── minimal_training_config.py
│       │   ├── products_list.txt
│       │   ├── class_distribution.png
│       │   ├── sample_images.png
│       │   └── images/                  # Training images (289 files)
│       │       └── Images/
│       │           ├── Cantaloupe/      # 50 images
│       │           ├── Island Passion Fruit/  # 24 images
│       │           ├── Kilauea Lemon Cake/   # 50 images
│       │           ├── Mango/           # 36 images
│       │           ├── Maui Custard/    # 40 images
│       │           ├── Mixed/          # 50 images
│       │           └── Pina/            # 39 images
│       │
│       ├── 📁 run/                      # Runtime files
│       │   ├── backend.log             # Backend logs
│       │   ├── pokebowl_launch.log    # Launch logs
│       │   └── pokebowl.pid            # Process ID file
│       │
│       ├── 📁 restock_photos/           # Restock photo uploads
│       │
│       ├── 📄 README.md                 # Main documentation
│       ├── 📄 PROJECT_BREAKDOWN.md      # Project overview
│       ├── 📄 PROJECT_STRUCTURE.md     # Structure documentation
│       ├── 📄 TEST_RESULTS.md          # Test results
│       ├── 📄 INTERFACE_GUIDE.txt       # Interface guide
│       ├── 📄 requirements.txt          # Python dependencies
│       └── 📄 veratori_restock.db       # Restock database
│
├── 📄 README.md                         # Root project README
├── 📄 REORGANIZATION_COMPLETE.md        # Reorganization summary
└── 📄 FILE_STRUCTURE.md                 # This file
```

## Directory Summary

### Root Level
- **`projects/`** - All project code organized by project type

### Inventory System (`projects/inventory-system/`)

#### Applications (`apps/`)
- **`web-frontend/`** - 8 HTML files (dashboard, login, analytics, etc.)
- **`mobile-app/`** - React Native app
- **`flutter-restock/`** - Flutter restock app

#### Backend (`backend/`)
- **12 Python modules** - Core application logic

#### Models (`models/`)
- **`best.pt`** - Trained YOLO model (6.0 MB)
- **`yolov8n.pt`** - Base YOLO model (6.2 MB)

#### Scripts (`scripts/`)
- **`setup/`** - 3 setup scripts
- **`management/`** - 4 management scripts (start/stop/restart/status)
- **`testing/`** - Testing utilities

#### Tests (`tests/`)
- **11 Python test files**
- **20+ documentation files**
- PC testing launchers and configs

#### Training (`training/`)
- Training notebook
- **289 training images**
- Training scripts and configs

#### Documentation (`docs/`)
- **30+ markdown files** - Complete system documentation

## File Counts

- **Backend Python files**: 12
- **Frontend HTML files**: 8
- **Test files**: 11 Python + 20+ docs
- **Scripts**: 7 shell + 2 Python
- **Documentation**: 30+ markdown files
- **Training images**: 289
- **Dataset images**: 112

## Quick Navigation

- **Start system**: `projects/inventory-system/scripts/management/start.sh`
- **Main backend**: `projects/inventory-system/backend/main.py`
- **Web UI**: `projects/inventory-system/apps/web-frontend/index.html`
- **Configuration**: `projects/inventory-system/config/config.yaml`
- **Tests**: `projects/inventory-system/tests/validate_system.py`
- **Training**: `projects/inventory-system/training/train_pokebowl_model.ipynb`

---

**Last Updated**: February 2025  
**Status**: ✅ Fully Organized & Operational



