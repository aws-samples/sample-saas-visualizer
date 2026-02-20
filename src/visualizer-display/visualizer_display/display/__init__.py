"""Display abstraction layer for LED matrix hardware and emulator."""

from .base import MatrixDisplay, CanvasProtocol, Color
from .factory import create_display

__all__ = ["MatrixDisplay", "CanvasProtocol", "Color", "create_display"]
