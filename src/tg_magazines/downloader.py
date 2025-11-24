"""Telegram PDF downloader core functionality."""

import logging
from pathlib import Path
from typing import Optional
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeFilename, Message

from .config import AppConfig, ChannelConfig
from .state import StateManager, ChannelState
from .utils import sanitize_filename, format_file_size, ensure_directory

logger = logging.getLogger(__name__)


class DownloadStats:
    """Statistics for a download session."""

    def __init__(self):
        self.downloaded = 0
        self.skipped_exists = 0
        self.skipped_small = 0
        self.skipped_not_pdf = 0
        self.errors = 0

    def __str__(self) -> str:
        return (
            f"Downloaded: {self.downloaded}, "
            f"Skipped (exists): {self.skipped_exists}, "
            f"Skipped (too small): {self.skipped_small}, "
            f"Skipped (not PDF): {self.skipped_not_pdf}, "
            f"Errors: {self.errors}"
        )


class TelegramDownloader:
    """Handles downloading PDFs from Telegram channels."""

    def __init__(self, config: AppConfig, dry_run: bool = False):
        """
        Initialize the downloader.

        Args:
            config: Application configuration
            dry_run: If True, only simulate downloads without actually downloading
        """
        self.config = config
        self.dry_run = dry_run
        self.state_manager = StateManager()
        self.client: Optional[TelegramClient] = None

    async def initialize(self) -> None:
        """Initialize the Telegram client and connect."""
        logger.info("Initializing Telegram client...")

        self.client = TelegramClient(
            'tg_magazines',
            int(self.config.api_id),
            self.config.api_hash
        )

        await self.client.start(phone=self.config.phone_number)

        if await self.client.is_user_authorized():
            me = await self.client.get_me()
            logger.info(f"Logged in as: {me.first_name} (@{me.username})")
        else:
            raise RuntimeError("Failed to authorize with Telegram")

    async def close(self) -> None:
        """Close the Telegram client connection."""
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram client disconnected")

    def _get_filename_from_message(self, message: Message) -> Optional[str]:
        """
        Extract filename from a Telegram message.

        Args:
            message: Telegram message object

        Returns:
            Filename if found, None otherwise
        """
        if not message.document:
            return None

        # Try to get filename from document attributes
        for attr in message.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                return attr.file_name

        # Fallback: generate filename from message ID and mime type
        if message.document.mime_type:
            ext = message.document.mime_type.split('/')[-1]
            return f"document_{message.id}.{ext}"

        return f"document_{message.id}"

    def _is_pdf_document(self, message: Message) -> bool:
        """
        Check if a message contains a PDF document.

        Args:
            message: Telegram message object

        Returns:
            True if message contains a PDF, False otherwise
        """
        if not message.document:
            return False

        mime_type = message.document.mime_type or ""
        return 'pdf' in mime_type.lower()

    def _meets_size_requirement(self, message: Message) -> bool:
        """
        Check if document meets minimum size requirement.

        Args:
            message: Telegram message object

        Returns:
            True if document is large enough, False otherwise
        """
        if not message.document:
            return False

        return message.document.size >= self.config.min_file_size_bytes

    async def _download_file(
        self,
        message: Message,
        destination: Path
    ) -> bool:
        """
        Download a file from a message.

        Args:
            message: Telegram message containing the file
            destination: Path where file should be saved

        Returns:
            True if download succeeded, False otherwise
        """
        try:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would download to: {destination}")
                return True

            logger.info(f"Downloading: {destination.name} ({format_file_size(message.document.size)})")
            await self.client.download_media(message, str(destination))
            logger.info(f"Successfully downloaded: {destination.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to download {destination.name}: {e}")
            return False

    async def process_channel(
        self,
        channel: ChannelConfig,
        limit_messages: Optional[int] = None
    ) -> DownloadStats:
        """
        Process a single channel and download new PDFs.

        Args:
            channel: Channel configuration
            limit_messages: Override for max messages to check (for first run)

        Returns:
            DownloadStats object with statistics
        """
        stats = DownloadStats()
        logger.info(f"Processing channel: @{channel.username}")

        # Get channel state
        state = self.state_manager.get_channel_state(channel.username)

        # Prepare download directory
        download_dir = self.config.download_root / channel.subfolder
        ensure_directory(download_dir)

        try:
            # Get the channel entity
            entity = await self.client.get_entity(channel.username)
            logger.info(f"Found channel: {entity.title}")

            # Determine message limit
            if state.last_message_id is None:
                msg_limit = limit_messages or self.config.max_messages_per_channel
                logger.info(f"First run for this channel, checking last {msg_limit} messages")
            else:
                msg_limit = None  # Get all new messages
                logger.info(f"Checking for messages newer than ID {state.last_message_id}")

            # Iterate through messages
            message_count = 0
            async for message in self.client.iter_messages(entity, limit=msg_limit):
                message_count += 1

                # Skip if already processed
                if not state.should_process_message(message.id):
                    continue

                # Check if it's a PDF document
                if not self._is_pdf_document(message):
                    stats.skipped_not_pdf += 1
                    continue

                # Check file size
                if not self._meets_size_requirement(message):
                    size_mb = message.document.size / (1024 * 1024)
                    logger.debug(
                        f"Skipping small file ({size_mb:.2f} MB): "
                        f"message ID {message.id}"
                    )
                    stats.skipped_small += 1
                    state.update_last_message_id(message.id)
                    continue

                # Get filename
                filename = self._get_filename_from_message(message)
                if not filename:
                    logger.warning(f"Could not determine filename for message ID {message.id}")
                    continue

                # Sanitize filename and prepare destination path
                safe_filename = sanitize_filename(filename)
                destination = download_dir / safe_filename

                # Check if file already exists
                if destination.exists():
                    logger.debug(f"File already exists, skipping: {safe_filename}")
                    stats.skipped_exists += 1
                    state.update_last_message_id(message.id)
                    continue

                # Download the file
                success = await self._download_file(message, destination)

                if success:
                    stats.downloaded += 1
                    state.update_last_message_id(message.id)
                else:
                    stats.errors += 1

            logger.info(f"Processed {message_count} messages from @{channel.username}")
            logger.info(f"Stats for @{channel.username}: {stats}")

            # Save state after processing channel
            state.save_state()

        except ValueError as e:
            logger.error(f"Channel not found: @{channel.username} - {e}")
            stats.errors += 1
        except Exception as e:
            logger.error(f"Error processing channel @{channel.username}: {e}")
            stats.errors += 1

        return stats

    async def run(self, channel_filter: Optional[str] = None) -> None:
        """
        Run the downloader for all configured channels or a specific one.

        Args:
            channel_filter: If specified, only process this channel
        """
        await self.initialize()

        try:
            # Filter channels if requested
            if channel_filter:
                try:
                    channels = [self.config.get_channel_by_username(channel_filter)]
                    logger.info(f"Processing only channel: @{channel_filter}")
                except ValueError as e:
                    logger.error(str(e))
                    return
            else:
                channels = self.config.channels
                logger.info(f"Processing {len(channels)} channel(s)")

            # Process each channel
            total_stats = DownloadStats()
            for channel in channels:
                stats = await self.process_channel(channel)

                # Aggregate stats
                total_stats.downloaded += stats.downloaded
                total_stats.skipped_exists += stats.skipped_exists
                total_stats.skipped_small += stats.skipped_small
                total_stats.skipped_not_pdf += stats.skipped_not_pdf
                total_stats.errors += stats.errors

            # Final summary
            logger.info("=" * 60)
            logger.info("Download session completed")
            logger.info(f"Total stats: {total_stats}")
            logger.info("=" * 60)

        finally:
            await self.close()
