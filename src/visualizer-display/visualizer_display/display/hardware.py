"""Real hardware implementation using rpi-rgb-led-matrix."""

from typing import Tuple, Any

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:
    raise ImportError(
        "rpi-rgb-led-matrix not installed. "
        "See docs/hardware-setup.md for installation instructions."
    )

from .base import MatrixDisplay, CanvasProtocol
from ..config import MatrixConfig


class HardwareCanvas(CanvasProtocol):
    """Wrapper for hardware canvas."""

    def __init__(self, canvas):
        """Initialize hardware canvas wrapper.

        Args:
            canvas: Native RGBMatrix canvas object
        """
        self._canvas = canvas

    def SetPixel(self, x: int, y: int, red: int, green: int, blue: int) -> None:
        """Set a single pixel color."""
        self._canvas.SetPixel(x, y, red, green, blue)

    def Clear(self) -> None:
        """Clear the canvas."""
        self._canvas.Clear()

    def SetImage(self, image: Any, x: int, y: int) -> None:
        """Draw a PIL Image using native hardware method.

        Args:
            image: PIL Image object (must be in RGB mode)
            x: Top-left X coordinate
            y: Top-left Y coordinate
        """
        try:
            # Check if SetImage method exists
            if hasattr(self._canvas, 'SetImage'):
                self._canvas.SetImage(image, x, y)
            else:
                # Fallback: manual pixel-by-pixel rendering
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("Canvas does not have SetImage method, using pixel-by-pixel fallback")
                width, height = image.size
                pixels = image.load()
                for py in range(height):
                    for px in range(width):
                        r, g, b = pixels[px, py]
                        self._canvas.SetPixel(x + px, y + py, r, g, b)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in SetImage: {e}", exc_info=True)

    def get_native_canvas(self) -> Any:
        """Return the underlying native canvas object."""
        return self._canvas


class HardwareDisplay(MatrixDisplay):
    """Hardware display using rpi-rgb-led-matrix.

    Implements double-buffering using CreateFrameCanvas() and SwapOnVSync()
    for flicker-free display updates.
    """

    def __init__(self, config: MatrixConfig):
        """Initialize hardware display.

        Args:
            config: Matrix hardware configuration
        """
        options = RGBMatrixOptions()
        options.rows = config.rows
        options.cols = config.cols
        options.chain_length = config.chain_length
        options.parallel = config.parallel
        options.brightness = config.brightness
        options.gpio_slowdown = config.gpio_slowdown
        options.hardware_mapping = config.hardware_mapping
        options.disable_hardware_pulsing = config.disable_hardware_pulsing
        options.pwm_bits = config.pwm_bits
        options.pwm_lsb_nanoseconds = config.pwm_lsb_nanoseconds

        # Privilege dropping configuration
        # By default, drops to SUDO_USER (the user who ran sudo)
        options.drop_privileges = config.drop_privileges
        if config.drop_privileges:
            options.drop_priv_user = config.drop_priv_user
            options.drop_priv_group = config.drop_priv_group

        self._matrix = RGBMatrix(options=options)
        self._width = config.cols * config.chain_length
        self._height = config.rows * config.parallel

    def get_dimensions(self) -> Tuple[int, int]:
        """Return (width, height) of display."""
        return (self._width, self._height)

    def create_canvas(self) -> CanvasProtocol:
        """Create off-screen canvas for double-buffering.

        Returns:
            Off-screen canvas for drawing
        """
        return HardwareCanvas(self._matrix.CreateFrameCanvas())

    def swap_canvas(self, canvas: CanvasProtocol) -> CanvasProtocol:
        """Atomically swap canvas - prevents flickering.

        Args:
            canvas: Canvas to display

        Returns:
            New canvas for next frame
        """
        if not isinstance(canvas, HardwareCanvas):
            raise TypeError("canvas must be a HardwareCanvas instance")

        new_canvas = self._matrix.SwapOnVSync(canvas._canvas)
        return HardwareCanvas(new_canvas)

    def clear(self) -> None:
        """Clear the display immediately."""
        self._matrix.Clear()

    def cleanup(self) -> None:
        """Release resources."""
        self._matrix.Clear()
