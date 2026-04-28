# Project Structure — Inventory System

Complete file structure of the Veratori Inventory Management System.

```
projects/inventory-system/
│
├── 📁 apps/                          # All applications
│   ├── web-frontend/                 # Web dashboard (main UI)
│   │   ├── index.html               # Main dashboard page
│   │   ├── login.html               # Login page
│   │   ├── account.html             # Account management
│   │   ├── analytics.html           # Analytics page
│   │   ├── upload.html               # Image upload page
│   │   ├── restock-app.html         # Restock management
│   │   ├── home.html                 # Home page
│   │   ├── shared.css               # Shared styles
│   │   └── shared.js                # Shared JavaScript
│   │
│   ├── mobile-app/                   # React Native mobile app
│   │   ├── App.js
│   │   ├── package.json
│   │   ├── README.md
│   │   └── src/
│   │       ├── config/
│   │       ├── screens/
│   │       └── services/
│   │
│   └── flutter-restock/              # Flutter restock app
│       ├── lib/
│       │   ├── main.dart
│       │   ├── models/
│       │   ├── providers/
│       │   ├── screens/
│       │   ├── services/
│       │   └── widgets/
│       ├── pubspec.yaml
│       └── README.md
│
├── 📁 backend/                       # Python backend code
│   ├── __init__.py
│   ├── main.py                       # Application entry point
│   ├── server.py                     # Web server & WebSocket
│   ├── camera.py                     # USB camera handler
│   ├── detector.py                   # YOLO inference
│   ├── inventory.py                  # Inventory tracking
│   ├── inventory_persistent.py       # Persistent inventory tracker
│   ├── persistence.py                # SQLite database layer
│   ├── sales_attribution.py          # Sales detection engine
│   ├── alerts.py                     # Alert system
│   ├── auth.py                       # Authentication
│   └── restock_manager.py            # Restock submissions
│
├── 📁 config/                        # Configuration files
│   └── config.yaml                   # Main system configuration
│
├── 📁 data/                          # Runtime data
│   └── inventory.db                  # SQLite database
│
├── 📁 dataset/                       # Training dataset
│   └── pokebowl_dataset/
│       ├── data.yaml
│       ├── images/
│       │   ├── train/
│       │   └── val/
│       └── labels/
│           ├── train/
│           └── val/
│
├── 📁 deployment/                     # Deployment scripts
│   ├── pokebowl-inventory.service    # Systemd service
│   ├── chromium-kiosk.service        # Browser kiosk service
│   ├── install_service.sh            # Service installer
│   ├── setup_autostart.sh            # Auto-start setup
│   ├── setup_jetson.sh               # Jetson setup
│   └── quick_test.sh                 # System test
│
├── 📁 docs/                          # Documentation (30+ files)
│   ├── ARCHITECTURE.md
│   ├── QUICKSTART.md
│   ├── DEPLOYMENT_CHECKLIST.md
│   ├── RELEASE_NOTES_v2.2.md
│   ├── RUN_COMMANDS.md
│   ├── TRAINING_ANALYSIS.md
│   └── images/                       # Documentation images
│
├── 📁 models/                         # ML models
│   ├── best.pt                       # Trained YOLO model
│   └── yolov8n.pt                    # Base YOLO model
│
├── 📁 scripts/                       # Utility scripts
│   ├── common.sh                     # Shared functions
│   ├── README.md
│   │
│   ├── setup/                        # Setup scripts
│   │   ├── generate_password_hash.py
│   │   ├── setup_auth.sh
│   │   └── start_auth_server.sh
│   │
│   ├── management/                   # System management
│   │   ├── start.sh                 # Start system
│   │   ├── stop.sh                  # Stop system
│   │   ├── restart.sh               # Restart system
│   │   └── status.sh                # Check status
│   │
│   └── testing/                      # Testing utilities
│       └── Py/
│           └── py.py
│
├── 📁 tests/                         # Test files & PC testing
│   ├── validate_system.py            # System validation
│   ├── test_auth_system.py
│   ├── test_freshness_all_products.py
│   ├── test_sales_attribution.py
│   ├── test_camera_switch.py
│   │
│   ├── run_pc_webcam.py              # PC webcam launcher
│   ├── run_phone_camera.py           # Phone camera launcher
│   ├── run_pc_switchable.py          # Switchable camera launcher
│   ├── run_pc_test.py
│   ├── run_pc_webcam_with_auth.py
│   │
│   ├── pc_config.yaml                 # PC webcam config
│   ├── phone_config.yaml              # Phone camera config
│   ├── index_switchable.html          # Switchable camera UI
│   │
│   └── [20+ test documentation files]
│
├── 📁 training/                       # Training files
│   ├── train_pokebowl_model.ipynb     # Training notebook
│   ├── migrate_dataset.py
│   ├── minimal_training_config.py
│   ├── products_list.txt
│   ├── class_distribution.png
│   ├── sample_images.png
│   └── images/                        # Training images
│       └── Images/
│           ├── Cantaloupe/
│           ├── Island Passion Fruit/
│           ├── Kilauea Lemon Cake/
│           ├── Mango/
│           ├── Maui Custard/
│           ├── Mixed/
│           └── Pina/
│
├── 📁 run/                           # Runtime files
│   ├── backend.log                   # Backend logs
│   ├── pokebowl_launch.log           # Launch logs
│   └── pokebowl.pid                  # Process ID file
│
├── 📁 restock_photos/                 # Restock photo uploads
│
├── 📄 README.md                       # Main documentation
├── 📄 PROJECT_BREAKDOWN.md            # Project overview
├── 📄 PROJECT_STRUCTURE.md            # This file
├── 📄 INTERFACE_GUIDE.txt             # Interface guide
├── 📄 requirements.txt                # Python dependencies
└── 📄 veratori_restock.db              # Restock database
```

## Quick Navigation

- **Start system**: `scripts/management/start.sh`
- **Main backend**: `backend/main.py`
- **Web UI**: `apps/web-frontend/index.html`
- **Configuration**: `config/config.yaml`
- **Tests**: `tests/validate_system.py`
- **Training**: `training/train_pokebowl_model.ipynb`

## File Count Summary

- **Backend Python files**: 12
- **Frontend HTML files**: 8
- **Configuration files**: 3
- **Test files**: 11 Python + documentation
- **Scripts**: 7 shell + 2 Python
- **Documentation**: 30+ markdown files
