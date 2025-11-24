"""Utility functions for the telegram magazine downloader."""

import re
from pathlib import Path
from typing import Optional


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.

    Args:
        filename: The original filename

    Returns:
        A sanitized filename safe for use on most filesystems
    """
    # Replace problematic characters with underscores
    # Windows forbidden: < > : " / \ | ? *
    # Also handle other potentially problematic characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')

    # Replace multiple consecutive underscores with a single one
    sanitized = re.sub(r'_+', '_', sanitized)

    # Ensure filename is not empty
    if not sanitized:
        sanitized = 'unnamed_file'

    # Limit length to 255 characters (common filesystem limit)
    if len(sanitized) > 255:
        name_part = Path(sanitized).stem[:200]
        ext_part = Path(sanitized).suffix
        sanitized = f"{name_part}{ext_part}"

    return sanitized


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string (e.g., "4.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def ensure_directory(path: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory
    """
    path.mkdir(parents=True, exist_ok=True)


def get_file_extension(filename: str) -> Optional[str]:
    """
    Get the file extension from a filename.

    Args:
        filename: The filename

    Returns:
        The extension (including the dot) or None if no extension
    """
    path = Path(filename)
    return path.suffix if path.suffix else None
