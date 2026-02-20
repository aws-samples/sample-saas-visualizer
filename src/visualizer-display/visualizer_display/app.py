"""Main application orchestrator."""

import argparse
import logging
import time
import signal
import sys
from pathlib import Path
from threading import Thread, Event
from typing import Optional

from .config import load_config, AppConfig, ConfigError
from .display.factory import create_display
from .display.base import MatrixDisplay
from .renderer import Renderer
from .mqtt_client import MQTTClient
from .transaction_state import TransactionManager

logger = logging.getLogger(__name__)


class LEDMatrixApp:
    """Main application with display loop and MQTT integration."""

    def __init__(self, config: AppConfig):
        """Initialize application.

        Args:
            config: Application configuration
        """
        self._config = config
        self._running = Event()
        self._display: Optional[MatrixDisplay] = None
        self._renderer: Optional[Renderer] = None
        self._mqtt: Optional[MQTTClient] = None
        self._transaction_manager: Optional[TransactionManager] = None
        self._display_thread: Optional[Thread] = None

    def setup(self) -> None:
        """Initialize all components.

        Raises:
            Exception: If initialization fails
        """
        # Create display (hardware or emulator)
        self._display = create_display(self._config)
        width, height = self._display.get_dimensions()
        logger.info(f"Display initialized: {width}x{height} ({self._config.matrix.parallel} parallel, {self._config.matrix.chain_length} chain)")

        # Create renderer with matrix config for coordinate conversion
        self._renderer = Renderer(self._display, self._config.display, self._config.matrix)
        logger.info("Renderer initialized with coordinate conversion")

        # Create transaction manager with message-queue timing
        self._transaction_manager = TransactionManager(
            minimum_display_duration=self._config.display.minimum_display_duration,
            final_linger_duration=self._config.display.final_linger_duration
        )
        logger.info("Transaction manager initialized (message-queue model)")

        # Create MQTT client
        self._mqtt = MQTTClient(self._config.aws)
        self._mqtt.connect()
        self._mqtt.subscribe(self._handle_mqtt_message)

    def _handle_mqtt_message(self, payload: dict) -> None:
        """Handle incoming MQTT message.

        Args:
            payload: Parsed JSON message payload
        """
        logger.info(f"MQTT message: {payload}")

        # Validate message format
        required_fields = ['TransactionId', 'timestamp', 'tenantid', 'tenantcolor', 'position']
        if not all(field in payload for field in required_fields):
            logger.warning(f"Invalid message format - missing fields: {payload}")
            return

        # Validate tenant ID range (1-24)
        try:
            tenant_num = int(payload['tenantid'])
            if not 1 <= tenant_num <= 24:
                logger.warning(f"Invalid tenant ID (must be 1-24): {payload['tenantid']}")
                return
        except ValueError:
            logger.warning(f"Invalid tenant ID format: {payload['tenantid']}")
            return

        # Validate position array not empty
        if not isinstance(payload['position'], list) or len(payload['position']) == 0:
            logger.warning(f"Invalid or empty position array: {payload.get('position')}")
            return

        # Add to transaction manager
        self._transaction_manager.add_transaction(payload)

    def _display_loop(self) -> None:
        """Main display rendering loop with double-buffering.

        Runs at 20 Hz for smooth display updates.
        Transaction manager handles timing internally.
        """
        # Create initial off-screen canvas
        canvas = self._display.create_canvas()

        # Stats logging
        stats_log_interval = 10  # Log detailed stats every 10 seconds
        last_stats_log = time.time()

        logger.info("Display loop started (20Hz render)")

        while self._running.is_set():
            current_time = time.time()

            # Update transaction state every frame
            self._transaction_manager.update_all_transactions()

            # Log detailed stats periodically
            if current_time - last_stats_log >= stats_log_interval:
                stats = self._transaction_manager.get_stats()
                if stats['active_transactions'] > 0:
                    logger.info("=== Transaction Stats ===")
                    logger.info(f"Active transactions: {stats['active_transactions']}")
                    for component, details in stats.get('slot_details', {}).items():
                        if details['occupied'] > 0 or details['overflow_risk']:
                            overflow_flag = ' [OVERFLOW RISK]' if details['overflow_risk'] else ''
                            logger.info(f"  {component}: {details['utilization']} slots{overflow_flag}")

                    # Verify slot consistency
                    consistency = self._transaction_manager.verify_slot_consistency()
                    if not consistency['consistent']:
                        logger.error("=== Slot Consistency Issues Detected ===")
                        for issue in consistency['issues']:
                            logger.error(f"  {issue}")

                last_stats_log = current_time

            # Get snapshot of transactions for rendering
            transactions = self._transaction_manager.get_active_transactions()

            # Render frame to off-screen canvas
            self._renderer.render_frame(canvas, transactions)

            # Atomically swap canvas - prevents flickering
            canvas = self._display.swap_canvas(canvas)

            # Maintain ~20Hz refresh rate
            # nosemgrep: arbitrary-sleep - Intentional frame rate limiter for smooth LED display rendering
            time.sleep(0.05)

        logger.info("Display loop stopped")

    def run(self) -> None:
        """Start the application.

        Runs the display loop in a separate thread and keeps the main thread
        alive until interrupted.
        """
        # Set up signal handlers before starting threads
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal")
            self.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self._running.set()

        # Start display loop in separate daemon thread
        self._display_thread = Thread(target=self._display_loop, daemon=True)
        self._display_thread.start()

        logger.info("Application running. Press Ctrl+C to exit.")

        # Keep main thread alive
        try:
            while self._running.is_set():
                # nosemgrep: arbitrary-sleep - Intentional idle loop to keep main thread alive while display runs
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.shutdown()

    def shutdown(self) -> None:
        """Clean shutdown of all components."""
        logger.info("Shutting down...")

        # Stop display loop
        self._running.clear()

        # Wait for display thread to finish
        if self._display_thread and self._display_thread.is_alive():
            self._display_thread.join(timeout=2)
            if self._display_thread.is_alive():
                logger.warning("Display thread did not stop in time")

        # Cleanup display
        if self._display:
            self._display.cleanup()
            logger.info("Display cleaned up")

        # Disconnect MQTT
        if self._mqtt:
            self._mqtt.disconnect()

        logger.info("Shutdown complete")


def main() -> None:
    """Entry point for the application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='LED Matrix Display with AWS IoT integration',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '-c', '--config',
        type=Path,
        default=None,
        help='Path to device-config.json (or set CONFIG_PATH env var)'
    )
    args = parser.parse_args()

    # Use --config if provided, otherwise fall back to CONFIG_PATH env var
    config_path = args.config
    if config_path is None:
        env_path = os.environ.get('CONFIG_PATH')
        if env_path:
            config_path = Path(env_path)
        else:
            print("Error: No config file specified", file=sys.stderr)
            print("Use --config or set CONFIG_PATH environment variable", file=sys.stderr)
            sys.exit(1)

    # Validate config file exists
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    if not config_path.is_file():
        print(f"Error: Configuration path is not a file: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        # Load configuration
        config = load_config(config_path)

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        logger.info("=== LED Matrix Display Starting ===")
        logger.info(f"Mode: {'Emulator' if config.emulator_mode else 'Hardware'}")
        logger.info(f"Display: {config.matrix.rows}x{config.matrix.cols}, "
                   f"{config.matrix.parallel} parallel, {config.matrix.chain_length} chain")
        logger.info(f"AWS IoT: {config.aws.endpoint}")
        logger.info(f"Topic: {config.aws.topic}")

        # Create and run app
        app = LEDMatrixApp(config)
        app.setup()
        app.run()

    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print(f"\nPlease check your configuration file: {config_path}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
