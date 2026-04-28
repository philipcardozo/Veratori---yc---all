# Deployment Checklist

Use this checklist to ensure successful deployment of the Poke Bowl Inventory System on your Jetson Orin Nano.

---

## Pre-Deployment Verification

### Hardware Setup
- [ ] Jetson Orin Nano powered on and accessible
- [ ] JetPack 6.x installed and verified
- [ ] USB camera connected and recognized
- [ ] HDMI display connected (if using kiosk mode)
- [ ] Network connection established (Ethernet or WiFi)
- [ ] Power supply adequate for Jetson + camera

### Software Prerequisites
- [ ] SSH access to Jetson configured
- [ ] `sudo` privileges available
- [ ] Git installed (`sudo apt-get install git`)
- [ ] Internet connectivity for package downloads

---

## Installation Steps

### 1. Clone Repository
```bash
cd ~
git clone <your-repo-url> Poke-Bowl---updated-January
cd Poke-Bowl---updated-January
```

- [ ] Repository cloned successfully
- [ ] `best.pt` model file present in root directory
- [ ] All files and directories visible

### 2. Run Automated Setup
```bash
cd deployment
chmod +x *.sh
bash setup_jetson.sh
```

- [ ] System packages updated
- [ ] Dependencies installed
- [ ] PyTorch installed (Jetson version)
- [ ] Torchvision compiled
- [ ] Python packages installed
- [ ] No critical errors in output

**Expected Time**: 15-30 minutes

### 3. Verify Camera
```bash
v4l2-ctl --list-devices
ls -l /dev/video*
```

- [ ] Camera device detected (e.g., `/dev/video0`)
- [ ] Device number noted for configuration

### 4. Update Configuration
Edit `config/config.yaml`:

```bash
cd ~/Poke-Bowl---updated-January
nano config/config.yaml
```

- [ ] Camera index set correctly (0, 1, 2, etc.)
- [ ] Resolution appropriate for your camera
- [ ] Other settings reviewed and adjusted

### 5. Test Manually
```bash
cd ~/Poke-Bowl---updated-January/backend
python3 main.py
```

**Expected Output**:
```
============================================================
Poke Bowl Inventory System
============================================================
Camera opened: 1280x720 @ 30fps
Model loaded in X.XXs
System ready!
Web interface available at: http://0.0.0.0:8080
============================================================
```

- [ ] Camera initialized successfully
- [ ] Model loaded without errors
- [ ] Web server started
- [ ] No exceptions or critical errors

### 6. Test Web Interface
Open browser on any device on the same network:
```
http://<jetson-ip>:8080
```

- [ ] Web page loads successfully
- [ ] Video feed appears
- [ ] Detection boxes visible
- [ ] Inventory counts updating
- [ ] No console errors in browser

Press `Ctrl+C` to stop the manual test.

---

## Production Deployment

### 7. Install Auto-Start Services
```bash
cd ~/Poke-Bowl---updated-January/deployment
sudo bash setup_autostart.sh
```

- [ ] Backend service installed
- [ ] Chromium kiosk service installed (if using display)
- [ ] Services enabled for auto-start
- [ ] No errors during installation

### 8. Start Services
```bash
sudo systemctl start pokebowl-inventory
```

- [ ] Service started successfully
- [ ] Status shows "active (running)"

Check status:
```bash
sudo systemctl status pokebowl-inventory
```

### 9. Verify Auto-Start
```bash
sudo systemctl status pokebowl-inventory
sudo systemctl status chromium-kiosk  # If using kiosk mode
```

- [ ] Both services show "enabled"
- [ ] Services set to start on boot

### 10. Test Reboot
```bash
sudo reboot
```

After reboot:
- [ ] System boots successfully
- [ ] Web interface automatically available
- [ ] Display shows interface (if using kiosk mode)
- [ ] Camera feed working
- [ ] Inventory updating

---

## Post-Deployment Validation

### Functional Tests

#### Camera Test
- [ ] Live video feed displays
- [ ] Frame rate acceptable (15+ FPS)
- [ ] No significant lag or stuttering
- [ ] Camera reconnects if unplugged and replugged

#### Detection Test
- [ ] Objects detected correctly
- [ ] Bounding boxes drawn accurately
- [ ] Class labels correct
- [ ] Confidence scores reasonable (>0.25)

#### Inventory Test
- [ ] Counts update in real-time
- [ ] Counts stable (not flickering)
- [ ] Multiple items counted correctly
- [ ] Counts reset when items removed

#### Web Interface Test
- [ ] Accessible from Jetson (localhost:8080)
- [ ] Accessible from LAN (jetson-ip:8080)
- [ ] Multiple clients can connect simultaneously
- [ ] Reconnects automatically after network interruption

#### Stability Test
- [ ] System runs for 1 hour without issues
- [ ] No memory leaks observed
- [ ] CPU/GPU usage stable
- [ ] No service crashes

### Performance Validation

Check performance metrics:
```bash
# GPU stats
tegrastats

# Service status
sudo systemctl status pokebowl-inventory

# View logs
sudo journalctl -u pokebowl-inventory -n 50
```

- [ ] FPS: 15-30 (acceptable range)
- [ ] Inference time: 30-50ms
- [ ] CPU usage: <60%
- [ ] GPU usage: <50%
- [ ] Memory usage: <500MB
- [ ] No error logs

### Network Test
- [ ] Web interface accessible from LAN
- [ ] Port 8080 open and responding
- [ ] WebSocket connection stable
- [ ] Multiple devices can connect

---

## Optimization (Optional)

### Performance Tuning

If experiencing low FPS:
- [ ] Enable max performance mode:
  ```bash
  sudo nvpmodel -m 0
  sudo jetson_clocks
  ```
- [ ] Reduce camera resolution in `config.yaml`
- [ ] Lower YOLO input size to 416
- [ ] Reduce target FPS to 15

If experiencing high resource usage:
- [ ] Enable half precision in config
- [ ] Lower camera resolution
- [ ] Reduce smoothing window

### Kiosk Mode Optimization

If using HDMI display:
- [ ] Screen doesn't go to sleep
- [ ] Mouse cursor hidden in kiosk mode
- [ ] Browser automatically refreshes if needed
- [ ] Fullscreen mode working

---

## Monitoring Setup

### Enable Continuous Monitoring

Create monitoring script:
```bash
cat > ~/monitor_inventory.sh << 'EOF'
#!/bin/bash
while true; do
    echo "=== $(date) ==="
    systemctl status pokebowl-inventory --no-pager | head -5
    echo ""
    curl -s http://localhost:8080/health | jq
    echo ""
    sleep 60
done
EOF

chmod +x ~/monitor_inventory.sh
```

- [ ] Monitoring script created
- [ ] Can view system health

### Log Rotation

Ensure logs don't fill disk:
```bash
sudo journalctl --vacuum-time=7d
```

- [ ] Log rotation configured
- [ ] Disk space sufficient (>5GB free)

---

## Security Hardening (Production)

### Basic Security
- [ ] Change default SSH password
- [ ] Enable firewall:
  ```bash
  sudo ufw enable
  sudo ufw allow 22    # SSH
  sudo ufw allow 8080  # Web interface
  ```
- [ ] Disable unused services
- [ ] Keep system updated

### Network Security
- [ ] Restrict web interface to localhost if not needed externally:
  Edit `config.yaml`: `host: '127.0.0.1'`
- [ ] Consider VPN access instead of direct exposure
- [ ] Use strong WiFi password if using wireless

### Advanced Security (Optional)
- [ ] Implement authentication on web interface
- [ ] Use HTTPS with SSL certificates
- [ ] Set up fail2ban for SSH protection
- [ ] Regular security updates scheduled

---

## Backup Configuration

### Create Backup
```bash
cd ~/Poke-Bowl---updated-January
tar -czf ~/pokebowl_backup_$(date +%Y%m%d).tar.gz \
    config/ best.pt deployment/ backend/ frontend/
```

- [ ] Configuration backed up
- [ ] Model file backed up
- [ ] Backup stored safely

### Recovery Plan
- [ ] Backup location documented
- [ ] Restore procedure tested
- [ ] Emergency contact information available

---

## Documentation

### System Information

Record the following for future reference:

**Hardware**:
- Jetson model: ______________________
- Camera model: ______________________
- Display model: ______________________

**Network**:
- IP address: ______________________
- MAC address: ______________________
- Port: 8080 (or custom: ______)

**Configuration**:
- Camera device: /dev/video____
- Resolution: __________
- Model: best.pt
- Classes: 40

**Credentials** (if applicable):
- SSH username: ______________________
- Web auth (if added): ______________________

**Contacts**:
- System administrator: ______________________
- Technical support: ______________________

---

## Final Checklist

### System Ready for Production
- [ ] All tests passed
- [ ] Performance acceptable
- [ ] Auto-start working
- [ ] Monitoring in place
- [ ] Backups created
- [ ] Documentation complete
- [ ] Team trained on basic operations

### Handoff Complete
- [ ] System administrator briefed
- [ ] Operations team trained
- [ ] Documentation provided
- [ ] Support contacts shared
- [ ] Maintenance schedule established

---

## Maintenance Schedule

### Daily
- [ ] Visual check of system operation
- [ ] Verify counts are reasonable

### Weekly
- [ ] Check system logs for errors
- [ ] Verify disk space available
- [ ] Test camera and display

### Monthly
- [ ] Review system performance
- [ ] Update system packages
- [ ] Test backup and restore
- [ ] Clean camera lens

### Quarterly
- [ ] Full system audit
- [ ] Performance optimization review
- [ ] Security updates
- [ ] Documentation updates

---

## Troubleshooting Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Camera not working | `sudo systemctl restart pokebowl-inventory` |
| Web interface down | Check logs: `sudo journalctl -u pokebowl-inventory -f` |
| Low FPS | Set max performance: `sudo jetson_clocks` |
| Service won't start | Check config: `python3 -c "import yaml; print(yaml.safe_load(open('config/config.yaml')))"` |
| Display issues | Restart kiosk: `sudo systemctl restart chromium-kiosk` |

For detailed troubleshooting, see **README.md** section.

---

## Support Resources

- **Main Documentation**: README.md
- **Quick Start**: QUICKSTART.md
- **Architecture**: ARCHITECTURE.md
- **System Diagrams**: SYSTEM_DIAGRAM.md
- **Project Summary**: PROJECT_SUMMARY.md

**Logs Location**:
- Service: `sudo journalctl -u pokebowl-inventory`
- Application: `/tmp/pokebowl_inventory.log`

**Health Check**: `curl http://localhost:8080/health`

---

## Sign-Off

**Deployed By**: _______________________  
**Date**: _______________________  
**Deployment Location**: _______________________  
**Status**: ⬜ Development  ⬜ Staging  ⬜ Production

**Notes**:
_____________________________________________________________
_____________________________________________________________
_____________________________________________________________

---

**Deployment Status**: ⬜ Complete ⬜ In Progress ⬜ Issues Found

If all checkboxes are marked, the system is ready for production use! 

