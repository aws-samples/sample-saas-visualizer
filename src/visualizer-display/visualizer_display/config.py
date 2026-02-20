"""Configuration management from environment variables."""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Configuration validation error."""
    pass


def get_font_path() -> str:
    """Get the path to the font file.

    Checks LED_FONT_PATH environment variable first (takes precedence, no search).
    If not set, searches for the font in common locations.

    Returns:
        Path to the 4x6.bdf font file.

    Raises:
        ConfigError: If font file not found at LED_FONT_PATH or in any search location.
    """
    # Environment variable takes precedence - no search performed
    env_path = os.getenv("LED_FONT_PATH")
    if env_path:
        font_path = Path(env_path)
        if not font_path.exists():
            raise ConfigError(f"Font file not found at LED_FONT_PATH: {font_path}")
        return str(font_path)

    # Search in common locations
    # config.py is at: src/visualizer-display/visualizer_display/config.py
    # (or on Pi: visualizer-display/visualizer_display/config.py)
    project_root = Path(__file__).parent.parent.parent.parent

    search_paths = [
        # Development: sibling to project root (../rpi-rgb-led-matrix/)
        project_root.parent / "rpi-rgb-led-matrix" / "fonts" / "4x6.bdf",
        # Raspberry Pi: home directory (~/rpi-rgb-led-matrix/)
        Path.home() / "rpi-rgb-led-matrix" / "fonts" / "4x6.bdf",
    ]

    for path in search_paths:
        if path.exists():
            return str(path)

    # None found - show helpful error
    searched = "\n".join(f"  - {p}" for p in search_paths)
    raise ConfigError(
        f"Font file not found. Searched locations:\n{searched}\n\n"
        "Please either:\n"
        "  1. Clone rpi-rgb-led-matrix:\n"
        "     git clone https://github.com/hzeller/rpi-rgb-led-matrix.git\n"
        "  2. Set LED_FONT_PATH environment variable to your font file location"
    )


def get_default_assets_path() -> str:
    """Get the path to the bundled assets directory.

    Returns:
        Path to the assets directory containing PNG icons.
    """
    assets_dir = Path(__file__).parent / "assets"

    if not assets_dir.exists():
        raise ConfigError(f"Assets directory not found at: {assets_dir}")

    return str(assets_dir)


@dataclass(frozen=True)
class AWSConfig:
    """AWS IoT Core configuration."""
    endpoint: str
    client_id: str
    topic: str
    cert_path: str
    key_path: str
    root_ca_path: str
    port: int = 8883

    def validate(self) -> None:
        """Validate AWS configuration."""
        if not self.endpoint:
            raise ConfigError("AWS IoT endpoint is required")
        if not self.client_id:
            raise ConfigError("AWS IoT client ID is required")
        if not self.topic:
            raise ConfigError("AWS IoT topic is required")

        # Validate certificate paths exist
        for path, name in [
            (self.cert_path, "Certificate"),
            (self.key_path, "Private key"),
            (self.root_ca_path, "Root CA certificate"),
        ]:
            if not path:
                raise ConfigError(f"{name} path is required")
            if not Path(path).exists():
                raise ConfigError(f"{name} file not found: {path}")


@dataclass(frozen=True)
class MatrixConfig:
    """LED Matrix hardware configuration."""
    rows: int
    cols: int
    parallel: int
    chain_length: int
    brightness: int
    gpio_slowdown: int
    hardware_mapping: str
    disable_hardware_pulsing: bool
    pwm_bits: int
    pwm_lsb_nanoseconds: int
    drop_privileges: bool
    drop_priv_user: str
    drop_priv_group: str

    def validate(self) -> None:
        """Validate matrix configuration."""
        if self.parallel <= 0:
            raise ConfigError("LED_MATRIX_PARALLEL must be positive")
        if self.chain_length <= 0:
            raise ConfigError("LED_MATRIX_CHAIN_LENGTH must be positive")
        if not (0 <= self.brightness <= 100):
            raise ConfigError("LED_MATRIX_BRIGHTNESS must be between 0 and 100")
        if not (0 <= self.gpio_slowdown <= 4):
            raise ConfigError("LED_MATRIX_GPIO_SLOWDOWN must be between 0 and 4")


@dataclass(frozen=True)
class DisplayConfig:
    """Display rendering configuration."""
    font_path: str
    assets_path: str
    outer_margin: int
    rect_height: int
    rect_spacing: int
    title_y_offset: int
    minimum_display_duration: float
    final_linger_duration: float
    update_cycle_frequency: float

    def validate(self) -> None:
        """Validate display configuration."""
        if not Path(self.font_path).exists():
            raise ConfigError(f"Font file not found: {self.font_path}")
        if not Path(self.assets_path).exists():
            raise ConfigError(f"Assets directory not found: {self.assets_path}")
        if self.minimum_display_duration <= 0:
            raise ConfigError("MINIMUM_DISPLAY_DURATION must be positive")
        if self.final_linger_duration <= 0:
            raise ConfigError("FINAL_LINGER_DURATION must be positive")
        if self.update_cycle_frequency <= 0:
            raise ConfigError("UPDATE_CYCLE_FREQUENCY must be positive")


@dataclass(frozen=True)
class AppConfig:
    """Complete application configuration."""
    aws: AWSConfig
    matrix: MatrixConfig
    display: DisplayConfig
    emulator_mode: bool
    log_level: str

    def validate(self) -> None:
        """Validate all configuration."""
        self.aws.validate()
        self.matrix.validate()
        self.display.validate()

        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_log_levels:
            raise ConfigError(f"LOG_LEVEL must be one of: {', '.join(valid_log_levels)}")


def _get_env(key: str, required: bool = True, default: Optional[str] = None) -> str:
    """Get environment variable with error handling.

    Args:
        key: Environment variable name
        required: Whether the variable is required
        default: Default value if not required

    Returns:
        Environment variable value

    Raises:
        ConfigError: If required variable is missing
    """
    value = os.getenv(key, default)
    if required and not value:
        raise ConfigError(f"Required environment variable {key} is not set")
    return value or ""


def _get_int_env(key: str, default: int) -> int:
    """Get integer environment variable with default.

    Args:
        key: Environment variable name
        default: Default value

    Returns:
        Integer value

    Raises:
        ConfigError: If value cannot be parsed as integer
    """
    value = os.getenv(key)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        raise ConfigError(f"{key} must be an integer, got: {value}")


def _get_bool_env(key: str, default: bool) -> bool:
    """Get boolean environment variable with default.

    Args:
        key: Environment variable name
        default: Default value

    Returns:
        Boolean value
    """
    value = os.getenv(key)
    if value is None:
        return default

    return value.lower() in ('true', '1', 'yes', 'on')


def load_aws_config_from_json(config_path: Path) -> AWSConfig:
    """Load AWS IoT configuration from device-config.json.

    Args:
        config_path: Path to device-config.json file

    Returns:
        AWS IoT configuration with resolved certificate paths

    Raises:
        ConfigError: If file is invalid, missing required fields, or paths cannot be resolved
    """
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"Failed to parse device-config.json: {e}\n"
            f"  File location: {config_path}"
        )
    except IOError as e:
        raise ConfigError(f"Failed to read device-config.json: {e}")

    # Extract required top-level fields
    required_fields = {
        'endpoint': data.get('endpoint'),
        'client_id': data.get('client_id'),
        'topic': data.get('topic'),
    }

    # Check for missing top-level fields
    missing = [k for k, v in required_fields.items() if not v]
    if missing:
        raise ConfigError(
            f"device-config.json is missing required fields: {', '.join(missing)}\n"
            f"  File location: {config_path}"
        )

    # Extract certificate paths from nested 'paths' object
    paths = data.get('paths', {})
    cert_fields = {
        'certificate': paths.get('certificate'),
        'private_key': paths.get('private_key'),
        'root_ca': paths.get('root_ca'),
    }

    missing_paths = [k for k, v in cert_fields.items() if not v]
    if missing_paths:
        raise ConfigError(
            f"device-config.json is missing required certificate paths: {', '.join(missing_paths)}\n"
            f"  File location: {config_path}\n"
            f"  Expected in 'paths' object: certificate, private_key, root_ca"
        )

    # Resolve certificate paths relative to config file directory
    config_dir = config_path.parent
    cert_path = str((config_dir / cert_fields['certificate']).resolve())
    key_path = str((config_dir / cert_fields['private_key']).resolve())
    root_ca_path = str((config_dir / cert_fields['root_ca']).resolve())

    # Port is fixed at 8883 (MQTT over TLS)
    port = 8883

    logger.info(f"Loaded AWS IoT configuration from: {config_path}")

    return AWSConfig(
        endpoint=required_fields['endpoint'],
        client_id=required_fields['client_id'],
        topic=required_fields['topic'],
        cert_path=cert_path,
        key_path=key_path,
        root_ca_path=root_ca_path,
        port=port,
    )


def load_config(config_path: Path) -> AppConfig:
    """Load and validate all configuration.

    AWS IoT configuration is loaded from device-config.json.
    Other configuration is loaded from environment variables.

    Args:
        config_path: Path to device-config.json file

    Returns:
        Complete validated application configuration

    Raises:
        ConfigError: If configuration is invalid or incomplete
    """
    # AWS IoT configuration from device-config.json
    aws_config = load_aws_config_from_json(config_path)

    # Matrix hardware configuration
    # Default drop_priv_user/group to SUDO_USER if running under sudo, otherwise current user
    default_priv_user = os.environ.get("SUDO_USER", os.environ.get("USER", "daemon"))
    default_priv_group = os.environ.get("SUDO_USER", os.environ.get("USER", "daemon"))

    matrix_config = MatrixConfig(
        rows=64,
        cols=128,
        parallel=_get_int_env("LED_MATRIX_PARALLEL", 2),
        chain_length=_get_int_env("LED_MATRIX_CHAIN_LENGTH", 1),
        brightness=_get_int_env("LED_MATRIX_BRIGHTNESS", 70),
        gpio_slowdown=_get_int_env("LED_MATRIX_GPIO_SLOWDOWN", 2),
        hardware_mapping=_get_env("LED_MATRIX_HARDWARE_MAPPING", required=False, default="regular"),
        disable_hardware_pulsing=_get_bool_env("LED_MATRIX_DISABLE_HARDWARE_PULSING", True),
        pwm_bits=_get_int_env("LED_MATRIX_PWM_BITS", 11),
        pwm_lsb_nanoseconds=_get_int_env("LED_MATRIX_PWM_LSB_NANOSECONDS", 130),
        drop_privileges=_get_bool_env("LED_MATRIX_DROP_PRIVILEGES", True),
        drop_priv_user=_get_env("LED_MATRIX_DROP_PRIV_USER", required=False, default=default_priv_user),
        drop_priv_group=_get_env("LED_MATRIX_DROP_PRIV_GROUP", required=False, default=default_priv_group),
    )

    # Display rendering configuration
    display_config = DisplayConfig(
        font_path=get_font_path(),
        assets_path=get_default_assets_path(),
        outer_margin=2,
        rect_height=14,
        rect_spacing=2,
        title_y_offset=40,
        minimum_display_duration=float(_get_env("MINIMUM_DISPLAY_DURATION", required=False, default="0.5")),
        final_linger_duration=float(_get_env("FINAL_LINGER_DURATION", required=False, default="10.0")),
        update_cycle_frequency=float(_get_env("UPDATE_CYCLE_FREQUENCY", required=False, default="1.0")),
    )

    # Application configuration
    app_config = AppConfig(
        aws=aws_config,
        matrix=matrix_config,
        display=display_config,
        emulator_mode=_get_bool_env("LED_EMULATOR_MODE", False),
        log_level=_get_env("LOG_LEVEL", required=False, default="INFO").upper(),
    )

    # Validate all configuration
    app_config.validate()

    return app_config
