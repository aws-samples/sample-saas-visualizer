# visualizer-display

AWS IoT LED Matrix Display with Hardware Abstraction

## Overview

LED matrix display controller for the SaaS Visualizer project. The controller receives tenant transaction messages via AWS IoT MQTT and renders them on a 128x128 LED matrix display.

Key capabilities:
- **JSON-based AWS IoT configuration** - Device settings loaded from device-config.json
- **UV dependency management** - Python 3.13 with modern tooling
- **Double-buffering** - Flicker-free display updates
- **Hardware abstraction** - Support for both real hardware and software emulator

## Features

- AWS IoT Core MQTT integration for real-time color commands
- Support for [rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) hardware
- Support for [RGBMatrixEmulator](https://github.com/ty-porter/RGBMatrixEmulator) for development
- Double-buffered rendering for smooth, flicker-free updates
- Comprehensive test suite

## Hardware Configuration

Default configuration:
- 64 rows per panel
- 128 columns per panel
- 2 parallel chains (vertical stacking)
- 1 chain length (horizontal)
- Total display: 128x128 pixels

## Installation

For detailed installation instructions, see:

- **Raspberry Pi hardware setup**: [docs/hardware-setup.md](../../docs/hardware-setup.md)
- **Development/emulator setup**: [docs/development.md](../../docs/development.md)

## Configuration

Configuration is split between two sources:

### AWS IoT Configuration (device-config.json)

AWS IoT settings are loaded from a `device-config.json` file passed via the `--config` argument.

**Required fields in device-config.json:**
```json
{
  "endpoint": "your-endpoint.iot.region.amazonaws.com",
  "client_id": "your-unique-client-id",
  "topic": "your/mqtt/topic",
  "paths": {
    "certificate": "certificate.pem.crt",
    "private_key": "private.pem.key",
    "root_ca": "rootCA.pem"
  }
}
```

**Note:** Certificate paths in `device-config.json` are relative to the config file's directory.

### Display Configuration (Environment Variables)

Matrix and display settings are configured via environment variables. See `.env.example` for all options.

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG_PATH` | `~/iot-certificates/device-config.json` | Path to device-config.json |
| `LED_EMULATOR_MODE` | `false` | Set to `true` for emulator mode |
| `LED_MATRIX_PARALLEL` | `2` | Number of parallel chains |
| `LED_MATRIX_CHAIN_LENGTH` | `1` | Number of panels chained |
| `LED_MATRIX_BRIGHTNESS` | `70` | Brightness level 0-100 |
| `LED_MATRIX_GPIO_SLOWDOWN` | `3` | GPIO slowdown (0-4, higher = more stable) |
| `LED_MATRIX_PWM_BITS` | `11` | PWM bit depth |
| `LED_MATRIX_PWM_LSB_NANOSECONDS` | `130` | PWM timing |
| `LED_MATRIX_HARDWARE_MAPPING` | `regular` | Hardware mapping type |
| `LED_MATRIX_DISABLE_HARDWARE_PULSING` | `false` | Disable hardware pulsing |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

## Usage

```bash
python -m visualizer_display --config /path/to/device-config.json
```

Short form:
```bash
python -m visualizer_display -c /path/to/device-config.json
```

Using uv run:
```bash
uv run python -m visualizer_display --config /path/to/device-config.json
```

Using convenience scripts:
```bash
./scripts/run_emulator.sh    # Development mode
./scripts/run_hardware.sh    # Hardware mode
```

Override default config path in scripts:
```bash
CONFIG_PATH=/custom/path/device-config.json ./scripts/run_emulator.sh
```

## MQTT Message Format

The application subscribes to the configured MQTT topic and expects JSON messages representing tenant transactions flowing through the SaaS architecture:

```json
{
  "TransactionId": "unique-transaction-id",
  "timestamp": 1234567890,
  "tenantid": "1",
  "tenantcolor": "#FF0000",
  "position": ["amplify", "apigateway", "lambda", "rdsproxy", "rds"]
}
```

**Required fields:**
- `TransactionId` - Unique identifier for the transaction
- `timestamp` - Unix timestamp
- `tenantid` - Tenant ID (1-24)
- `tenantcolor` - Hex color code for the tenant (e.g., `#FF0000`)
- `position` - Array of component positions the transaction passes through

**Valid positions:** `amplify`, `apigateway`, `siloedsqs`, `sharedsqs`, `lambda`, `rdsproxy`, `rds`

## Architecture

- **app.py** - Main application orchestrator with CLI argument parsing
- **config.py** - Configuration management (JSON for AWS IoT, environment variables for display)
- **mqtt_client.py** - AWS IoT MQTT client wrapper
- **transaction_state.py** - Transaction lifecycle and slot allocation management
- **renderer.py** - Display rendering logic with double-buffering
- **layout.py** - Static layout coordinates and component positions
- **coordinate_converter.py** - Coordinate conversion for different panel configurations
- **display/** - Hardware abstraction layer
  - **base.py** - Abstract base classes and protocols
  - **hardware.py** - Real LED matrix hardware implementation
  - **emulator.py** - Software emulator implementation
  - **factory.py** - Factory pattern for display creation

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=visualizer_display --cov-report=html

# Run specific test file
uv run pytest tests/test_config.py
```

## Development

```bash
# Install all dependencies including dev tools
uv sync --group dev

# Run tests
uv run pytest

# Type checking (if you add type hints)
uv run mypy visualizer_display
```

## License

See the main project LICENSE file.
