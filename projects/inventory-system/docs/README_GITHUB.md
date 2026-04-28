#  Jetson Orin Inventory Vision System

[![Platform](https://img.shields.io/badge/Platform-Jetson%20Orin%20Nano-76B900?logo=nvidia)](https://developer.nvidia.com/embedded/jetson-orin)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python)](https://www.python.org/)
[![YOLO](https://img.shields.io/badge/YOLO-v8+-00FFFF?logo=yolo)](https://github.com/ultralytics/ultralytics)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Production-ready computer vision inventory system for restaurant environments**  
> Real-time object detection • Automatic counting • WebSocket streaming • Auto-start on boot

[ Quick Start](#-quick-start) • [ Documentation](#-documentation) • [ Features](#-features) • [ Architecture](#%EF%B8%8F-architecture)

---

##  Features

[OK] **Real-time Detection** - YOLO v8+ with GPU acceleration (15-30 FPS)  
[OK] **Stable Counting** - Temporal smoothing eliminates false positives  
[OK] **Live Web Interface** - WebSocket streaming with inventory display  
[OK] **Auto-Start** - Powers on → system ready (no manual intervention)  
[OK] **Self-Healing** - Automatic camera reconnection  
[OK] **Production-Grade** - Comprehensive error handling and logging  
[OK] **40 Product Classes** - Pre-trained model included  
[OK] **One-Command Deploy** - Fully automated setup

---

## 📸 Screenshots

### Web Interface
Live camera feed with real-time detection overlays and inventory counts.

```
┌─────────────────────────────────────────────┐
│  Poke Bowl Inventory         Connected ● │
├─────────────────────┬───────────────────────┤
│                     │  Current Inventory    │
│   Live Camera       │                       │
│   [Detection Feed]  │  Mango          5     │
│   with bounding     │  Cantaloupe     3     │
│   boxes & labels    │  Sprite        12     │
│                     │  ...                  │
│   FPS: 22.1         │                       │
│   Inference: 35ms   │  Total Items:  47     │
└─────────────────────┴───────────────────────┘
```

---

##  Quick Start

### Prerequisites
- NVIDIA Jetson Orin Nano with JetPack 6.x
- USB camera (UVC-compliant)
- HDMI display (optional)

### Installation (10 minutes)

```bash
# Clone repository
git clone https://github.com/FelipeCardozo0/Jetson-Orin-Inventory-Vision-System.git
cd Jetson-Orin-Inventory-Vision-System

# Run automated setup
cd deployment
bash setup_jetson.sh

# Test manually
cd ../backend
python3 main.py
```

Open browser: `http://localhost:8080`

### Production Deployment

```bash
# Enable auto-start on boot
cd deployment
sudo bash setup_autostart.sh

# Reboot to test
sudo reboot
```

** Full installation guide**: [QUICKSTART.md](QUICKSTART.md)

---

##  Documentation

| Document | Description |
|----------|-------------|
| **[INDEX.md](INDEX.md)** | 📑 Documentation navigation |
| **[QUICKSTART.md](QUICKSTART.md)** |  10-minute setup guide |
| **[README.md](README.md)** | 📘 Complete user manual |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** |  Technical architecture |
| **[SYSTEM_DIAGRAM.md](SYSTEM_DIAGRAM.md)** |  Visual diagrams |
| **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** | [OK] Production deployment |

---

##  Architecture

```
Camera → YOLO Detector → Inventory Tracker → Web Server → Browser(s)
  ↑                                                            │
  └────────────────────────────────────────────────────────────┘
```

### Tech Stack
- **Hardware**: NVIDIA Jetson Orin Nano
- **ML Framework**: PyTorch 2.1.0 (FP16)
- **Detection**: Ultralytics YOLO v8+
- **Vision**: OpenCV 4.8+
- **Backend**: Python 3.10 + aiohttp
- **Frontend**: HTML5 + WebSocket

**[View detailed architecture →](ARCHITECTURE.md)**

---

##  Performance

| Metric | Typical | Optimized |
|--------|---------|-----------|
| **FPS** | 18-22 | 25-30 |
| **Latency** | 60ms | <50ms |
| **Inference** | 35ms | 30ms |
| **CPU Usage** | 40% | 35% |
| **GPU Usage** | 35% | 40% |
| **Memory** | 200MB | 180MB |

---

## 📁 Project Structure

```
Jetson-Orin-Inventory-Vision-System/
├── backend/              # Python application (6 modules)
│   ├── main.py          # Entry point
│   ├── camera.py        # USB camera handler
│   ├── detector.py      # YOLO inference
│   ├── inventory.py     # Count tracking
│   └── server.py        # Web server
├── frontend/            # Web interface
│   └── index.html       # Single-page UI
├── config/              # Configuration
│   └── config.yaml      # System settings
├── deployment/          # Automation scripts
│   ├── setup_jetson.sh
│   └── setup_autostart.sh
├── best.pt              # Pre-trained model (40 classes)
└── *.md                 # Documentation (8 files)
```

---

##  Usage

### Manual Start
```bash
cd backend
python3 main.py
```

### As Service
```bash
sudo systemctl start pokebowl-inventory
sudo systemctl status pokebowl-inventory
```

### View Logs
```bash
sudo journalctl -u pokebowl-inventory -f
```

### Configuration
Edit `config/config.yaml`:
```yaml
camera:
  index: 0              # USB camera device
  width: 1280
  height: 720

detector:
  conf_threshold: 0.25  # Detection sensitivity
  half: true            # FP16 precision
```

---

##  Troubleshooting

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
sudo journalctl -u pokebowl-inventory -n 50
```

**[Full troubleshooting guide →](README.md#-troubleshooting)**

---

##  Detected Classes (40 total)

Beverages: Black Cherry Cane Sugar, Coke Diet, Coke Zero, Cold Brew Matcha Green Tea, Essentia, Ginger Ale Canada, Guava Green Tea, Iced Tea Cane Sugar, Ito Milk Tea, Jasmine Green Tea, Limonade Cane Sugar, Little Jasmine White Peach Black Tea, Lychee Oolong Tea, Mango Oolong Tea, Oi Ocha Unsweetened Green Tea, Orange Cane Sugar, Passionfruit Green Tea, Perrier, Pineapple Cane Sugar, Pineapple Green Tea, Root Bear Cane Sugar, San Pe Blood Orange, San Pe Lemonade, San Pe Orange, Sprite, Sunkist Orange, Teas' Tea Rose Green Tea, Traditional Golden Oolong Tea, Traditional Jasmine Green Tea, Vanilla Cream Cane Sugar

Fruits: Cantaloupe, Grapes, Mango, Pineapple, Strawberry, Watermelon

Items: Island Passion Fruit, Kilauea Lemon Cake, Maui Custard, Philadelphia 6 roll

---

## 🤝 Contributing

Contributions welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) - Object detection framework
- [NVIDIA Jetson](https://developer.nvidia.com/embedded/jetson) - Edge AI platform
- [aiohttp](https://docs.aiohttp.org/) - Async HTTP framework

---

## 📧 Contact

**Felipe Cardozo**  
GitHub: [@FelipeCardozo0](https://github.com/FelipeCardozo0)  
Repository: [Jetson-Orin-Inventory-Vision-System](https://github.com/FelipeCardozo0/Jetson-Orin-Inventory-Vision-System)

---

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=FelipeCardozo0/Jetson-Orin-Inventory-Vision-System&type=Date)](https://star-history.com/#FelipeCardozo0/Jetson-Orin-Inventory-Vision-System&Date)

---

##  Status

**Version**: 1.0.0  
**Status**: [OK] Production Ready  
**Last Updated**: January 2026

**Ready for immediate deployment on Jetson Orin Nano!**

---

<p align="center">
  Made with ❤ for restaurant inventory management
</p>

