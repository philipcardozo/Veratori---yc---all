# Veratori — Ethical Inventory Management Platform

[![Platform](https://img.shields.io/badge/Platform-Jetson%20Orin%20Nano-76B900?logo=nvidia)](https://developer.nvidia.com/embedded/jetson-orin)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python)](https://www.python.org/)
[![YOLO](https://img.shields.io/badge/YOLO-v8+-00FFFF?logo=yolo)](https://github.com/ultralytics/ultralytics)
[![Flutter](https://img.shields.io/badge/Flutter-3.0+-02569B?logo=flutter)](https://flutter.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Veratori is a comprehensive inventory management platform for food retail and logistics. The system combines real-time AI object detection, multi-franchise management, mobile restock documentation, and advanced analytics to reduce food waste by up to 40% while optimizing space utilization and operational efficiency.

**Quick Links**: [Quick Start](#quick-start) | [Features](#features) | [Architecture](#architecture) | [Mobile App](#mobile-app) | [Documentation](#documentation)

---

## Overview

Veratori integrates multiple components to deliver a complete inventory management solution:

- **Real-time AI Detection**: YOLO v8+ object detection with GPU acceleration for accurate product identification
- **Multi-Franchise Dashboard**: Centralized executive control room for managing multiple locations
- **Mobile Restock App**: Flutter-based employee application for documenting restock actions
- **Advanced Analytics**: Trend analysis, forecasting, and operational intelligence
- **Automated Alerts**: Low-stock and expiration monitoring with real-time notifications
- **Sales Attribution**: Automatic sales detection and tracking

**Result**: Up to 40% reduction in food waste, optimized space utilization, and precise waste-free operations.

![Platform Overview](docs/images/platform-overview.png)
*Veratori platform architecture and component integration*

---

## Features

### Core Platform

**Real-time Detection**
- YOLO v8+ with GPU acceleration (15-30 FPS)
- Temporal smoothing for stable inventory counts
- Support for 40+ product classes

**Multi-Franchise Management**
- Centralized control room for all locations
- Cross-franchise comparison and benchmarking
- Weighted aggregation for accurate metrics

**Executive Dashboard**
- Real-time KPI tracking and analytics
- Predictive stockout estimation
- Financial impact analysis
- Operational risk assessment

**Role-Based Access Control**
- Owner, Regional Manager, Supervisor, Employee roles
- Franchise-scoped data access
- Secure session-based authentication

**Live Operational Intelligence**
- Real-time activity feed
- System health monitoring (GPU, latency, database)
- WebSocket-based updates

**Automated Alerts**
- Low-stock notifications
- Expiration monitoring
- Configurable thresholds per product

**Sales Attribution**
- Automatic sales detection
- SKU-level accuracy
- EST timestamp tracking

**Data Persistence**
- SQLite database with audit trails
- Inventory snapshots and history
- Sales logs and alert records

![Dashboard Screenshot](docs/images/dashboard-screenshot.png)
*Executive control room dashboard with real-time KPIs and analytics*

### Mobile App (Flutter)

**Employee Restock Submissions**
- Photo-based restock documentation
- Minimum 3 photos per submission (front, left, right)
- Optional additional angles

**YOLO Detection Preview**
- Real-time product detection before submission
- Visual bounding boxes with detected quantities
- Employee verification and retake capability

**Submission Management**
- View all submissions with status tracking
- Filter by date, status, and product
- Detection results display

**Push Notifications**
- Manager review updates
- Status change notifications
- Unread count tracking

**Cross-Platform Support**
- iOS and Android deployment
- Offline capability
- Session persistence

![Mobile App Screenshot](docs/images/mobile-app-screenshot.png)
*Flutter mobile app interface for employee restock submissions*

### Web Dashboard

**Business Control Room**
- Executive KPI strip with real-time metrics
- Period-over-period comparisons
- Delta indicators and trend analysis

**Franchise Comparison**
- Side-by-side performance analysis
- Best performer highlighting
- Comparative KPIs

**Advanced Analytics**
- Sales trends and forecasting
- Inventory turnover rates
- Alert frequency analysis
- Uptime stability metrics

**Forecast Snapshot**
- Predictive stockout estimation
- Estimated restock windows
- Trend confidence indicators

**Risk & Attention Panel**
- Highlighted operational issues
- Quantified impact estimates
- Actionable recommendations

**Restock Moderation**
- Manager review and approval workflow
- Status management (Pending, Approved, Flagged, Adjustment Required)
- Feedback system
- Photo gallery view

**Export & Reporting**
- PDF business reports
- Excel data exports
- Scheduled report delivery

![Analytics Dashboard](docs/images/analytics-dashboard.png)
*Advanced analytics with trend analysis and forecasting*

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Veratori Platform                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Camera     │───▶│ YOLO Detector│───▶│  Inventory   │  │
│  │   Feed       │    │  (GPU)       │    │  Tracker     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
│         └────────────────────┼────────────────────┘          │
│                              │                               │
│                    ┌─────────▼─────────┐                    │
│                    │   Web Server      │                    │
│                    │   (aiohttp)       │                    │
│                    └─────────┬─────────┘                    │
│                              │                               │
│         ┌────────────────────┼────────────────────┐         │
│         │                    │                    │         │
│  ┌──────▼──────┐    ┌─────────▼─────────┐  ┌──────▼──────┐ │
│  │   Web       │    │  Restock Manager  │  │  Database   │ │
│  │  Dashboard  │    │  (API Endpoints) │  │  (SQLite)   │ │
│  └─────────────┘    └───────────────────┘  └─────────────┘ │
│         │                    │                               │
│         └────────────────────┼───────────────────────────────┘
│                              │
│                    ┌─────────▼─────────┐
│                    │  Flutter Mobile  │
│                    │      App          │
│                    └───────────────────┘
│
└─────────────────────────────────────────────────────────────┘
```

![System Architecture](docs/images/system-architecture.png)
*Complete system architecture diagram*

### Tech Stack

**Backend**
- Python 3.10 + aiohttp (async web server)
- PyTorch 2.1.0 (FP16 precision)
- Ultralytics YOLO v8+
- OpenCV 4.8+ (computer vision)
- SQLite (data persistence)

**Frontend**
- HTML5 + JavaScript (web dashboard)
- WebSocket (real-time updates)
- Chart.js (data visualization)
- Flatpickr (date selection)

**Mobile**
- Flutter 3.0+ (cross-platform)
- Provider (state management)
- Dio (HTTP client)
- Image Picker (camera/gallery)

**Hardware**
- NVIDIA Jetson Orin Nano
- USB camera (UVC-compliant)
- Optional: HDMI display

---

## Mobile App

### Veratori Restock (Flutter)

Employee-facing mobile application for documenting restock actions through structured photo submissions.

**Features**
- Photo capture (minimum 3 photos: front, left, right)
- Real-time YOLO detection preview
- Submission management with status tracking
- Push notifications for manager reviews
- Role-based access (employees only see their franchise)

**Setup**

```bash
cd Poke-Bowl---updated-January/veratori_restock_flutter
flutter pub get
flutter run
```

**Configuration**

Update `lib/services/api_service.dart` with your backend URL:

```dart
_baseUrl = 'http://YOUR_SERVER_IP:8080';
```

For production, use HTTPS:

```dart
_baseUrl = 'https://your-domain.com';
```

See [veratori_restock_flutter/README.md](Poke-Bowl---updated-January/veratori_restock_flutter/README.md) for complete documentation.

---

## Quick Start

### Prerequisites

- NVIDIA Jetson Orin Nano with JetPack 6.x
- USB camera (UVC-compliant)
- Python 3.10+
- Flutter SDK (for mobile app)

### Installation

**1. Clone Repository**

```bash
git clone https://github.com/FelipeCardozo0/Veratori.git
cd Veratori/Poke-Bowl---updated-January
```

**2. Backend Setup**

```bash
# Install dependencies
pip3 install -r requirements.txt

# Configure (edit config/config.yaml)
# - Camera device index
# - YOLO model path
# - Detection thresholds

# Run server
cd backend
python3 main.py
```

**3. Access Web Dashboard**

```
http://localhost:8080
```

**4. Production Deployment (Auto-start)**

```bash
cd deployment
sudo bash setup_autostart.sh
sudo reboot
```

**Full installation guide**: [QUICKSTART.md](QUICKSTART.md)

![Installation Process](docs/images/installation-process.png)
*Step-by-step installation and deployment process*

---

## Project Structure

```
Veratori/
├── Poke-Bowl---updated-January/        # Main application
│   ├── backend/                        # Python backend
│   │   ├── main.py                     # Entry point
│   │   ├── camera.py                   # Camera handler
│   │   ├── detector.py                # YOLO inference
│   │   ├── inventory.py               # Inventory tracking
│   │   ├── server.py                  # Web server + APIs
│   │   ├── restock_manager.py         # Restock submission manager
│   │   └── auth.py                    # Authentication
│   ├── frontend/                       # Web dashboard
│   │   ├── home.html                  # Executive control room
│   │   ├── index.html                 # Main dashboard
│   │   ├── upload.html                # Upload + moderation
│   │   ├── analytics.html             # Analytics page
│   │   └── login.html                 # Authentication
│   ├── veratori_restock_flutter/      # Mobile app
│   │   ├── lib/
│   │   │   ├── screens/               # App screens
│   │   │   ├── services/              # API services
│   │   │   └── providers/             # State management
│   │   └── pubspec.yaml
│   ├── config/                        # Configuration
│   │   └── config.yaml
│   ├── deployment/                    # Deployment scripts
│   │   ├── setup_jetson.sh
│   │   └── setup_autostart.sh
│   └── best.pt                         # Pre-trained YOLO model
├── src/                                # Next.js marketing site
│   └── app/                           # Marketing pages
└── docs/                              # Documentation
```

---

## API Endpoints

### Core APIs

- `GET /` - Web dashboard
- `GET /api/stats` - System statistics
- `GET /api/inventory` - Current inventory
- `GET /api/sales` - Sales history
- `GET /api/alerts` - Active alerts
- `GET /ws` - WebSocket connection

### Restock APIs (Mobile App)

- `POST /api/restock/login` - Employee login
- `POST /api/restock/validate` - Session validation
- `POST /api/restock/detect` - YOLO detection on photo
- `POST /api/restock/upload` - Submit restock with photos
- `GET /api/restock/submissions` - Get employee submissions
- `GET /api/restock/notifications` - Get notifications
- `GET /api/restock/all` - Manager view (all submissions)
- `POST /api/restock/status` - Update submission status

---

## Performance

| Metric | Typical | Optimized |
|--------|---------|-----------|
| **FPS** | 18-22 | 25-30 |
| **Latency** | 60ms | <50ms |
| **Inference** | 35ms | 30ms |
| **CPU Usage** | 40% | 35% |
| **GPU Usage** | 35% | 40% |
| **Memory** | 200MB | 180MB |

![Performance Metrics](docs/images/performance-metrics.png)
*System performance benchmarks and optimization results*

---

## Configuration

Edit `config/config.yaml`:

```yaml
camera:
  index: 0              # USB camera device
  width: 1280
  height: 720
  fps: 30

detector:
  model_path: best.pt
  conf_threshold: 0.25
  iou_threshold: 0.45
  device: '0'          # GPU
  half: true           # FP16 precision

inventory:
  smoothing_window: 10
  smoothing_method: median
  enable_persistence: true
  snapshot_interval: 5.0
  expiration_days: 5

alerts:
  enable_alerts: true
  low_stock_thresholds:
    mango: 3
    watermelon: 2
    # ... more products

server:
  host: '0.0.0.0'
  port: 8080
```

---

## Usage

### Start Backend

```bash
cd backend
python3 main.py
```

### Start as Service

```bash
sudo systemctl start veratori-inventory
sudo systemctl status veratori-inventory
```

### View Logs

```bash
sudo journalctl -u veratori-inventory -f
tail -f /tmp/veratori_inventory.log
```

### Mobile App

```bash
cd veratori_restock_flutter
flutter run
```

---

## Troubleshooting

### Camera not detected

```bash
v4l2-ctl --list-devices
# Update config.yaml with correct device index
```

### Low FPS

```bash
# Enable max performance
sudo nvpmodel -m 0
sudo jetson_clocks
```

### Service won't start

```bash
# Check logs
sudo journalctl -u veratori-inventory -n 50
```

### Mobile app connection issues

- Verify backend server is running
- Check API base URL in `api_service.dart`
- Ensure firewall allows connections

---

## Documentation

| Document | Description |
|----------|-------------|
| **[QUICKSTART.md](QUICKSTART.md)** | 10-minute setup guide |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Technical architecture |
| **[SYSTEM_DIAGRAM.md](SYSTEM_DIAGRAM.md)** | Visual system diagrams |
| **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** | Production deployment |
| **[veratori_restock_flutter/README.md](Poke-Bowl---updated-January/veratori_restock_flutter/README.md)** | Mobile app documentation |

---

## Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) - Object detection framework
- [NVIDIA Jetson](https://developer.nvidia.com/embedded/jetson) - Edge AI platform
- [Flutter](https://flutter.dev/) - Cross-platform mobile framework
- [aiohttp](https://docs.aiohttp.org/) - Async HTTP framework

---

## Contact

**Felipe Cardozo**  
GitHub: [@FelipeCardozo0](https://github.com/FelipeCardozo0)  
Repository: [Veratori](https://github.com/FelipeCardozo0/Veratori)

---

## Status

**Version**: 2.0.0  
**Status**: Production Ready  
**Last Updated**: January 2026

Ready for immediate deployment.
