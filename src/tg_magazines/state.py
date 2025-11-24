"""State management for tracking processed messages."""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ChannelState:
    """Manages state for a single channel."""

    def __init__(self, channel_username: str, state_dir: Path = Path('state')):
        """
        Initialize channel state.

        Args:
            channel_username: Telegram channel username
            state_dir: Directory to store state files
        """
        self.channel_username = channel_username
        self.state_dir = state_dir
        self.state_file = state_dir / f"{channel_username}.json"
        self.last_message_id: Optional[int] = None

        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Load existing state if available
        self._load_state()

    def _load_state(self) -> None:
        """Load state from file if it exists."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.last_message_id = data.get('last_message_id')
                    logger.debug(
                        f"Loaded state for {self.channel_username}: "
                        f"last_message_id={self.last_message_id}"
                    )
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    f"Failed to load state for {self.channel_username}: {e}. "
                    f"Starting fresh."
                )
                self.last_message_id = None
        else:
            logger.debug(f"No existing state found for {self.channel_username}")

    def save_state(self) -> None:
        """Save current state to file."""
        try:
            data = {
                'last_message_id': self.last_message_id,
                'channel_username': self.channel_username
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug(
                f"Saved state for {self.channel_username}: "
                f"last_message_id={self.last_message_id}"
            )
        except IOError as e:
            logger.error(f"Failed to save state for {self.channel_username}: {e}")

    def update_last_message_id(self, message_id: int) -> None:
        """
        Update the last processed message ID.

        Args:
            message_id: The ID of the last processed message
        """
        if self.last_message_id is None or message_id > self.last_message_id:
            self.last_message_id = message_id
            logger.debug(f"Updated last_message_id for {self.channel_username} to {message_id}")

    def should_process_message(self, message_id: int) -> bool:
        """
        Check if a message should be processed based on current state.

        Args:
            message_id: Message ID to check

        Returns:
            True if message should be processed, False otherwise
        """
        if self.last_message_id is None:
            return True
        return message_id > self.last_message_id

    def reset(self) -> None:
        """Reset state (useful for re-downloading all files)."""
        self.last_message_id = None
        if self.state_file.exists():
            self.state_file.unlink()
            logger.info(f"Reset state for {self.channel_username}")


class StateManager:
    """Manages state for all channels."""

    def __init__(self, state_dir: Path = Path('state')):
        """
        Initialize state manager.

        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = state_dir
        self.states: dict[str, ChannelState] = {}

    def get_channel_state(self, channel_username: str) -> ChannelState:
        """
        Get or create state for a channel.

        Args:
            channel_username: Telegram channel username

        Returns:
            ChannelState object
        """
        if channel_username not in self.states:
            self.states[channel_username] = ChannelState(channel_username, self.state_dir)
        return self.states[channel_username]

    def save_all(self) -> None:
        """Save state for all channels."""
        for state in self.states.values():
            state.save_state()
