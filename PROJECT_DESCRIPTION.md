# Veratori — Complete Project Description

## Overview

**Veratori** is a comprehensive, production-ready inventory management system designed for food retail and logistics. The system uses real-time AI object detection (YOLO) to automatically track inventory levels, monitor product freshness, detect sales, and provide actionable insights to reduce food waste and optimize operations.

### Key Capabilities

- **Real-time AI Detection** - YOLO v8+ with GPU acceleration for accurate product identification (40 product classes)
- **Multi-Franchise Dashboard** - Centralized executive control room for managing multiple locations
- **Mobile Restock App** - Flutter-based employee application for documenting restock actions
- **Advanced Analytics** - Trend analysis, forecasting, and operational intelligence
- **Automated Alerts** - Low-stock and expiration monitoring with real-time notifications
- **Sales Attribution** - Automatic sales detection and tracking with SKU-level accuracy
- **Product Freshness Tracking** - 5-day expiration monitoring for perishable items
- **Secure Authentication** - Session-based auth with bcrypt password hashing

---

## Complete File Structure & Explanations

```
Veratori/
│
├── 📁 projects/
│   └── inventory-system/              # Main inventory management system
│       │
│       ├── 📁 apps/                   # All user-facing applications
│       │   │
│       │   ├── web-frontend/          # Web Dashboard (Main UI)
│       │   │   ├── index.html         # Main dashboard - real-time inventory display
│       │   │   ├── login.html         # Authentication page
│       │   │   ├── account.html       # User account management
│       │   │   ├── analytics.html     # Analytics and reporting dashboard
│       │   │   ├── upload.html        # Image upload for manual detection
│       │   │   ├── restock-app.html   # Restock management interface
│       │   │   ├── home.html          # Home/landing page
│       │   │   ├── shared.css         # Shared styles across all pages
│       │   │   └── shared.js          # Shared JavaScript utilities
│       │   │
│       │   │   Purpose: Provides the main web interface for monitoring inventory,
│       │   │   viewing analytics, managing restocks, and configuring the system.
│       │   │   Uses WebSocket for real-time updates from the backend.
│       │   │
│       │   ├── mobile-app/            # React Native Mobile App
│       │   │   ├── App.js            # Main app component
│       │   │   ├── package.json      # Node.js dependencies
│       │   │   ├── README.md         # Mobile app documentation
│       │   │   └── src/
│       │   │       ├── config/        # API configuration
│       │   │       ├── screens/      # App screens/components
│       │   │       └── services/      # API service layer
│       │   │
│       │   │   Purpose: Mobile application for on-the-go inventory management.
│       │   │   Allows employees to check inventory, view alerts, and manage stock.
│       │   │
│       │   └── flutter-restock/       # Flutter Restock App
│       │       ├── lib/
│       │       │   ├── main.dart     # Flutter app entry point
│       │       │   ├── models/       # Data models
│       │       │   ├── providers/    # State management (Riverpod/Provider)
│       │       │   ├── screens/      # App screens
│       │       │   ├── services/     # API services
│       │       │   └── widgets/      # Reusable UI components
│       │       ├── pubspec.yaml      # Flutter dependencies
│       │       └── README.md         # Flutter app documentation
│       │   │
│       │   │   Purpose: Employee-facing mobile app for documenting restock actions.
│       │   │   Employees can take photos, submit restock requests, and track submissions.
│       │   │   Includes photo upload, detection preview, and notification system.
│       │   │
│       ├── 📁 backend/                 # Python Backend (Core Application Logic)
│       │   │
│       │   ├── main.py                 # Application Entry Point
│       │   │   │
│       │   │   Purpose: Main entry point that initializes and coordinates all components.
│       │   │   - Loads configuration from config.yaml
│       │   │   - Initializes camera, detector, inventory tracker, and web server
│       │   │   - Manages application lifecycle (startup, shutdown, signal handling)
│       │   │   - Creates PID file for single-instance protection
│       │   │
│       │   ├── server.py               # Web Server & WebSocket Handler
│       │   │   │
│       │   │   Purpose: HTTP/WebSocket server that serves the frontend and streams data.
│       │   │   - Serves static HTML/CSS/JS files
│       │   │   - WebSocket connections for real-time video and inventory updates
│       │   │   - REST API endpoints for analytics, uploads, camera switching
│       │   │   - Authentication and session management
│       │   │   - Restock API endpoints for mobile app
│       │   │   - Handles file uploads and image detection requests
│       │   │
│       │   ├── camera.py               # USB Camera Handler
│       │   │   │
│       │   │   Purpose: Manages USB camera connections and frame capture.
│       │   │   - Opens/closes camera devices
│       │   │   - Captures frames at specified resolution and FPS
│       │   │   - Handles camera disconnection and reconnection
│       │   │   - Enumerates available cameras
│       │   │   - Runtime camera switching support
│       │   │
│       │   ├── detector.py             # YOLO Inference Engine
│       │   │   │
│       │   │   Purpose: Runs YOLO object detection on camera frames.
│       │   │   - Loads YOLO model (best.pt)
│       │   │   - Runs inference on frames (GPU-accelerated)
│       │   │   - Returns detections with bounding boxes and confidence scores
│       │   │   - Draws detections on frames for visualization
│       │   │   - Tracks inference performance (FPS, latency)
│       │   │   - Supports 40 product classes
│       │   │
│       │   ├── inventory.py           # Base Inventory Tracker
│       │   │   │
│       │   │   Purpose: Tracks inventory counts with temporal smoothing.
│       │   │   - Maintains running counts per product
│       │   │   - Applies temporal smoothing (median/mean/mode) to reduce noise
│       │   │   - Provides current inventory state
│       │   │   - Base class for persistent inventory tracker
│       │   │
│       │   ├── inventory_persistent.py  # Persistent Inventory Tracker
│       │   │   │
│       │   │   Purpose: Extends base tracker with database persistence and advanced features.
│       │   │   - Saves inventory snapshots to database
│       │   │   - Tracks product freshness (first seen, last seen, expiration)
│       │   │   - Integrates sales attribution engine
│       │   │   - Integrates alert engine
│       │   │   - Restores state on startup
│       │   │   - Manages data retention (30-day snapshots)
│       │   │
│       │   ├── persistence.py          # SQLite Database Layer
│       │   │   │
│       │   │   Purpose: Manages all database operations.
│       │   │   - Creates and maintains database schema
│       │   │   - Stores inventory snapshots
│       │   │   - Stores product freshness data
│       │   │   - Stores sales log
│       │   │   - Stores alerts log
│       │   │   - Provides query interface for analytics
│       │   │   - Manages data retention and cleanup
│       │   │   - Uses WAL mode for better concurrency
│       │   │
│       │   ├── sales_attribution.py    # Sales Detection Engine
│       │   │   │
│       │   │   Purpose: Automatically detects and logs sales events.
│       │   │   - Monitors inventory decreases
│       │   │   - Validates sales with temporal confirmation (2 intervals)
│       │   │   - Applies cooldown to prevent duplicate detections (10 seconds)
│       │   │   - Records sales with EST timestamps
│       │   │   - SKU-level accuracy (per-product sales)
│       │   │   - Noise-resistant (requires sustained decrease)
│       │   │
│       │   ├── alerts.py              # Alert System
│       │   │   │
│       │   │   Purpose: Monitors inventory and generates alerts.
│       │   │   - Low-stock alerts (configurable thresholds per product)
│       │   │   - Expiration alerts (5+ days old)
│       │   │   - Temporal validation (2 intervals)
│       │   │   - Cooldown to prevent spam (1 hour)
│       │   │   - Email notifications via SMTP (optional)
│       │   │   - Stores alerts in database
│       │   │
│       │   ├── auth.py                 # Authentication System
│       │   │   │
│       │   │   Purpose: Handles user authentication and session management.
│       │   │   - Bcrypt password hashing
│       │   │   - HMAC-signed session tokens
│       │   │   - HttpOnly cookies with SameSite protection
│       │   │   - 24-hour session TTL
│       │   │   - Environment-based configuration
│       │   │   - Session validation
│       │   │
│       │   ├── restock_manager.py      # Restock Submission Manager
│       │   │   │
│       │   │   Purpose: Manages restock submissions from mobile app.
│       │   │   - Stores employee submissions
│       │   │   - Manages photo uploads
│       │   │   - Tracks submission status (pending, approved, rejected)
│       │   │   - Notification system for employees
│       │   │   - Manager moderation workflow
│       │   │   - SQLite database for submissions
│       │   │
│       │   └── __init__.py            # Package initialization
│       │       │
│       │       Purpose: Makes backend a Python package and exports main classes.
│       │
│       ├── 📁 models/                  # Machine Learning Models
│       │   │
│       │   ├── best.pt                # Trained YOLO Model
│       │   │   │
│       │   │   Purpose: Production YOLO model trained on 40 product classes.
│       │   │   - Size: ~6.0 MB
│       │   │   - Trained on pokebowl dataset (112 images)
│       │   │   - 40 product classes (beverages, fruits, specialty items)
│       │   │   - Optimized for Jetson Orin Nano
│       │   │   - Used by detector.py for real-time inference
│       │   │
│       │   └── yolov8n.pt             # Base YOLO Model
│       │       │
│       │       Purpose: Pre-trained YOLO nano model (starting point for training).
│       │       - Size: ~6.2 MB
│       │       - Used as base for transfer learning
│       │       - Can be used for inference if best.pt not available
│       │
│       ├── 📁 config/                  # Configuration Files
│       │   │
│       │   └── config.yaml             # Main System Configuration
│       │       │
│       │       Purpose: Centralized configuration for all system components.
│       │       - Camera settings (index, resolution, FPS)
│       │       - Detector settings (model path, confidence, IoU thresholds)
│       │       - Inventory settings (smoothing, persistence, expiration)
│       │       - Server settings (host, port)
│       │       - Alert settings (thresholds, cooldowns)
│       │       - Sales attribution settings
│       │
│       ├── 📁 data/                     # Runtime Data
│       │   │
│       │   └── inventory.db            # SQLite Database
│       │       │
│       │       Purpose: Stores all persistent data.
│       │       - Inventory snapshots (with 30-day retention)
│       │       - Product freshness tracking
│       │       - Sales log (all sales events)
│       │       - Alerts log (all alerts)
│       │       - WAL mode enabled for better performance
│       │       - Auto-created on first run
│       │
│       ├── 📁 dataset/                  # Training Dataset
│       │   │
│       │   └── pokebowl_dataset/        # YOLO Training Dataset
│       │       ├── data.yaml           # Dataset configuration (class names, paths)
│       │       ├── images/
│       │       │   ├── train/          # 89 training images
│       │       │   └── val/            # 23 validation images
│       │       └── labels/
│       │           ├── train/          # 89 training label files (.txt)
│       │           └── val/             # 23 validation label files (.txt)
│       │       │
│       │       Purpose: YOLO-formatted dataset for training the detection model.
│       │       - Images: Product photos with bounding boxes
│       │       - Labels: YOLO format (class_id, x_center, y_center, width, height)
│       │       - Used by train_pokebowl_model.ipynb for model training
│       │
│       ├── 📁 deployment/                # Deployment Scripts
│       │   │
│       │   ├── pokebowl-inventory.service  # Systemd Service File
│       │   │   │
│       │   │   Purpose: Systemd service definition for auto-start on Jetson.
│       │   │   - Runs backend/main.py on boot
│       │   │   - Restarts on failure
│       │   │   - Logs to systemd journal
│       │   │
│       │   ├── chromium-kiosk.service     # Browser Kiosk Service
│       │   │   │
│       │   │   Purpose: Auto-launches Chromium in kiosk mode on boot.
│       │   │   - Opens web dashboard automatically
│       │   │   - Fullscreen mode
│       │   │   - No browser UI (kiosk mode)
│       │   │
│       │   ├── install_service.sh          # Service Installer
│       │   │   │
│       │   │   Purpose: Installs systemd services on Jetson.
│       │   │   - Copies service files to /etc/systemd/system/
│       │   │   - Reloads systemd
│       │   │   - Enables services
│       │   │
│       │   ├── setup_autostart.sh         # Auto-Start Setup
│       │   │   │
│       │   │   Purpose: Complete auto-start setup script.
│       │   │   - Installs backend service
│       │   │   - Installs browser kiosk service
│       │   │   - Enables both services
│       │   │
│       │   ├── setup_jetson.sh            # Jetson Setup Script
│       │   │   │
│       │   │   Purpose: Complete Jetson system setup.
│       │   │   - Installs system dependencies
│       │   │   - Installs Python packages
│       │   │   - Configures system
│       │   │
│       │   └── quick_test.sh              # System Test Script
│       │       │
│       │       Purpose: Quick system validation.
│       │       - Checks Python version
│       │       - Checks dependencies
│       │       - Checks model files
│       │       - Checks camera
│       │       - Tests imports
│       │
│       ├── 📁 docs/                      # Documentation (30+ files)
│       │   │
│       │   ├── ARCHITECTURE.md           # System architecture documentation
│       │   ├── QUICKSTART.md             # Quick start guide
│       │   ├── DEPLOYMENT_CHECKLIST.md  # Deployment guide
│       │   ├── RELEASE_NOTES_v2.2.md    # Release notes
│       │   ├── RUN_COMMANDS.md          # Command reference
│       │   ├── TRAINING_ANALYSIS.md     # Training documentation
│       │   ├── AUTH_TEST_REPORT.md      # Authentication testing
│       │   └── [20+ more documentation files]
│       │   │
│       │   Purpose: Comprehensive documentation covering all aspects of the system.
│       │
│       ├── 📁 scripts/                   # Utility Scripts
│       │   │
│       │   ├── common.sh                 # Shared Functions
│       │   │   │
│       │   │   Purpose: Common functions used by all management scripts.
│       │   │   - OS detection (Jetson vs PC)
│       │   │   - Process management
│       │   │   - Health check functions
│       │   │   - Browser opening
│       │   │   - Logging utilities
│       │   │
│       │   ├── setup/                    # Setup Scripts
│       │   │   ├── generate_password_hash.py  # Password hash generator
│       │   │   ├── setup_auth.sh             # Authentication setup
│       │   │   └── start_auth_server.sh      # Start server with auth
│       │   │   │
│       │   │   Purpose: Scripts for initial system setup and configuration.
│       │   │
│       │   ├── management/                # System Management
│       │   │   ├── start.sh              # Start the system
│       │   │   ├── stop.sh               # Stop the system
│       │   │   ├── restart.sh            # Restart the system
│       │   │   └── status.sh             # Check system status
│       │   │   │
│       │   │   Purpose: High-level system management commands.
│       │   │   - Detects environment (Jetson vs PC)
│       │   │   - Starts/stops backend appropriately
│       │   │   - Opens browser automatically
│       │   │   - Handles both systemd (Jetson) and direct (PC) execution
│       │   │
│       │   └── testing/                   # Testing Utilities
│       │       └── Py/
│       │           └── py.py            # Python testing utilities
│       │
│       ├── 📁 tests/                      # Test Files & PC Testing
│       │   │
│       │   ├── validate_system.py        # System Validation
│       │   │   │
│       │   │   Purpose: Comprehensive system validation script.
│       │   │   - Checks all critical files exist
│       │   │   - Validates Python dependencies
│       │   │   - Validates configuration files
│       │   │   - Checks database schema
│       │   │   - Verifies permissions
│       │   │
│       │   ├── test_auth_system.py       # Authentication Tests
│       │   ├── test_freshness_all_products.py  # Freshness Tests
│       │   ├── test_sales_attribution.py # Sales Attribution Tests
│       │   ├── test_camera_switch.py     # Camera Switching Tests
│       │   │
│       │   ├── run_pc_webcam.py          # PC Webcam Launcher
│       │   │   │
│       │   │   Purpose: Launches system on PC with webcam.
│       │   │   - Uses PC configuration
│       │   │   - Runs without systemd
│       │   │   - For development/testing
│       │   │
│       │   ├── run_phone_camera.py       # Phone Camera Launcher
│       │   │   │
│       │   │   Purpose: Launches system on PC with phone camera (via USB).
│       │   │   - Uses phone camera configuration
│       │   │   - For testing with phone camera
│       │   │
│       │   ├── run_pc_switchable.py      # Switchable Camera Launcher
│       │   │   │
│       │   │   Purpose: Launches system with camera switching UI.
│       │   │   - Allows runtime camera switching
│       │   │   - Custom frontend with switch UI
│       │   │   - For testing multiple cameras
│       │   │
│       │   ├── pc_config.yaml            # PC Webcam Configuration
│       │   ├── phone_config.yaml        # Phone Camera Configuration
│       │   ├── index_switchable.html     # Switchable Camera UI
│       │   │
│       │   └── [20+ test documentation files]
│       │       │
│       │       Purpose: Comprehensive testing documentation and guides.
│       │
│       ├── 📁 training/                   # Training Files
│       │   │
│       │   ├── train_pokebowl_model.ipynb  # Training Notebook
│       │   │   │
│       │   │   Purpose: Jupyter notebook for training YOLO model.
│       │   │   - Loads dataset
│       │   │   - Configures training parameters
│       │   │   - Trains model
│       │   │   - Evaluates performance
│       │   │   - Saves best model to models/best.pt
│       │   │
│       │   ├── migrate_dataset.py        # Dataset Migration
│       │   ├── minimal_training_config.py # Training Config
│       │   ├── products_list.txt          # Product List
│       │   ├── class_distribution.png     # Class Distribution Visualization
│       │   ├── sample_images.png          # Sample Training Images
│       │   │
│       │   └── images/                    # Training Images (289 files)
│       │       └── Images/
│       │           ├── Cantaloupe/        # 50 images
│       │           ├── Island Passion Fruit/  # 24 images
│       │           ├── Kilauea Lemon Cake/   # 50 images
│       │           ├── Mango/            # 36 images
│       │           ├── Maui Custard/      # 40 images
│       │           ├── Mixed/            # 50 images
│       │           └── Pina/             # 39 images
│       │       │
│       │       Purpose: Raw training images organized by product class.
│       │       - Used for creating YOLO dataset
│       │       - Source images before annotation
│       │
│       ├── 📁 run/                        # Runtime Files
│       │   │
│       │   ├── backend.log               # Backend Application Logs
│       │   ├── pokebowl_launch.log       # Launch Script Logs
│       │   └── pokebowl.pid              # Process ID File
│       │   │
│       │   Purpose: Runtime files created during system operation.
│       │   - Logs for debugging
│       │   - PID file for single-instance protection
│       │
│       ├── 📁 restock_photos/             # Restock Photo Uploads
│       │   │
│       │   Purpose: Stores photos uploaded by employees via restock app.
│       │   - Organized by submission ID
│       │   - Served by restock_manager.py
│       │
│       ├── 📄 README.md                   # Main Documentation
│       ├── 📄 PROJECT_BREAKDOWN.md        # Project Overview
│       ├── 📄 PROJECT_STRUCTURE.md        # Structure Documentation
│       ├── 📄 TEST_RESULTS.md            # Test Results
│       ├── 📄 INTERFACE_GUIDE.txt         # Interface Guide
│       ├── 📄 requirements.txt            # Python Dependencies
│       └── 📄 veratori_restock.db         # Restock Database
│
├── 📄 README.md                           # Root Project README
├── 📄 REORGANIZATION_COMPLETE.md          # Reorganization Summary
└── 📄 FILE_STRUCTURE.md                   # File Structure Documentation
```

---

## System Architecture

### Data Flow

1. **Camera** → Captures frames from USB camera
2. **Detector** → Runs YOLO inference on frames
3. **Inventory Tracker** → Processes detections, applies smoothing
4. **Persistence** → Saves snapshots to database
5. **Sales Attribution** → Detects inventory decreases (sales)
6. **Alerts** → Monitors thresholds and generates alerts
7. **Server** → Streams data to frontend via WebSocket
8. **Frontend** → Displays real-time inventory and analytics

### Component Interactions

```
┌─────────────┐
│   Camera    │ → Frames
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Detector   │ → Detections
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Inventory  │ → Counts
└──────┬──────┘
       │
       ├──→ Persistence → Database
       ├──→ Sales Attribution → Sales Log
       └──→ Alerts → Alert Log
       │
       ▼
┌─────────────┐
│   Server    │ → WebSocket → Frontend
└─────────────┘
```

---

## Key Features Explained

### 1. Real-Time Detection
- **Technology**: YOLO v8+ (Ultralytics)
- **Performance**: 30-50ms inference time per frame
- **Accuracy**: 40 product classes with high precision
- **Hardware**: GPU-accelerated (CUDA on Jetson)

### 2. Temporal Smoothing
- **Purpose**: Reduces noise from detection fluctuations
- **Method**: Median/mean/mode over 10 frames
- **Result**: Stable, accurate inventory counts

### 3. Database Persistence
- **Database**: SQLite with WAL mode
- **Tables**: 
  - `inventory_snapshots` - Historical inventory data
  - `product_freshness` - Product age tracking
  - `sales_log` - All sales events
  - `alerts_log` - All alerts
- **Retention**: 30 days for snapshots (configurable)

### 4. Product Freshness Tracking
- **Tracks**: 6 products (passion fruit, maui custard, lemon cake, mango, watermelon, pineapple)
- **Expiration**: 5 days
- **Display**: "Fresh - X days old" or "EXPIRED (X days old)"
- **Alerts**: Automatic expiration alerts

### 5. Sales Attribution
- **Method**: Detects inventory decreases
- **Validation**: Requires 2 consecutive intervals
- **Cooldown**: 10 seconds to prevent duplicates
- **Accuracy**: SKU-level (per-product)
- **Timestamps**: EST timezone

### 6. Alert System
- **Types**: Low-stock, expiration
- **Validation**: 2 intervals required
- **Cooldown**: 1 hour between alerts
- **Notifications**: Email via SMTP (optional)
- **Storage**: All alerts logged to database

### 7. Authentication
- **Method**: Session-based with bcrypt
- **Security**: HttpOnly cookies, SameSite protection
- **Sessions**: 24-hour TTL
- **Configuration**: Environment variables

### 8. Restock Management
- **Mobile App**: Flutter app for employees
- **Features**: Photo upload, detection preview, submission tracking
- **Workflow**: Employee submits → Manager reviews → Status update
- **Notifications**: Real-time notifications for employees

---

## Technology Stack

### Backend
- **Language**: Python 3.8+
- **Web Framework**: aiohttp (async HTTP/WebSocket)
- **AI/ML**: Ultralytics YOLO v8+
- **Database**: SQLite with WAL mode
- **Computer Vision**: OpenCV, NumPy
- **Authentication**: bcrypt, HMAC

### Frontend
- **Web**: HTML5, CSS3, JavaScript (vanilla)
- **Communication**: WebSocket for real-time updates
- **Mobile**: React Native (mobile-app)
- **Restock App**: Flutter/Dart

### Deployment
- **Platform**: NVIDIA Jetson Orin Nano
- **OS**: JetPack 6.x (Ubuntu 22.04)
- **Service Management**: systemd
- **Browser**: Chromium (kiosk mode)

---

## Performance Characteristics

- **Frame Rate**: 15-30 FPS
- **Inference Time**: 30-50ms per frame
- **Latency**: <100ms end-to-end
- **CPU Usage**: ~40%
- **GPU Usage**: ~35%
- **Memory**: ~200MB
- **Database Size**: ~2.5-5 MB/day (with 30-day retention)

---

## Use Cases

1. **Restaurant Inventory Management**
   - Real-time stock monitoring
   - Automatic sales tracking
   - Expiration alerts
   - Waste reduction

2. **Multi-Location Management**
   - Centralized dashboard
   - Franchise-level analytics
   - Cross-location insights

3. **Employee Workflow**
   - Mobile restock documentation
   - Photo-based verification
   - Manager approval workflow

4. **Analytics & Reporting**
   - Sales trends
   - Product performance
   - Waste analysis
   - Export to Excel

---

## Development Workflow

### Local Development (PC)
```bash
cd projects/inventory-system
./scripts/management/start.sh webcam
```

### Production Deployment (Jetson)
```bash
cd projects/inventory-system
sudo bash deployment/setup_autostart.sh
```

### Testing
```bash
cd projects/inventory-system
python3 tests/validate_system.py
```

---

## File Organization Principles

1. **Separation by Function**: Each component type has its own directory
2. **Clear Naming**: Descriptive folder and file names
3. **Logical Grouping**: Related files are grouped together
4. **Scalability**: Easy to add new components
5. **Maintainability**: Clear structure for future developers

---

## Project Status

✅ **Production Ready** - System is fully operational and tested
✅ **Well Documented** - 30+ documentation files
✅ **Organized** - Clean, logical file structure
✅ **Tested** - Comprehensive test suite
✅ **Deployed** - Ready for Jetson deployment

---

**Last Updated**: February 2025  
**Version**: 2.2  
**Status**: Production Ready



