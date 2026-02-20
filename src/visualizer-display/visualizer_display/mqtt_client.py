"""AWS IoT MQTT client wrapper."""

import json
import logging
from typing import Callable, Optional

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

from .config import AWSConfig

logger = logging.getLogger(__name__)


class MQTTClient:
    """AWS IoT MQTT client with automatic reconnection."""

    def __init__(self, config: AWSConfig):
        """Initialize MQTT client.

        Args:
            config: AWS IoT configuration
        """
        self._config = config
        self._client = AWSIoTMQTTClient(config.client_id)
        self._setup_client()
        self._message_callback: Optional[Callable] = None

    def _setup_client(self) -> None:
        """Configure MQTT client."""
        self._client.configureEndpoint(self._config.endpoint, self._config.port)
        self._client.configureCredentials(
            self._config.root_ca_path,
            self._config.key_path,
            self._config.cert_path
        )

        # Connection parameters
        self._client.configureAutoReconnectBackoffTime(1, 32, 20)
        self._client.configureOfflinePublishQueueing(-1)
        self._client.configureDrainingFrequency(2)
        self._client.configureConnectDisconnectTimeout(20)
        self._client.configureMQTTOperationTimeout(10)

    def connect(self) -> None:
        """Connect to AWS IoT.

        Raises:
            Exception: If connection fails
        """
        logger.info(f"Connecting to AWS IoT: {self._config.endpoint}")
        self._client.connect()
        logger.info("Connected successfully")

    def subscribe(self, callback: Callable[[dict], None]) -> None:
        """Subscribe to configured topic with callback.

        Args:
            callback: Function to call with parsed JSON payload
        """
        self._message_callback = callback

        def mqtt_callback(client, userdata, message):
            """Internal MQTT callback that handles JSON parsing."""
            try:
                payload_str = message.payload.decode('utf-8')
                logger.debug(f"Received message: {payload_str}")

                payload = json.loads(payload_str)
                if self._message_callback:
                    self._message_callback(payload)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON message: {e}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")

        self._client.subscribe(self._config.topic, 1, mqtt_callback)
        logger.info(f"Subscribed to topic: {self._config.topic}")

    def publish(self, message: dict) -> None:
        """Publish message to configured topic.

        Args:
            message: Dictionary to publish as JSON
        """
        payload = json.dumps(message)
        self._client.publish(self._config.topic, payload, 1)
        logger.debug(f"Published message: {payload}")

    def disconnect(self) -> None:
        """Disconnect from AWS IoT."""
        self._client.disconnect()
        logger.info("Disconnected from AWS IoT")
