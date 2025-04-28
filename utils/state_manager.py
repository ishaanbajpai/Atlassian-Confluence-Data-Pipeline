"""
State manager for tracking processed Confluence pages.
"""
import json
import logging
from pathlib import Path

from setup.config import STATE_FILE

logger = logging.getLogger(__name__)

class StateManager:
    """Manages the state of processed Confluence pages."""

    def __init__(self):
        """Initialize the state manager."""
        self.state_file = STATE_FILE
        self.state = self.load_state()

    def load_state(self):
        """Load the state from the state file.

        Returns:
            dict: Current state
        """
        if not self.state_file.exists():
            logger.info(f"State file not found at {self.state_file}. Creating new state.")
            return {}

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)
                logger.info(f"Loaded state for {len(state)} pages")
                return state
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in state file {self.state_file}. Creating new state.")
            return {}
        except Exception as e:
            logger.error(f"Failed to load state file: {e}")
            return {}

    def save_state(self):
        """Save the current state to the state file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
                logger.info(f"Saved state for {len(self.state)} pages")
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    # Keep the old method names as aliases for backward compatibility
    _load_state = load_state
    _save_state = save_state

    def should_process_page(self, page, force_space=None):
        """Check if a page should be processed based on its version and space.

        Args:
            page (dict): Page data from the Confluence API
            force_space (str, optional): If provided, forces processing of all pages in this space

        Returns:
            bool: True if the page should be processed, False otherwise
        """
        page_id = page["id"]
        current_version = page["version"]["number"]
        space_key = page["space"]["key"]

        # If force_space is provided and matches the page's space, process it
        if force_space and space_key == force_space:
            # Still check version to avoid unnecessary processing
            if page_id in self.state and self.state[page_id]["version"] >= current_version:
                logger.info(f"Skipping page '{page['title']}' (ID: {page_id}) in space '{space_key}' - no changes since last processing")
                return False
            return True

        # If page is not in state or version has changed, process it
        if page_id not in self.state or self.state[page_id]["version"] < current_version:
            return True

        logger.info(f"Skipping page '{page['title']}' (ID: {page_id}) - no changes since last processing")
        return False

    def update_page_state(self, page, output_paths):
        """Update the state for a processed page.

        Args:
            page (dict): Page data from the Confluence API
            output_paths (dict): Paths to the generated output files (e.g., {"pdf": "/path/to/file.pdf"})
        """
        page_id = page["id"]

        self.state[page_id] = {
            "title": page["title"],
            "space_key": page["space"]["key"],
            "version": page["version"]["number"],
            "last_modified": page["version"].get("when", ""),
            "output_paths": output_paths
        }

        # Save the updated state
        self.save_state()

    def get_page_state(self, page_id):
        """Get the state for a specific page.

        Args:
            page_id (str): The ID of the page

        Returns:
            dict: Page state or None if not found
        """
        return self.state.get(page_id)
