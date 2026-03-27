"""Application state machine with State Pattern."""

from enum import Enum, auto
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


class AppState(Enum):
    IDLE = auto()
    SELECTING = auto()
    READY = auto()
    COUNTDOWN = auto()
    RECORDING = auto()
    PAUSED = auto()
    PROCESSING = auto()
    PREVIEW = auto()


# Valid state transitions
VALID_TRANSITIONS: dict[AppState, set[AppState]] = {
    AppState.IDLE:       {AppState.SELECTING},
    AppState.SELECTING:  {AppState.READY, AppState.IDLE},
    AppState.READY:      {AppState.COUNTDOWN, AppState.IDLE},
    AppState.COUNTDOWN:  {AppState.RECORDING, AppState.IDLE},
    AppState.RECORDING:  {AppState.PAUSED, AppState.PROCESSING, AppState.IDLE},
    AppState.PAUSED:     {AppState.RECORDING, AppState.PROCESSING, AppState.IDLE},
    AppState.PROCESSING: {AppState.PREVIEW},
    AppState.PREVIEW:    {AppState.IDLE},
}

StateCallback = Callable[[AppState, AppState], None]


class StateMachine:
    """Manages application state transitions with enter/exit callbacks."""

    def __init__(self):
        self._state = AppState.IDLE
        self._on_enter: dict[AppState, list[StateCallback]] = {}
        self._on_exit: dict[AppState, list[StateCallback]] = {}

    @property
    def state(self) -> AppState:
        return self._state

    def on_enter(self, state: AppState, callback: StateCallback):
        """Register a callback for entering a state.
        Callback receives (old_state, new_state)."""
        self._on_enter.setdefault(state, []).append(callback)

    def on_exit(self, state: AppState, callback: StateCallback):
        """Register a callback for exiting a state.
        Callback receives (old_state, new_state)."""
        self._on_exit.setdefault(state, []).append(callback)

    def transition(self, new_state: AppState) -> bool:
        """Transition to a new state. Returns True if successful."""
        old_state = self._state

        if new_state not in VALID_TRANSITIONS.get(old_state, set()):
            logger.warning(
                f"Invalid transition: {old_state.name} -> {new_state.name}"
            )
            return False

        logger.info(f"State: {old_state.name} -> {new_state.name}")

        # Exit callbacks
        for cb in self._on_exit.get(old_state, []):
            cb(old_state, new_state)

        self._state = new_state

        # Enter callbacks
        for cb in self._on_enter.get(new_state, []):
            cb(old_state, new_state)

        return True

    def is_state(self, state: AppState) -> bool:
        return self._state == state
