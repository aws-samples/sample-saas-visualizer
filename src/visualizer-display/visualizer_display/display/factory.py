"""Factory for creating display instances."""

from .base import MatrixDisplay
from ..config import AppConfig


def create_display(config: AppConfig) -> MatrixDisplay:
    """Create appropriate display based on configuration.

    Args:
        config: Application configuration

    Returns:
        MatrixDisplay instance (hardware or emulator)

    Raises:
        ImportError: If required display library is not installed
    """
    if config.emulator_mode:
        from .emulator import EmulatorDisplay
        return EmulatorDisplay(config.matrix)
    else:
        from .hardware import HardwareDisplay
        return HardwareDisplay(config.matrix)
