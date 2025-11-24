"""
Telegram Magazine Downloader

A command-line tool to automatically download PDF magazines from Telegram channels.
"""

__version__ = '1.0.0'
__author__ = 'Your Name'
__license__ = 'MIT'

from .cli import main
from .config import load_config, AppConfig, ChannelConfig
from .downloader import TelegramDownloader
from .state import StateManager, ChannelState

__all__ = [
    'main',
    'load_config',
    'AppConfig',
    'ChannelConfig',
    'TelegramDownloader',
    'StateManager',
    'ChannelState',
]
