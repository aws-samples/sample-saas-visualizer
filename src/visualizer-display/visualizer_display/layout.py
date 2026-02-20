"""Static layout coordinates and constants for LED display.

This module contains all static positioning data from the LED_DISPLAY_SPEC.md.
All coordinates are in logical coordinate space (0-127 for both X and Y).
In parallel mode (PARALLEL=2, CHAIN_LENGTH=1), logical coordinates map directly
to physical coordinates - no conversion needed.
"""

from typing import Dict, Tuple

# Display dimensions
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 128

# Component section boundaries (x, y, width, height)
COMPONENT_SECTIONS = {
    'amplify': {'x': 2, 'y': 2, 'width': 124, 'height': 18},
    'apigateway': {'x': 2, 'y': 26, 'width': 124, 'height': 12},
    'siloedsqs': {'x': 2, 'y': 42, 'width': 60, 'height': 20},
    'sharedsqs': {'x': 66, 'y': 42, 'width': 60, 'height': 20},
    'lambda': {'x': 2, 'y': 66, 'width': 124, 'height': 10},
    'rdsproxy': {'x': 2, 'y': 82, 'width': 124, 'height': 10},
    'rds': {'x': 2, 'y': 98, 'width': 124, 'height': 28}
}

# Component icon specifications (filename, x, y, width, height)
COMPONENT_ICONS = {
    'amplify': {'file': 'Amplify.png', 'x': 4, 'y': 6, 'width': 10, 'height': 10},
    'apigateway': {'file': 'APIGateway.png', 'x': 4, 'y': 28, 'width': 8, 'height': 8},
    'siloedsqs': {'file': 'SQS.png', 'x': 4, 'y': 44, 'width': 8, 'height': 8},
    'sharedsqs': {'file': 'SQS.png', 'x': 68, 'y': 44, 'width': 8, 'height': 8},
    'lambda': {'file': 'Lambda.png', 'x': 4, 'y': 67, 'width': 8, 'height': 8},
    'rdsproxy': {'file': 'RDSProxy.png', 'x': 4, 'y': 83, 'width': 8, 'height': 8},
    'rds': {'file': 'RDS.png', 'x': 6, 'y': 102, 'width': 12, 'height': 12}
}

# Component text labels (text, x, y)
# Note: Y coordinates are baselines for text rendering
COMPONENT_LABELS = {
    'amplify': {'text': 'Amplify', 'x': 16, 'y': 13},
    'apigateway': {'text': 'API Gateway', 'x': 16, 'y': 34},
    'siloedsqs': {'text': 'SQS-Siloed', 'x': 16, 'y': 52},
    'sharedsqs': {'text': 'SQS-Shared', 'x': 80, 'y': 52},
    'lambda': {'text': 'Lambda', 'x': 16, 'y': 73},
    'rdsproxy': {'text': 'RDS Proxy', 'x': 16, 'y': 89},
    'rds': {'text': 'RDS', 'x': 6, 'y': 120}
}

# Flow arrows (x, y_start, length, direction)
# Direction: 'down' for vertical arrows, 'horizontal' for horizontal lines
# Arrows positioned to touch but not overlap with cyan borders
FLOW_ARROWS = [
    {'x': 64, 'y_start': 19, 'length': 6, 'direction': 'down'},  # Amplify to API Gateway
    {'x': 64, 'y_start': 37, 'length': 4, 'direction': 'down'},  # API Gateway to SQS Layer
    {'x_start': 62, 'y': 52, 'length': 4, 'direction': 'horizontal'},  # SQS Layer horizontal
    {'x': 64, 'y_start': 75, 'length': 6, 'direction': 'down'},  # Lambda to RDS Proxy
    {'x': 64, 'y_start': 91, 'length': 6, 'direction': 'down'}  # RDS Proxy to RDS
]

# Activity box base positions (where slots start for each component)
# Format: (x, y) tuple
# Positions aligned to avoid text overlap: Amplify/API Gateway/Lambda/RDS Proxy at x=64
# SQS sections aligned with their label starts (x=16 and x=80)
ACTIVITY_BASE_POSITIONS: Dict[str, Tuple[int, int]] = {
    'amplify': (64, 10),      # Aligned vertically with other components
    'apigateway': (64, 30),   # Aligned vertically, to the right of text
    'siloedsqs': (16, 55),    # Aligned with label start
    'sharedsqs': (80, 55),    # Aligned with label start
    'lambda': (64, 70),       # Aligned vertically with other components
    'rdsproxy': (64, 85)      # Aligned vertically with other components
    # RDS uses tenant-specific boxes, not slots
}

# RDS tenant box coordinates (pre-computed from spec grid)
# Each tenant (1-24) has a fixed 10×6 pixel box
# Positioned to the RIGHT of RDS icon/label (icon at x:6-17, label extends to ~x:18)
# Grid starts at x:24 with 2px horizontal spacing and 3px vertical spacing
RDS_BOX_COORDINATES: Dict[str, Tuple[int, int]] = {
    # Row 1 (Y: 100)
    '1': (24, 100), '2': (36, 100), '3': (48, 100), '4': (60, 100),
    '5': (72, 100), '6': (84, 100), '7': (96, 100), '8': (108, 100),
    # Row 2 (Y: 109)
    '9': (24, 109), '10': (36, 109), '11': (48, 109), '12': (60, 109),
    '13': (72, 109), '14': (84, 109), '15': (96, 109), '16': (108, 109),
    # Row 3 (Y: 118)
    '17': (24, 118), '18': (36, 118), '19': (48, 118), '20': (60, 118),
    '21': (72, 118), '22': (84, 118), '23': (96, 118), '24': (108, 118)
}

# Predefined tenant colors (used for RDS tenant box borders)
# When MQTT messages provide tenantcolor, that takes precedence for activity boxes
# Colors match those defined in cfn/cognito-users.template
TENANT_COLORS: Dict[str, Tuple[int, int, int]] = {
    '1': (255, 0, 0),      # #FF0000 - Red
    '2': (0, 255, 0),      # #00FF00 - Green
    '3': (0, 0, 255),      # #0000FF - Blue
    '4': (255, 255, 0),    # #FFFF00 - Yellow
    '5': (255, 0, 255),    # #FF00FF - Magenta
    '6': (0, 255, 255),    # #00FFFF - Cyan
    '7': (128, 0, 0),      # #800000 - Maroon
    '8': (0, 128, 0),      # #008000 - Green
    '9': (0, 0, 128),      # #000080 - Navy
    '10': (128, 128, 0),   # #808000 - Olive
    '11': (128, 0, 128),   # #800080 - Purple
    '12': (0, 128, 128),   # #008080 - Teal
    '13': (255, 69, 0),    # #FF4500 - Orange Red
    '14': (50, 205, 50),   # #32CD32 - Lime Green
    '15': (65, 105, 225),  # #4169E1 - Royal Blue
    '16': (255, 215, 0),   # #FFD700 - Gold
    '17': (218, 112, 214), # #DA70D6 - Orchid
    '18': (64, 224, 208),  # #40E0D0 - Turquoise
    '19': (178, 34, 34),   # #B22222 - Firebrick
    '20': (34, 139, 34),   # #228B22 - Forest Green
    '21': (70, 130, 180),  # #4682B4 - Steel Blue
    '22': (218, 165, 32),  # #DAA520 - Goldenrod
    '23': (147, 112, 219), # #9370DB - Medium Purple
    '24': (72, 209, 204)   # #48D1CC - Medium Turquoise
}

# Standard colors
COLOR_CYAN: Tuple[int, int, int] = (0, 255, 255)  # Borders
COLOR_WHITE: Tuple[int, int, int] = (255, 255, 255)  # Text and arrows

# Display constants
ACTIVITY_BOX_SIZE = 3  # Activity boxes are 3×3 pixels
SLOT_SPACING = 4  # Horizontal spacing between activity box slots
RDS_BOX_WIDTH = 10  # RDS tenant box width
RDS_BOX_HEIGHT = 6  # RDS tenant box height
RDS_ACTIVITY_OFFSET_X = 4  # Offset to center 3×3 activity box within 10×6 tenant box
RDS_ACTIVITY_OFFSET_Y = 2  # Offset to center 3×3 activity box within 10×6 tenant box

def get_rds_activity_position(tenant_id: str) -> Tuple[int, int]:
    """Calculate position for activity box inside tenant's RDS box.

    Args:
        tenant_id: Tenant ID string ("1" through "24")

    Returns:
        (x, y) tuple for top-left corner of 3×3 activity box

    Raises:
        KeyError: If tenant_id not in valid range
    """
    box_x, box_y = RDS_BOX_COORDINATES[tenant_id]
    # Center 3×3 within 10×6 box
    return (box_x + RDS_ACTIVITY_OFFSET_X, box_y + RDS_ACTIVITY_OFFSET_Y)


def get_activity_position(component: str, slot: int) -> Tuple[int, int]:
    """Calculate position for activity box at component slot.

    Args:
        component: Component name (e.g., "apigateway")
        slot: Slot index (0-based)

    Returns:
        (x, y) tuple for top-left corner of 3×3 activity box

    Raises:
        KeyError: If component not in ACTIVITY_BASE_POSITIONS
    """
    base_x, base_y = ACTIVITY_BASE_POSITIONS[component]
    x = base_x + (slot * SLOT_SPACING)
    y = base_y
    return (x, y)
