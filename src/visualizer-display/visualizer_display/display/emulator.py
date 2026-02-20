"""Emulator implementation using RGBMatrixEmulator."""

from typing import Tuple, Any

try:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
except ImportError:
    raise ImportError(
        "RGBMatrixEmulator not installed. "
        "See docs/development.md for installation instructions."
    )

from .base import MatrixDisplay, CanvasProtocol
from ..config import MatrixConfig


class EmulatorCanvas(CanvasProtocol):
    """Wrapper for emulator canvas."""

    def __init__(self, canvas):
        """Initialize emulator canvas wrapper.

        Args:
            canvas: Native RGBMatrixEmulator canvas object
        """
        self._canvas = canvas

    def SetPixel(self, x: int, y: int, red: int, green: int, blue: int) -> None:
        """Set a single pixel color."""
        self._canvas.SetPixel(x, y, red, green, blue)

    def Clear(self) -> None:
        """Clear the canvas."""
        self._canvas.Clear()

    def SetImage(self, image: Any, x: int, y: int) -> None:
        """Draw a PIL Image using emulator method.

        Args:
            image: PIL Image object (must be in RGB mode)
            x: Top-left X coordinate
            y: Top-left Y coordinate
        """
        self._canvas.SetImage(image, x, y)

    def get_native_canvas(self) -> Any:
        """Return the underlying native canvas object."""
        return self._canvas


class EmulatorDisplay(MatrixDisplay):
    """Emulator display using RGBMatrixEmulator.

    Provides same double-buffering API as hardware for consistent behavior.
    """

    def __init__(self, config: MatrixConfig):
        """Initialize emulator display.

        Args:
            config: Matrix hardware configuration
        """
        options = RGBMatrixOptions()
        options.rows = config.rows
        options.cols = config.cols
        options.chain_length = config.chain_length
        options.parallel = config.parallel

        self._matrix = RGBMatrix(options=options)
        self._width = config.cols * config.chain_length
        self._height = config.rows * config.parallel

    def get_dimensions(self) -> Tuple[int, int]:
        """Return (width, height) of display."""
        return (self._width, self._height)

    def create_canvas(self) -> CanvasProtocol:
        """Create off-screen canvas.

        Returns:
            Off-screen canvas for drawing
        """
        return EmulatorCanvas(self._matrix.CreateFrameCanvas())

    def swap_canvas(self, canvas: CanvasProtocol) -> CanvasProtocol:
        """Swap canvas to display.

        Args:
            canvas: Canvas to display

        Returns:
            New canvas for next frame
        """
        if not isinstance(canvas, EmulatorCanvas):
            raise TypeError("canvas must be an EmulatorCanvas instance")

        new_canvas = self._matrix.SwapOnVSync(canvas._canvas)
        return EmulatorCanvas(new_canvas)

    def clear(self) -> None:
        """Clear the display immediately."""
        self._matrix.Clear()

    def cleanup(self) -> None:
        """Release resources."""
        self._matrix.Clear()
