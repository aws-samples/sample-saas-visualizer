# Development

This guide covers development setup for the three main components of the project:

1. **Web Frontend** - React application with Vite and Tailwind CSS
2. **AWS Infrastructure & Backend** - CloudFormation templates and Lambda functions
3. **LED Display Visualizer** - Python application for Raspberry Pi or emulator mode

## 1. Web Frontend Development

### Prerequisites

- Node.js v18+

### Understanding Configuration

The frontend uses a runtime configuration approach:

- **Deployed environments**: The stack automatically creates a `config.js` file in the Amazon S3 bucket with all necessary settings (API endpoints, Amazon Cognito configuration, etc.)
- **Local development**: Download this `config.js` file from Amazon S3 to your local `public/` directory

### Setup

1. Install dependencies:

   ```bash
   npm install
   ```

2. Download configuration from your deployed stack:

   ```bash
   BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name visualise-saas --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucket`].OutputValue' --output text)
   aws s3 cp s3://$BUCKET_NAME/config.js public/config.js
   ```

### Running Locally

```bash
npm run dev
```

The development server will start and you can access the application at `http://localhost:5173` (or the port shown in your terminal).

### Linting

```bash
npm run lint
```

### Building

```bash
npm run build
```

---

## 2. AWS Infrastructure & Backend Development

### Prerequisites

- AWS SAM CLI
- AWS CLI with configured credentials
- Python 3.x (for Lambda functions)

### Deploying Changes

After making changes to backend or infrastructure code:

```bash
sam build
sam deploy
```

For more efficient iteration during development, you can use:

```bash
sam sync
```

### Debug Mode

For additional debugging, deploy with development settings:

```bash
sam deploy --parameter-overrides IsDevDeployment=True
```

This enables additional logging and debugging features in the backend.

For more troubleshooting help, see the [Troubleshooting Guide](./troubleshooting.md).

### What's Where

- **CloudFormation templates**: `cfn/`
- **API Lambda functions**: `src/backend/`
- **Load generator Lambda**: `src/load-generator/`
- **Database cleanup Lambda**: `src/mysql-record-reaper/`

### Load Generator

The load generator is an optional Lambda function that automatically generates simulated traffic to demonstrate the SaaS architecture under load.

#### Configuration

Load generator settings are configured in `samconfig.toml` before deployment:

```toml
parameter_overrides=[
  "EnableLoadGenerator=False",           # Set to True to enable
  "LoadGeneratorMinRequests=1",          # Min requests per invocation
  "LoadGeneratorMaxRequests=5",          # Max requests per invocation
  "LoadGeneratorFrequency=5",            # Run every N minutes
]
```

#### How It Works

When enabled, the load generator:

1. **Runs on a schedule** - Invokes every N minutes (default: 5 minutes)
2. **Authenticates as demo users** - Uses tenants 21-24 for generated traffic
3. **Places random orders** - Generates 1-5 orders per invocation with random products
4. **Uses both queue types** - Randomly selects shared or siloed queue paths
5. **Provides continuous visualization** - Keeps the LED display active even when idle

#### Enabling the Load Generator

To enable after initial deployment:

1. Edit `samconfig.toml` and set `EnableLoadGenerator=True`
2. Optionally adjust frequency and request counts
3. Redeploy:
   ```bash
   sam build
   sam deploy
   ```

The load generator will start running on the configured schedule. You can monitor its activity by:
- Watching the LED display for automated transactions
- Logging in as tenants 21-24 to see generated orders
- Checking CloudWatch Logs for the LoadGenerator Lambda function

#### Disabling the Load Generator

To stop automated traffic generation:

1. Edit `samconfig.toml` and set `EnableLoadGenerator=False`
2. Redeploy:
   ```bash
   sam build
   sam deploy
   ```

The EventBridge schedule will be disabled, stopping all automated invocations.

#### Cost Considerations

The load generator adds minimal cost:
- **Lambda invocations**: ~8,640/month at 5-minute intervals (within free tier: 1M requests/month)
- **Lambda duration**: ~1-2 seconds per invocation (within free tier: 400,000 GB-seconds/month)
- **Database writes**: Additional Aurora write operations (~10K-40K/month depending on configuration)

For cost optimization during extended testing, consider:
- Increasing `LoadGeneratorFrequency` to 15 or 30 minutes
- Reducing `LoadGeneratorMaxRequests` to 1-2
- Disabling when not actively demonstrating the system

---

## 3. LED Display Development

### Prerequisites

- Python 3.13+
- uv package manager

### Emulator Mode (Local Development)

The LED display code can run in emulator mode, allowing development and testing without Raspberry Pi hardware. The emulator runs a web server that displays the LED matrix in your browser.

#### Setup

Navigate to the visualizer-display directory:
```bash
cd src/visualizer-display
```

Install uv if needed (see https://docs.astral.sh/uv/getting-started/installation/)

Install all dependencies (uv automatically creates and manages virtualenv):
```bash
uv sync --group dev
```

Copy environment configuration:
```bash
cp .env.example .env
```

Edit .env and set LED_EMULATOR_MODE=true

#### Clone rpi-rgb-led-matrix for fonts

The display requires a font file from the rpi-rgb-led-matrix project. Clone it as a sibling directory:

```bash
# From project root (visualise-saas directory), clone as sibling
cd ..
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix
git checkout ef43b877570b727d771e13f287546f12fcf2217b
cd ../visualise-saas
```

The font will be automatically discovered at `../rpi-rgb-led-matrix/fonts/4x6.bdf`.

Alternatively, set `LED_FONT_PATH` in `.env` to point to an existing font file.

#### Generate IoT Certificates

Generate the IoT certificates required for device authentication.

From the root of the saas-visualiser repository:
```bash
cd ../..
uv run scripts/setup_iot_certificates.py create
```

This creates an `iot-certificates/` directory containing:
- `certificate.pem.crt` - Device certificate
- `private.pem.key` - Private key
- `rootCA.pem` - Amazon Root CA
- `device-config.json` - Configuration file with IoT endpoint and topic

#### Running the Emulator

After deploying your CloudFormation stack and setting up IoT certificates.

Navigate back to the visualizer-display directory:
```bash
cd src/visualizer-display
```

Use the convenience script:
```bash
./scripts/run_emulator.sh
```

Or run directly (uv handles virtualenv automatically):
```bash
uv run visualizer-display --config /path/to/device-config.json
```

The emulator will start a web server at http://localhost:8888/ where you can view the LED matrix in your browser. It connects to AWS IoT Core and visualizes transactions in real-time, just like the physical hardware.

#### Using the Emulator

Once the emulator is running and connected to AWS IoT Core, you can start using the application! See the [Usage Guide](./use-sample.md) for:
- How to log in and test the application
- Watching transactions flow through the architecture visualization
- Understanding what each component represents on the LED display

### Hardware Mode (Raspberry Pi)

Make sure you're in the visualizer-display directory:
```bash
cd src/visualizer-display
```

Install all dependencies (same as emulator setup):
```bash
uv sync
```

Copy environment configuration:
```bash
cp .env.example .env
```

Edit .env and set LED_EMULATOR_MODE=false:
```bash
nano .env
```

Run:
```bash
./scripts/run_hardware.sh
```

Note: The hardware library (`rgbmatrix`) requires Raspberry Pi with GPIO access. See [Hardware Setup](./hardware-setup.md) for detailed instructions.

### Debug Logging

For detailed LED display debugging, set `LOG_LEVEL=DEBUG` in the `.env` file:

In src/visualizer-display/.env:
```
LOG_LEVEL=DEBUG
```

This will output detailed transaction processing, MQTT messages, and rendering statistics.

### Hardware vs Emulator Differences

The emulator provides an identical software interface to the hardware. The only differences are:
- Emulator renders to a web browser instead of GPIO pins
- Emulator may run at different framerates depending on system performance
- Hardware requires sudo for GPIO access, emulator does not

All configuration, MQTT integration, state management, and rendering logic are identical.
