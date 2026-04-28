# Scripts Folder

This folder contains shared functions used by the start/stop control scripts.

## Files

- **`common.sh`** - Shared functions for all control scripts
  - OS detection
  - Process management
  - Health checking
  - Browser launching
  - Logging utilities

## Usage

These scripts are **internal** and should not be run directly. They are sourced by the main control scripts:

- `../start.sh`
- `../stop.sh`
- `../restart.sh`
- `../status.sh`

## Functions Available

### Environment Detection
- `detect_os()` - Detect operating system (linux, macos, windows)
- `is_jetson()` - Check if running on Jetson with systemd service

### Process Management
- `is_running()` - Check if backend is running
- `get_pid()` - Get current process ID
- `get_status()` - Get full status information

### Backend Control
- `start_pc_backend(mode)` - Start PC testing backend
- `start_jetson_backend()` - Start Jetson production backend
- `stop_pc_backend()` - Stop PC backend
- `stop_jetson_backend()` - Stop Jetson backend

### Health & Browser
- `wait_for_health(url)` - Wait for health endpoint to respond
- `open_browser(url)` - Open URL in appropriate browser

### Utilities
- `log(message)` - Log to file
- `print_success(message)` - Green checkmark output
- `print_warning(message)` - Yellow warning output
- `print_error(message)` - Red error output
- `print_info(message)` - Info output

## Configuration

Default paths and settings are defined in `common.sh`:

```bash
PID_FILE="$REPO_ROOT/run/pokebowl.pid"
LOG_FILE="$REPO_ROOT/run/pokebowl_launch.log"
DEFAULT_PORT=8080
HEALTH_ENDPOINT="/health"
```

## Logs

Launch logs are written to `../run/pokebowl_launch.log`





