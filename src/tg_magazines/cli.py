"""Command-line interface for the Telegram magazine downloader."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .config import load_config
from .downloader import TelegramDownloader


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the application.

    Args:
        verbose: If True, enable debug logging
    """
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Set log level
    log_level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler (simplified format)
            logging.StreamHandler(sys.stdout),
            # File handler (detailed format)
            logging.FileHandler(
                log_dir / 'tg_magazines.log',
                encoding='utf-8'
            )
        ]
    )

    # Simplify console output format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        logging.Formatter('%(levelname)s: %(message)s')
    )

    # Get root logger and update console handler
    logger = logging.getLogger()
    logger.handlers[0] = console_handler


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='Download PDF magazines from Telegram channels',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Download from all configured channels
  %(prog)s --config my_config.yaml           # Use custom config file
  %(prog)s --channel newscientistmag         # Only process specific channel
  %(prog)s --dry-run                         # Preview what would be downloaded
  %(prog)s --verbose                         # Enable detailed logging

Configuration:
  1. Copy .env.example to .env and fill in your Telegram credentials
  2. Edit config.yaml to add channels you want to monitor
  3. Run the script and authenticate on first use
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--channel',
        type=str,
        help='Process only this channel (username without @)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate downloads without actually downloading files'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging (debug level)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )

    return parser.parse_args()


async def async_main() -> int:
    """
    Async main function.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    # Parse command-line arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        logger.info(f"Loading configuration from: {args.config}")
        config = load_config(args.config)

        logger.info(f"Configuration loaded successfully")
        logger.info(f"Download root: {config.download_root}")
        logger.info(f"Configured channels: {len(config.channels)}")

        if args.dry_run:
            logger.info("DRY RUN MODE: No files will be downloaded")

        # Create and run downloader
        downloader = TelegramDownloader(config, dry_run=args.dry_run)
        await downloader.run(channel_filter=args.channel)

        logger.info("All done!")
        return 0

    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


def main() -> int:
    """
    Main entry point for the CLI.

    Returns:
        Exit code
    """
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130


if __name__ == '__main__':
    sys.exit(main())
