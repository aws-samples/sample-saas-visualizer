"""Coordinate conversion for LED matrix displays.

This module provides coordinate conversion between logical layout coordinates
(128×128) and physical panel coordinates, supporting different panel
configurations (parallel vs chained modes).

For parallel=2, chain=1 (vertical stacking in parallel mode):
- Logical and physical coordinates are identical (identity conversion)
- Display: 128×128
- Top panel: Y 0-63, bottom panel: Y 64-127

For parallel=1, chain=2 (vertical stacking in chain mode):
- Logical: 128×128, Physical: 256×64
- Top panel (Y 0-63): maps to physical X 0-127
- Bottom panel (Y 64-127): maps to physical X 128-255 (offset X by 128, Y by -64)
"""

from abc import ABC, abstractmethod
from typing import Tuple, Any, Optional
import logging

from .display.base import CanvasProtocol
from .config import MatrixConfig

logger = logging.getLogger(__name__)


class CoordinateConverter(ABC):
    """Abstract base class for coordinate conversion.

    Converts logical layout coordinates (always 128×128) to physical
    panel coordinates (depends on configuration).
    """

    def __init__(self, config: MatrixConfig):
        """Initialize converter with matrix configuration.

        Args:
            config: Matrix hardware configuration
        """
        self._config = config

    @abstractmethod
    def convert(self, logical_x: int, logical_y: int) -> Tuple[int, int]:
        """Convert logical coordinates to physical coordinates.

        Args:
            logical_x: Logical X coordinate (0-127)
            logical_y: Logical Y coordinate (0-127)

        Returns:
            Tuple of (physical_x, physical_y)
        """
        pass

    @abstractmethod
    def get_physical_dimensions(self) -> Tuple[int, int]:
        """Get physical display dimensions.

        Returns:
            Tuple of (width, height) in pixels
        """
        pass

    @property
    def logical_dimensions(self) -> Tuple[int, int]:
        """Get logical display dimensions (always 128×128).

        Returns:
            Tuple of (width, height) = (128, 128)
        """
        return (128, 128)


class ParallelModeConverter(CoordinateConverter):
    """Identity converter for parallel=2, chain=1 configuration.

    No conversion needed - logical and physical coordinates are identical.
    Used for vertical panel stacking in parallel mode.
    """

    def convert(self, logical_x: int, logical_y: int) -> Tuple[int, int]:
        """Identity conversion - coordinates unchanged.

        Args:
            logical_x: Logical X coordinate (0-127)
            logical_y: Logical Y coordinate (0-127)

        Returns:
            Same coordinates: (logical_x, logical_y)
        """
        return (logical_x, logical_y)

    def get_physical_dimensions(self) -> Tuple[int, int]:
        """Get physical display dimensions.

        For parallel=2, chain=1: 128 × 128

        Returns:
            Tuple of (128, 128)
        """
        return (128, 128)


class ChainModeVerticalConverter(CoordinateConverter):
    """Converter for parallel=1, chain=2 with vertical stacking.

    Converts logical 128×128 space to physical 256×64 space where:
    - Top panel (logical Y 0-63): Physical X 0-127, Y 0-63
    - Bottom panel (logical Y 64-127): Physical X 128-255, Y 0-63

    The panels are physically stacked vertically but chained horizontally
    in the hardware, so the bottom panel appears at X offset 128.
    """

    def convert(self, logical_x: int, logical_y: int) -> Tuple[int, int]:
        """Convert logical to physical coordinates for chained vertical panels.

        Args:
            logical_x: Logical X coordinate (0-127)
            logical_y: Logical Y coordinate (0-127)

        Returns:
            Tuple of (physical_x, physical_y)
        """
        if logical_y < 64:
            # Top panel (Panel 0 in chain)
            # Maps to left side of horizontal chain
            return (logical_x, logical_y)
        else:
            # Bottom panel (Panel 1 in chain)
            # Maps to right side of horizontal chain
            # Offset X by panel width (128), subtract Y offset (64)
            return (logical_x + 128, logical_y - 64)

    def get_physical_dimensions(self) -> Tuple[int, int]:
        """Get physical display dimensions.

        For parallel=1, chain=2: 256 × 64

        Returns:
            Tuple of (256, 64)
        """
        return (256, 64)


class CoordinateConvertingCanvas(CanvasProtocol):
    """Canvas wrapper that applies coordinate conversion transparently.

    Wraps a native canvas and converts all coordinate operations from
    logical (128×128) to physical panel coordinates based on the converter.
    """

    def __init__(self, native_canvas: CanvasProtocol, converter: CoordinateConverter):
        """Initialize canvas wrapper.

        Args:
            native_canvas: Underlying hardware/emulator canvas
            converter: Coordinate converter to use
        """
        self._canvas = native_canvas
        self._converter = converter
        self._logical_width, self._logical_height = converter.logical_dimensions
        self._physical_width, self._physical_height = converter.get_physical_dimensions()

    def SetPixel(self, x: int, y: int, red: int, green: int, blue: int) -> None:
        """Set pixel with coordinate conversion.

        Args:
            x: Logical X coordinate
            y: Logical Y coordinate
            red: Red component (0-255)
            green: Green component (0-255)
            blue: Blue component (0-255)
        """
        # Bounds check logical coordinates
        if not (0 <= x < self._logical_width and 0 <= y < self._logical_height):
            return  # Out of logical bounds, skip silently

        # Convert to physical coordinates
        phys_x, phys_y = self._converter.convert(x, y)

        # Bounds check physical coordinates
        if not (0 <= phys_x < self._physical_width and 0 <= phys_y < self._physical_height):
            logger.debug(f"Physical coords out of bounds: ({phys_x}, {phys_y}) from logical ({x}, {y})")
            return

        # Set pixel on native canvas
        self._canvas.SetPixel(phys_x, phys_y, red, green, blue)

    def Clear(self) -> None:
        """Clear the canvas."""
        self._canvas.Clear()

    def SetImage(self, image: Any, x: int, y: int) -> None:
        """Draw image pixel-by-pixel with coordinate conversion.

        Args:
            image: PIL Image object (RGB mode)
            x: Top-left logical X coordinate
            y: Top-left logical Y coordinate
        """
        # Get image dimensions and pixels
        width, height = image.size
        pixels = image.load()

        # Draw each pixel with coordinate conversion
        for py in range(height):
            for px in range(width):
                logical_x = x + px
                logical_y = y + py

                # Get pixel color
                pixel = pixels[px, py]
                if isinstance(pixel, tuple) and len(pixel) >= 3:
                    r, g, b = pixel[0], pixel[1], pixel[2]
                else:
                    logger.warning(f"Unexpected pixel format at ({px}, {py}): {pixel}")
                    continue

                # Set pixel with conversion
                self.SetPixel(logical_x, logical_y, r, g, b)

    def get_native_canvas(self) -> Any:
        """Return the underlying native canvas.

        Used for operations like DrawText that need direct access
        to the hardware/emulator canvas.

        Returns:
            The wrapped native canvas
        """
        return self._canvas.get_native_canvas()

    def convert_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Convert logical coordinates to physical coordinates.

        Args:
            x: Logical X coordinate
            y: Logical Y coordinate

        Returns:
            Tuple of (physical_x, physical_y)
        """
        return self._converter.convert(x, y)


def create_coordinate_converter(config: MatrixConfig) -> CoordinateConverter:
    """Factory function to create appropriate coordinate converter.

    Detects matrix configuration and returns the correct converter:
    - parallel=2, chain=1: ParallelModeConverter (identity)
    - parallel=1, chain=2: ChainModeVerticalConverter (vertical stacking)

    Args:
        config: Matrix hardware configuration

    Returns:
        Appropriate CoordinateConverter instance

    Raises:
        ValueError: If configuration is not supported
    """
    if config.parallel == 2 and config.chain_length == 1:
        logger.info("Using ParallelModeConverter (identity conversion)")
        return ParallelModeConverter(config)
    elif config.parallel == 1 and config.chain_length == 2:
        logger.info("Using ChainModeVerticalConverter (vertical stacking in chain mode)")
        return ChainModeVerticalConverter(config)
    else:
        raise ValueError(
            f"Unsupported matrix configuration: parallel={config.parallel}, "
            f"chain_length={config.chain_length}. "
            f"Supported configurations: "
            f"(parallel=2, chain=1) for vertical parallel mode, "
            f"(parallel=1, chain=2) for vertical chain mode."
        )
