"""Abstract base class for LED matrix displays."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Any


@dataclass(frozen=True)
class Color:
    """RGB color representation."""
    red: int
    green: int
    blue: int


class CanvasProtocol(ABC):
    """Protocol for drawing canvas."""

    @abstractmethod
    def SetPixel(self, x: int, y: int, red: int, green: int, blue: int) -> None:
        """Set a single pixel color.

        Args:
            x: X coordinate
            y: Y coordinate
            red: Red component (0-255)
            green: Green component (0-255)
            blue: Blue component (0-255)
        """
        pass

    @abstractmethod
    def Clear(self) -> None:
        """Clear the canvas."""
        pass

    @abstractmethod
    def SetImage(self, image: Any, x: int, y: int) -> None:
        """Draw a PIL Image on the canvas.

        Args:
            image: PIL Image object (must be in RGB mode)
            x: Top-left X coordinate
            y: Top-left Y coordinate
        """
        pass

    @abstractmethod
    def get_native_canvas(self) -> Any:
        """Return the underlying native canvas object.

        Used when direct access to the hardware/emulator canvas is needed
        for operations like DrawText that require the native object.

        Returns:
            The underlying canvas object from rgbmatrix or RGBMatrixEmulator.
        """
        pass


class MatrixDisplay(ABC):
    """Abstract base class for LED matrix displays.

    Provides hardware abstraction for both real hardware and emulator.
    Uses double-buffering pattern for flicker-free updates.
    """

    @abstractmethod
    def get_dimensions(self) -> Tuple[int, int]:
        """Return (width, height) of display.

        Returns:
            Tuple of (width, height) in pixels
        """
        pass

    @abstractmethod
    def create_canvas(self) -> CanvasProtocol:
        """Create an off-screen canvas for drawing.

        Returns:
            Canvas for drawing operations
        """
        pass

    @abstractmethod
    def swap_canvas(self, canvas: CanvasProtocol) -> CanvasProtocol:
        """Swap canvas to display, return new canvas for next frame.

        This implements the double-buffering pattern. The provided canvas
        is displayed, and a new off-screen canvas is returned for the next
        frame to be drawn.

        Args:
            canvas: Canvas to display

        Returns:
            New canvas for next frame
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the display immediately."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Release resources."""
        pass
