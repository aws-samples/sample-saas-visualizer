"""Thread-safe transaction state management.

Manages all active transactions, slot allocation, and provides thread-safe
access patterns for both MQTT message handler (write) and renderer (read).
"""

import threading
import time
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .renderer import TransactionSnapshot

logger = logging.getLogger(__name__)


@dataclass
class TransactionState:
    """State for a single transaction."""
    transaction_id: str
    tenant_id: str  # "1" through "24"
    color: Tuple[int, int, int]  # RGB tuple from hex conversion
    current_message_positions: List[str]  # Positions from current message being displayed
    current_position_index: int  # Index within current message (0-based)
    message_queue: List[List[str]]  # Queue of pending messages (each is position array)
    display_start_time: float  # When current position started displaying
    is_lingering: bool  # True after completing all messages
    linger_start_time: Optional[float]  # When linger started
    is_active: bool  # True during animation/linger
    slot: Optional[int]  # Allocated display slot
    slot_component: Optional[str]  # Component owning current slot


# Valid component positions for transactions
VALID_POSITIONS = frozenset({
    'amplify', 'apigateway', 'siloedsqs', 'sharedsqs',
    'lambda', 'rdsproxy', 'rds'
})


class TransactionManager:
    """Thread-safe manager for all active transactions.

    Handles:
    - Adding new transactions from MQTT messages
    - Updating transaction state (advancing positions, timers)
    - Slot allocation and release for component display
    - Providing thread-safe snapshots for rendering
    """

    def __init__(self,
                 minimum_display_duration: float = 0.5,
                 final_linger_duration: float = 10.0):
        """Initialize transaction manager with message-queue timing.

        Args:
            minimum_display_duration: Min time to show each position (seconds)
            final_linger_duration: Time to linger at final position (seconds)
        """
        self._lock = threading.Lock()
        self._transactions: Dict[str, TransactionState] = {}
        self._minimum_display_duration = minimum_display_duration
        self._final_linger_duration = final_linger_duration

        # Slot tracking per component (excluding RDS which uses tenant boxes)
        self._component_slots: Dict[str, List[Optional[str]]] = {
            'amplify': [],
            'apigateway': [],
            'siloedsqs': [],
            'sharedsqs': [],
            'lambda': [],
            'rdsproxy': []
            # RDS doesn't use slots - uses tenant-specific boxes
        }

        logger.info(f"TransactionManager initialized "
                   f"(min_display={minimum_display_duration}s, linger={final_linger_duration}s)")

    def add_transaction(self, payload: dict) -> None:
        """Add new transaction or queue new message for existing transaction.

        Processes entire position array from each message:
        - If transaction NEW: creates state with message as current positions
        - If transaction EXISTS: queues the entire message (position array)
        - If lingering: reactivates transaction and queues message

        Thread-safe: Can be called from MQTT callback thread.

        Args:
            payload: MQTT message payload with keys:
                - TransactionId: Unique transaction identifier
                - tenantid: Tenant ID string ("1" through "24")
                - tenantcolor: Hex color string (e.g., "#FF0000")
                - position: List of component names (new/next segments)
                - timestamp: Message timestamp (not used currently)
        """
        try:
            # Extract required fields
            transaction_id = payload['TransactionId']
            tenant_id = payload['tenantid']
            tenantcolor_hex = payload['tenantcolor']
            position_array = payload['position']

            # Validate position array
            if not position_array or len(position_array) == 0:
                logger.warning(f"Empty position array in message: {payload}")
                return

            # Validate all positions are known components
            invalid_positions = [p for p in position_array if p not in VALID_POSITIONS]
            if invalid_positions:
                logger.warning(f"Invalid positions in message: {invalid_positions}. "
                             f"Valid positions are: {sorted(VALID_POSITIONS)}")
                return

            transaction_key = tenant_id + transaction_id

            # Parse hex color to RGB
            try:
                color = self._hex_to_rgb(tenantcolor_hex)
            except ValueError as e:
                logger.warning(f"Invalid color '{tenantcolor_hex}': {e}")
                return

            current_time = time.time()

            with self._lock:
                if transaction_key in self._transactions:
                    # EXISTING transaction - queue the entire message
                    state = self._transactions[transaction_key]

                    # Queue the entire position array as a message
                    state.message_queue.append(position_array.copy())

                    logger.debug(f"Queued message for {transaction_key} "
                               f"(positions: {position_array}, queue depth: {len(state.message_queue)})")

                    # Reactivate if lingering
                    if state.is_lingering:
                        state.is_lingering = False
                        state.linger_start_time = None
                        logger.info(f"Reactivated lingering transaction: {transaction_key}")

                else:
                    # NEW transaction - create state with first message
                    first_position = position_array[0]

                    state = TransactionState(
                        transaction_id=transaction_id,
                        tenant_id=tenant_id,
                        color=color,
                        current_message_positions=position_array.copy(),
                        current_position_index=0,
                        message_queue=[],
                        display_start_time=current_time,
                        is_lingering=False,
                        linger_start_time=None,
                        is_active=True,
                        slot=None,
                        slot_component=None
                    )

                    self._transactions[transaction_key] = state

                    # Allocate initial slot for first position (if not RDS)
                    if first_position != 'rds':
                        slot = self._allocate_slot(first_position, transaction_key)
                        if slot is not None:
                            state.slot = slot
                            state.slot_component = first_position
                            logger.debug(f"Allocated initial slot {slot} at {first_position} for {transaction_key}")

                    logger.info(f"Created transaction: {transaction_key} "
                              f"(tenant={tenant_id}, message_positions={position_array})")

        except KeyError as e:
            logger.error(f"Missing required field in MQTT payload: {e}")
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")

    def update_all_transactions(self) -> None:
        """Process all active transactions.

        Called at high frequency (20Hz from render loop):
        - Advances through positions in current message
        - When message complete, loads next queued message
        - Enters linger when all messages processed
        - Handles slot allocation/release during position changes

        Thread-safe: Acquires lock for entire update.
        """
        current_time = time.time()

        with self._lock:
            transaction_keys = list(self._transactions.keys())

            for key in transaction_keys:
                if key not in self._transactions:
                    continue

                state = self._transactions[key]

                # Cleanup inactive transactions
                if not state.is_active:
                    self._cleanup_transaction(key, state)
                    continue

                # LINGER PHASE
                if state.is_lingering:
                    # Check for new messages (reactivation)
                    if state.message_queue:
                        # New message arrived during linger - load it
                        self._load_next_message(key, state, current_time)
                        logger.debug(f"Transaction {key} exited linger (loaded new message)")
                        continue

                    # Check linger expiration
                    linger_elapsed = current_time - state.linger_start_time
                    if linger_elapsed >= self._final_linger_duration:
                        state.is_active = False
                        logger.debug(f"Transaction {key} linger expired, marking for cleanup")
                        continue

                    # Still lingering - do nothing, keep rendering at final position
                    continue

                # ACTIVE PHASE - Playing current message
                time_at_position = current_time - state.display_start_time

                if time_at_position >= self._minimum_display_duration:
                    # Ready to advance to next position in current message
                    old_index = state.current_position_index
                    old_position = state.current_message_positions[old_index]

                    # Advance index
                    state.current_position_index += 1
                    state.display_start_time = current_time

                    # Check if current message is complete
                    if state.current_position_index >= len(state.current_message_positions):
                        # Message complete
                        logger.debug(f"Transaction {key} completed message at position {len(state.current_message_positions)}")

                        # Check if more messages queued
                        if state.message_queue:
                            # Load next message
                            self._load_next_message(key, state, current_time)
                        else:
                            # No more messages - enter linger
                            state.is_lingering = True
                            state.linger_start_time = current_time
                            # Reset index to last position for rendering during linger
                            state.current_position_index = len(state.current_message_positions) - 1
                            logger.debug(f"Transaction {key} entering linger at '{state.current_message_positions[-1]}'")
                    else:
                        # Still within current message - handle slot changes
                        new_position = state.current_message_positions[state.current_position_index]

                        # Handle slot reallocation if component changed
                        if old_position != new_position:
                            # Release old slot (if not RDS)
                            if old_position != 'rds' and state.slot is not None and state.slot_component is not None:
                                self._release_slot(state.slot_component, state.slot)
                                logger.debug(f"Released slot {state.slot} at {state.slot_component} for {key}")
                                state.slot = None
                                state.slot_component = None

                            # Allocate new slot (if not RDS)
                            if new_position != 'rds':
                                new_slot = self._allocate_slot(new_position, key)
                                if new_slot is not None:
                                    state.slot = new_slot
                                    state.slot_component = new_position
                                    logger.debug(f"Allocated slot {new_slot} at {new_position} for {key}")
                                else:
                                    logger.warning(f"Could not allocate slot for {key} at {new_position}")

                        logger.debug(f"Transaction {key} advanced to position {state.current_position_index}/{len(state.current_message_positions)}: '{new_position}'")

    def _load_next_message(self, transaction_key: str,
                           state: TransactionState,
                           current_time: float) -> None:
        """Load next message from queue and start displaying it.

        Must be called with lock held.

        Handles:
        - Slot release at current position
        - Pop next message from queue (FIFO)
        - Reset to start of new message
        - Slot allocation for first position

        Args:
            transaction_key: Transaction identifier
            state: Transaction state
            current_time: Current timestamp
        """
        # Release current slot (if allocated)
        if state.slot is not None and state.slot_component is not None:
            # Get current position (may be last of previous message or mid-message)
            if state.current_position_index < len(state.current_message_positions):
                old_position = state.current_message_positions[state.current_position_index]
            else:
                old_position = state.current_message_positions[-1]

            if old_position != 'rds':
                self._release_slot(state.slot_component, state.slot)
                logger.debug(f"Released slot {state.slot} at {state.slot_component} for {transaction_key}")
            state.slot = None
            state.slot_component = None

        # Pop next message from queue
        next_message = state.message_queue.pop(0)
        state.current_message_positions = next_message
        state.current_position_index = 0
        state.display_start_time = current_time
        state.is_lingering = False
        state.linger_start_time = None

        # Allocate slot for first position (if not RDS)
        first_position = next_message[0]
        if first_position != 'rds':
            slot = self._allocate_slot(first_position, transaction_key)
            if slot is not None:
                state.slot = slot
                state.slot_component = first_position
                logger.debug(f"Allocated slot {slot} at {first_position} for {transaction_key}")
            else:
                logger.warning(f"Could not allocate slot for {transaction_key} at {first_position}")

        logger.info(f"Transaction {transaction_key} loaded next message: {next_message} "
                   f"(queue remaining: {len(state.message_queue)})")

    def get_active_transactions(self) -> List[TransactionSnapshot]:
        """Get snapshot of all active transactions for rendering.

        Thread-safe: Acquires lock briefly to copy transaction data.
        Called at 20 Hz by renderer.

        Returns:
            List of TransactionSnapshot objects (safe to use without lock)
        """
        with self._lock:
            snapshots = []

            for key, state in self._transactions.items():
                if not state.is_active:
                    continue

                # Calculate current position from index
                # Ensure index is within bounds (important during linger)
                index = min(state.current_position_index, len(state.current_message_positions) - 1)
                current_position = state.current_message_positions[index]

                # Create snapshot
                snapshot = TransactionSnapshot(
                    transaction_key=key,
                    tenant_id=state.tenant_id,
                    color=state.color,
                    current_position=current_position,
                    slot=state.slot
                )
                snapshots.append(snapshot)

            return snapshots

    def _allocate_slot(self, component: str, transaction_key: str) -> Optional[int]:
        """Allocate display slot for transaction at component.

        Must be called with lock held.

        Args:
            component: Component name (e.g., "apigateway")
            transaction_key: Transaction identifier

        Returns:
            Slot index (0-based), or None if no slots available
        """
        if component not in self._component_slots:
            logger.warning(f"Unknown component for slot allocation: {component}")
            return None

        slots = self._component_slots[component]
        max_safe_slots = self._calculate_max_slots(component)

        # Find first empty (None) slot within bounds
        for i, occupant in enumerate(slots):
            if occupant is None and i < max_safe_slots:
                slots[i] = transaction_key
                logger.debug(f"Allocated slot {i} for {transaction_key} at {component}")
                return i

        # No empty slots - try to append new slot (with bounds check)
        slot_index = len(slots)
        if slot_index >= max_safe_slots:
            logger.warning(
                f"Component {component} at max slots ({max_safe_slots}). "
                f"Cannot allocate slot for {transaction_key}. Transaction will not be rendered."
            )
            # Return None - transaction will be skipped for rendering
            return None

        slots.append(transaction_key)
        logger.debug(f"Created new slot {slot_index} for {transaction_key} at {component}")
        return slot_index

    def _release_slot(self, component: str, slot: int) -> None:
        """Release display slot when transaction completes.

        Must be called with lock held.

        Args:
            component: Component name
            slot: Slot index to release
        """
        if component not in self._component_slots:
            return

        slots = self._component_slots[component]

        if 0 <= slot < len(slots):
            slots[slot] = None
            logger.debug(f"Released slot {slot} at {component}")
            self._compact_slots(component)  # Compact after releasing

    def _compact_slots(self, component: str) -> None:
        """Remove trailing None values from slot list.

        Prevents unbounded growth while preserving low slot indices for reuse.
        Must be called with lock held.

        Args:
            component: Component name
        """
        if component not in self._component_slots:
            return

        slots = self._component_slots[component]

        # Trim trailing None values
        while slots and slots[-1] is None:
            slots.pop()

        logger.debug(f"Compacted {component} slots to length {len(slots)}")

    def _calculate_max_slots(self, component: str) -> int:
        """Calculate maximum safe slot index for component.

        Based on component boundaries to ensure activity boxes don't render
        outside component boundaries.

        Args:
            component: Component name

        Returns:
            Maximum number of slots that fit within component bounds
        """
        from . import layout

        if component not in layout.ACTIVITY_BASE_POSITIONS:
            return 50  # Fallback for unknown components

        if component not in layout.COMPONENT_SECTIONS:
            return 50  # Fallback for unknown components

        base_x, _ = layout.ACTIVITY_BASE_POSITIONS[component]
        section = layout.COMPONENT_SECTIONS[component]
        section_max_x = section['x'] + section['width']

        # Calculate available width
        available_width = section_max_x - base_x

        # Calculate max slots (subtract box size to ensure last box fits completely)
        max_slots = (available_width - layout.ACTIVITY_BOX_SIZE) // layout.SLOT_SPACING

        return max(1, max_slots)  # At least 1 slot

    def _cleanup_transaction(self, transaction_key: str, state: TransactionState) -> None:
        """Remove completed transaction and release resources.

        Must be called with lock held.

        Args:
            transaction_key: Unique transaction identifier
            state: Final transaction state
        """
        # Release slot if allocated
        if state.slot is not None and state.slot_component is not None:
            # Additional safety check: verify the slot is within bounds
            slots = self._component_slots.get(state.slot_component, [])
            if state.slot < len(slots):
                self._release_slot(state.slot_component, state.slot)
                logger.debug(f"Released slot {state.slot} at {state.slot_component} during cleanup")
            else:
                logger.warning(f"Slot {state.slot} out of bounds for {state.slot_component} (len={len(slots)})")

        # Remove transaction
        if transaction_key in self._transactions:
            del self._transactions[transaction_key]
            logger.info(f"Cleaned up transaction: {transaction_key}")

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color string to RGB tuple.

        Args:
            hex_color: Hex color with or without # prefix (e.g., "#FF0000")

        Returns:
            Tuple of (red, green, blue) values 0-255

        Raises:
            ValueError: If hex_color is invalid format
        """
        # Remove # prefix if present
        hex_color = hex_color.lstrip('#')

        # Validate length
        if len(hex_color) != 6:
            raise ValueError(f"Hex color must be 6 characters, got {len(hex_color)}")

        # Convert hex to integers
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except ValueError as e:
            raise ValueError(f"Invalid hex color format: {hex_color}") from e

        return (r, g, b)

    def get_stats(self) -> dict:
        """Get statistics about current state.

        Returns:
            Dictionary with statistics about active transactions and slots
        """
        with self._lock:
            slot_details = {}
            for component, slots in self._component_slots.items():
                occupied = sum(1 for s in slots if s is not None)
                max_safe = self._calculate_max_slots(component)
                slot_details[component] = {
                    'total': len(slots),
                    'occupied': occupied,
                    'max_safe': max_safe,
                    'utilization': f"{occupied}/{max_safe}",
                    'overflow_risk': len(slots) >= max_safe
                }

            return {
                'active_transactions': len(self._transactions),
                'slot_details': slot_details
            }

    def verify_slot_consistency(self) -> dict:
        """Verify slot allocations match active transactions.

        Returns:
            Dictionary with consistency report including:
            - consistent: True if all slots match active transactions
            - issues: List of inconsistency descriptions
            - active_transactions: Count of active transactions
            - allocated_slots: Count of slots that should be allocated
        """
        with self._lock:
            issues = []

            # Build map of which transactions should own which slots
            expected_slots = {}
            for key, state in self._transactions.items():
                if state.slot is not None and state.slot_component is not None:
                    comp_slot = f"{state.slot_component}:{state.slot}"
                    if comp_slot in expected_slots:
                        issues.append(
                            f"Multiple transactions claim {comp_slot}: "
                            f"{expected_slots[comp_slot]} and {key}"
                        )
                    expected_slots[comp_slot] = key

            # Check actual slots match expected
            for component, slots in self._component_slots.items():
                for i, occupant in enumerate(slots):
                    comp_slot = f"{component}:{i}"
                    if occupant is not None:
                        if comp_slot not in expected_slots:
                            issues.append(
                                f"Slot {comp_slot} occupied by {occupant} "
                                f"but no active transaction owns it"
                            )
                        elif expected_slots[comp_slot] != occupant:
                            issues.append(
                                f"Slot {comp_slot} has {occupant} "
                                f"but expected {expected_slots[comp_slot]}"
                            )

            return {
                'consistent': len(issues) == 0,
                'issues': issues,
                'active_transactions': len(self._transactions),
                'allocated_slots': len(expected_slots)
            }
