"""Display rendering logic for SaaS architecture visualization.

This module handles all drawing operations for the LED display:
- Static layout: component borders, icons, labels, arrows, RDS tenant boxes
- Dynamic activity: transaction activity boxes at component positions
- Thread-safe: Works with transaction snapshots from TransactionManager
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

from .display.base import MatrixDisplay, CanvasProtocol, Color
from .config import DisplayConfig, MatrixConfig
from . import layout
from .coordinate_converter import create_coordinate_converter, CoordinateConvertingCanvas

logger = logging.getLogger(__name__)

# Lazy import of graphics module - will be loaded when Renderer is instantiated
_graphics: Optional[Any] = None


def _get_graphics():
    """Lazy load graphics module.

    Returns:
        graphics module from either rgbmatrix or RGBMatrixEmulator

    Raises:
        ImportError: If neither library is installed
    """
    global _graphics
    if _graphics is not None:
        return _graphics

    try:
        from rgbmatrix import graphics
        _graphics = graphics
        return graphics
    except ImportError:
        pass

    try:
        from RGBMatrixEmulator import graphics
        _graphics = graphics
        return graphics
    except ImportError:
        pass

    raise ImportError(
        "Neither rpi-rgb-led-matrix nor RGBMatrixEmulator is installed. "
        "See docs/hardware-setup.md or docs/development.md for installation instructions."
    )


@dataclass
class TransactionSnapshot:
    """Snapshot of a transaction for rendering.

    Passed from TransactionManager to avoid holding locks during rendering.
    """
    transaction_key: str
    tenant_id: str
    color: Tuple[int, int, int]
    current_position: str
    slot: Optional[int]


class Renderer:
    """Renders SaaS architecture visualization using double-buffering."""

    def __init__(self, display: MatrixDisplay, config: DisplayConfig, matrix_config: MatrixConfig):
        """Initialize renderer.

        Args:
            display: Matrix display instance
            config: Display rendering configuration
            matrix_config: Matrix hardware configuration
        """
        self._display = display
        self._config = config
        self._matrix_config = matrix_config

        # Create coordinate converter based on matrix configuration
        self._converter = create_coordinate_converter(matrix_config)

        # Use logical dimensions for bounds checking (always 128×128)
        self._width, self._height = self._converter.logical_dimensions

        self._graphics = _get_graphics()

        # Load font
        self._font = self._graphics.Font()
        self._font.LoadFont(config.font_path)
        logger.info(f"Loaded font from: {config.font_path}")

        # Load PNG icon images
        self._icons: Dict[str, Any] = {}
        self._load_assets()

        logger.info(f"Renderer initialized with {type(self._converter).__name__}")

    def _load_assets(self) -> None:
        """Load PNG icons from assets directory.

        Loads all component icons and stores them for rendering.
        Uses PIL to load PNG files and convert to format suitable for display.
        """
        try:
            from PIL import Image
        except ImportError:
            logger.error("PIL (Pillow) not installed. Cannot load PNG icons.")
            logger.error("See docs/hardware-setup.md for installation instructions.")
            return

        assets_dir = Path(self._config.assets_path)

        for component, icon_spec in layout.COMPONENT_ICONS.items():
            icon_file = icon_spec['file']
            icon_path = assets_dir / icon_file

            if not icon_path.exists():
                logger.warning(f"Icon not found: {icon_path}")
                continue

            try:
                # Load and convert image
                img = Image.open(icon_path)

                # Resize if needed to match spec dimensions
                target_width = icon_spec['width']
                target_height = icon_spec['height']
                if img.size != (target_width, target_height):
                    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                self._icons[component] = img
                logger.debug(f"Loaded icon: {component} from {icon_file}")

            except Exception as e:
                logger.error(f"Failed to load icon {icon_file}: {e}")

    def render_frame(self, canvas: CanvasProtocol,
                     transactions: Optional[List[TransactionSnapshot]] = None) -> None:
        """Render complete frame to canvas.

        Draws static layout (borders, icons, labels, arrows, RDS boxes) and
        dynamic transaction activity boxes.

        Args:
            canvas: Canvas to draw on
            transactions: List of transaction snapshots to render (optional)
        """
        # Wrap canvas with coordinate conversion
        converting_canvas = CoordinateConvertingCanvas(canvas, self._converter)

        converting_canvas.Clear()

        # Draw static layout every frame
        self._draw_static_layout(converting_canvas)

        # Draw active transactions
        if transactions:
            for tx in transactions:
                self._draw_transaction(converting_canvas, tx)

    def _draw_static_layout(self, canvas: CanvasProtocol) -> None:
        """Draw all static elements of the display.

        This includes:
        - Component section borders (cyan)
        - Component icons (PNG images)
        - Component labels (white text)
        - Flow arrows (white with arrowheads)
        - RDS tenant boxes (colored borders)
        """
        # Draw component borders
        for component, section in layout.COMPONENT_SECTIONS.items():
            self._draw_rectangle_border(
                canvas,
                section['x'], section['y'],
                section['width'], section['height'],
                layout.COLOR_CYAN
            )

        # Draw component icons
        for component, icon_spec in layout.COMPONENT_ICONS.items():
            if component in self._icons:
                self._draw_icon(
                    canvas,
                    self._icons[component],
                    icon_spec['x'], icon_spec['y']
                )

        # Draw component labels
        for component, label_spec in layout.COMPONENT_LABELS.items():
            self._draw_text(
                canvas,
                label_spec['text'],
                label_spec['x'], label_spec['y'],
                layout.COLOR_WHITE
            )

        # Draw flow arrows
        for arrow in layout.FLOW_ARROWS:
            if arrow['direction'] == 'down':
                self._draw_vertical_arrow(
                    canvas,
                    arrow['x'], arrow['y_start'],
                    arrow['length'],
                    layout.COLOR_WHITE
                )
            elif arrow['direction'] == 'horizontal':
                self._draw_horizontal_line(
                    canvas,
                    arrow['x_start'], arrow['y'],
                    arrow['length'],
                    layout.COLOR_WHITE
                )

        # Draw RDS tenant boxes
        self._draw_rds_tenant_boxes(canvas)

    def _draw_rectangle_border(self, canvas: CanvasProtocol,
                               x: int, y: int, width: int, height: int,
                               color: Tuple[int, int, int]) -> None:
        """Draw rectangle border (outline only).

        Args:
            canvas: Canvas to draw on
            x: Top-left X coordinate
            y: Top-left Y coordinate
            width: Rectangle width in pixels
            height: Rectangle height in pixels
            color: RGB tuple (r, g, b)
        """
        # Top and bottom horizontal lines
        for i in range(width):
            px = x + i
            if 0 <= px < self._width:
                # Top edge
                if 0 <= y < self._height:
                    canvas.SetPixel(px, y, color[0], color[1], color[2])
                # Bottom edge
                py = y + height - 1
                if 0 <= py < self._height:
                    canvas.SetPixel(px, py, color[0], color[1], color[2])

        # Left and right vertical lines
        for j in range(height):
            py = y + j
            if 0 <= py < self._height:
                # Left edge
                if 0 <= x < self._width:
                    canvas.SetPixel(x, py, color[0], color[1], color[2])
                # Right edge
                px = x + width - 1
                if 0 <= px < self._width:
                    canvas.SetPixel(px, py, color[0], color[1], color[2])

    def _draw_icon(self, canvas: CanvasProtocol, image: Any, x: int, y: int) -> None:
        """Draw PNG icon on canvas using native SetImage method.

        Args:
            canvas: Canvas to draw on
            image: PIL Image object (RGB mode)
            x: Top-left X coordinate
            y: Top-left Y coordinate
        """
        logger.debug(f"Drawing icon at ({x}, {y}), size: {image.size}, mode: {image.mode}")
        canvas.SetImage(image, x, y)

    def _draw_text(self, canvas: CanvasProtocol, text: str,
                   x: int, y: int, color: Tuple[int, int, int]) -> None:
        """Draw text on canvas.

        Args:
            canvas: Canvas to draw on (CoordinateConvertingCanvas)
            text: Text to draw
            x: X coordinate (left edge) in logical coordinates
            y: Y coordinate (baseline) in logical coordinates
            color: RGB tuple (r, g, b)
        """
        # Convert logical coordinates to physical coordinates
        phys_x, phys_y = canvas.convert_coordinates(x, y)

        graphics_color = self._graphics.Color(color[0], color[1], color[2])
        self._graphics.DrawText(canvas.get_native_canvas(), self._font, phys_x, phys_y, graphics_color, text)

    def _draw_vertical_arrow(self, canvas: CanvasProtocol,
                            x: int, y_start: int, length: int,
                            color: Tuple[int, int, int]) -> None:
        """Draw vertical arrow pointing down with arrowhead.

        Args:
            canvas: Canvas to draw on
            x: X coordinate of arrow line
            y_start: Y coordinate of arrow start
            length: Length of arrow in pixels
            color: RGB tuple (r, g, b)
        """
        # Draw vertical line
        for y in range(y_start + 1, y_start + length):
            if 0 <= x < self._width and 0 <= y < self._height:
                canvas.SetPixel(x, y, color[0], color[1], color[2])

        # Draw arrowhead (3 pixels: center and two diagonal)
        y_tip = y_start + length
        if 0 <= y_tip < self._height:
            # Center
            if 0 <= x < self._width:
                canvas.SetPixel(x, y_tip, color[0], color[1], color[2])
            # Left diagonal
            if 0 <= x - 1 < self._width and 0 <= y_tip - 1 < self._height:
                canvas.SetPixel(x - 1, y_tip - 1, color[0], color[1], color[2])
            # Right diagonal
            if 0 <= x + 1 < self._width and 0 <= y_tip - 1 < self._height:
                canvas.SetPixel(x + 1, y_tip - 1, color[0], color[1], color[2])

    def _draw_horizontal_line(self, canvas: CanvasProtocol,
                             x_start: int, y: int, length: int,
                             color: Tuple[int, int, int]) -> None:
        """Draw horizontal line.

        Args:
            canvas: Canvas to draw on
            x_start: Starting X coordinate
            y: Y coordinate
            length: Length of line in pixels
            color: RGB tuple (r, g, b)
        """
        for x in range(x_start, x_start + length + 1):
            if 0 <= x < self._width and 0 <= y < self._height:
                canvas.SetPixel(x, y, color[0], color[1], color[2])

    def _draw_rds_tenant_boxes(self, canvas: CanvasProtocol) -> None:
        """Draw all 24 RDS tenant boxes with colored borders.

        Each tenant gets a 10×6 pixel box with a colored border from the
        predefined tenant color map.
        """
        for tenant_id in range(1, 25):
            tenant_key = str(tenant_id)
            if tenant_key in layout.RDS_BOX_COORDINATES:
                box_x, box_y = layout.RDS_BOX_COORDINATES[tenant_key]
                color = layout.TENANT_COLORS.get(tenant_key, layout.COLOR_WHITE)

                self._draw_rectangle_border(
                    canvas,
                    box_x, box_y,
                    layout.RDS_BOX_WIDTH, layout.RDS_BOX_HEIGHT,
                    color
                )

    def _draw_transaction(self, canvas: CanvasProtocol,
                         tx: TransactionSnapshot) -> None:
        """Draw activity box for a single transaction.

        Args:
            canvas: Canvas to draw on
            tx: Transaction snapshot with position and color info
        """
        current_component = tx.current_position

        # Calculate position for activity box
        if current_component == 'rds':
            # Special RDS handling - use tenant-specific box
            try:
                x, y = layout.get_rds_activity_position(tx.tenant_id)
            except KeyError:
                logger.warning(f"Invalid tenant_id for RDS: {tx.tenant_id}")
                return
        else:
            # Standard slot-based positioning
            if tx.slot is None:
                logger.warning(f"Transaction {tx.transaction_key} has no slot allocated")
                return

            try:
                x, y = layout.get_activity_position(current_component, tx.slot)
            except KeyError:
                logger.warning(f"Invalid component for activity: {current_component}")
                return

        # Draw 3×3 activity box
        self._draw_solid_box(canvas, x, y, layout.ACTIVITY_BOX_SIZE, tx.color)

    def _draw_solid_box(self, canvas: CanvasProtocol,
                       x: int, y: int, size: int,
                       color: Tuple[int, int, int]) -> None:
        """Draw solid filled square box.

        Args:
            canvas: Canvas to draw on
            x: Top-left X coordinate
            y: Top-left Y coordinate
            size: Box size (width and height)
            color: RGB tuple (r, g, b)
        """
        for i in range(size):
            for j in range(size):
                px = x + i
                py = y + j
                if 0 <= px < self._width and 0 <= py < self._height:
                    canvas.SetPixel(px, py, color[0], color[1], color[2])
