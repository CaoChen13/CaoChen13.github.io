"""Configuration loading and management."""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import yaml
from dotenv import load_dotenv


class ChannelConfig:
    """Configuration for a single Telegram channel."""

    def __init__(self, username: str, subfolder: str):
        """
        Initialize channel configuration.

        Args:
            username: Telegram channel username (without @)
            subfolder: Subdirectory name for this channel's downloads
        """
        self.username = username
        self.subfolder = subfolder

    def __repr__(self) -> str:
        return f"ChannelConfig(username='{self.username}', subfolder='{self.subfolder}')"


class AppConfig:
    """Main application configuration."""

    def __init__(self, config_data: Dict[str, Any]):
        """
        Initialize application configuration.

        Args:
            config_data: Dictionary containing configuration data
        """
        self.download_root = Path(config_data.get('download_root', './downloads'))
        self.min_file_size_mb = config_data.get('min_file_size_mb', 3)
        self.max_messages_per_channel = config_data.get('max_messages_per_channel', 200)

        # Parse channels
        self.channels: List[ChannelConfig] = []
        for channel_data in config_data.get('channels', []):
            username = channel_data.get('username')
            subfolder = channel_data.get('subfolder')
            if username and subfolder:
                self.channels.append(ChannelConfig(username, subfolder))

        # Telegram credentials from environment
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        self.phone_number = os.getenv('PHONE_NUMBER')

    @property
    def min_file_size_bytes(self) -> int:
        """Get minimum file size in bytes."""
        return int(self.min_file_size_mb * 1024 * 1024)

    def validate(self) -> None:
        """
        Validate configuration.

        Raises:
            ValueError: If configuration is invalid or incomplete
        """
        if not self.api_id:
            raise ValueError("API_ID not found in environment variables. Please check your .env file.")

        if not self.api_hash:
            raise ValueError("API_HASH not found in environment variables. Please check your .env file.")

        if not self.phone_number:
            raise ValueError("PHONE_NUMBER not found in environment variables. Please check your .env file.")

        if not self.channels:
            raise ValueError("No channels configured. Please add at least one channel to your config file.")

        if self.min_file_size_mb < 0:
            raise ValueError("min_file_size_mb must be non-negative.")

        if self.max_messages_per_channel < 1:
            raise ValueError("max_messages_per_channel must be at least 1.")

    def get_channel_by_username(self, username: str) -> ChannelConfig:
        """
        Get channel configuration by username.

        Args:
            username: Channel username

        Returns:
            ChannelConfig object

        Raises:
            ValueError: If channel not found
        """
        for channel in self.channels:
            if channel.username == username:
                return channel
        raise ValueError(f"Channel '{username}' not found in configuration.")


def load_config(config_path: str = 'config.yaml') -> AppConfig:
    """
    Load configuration from YAML file and environment variables.

    Args:
        config_path: Path to the configuration file

    Returns:
        AppConfig object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
    """
    # Load environment variables from .env file
    load_dotenv()

    # Check if config file exists
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please create a config.yaml file. See config.yaml in the project root for an example."
        )

    # Load YAML configuration
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML configuration: {e}")

    if not config_data:
        raise ValueError("Configuration file is empty.")

    # Create and validate configuration
    config = AppConfig(config_data)
    config.validate()

    return config
