"""InstaRecApp - Top-level application controller."""

import sys
import logging
import customtkinter as ctk
from state import StateMachine, AppState
from config import AppConfig
from ui.main_toolbar import MainToolbar
from ui.selection_overlay import SelectionOverlay
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


class InstaRecApp(ctk.CTk):
    """Root application window (hidden). Manages state and UI components."""

    def __init__(self):
        super().__init__()

        # Setup
        setup_logging()
        logger.info("InstaRec starting")

        ctk.set_appearance_mode("dark")

        # Hide root window - MainToolbar is the visible UI
        self.withdraw()

        # Config & State
        self.config = AppConfig.load()
        self.state_machine = StateMachine()

        # Recording state
        self._selected_region = None

        # Register state callbacks
        self._register_state_callbacks()

        # Create main toolbar
        self.toolbar = MainToolbar(
            self,
            on_new=self._on_new,
            on_quit=self._on_quit,
        )

        logger.info("InstaRec ready (IDLE)")

    def _register_state_callbacks(self):
        sm = self.state_machine

        sm.on_enter(AppState.SELECTING, self._enter_selecting)
        sm.on_enter(AppState.IDLE, self._enter_idle)
        sm.on_enter(AppState.READY, self._enter_ready)

    def _enter_idle(self, old_state, new_state):
        """Return to idle - show toolbar, cleanup."""
        self.toolbar.set_enabled(True)
        self.toolbar.deiconify()
        self._selected_region = None
        logger.info("Returned to IDLE")

    def _enter_selecting(self, old_state, new_state):
        """Start region selection overlay."""
        self.toolbar.set_enabled(False)
        self.toolbar.withdraw()

        self._overlay = SelectionOverlay(
            master=self,
            on_confirmed=self._on_selection_confirmed,
            on_cancelled=self._on_selection_cancelled,
        )
        self._overlay.show()
        logger.info("Entering SELECTING")

    def _on_selection_confirmed(self, region):
        """Called when user confirms a selection region."""
        self._selected_region = region
        self._overlay = None
        logger.info(f"Selection confirmed: {region}")
        self.state_machine.transition(AppState.READY)

    def _on_selection_cancelled(self):
        """Called when user cancels selection."""
        self._overlay = None
        logger.info("Selection cancelled")
        self.state_machine.transition(AppState.IDLE)

    def _enter_ready(self, old_state, new_state):
        """Selection confirmed - show toolbar and wait for recording start."""
        self.toolbar.set_enabled(True)
        self.toolbar.deiconify()
        logger.info(f"READY: region={self._selected_region}")

    def _on_new(self):
        """Handle 'New' button click."""
        self.state_machine.transition(AppState.SELECTING)

    def _on_quit(self):
        """Handle quit request."""
        logger.info("InstaRec shutting down")
        self.config.save()
        self.toolbar.destroy()
        self.quit()
        sys.exit()

    def mainloop(self, *args, **kwargs):
        """Override to handle clean shutdown."""
        try:
            super().mainloop(*args, **kwargs)
        except KeyboardInterrupt:
            self._on_quit()
