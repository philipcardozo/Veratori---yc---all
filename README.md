# Veratori — Inventory Management Platform

Comprehensive inventory management system for food retail and logistics, featuring real-time AI object detection, multi-franchise management, mobile restock documentation, and advanced analytics.

## 🏗️ Project Structure

```
Veratori/
│
├── 📁 projects/
│   └── inventory-system/          # Main inventory management system
│       ├── apps/                  # All applications
│       │   ├── web-frontend/      # Web dashboard (HTML/CSS/JS)
│       │   ├── mobile-app/        # React Native mobile app
│       │   └── flutter-restock/   # Flutter restock app
│       │
│       ├── backend/               # Python backend (12 modules)
│       ├── models/                # ML models (YOLO)
│       ├── config/                # Configuration files
│       ├── data/                  # Runtime data (databases)
│       ├── dataset/               # Training dataset
│       ├── deployment/            # Deployment scripts
│       ├── docs/                  # Documentation (30+ files)
│       ├── scripts/               # Utility scripts
│       │   ├── setup/            # Setup scripts
│       │   ├── management/        # Start/stop/restart
│       │   └── testing/           # Test utilities
│       ├── tests/                 # Test files & PC testing
│       ├── training/              # Training files & images
│       └── requirements.txt       # Python dependencies
│
└── README.md                      # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- NVIDIA Jetson Orin Nano (for production) or PC (for testing)
- USB camera
- CUDA-capable GPU (optional, for faster inference)

### Installation

```bash
# Navigate to project
cd projects/inventory-system

# Install Python dependencies
pip3 install -r requirements.txt

# Start the system
./scripts/management/start.sh
```

Access the web dashboard at `http://localhost:8080`

## 📱 Applications

### 1. Web Dashboard (`apps/web-frontend/`)
- Real-time inventory monitoring
- Live camera feed with YOLO detection
- Analytics and reporting
- Sales tracking
- Product freshness monitoring

### 2. Mobile App (`apps/mobile-app/`)
React Native application for mobile inventory management.

### 3. Flutter Restock App (`apps/flutter-restock/`)
Flutter application for employee restock submissions and photo documentation.

## 🔧 Components

### Backend (`backend/`)
- **`main.py`** - Application entry point
- **`server.py`** - Web server & WebSocket streaming
- **`camera.py`** - USB camera handler
- **`detector.py`** - YOLO inference engine
- **`inventory.py`** - Inventory tracking
- **`inventory_persistent.py`** - Persistent inventory with database
- **`persistence.py`** - SQLite database layer
- **`sales_attribution.py`** - Sales detection engine
- **`alerts.py`** - Alert system
- **`auth.py`** - Authentication
- **`restock_manager.py`** - Restock submissions

### Models (`models/`)
- **`best.pt`** - Trained YOLO model (40 product classes)
- **`yolov8n.pt`** - Base YOLO model

## 📚 Documentation

All documentation is located in `projects/inventory-system/docs/`:

- **`QUICKSTART.md`** - Quick start guide
- **`ARCHITECTURE.md`** - System architecture
- **`DEPLOYMENT_CHECKLIST.md`** - Deployment guide
- **`TRAINING_ANALYSIS.md`** - Model training guide
- **`RUN_COMMANDS.md`** - Command reference

## 🧪 Testing

```bash
# Run system validation
cd projects/inventory-system
python3 tests/validate_system.py

# PC testing modes
./scripts/management/start.sh webcam      # Use webcam
./scripts/management/start.sh phone       # Use phone camera
./scripts/management/start.sh switchable  # Switchable cameras
```

## 🎯 Key Features

- **Real-time AI Detection** - YOLO v8+ with GPU acceleration
- **Multi-Franchise Dashboard** - Centralized management
- **Mobile Restock App** - Employee photo documentation
- **Advanced Analytics** - Trend analysis and forecasting
- **Automated Alerts** - Low-stock and expiration monitoring
- **Sales Attribution** - Automatic sales detection
- **Product Freshness Tracking** - 5-day expiration monitoring
- **Secure Authentication** - Session-based auth with bcrypt

## 📊 System Requirements

### Production (Jetson)
- NVIDIA Jetson Orin Nano
- JetPack 6.x
- USB camera
- 4GB+ RAM

### Development (PC)
- Python 3.8+
- Webcam or phone camera
- 8GB+ RAM
- CUDA-capable GPU (optional)

## 🔐 Authentication

Default test users:
- **Username**: `JustinMenezes`, **Password**: `386canalst`
- **Username**: `FelipeCardozo`, **Password**: `26cmu`

## 📖 More Information

For detailed documentation, see:
- `projects/inventory-system/README.md` - Complete system documentation
- `projects/inventory-system/docs/` - All documentation files

## 🗂️ Project Organization

All code is organized under `projects/inventory-system/`:
- **Apps** → `apps/`
- **Backend** → `backend/`
- **Models** → `models/`
- **Scripts** → `scripts/`
- **Tests** → `tests/`
- **Training** → `training/`
- **Docs** → `docs/`

## 📝 License

This project is provided as-is for educational and commercial use.

---

**Last Updated**: February 2025  
**Status**: Production Ready
