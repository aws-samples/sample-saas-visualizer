# Hardware Setup Guide

This guide covers the hardware requirements and setup for the physical LED display component of the SaaS Visualizer sample.

> **Note**
> This section is optional. The UI can run successfully without physical hardware. However, to replicate the full end-to-end sample with the physical LED display, you can choose to set up the hardware components, with guidance documented below.

> **Important**: Review the [Hardware Cost Considerations](#hardware-cost-considerations) section before purchasing components to understand the investment required.

## Hardware Requirements

To build the physical LED display:

- **Raspberry Pi** (tested with Raspberry Pi 3 or 4, running Raspberry Pi OS Lite "Trixie" or later - the Lite image without desktop environment is recommended)
- **RGB LED Matrix Panels** - Two 128x64 panels (the code assumes two panels stacked vertically for a 128x128 display)
- **Power Supply** - Adequate power supply for the LED panels (check panel specifications depending on the selected panels)
- **[PCB adapter for Raspberry Pi to Hub75](https://github.com/hzeller/rpi-rgb-led-matrix/tree/ef43b877570b727d771e13f287546f12fcf2217b/adapter)** - For connecting the panels to the Raspberry Pi
- **Cables and connectors** - As specified by your panel manufacturer

## Software Requirements

- **Python** - Version 3.13 or higher
- **UV Package Manager** - Modern Python package and project manager
- **rpi-rgb-led-matrix library** - LED matrix driver for Raspberry Pi

> **Important**
> This project uses the [rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix/tree/ef43b877570b727d771e13f287546f12fcf2217b/) library. Choosing to use this means that you are solely responsible for reviewing, verifying, and maintaining all code and dependencies from that repository. This includes ensuring compatibility, security, and proper functionality for your specific use case.

## Prerequisites

> **Important**: Complete the [AWS Deployment Guide](./aws-deployment.md) before proceeding with hardware setup. The IoT certificates required for device authentication are generated from the deployed CloudFormation stack.

## Software Setup

### Step 1: Generate IoT Certificates

On a machine with AWS CLI credentials configured (not necessarily the Raspberry Pi), generate the IoT certificates:

From the root of the saas-visualiser repository:
```bash
uv run scripts/setup_iot_certificates.py create
```

This creates an `iot-certificates/` directory containing:
- `certificate.pem.crt` - Device certificate
- `private.pem.key` - Private key
- `rootCA.pem` - Amazon Root CA
- `device-config.json` - Configuration file with IoT endpoint and topic

### Step 2: Choose Compatible Hardware

Validate your LED panels are [supported by rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix/tree/ef43b877570b727d771e13f287546f12fcf2217b?tab=readme-ov-file#panels-supported). Not all panels work with this library.

### Step 3: Wire Your Hardware

Follow the [wiring instructions](https://github.com/hzeller/rpi-rgb-led-matrix/blob/ef43b877570b727d771e13f287546f12fcf2217b/wiring.md) from the rpi-rgb-led-matrix repository. Incorrect wiring can damage your hardware.

### Step 4: Install Build Dependencies

On your Raspberry Pi, update the system and install the required packages for building the LED matrix library:

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y git build-essential python3-dev cython3 python3-pil
```

### Step 5: Build the rpi-rgb-led-matrix Library

Clone and build the library:

```bash
cd ~
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix
git checkout ef43b877570b727d771e13f287546f12fcf2217b

# Build the C library
make -C lib

# Generate Python binding source files
make -C bindings/python/rgbmatrix
```

Follow any additional installation steps from the [rpi-rgb-led-matrix documentation](https://github.com/hzeller/rpi-rgb-led-matrix).

> **Note**: The font file at `~/rpi-rgb-led-matrix/fonts/4x6.bdf` will be automatically discovered by the display application. No additional configuration is needed for `LED_FONT_PATH`.

### Step 6: Copy Code and Certificates to Raspberry Pi

From your local machine, copy the visualizer-display directory and IoT certificates to your Raspberry Pi:

```bash
rsync -av src/visualizer-display iot-certificates pi@your-pi-ip:
```

### Step 7: Install Python Dependencies

On your Raspberry Pi, install UV and the display application dependencies:

Install UV package manager (see https://docs.astral.sh/uv/getting-started/installation/)

Navigate to the display directory:
```bash
cd "${HOME}/visualizer-display"
```

Sync project dependencies:
```bash
uv sync
```

Install the locally-built rgbmatrix library:
```bash
uv pip install "${HOME}/rpi-rgb-led-matrix/bindings/python"
```

### Step 8: Configure Display Settings

Configure the display application using environment variables:

Copy the example environment file:
```bash
cp .env.example .env
```

Edit configuration (optional - defaults work for most setups):
```bash
nano .env
```

The default configuration is:
- 64 rows per panel
- 128 columns
- 2 parallel chains (vertical stacking)
- Brightness: 70%

You can adjust these settings in the `.env` file if your hardware differs.

### Step 9: Run the Display

Run the display application:

```bash
cd "${HOME}/visualizer-display"
sudo ./scripts/run_hardware.sh
```

> **Note**: The application requires root privileges for GPIO access. You should see the display initialize and connect to AWS IoT.

### Step 10 (Optional): Install Systemd Service

To run the display automatically on boot, install the systemd service:

```bash
cd "${HOME}/visualizer-display"
sudo ./scripts/install-service.sh
sudo systemctl enable visualizer-display
sudo systemctl start visualizer-display
```

Check the service status:

```bash
sudo systemctl status visualizer-display
journalctl -u visualizer-display -f
```

## Using the Hardware Display

Once the hardware display is running and connected to AWS IoT Core, you're ready to use the application! See the [Usage Guide](./use-sample.md) for:
- How to log in and test the application
- Watching transactions flow through the architecture on the physical LED display
- Understanding what each component represents on the LED matrix
- Testing multi-tenant visualization with different colored transactions

## Development Mode

For development without physical hardware, the display code can run in emulator mode. See the [Development Guide](./development.md) for details.

## Hardware Cost Considerations

> **Important Hardware Cost Disclaimer**
> Building the physical LED display requires purchasing hardware components. Costs can vary significantly based on component selection, vendor, and location.
### Estimated Hardware Costs

| Component | Specification | Estimated Cost (USD) | Notes |
|-----------|--------------|---------------------|-------|
| Raspberry Pi 4 (4GB) | Single board computer | $55 - $75 | Pi 3 also works but Pi 4 recommended |
| RGB LED Matrix Panels | Two 128x64 HUB75 panels | $80 - $150 | Price varies by quality and supplier |
| Power Supply | 5V 10A+ (50W+) | $15 - $30 | Must support panel power requirements |
| Adafruit RGB Matrix HAT | PCB adapter for Pi to HUB75 | $25 - $35 | Or equivalent compatible adapter |
| MicroSD Card | 32GB | $8 - $15 | For Raspberry Pi OS |
| Cables & Connectors | Power cables, ribbon cables | $10 - $20 | Depends on panel and setup |
| Enclosure/Frame | Optional mounting | $20 - $100 | Optional, for professional appearance |
| **TOTAL** | | **$213 - $425** | Excluding shipping and taxes |

Note again that the purchase of hardware is optional to make this sample run. **Emulator mode** works without the purchase of any hardware.

### Ongoing Costs

- **Electricity**: LED panels consume approximately 20-40W when running, costing ~$0.05-0.10 per day depending on local electricity rates.
- **AWS IoT**: Minimal cost (~$0.01/day) for MQTT messages from the device (included in AWS deployment costs).

### Important Reminders

⚠️ **Hardware is optional**: The application works fully without physical hardware using the software emulator.

⚠️ **Verify compatibility**: Ensure your LED panels are [compatible with rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix/tree/ef43b877570b727d771e13f287546f12fcf2217b?tab=readme-ov-file#panels-supported) before purchasing.

⚠️ **Power requirements**: Inadequate power supply can cause display issues or damage components.

⚠️ **Skill level**: This project requires basic electronics knowledge and comfort with command-line tools.