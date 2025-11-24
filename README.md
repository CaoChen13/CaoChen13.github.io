# Telegram Magazine Downloader

A Python command-line tool to automatically download PDF magazines from public Telegram channels. Ideal for collecting magazines like *The Economist*, *New Scientist*, and other publications shared on Telegram.

## Features

- 📥 **Automated Downloads**: Automatically download PDF files from configured Telegram channels
- 🎯 **Smart Filtering**: Skip files below minimum size threshold (to avoid ads and small documents)
- 📁 **Organized Storage**: Save files to channel-specific folders for easy organization
- 🔄 **Incremental Updates**: Track processed messages to avoid re-downloading existing files
- 🚫 **Duplicate Prevention**: Skip files that already exist locally
- 🔍 **Dry Run Mode**: Preview what would be downloaded without actually downloading
- 📊 **Detailed Statistics**: View download statistics and logs for each session
- 🔧 **Flexible Configuration**: YAML-based configuration for easy customization

## Requirements

- Python 3.8 or higher
- A Telegram account
- Telegram API credentials (API ID and API Hash)

## Installation

### 1. Clone or Download This Repository

```bash
git clone <repository-url>
cd tg-pdf-downloader
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Or create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Get Telegram API Credentials

1. Visit https://my.telegram.org/apps
2. Log in with your phone number
3. Click on "API development tools"
4. Fill out the form to create a new application
   - App title: `Magazine Downloader` (or any name)
   - Short name: `mag_dl` (or any name)
   - Platform: Select "Desktop"
5. You'll receive:
   - **api_id**: A numeric value (e.g., 12345678)
   - **api_hash**: A 32-character hexadecimal string

### 4. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your Telegram credentials:

```env
API_ID=12345678
API_HASH=0123456789abcdef0123456789abcdef
PHONE_NUMBER=+1234567890
```

**Important**:
- Replace the values with your actual credentials
- Include country code in phone number (e.g., `+1` for US, `+86` for China)
- The `.env` file is ignored by git and will not be committed

### 5. Configure Channels

Edit `config.yaml` to specify which channels to monitor:

```yaml
# Root directory where all magazines will be downloaded
download_root: "./downloads"  # Or "D:/Magazines" on Windows

# Minimum file size in MB (files smaller than this are ignored)
min_file_size_mb: 3

# Maximum messages to check per channel on first run
max_messages_per_channel: 200

# Channels to monitor
channels:
  - username: "newscientistmag"      # Channel username (without @)
    subfolder: "NewScientist"         # Local folder name

  - username: "economistpdfs"
    subfolder: "TheEconomist"

  # Add more channels here
```

**Finding Channel Usernames**:
- Channel URL format: `https://t.me/channel_username`
- Use the part after `t.me/` as the username
- Example: For `https://t.me/economistpdfs`, use `economistpdfs`

## Usage

### Basic Usage

Run the downloader for all configured channels:

```bash
python -m tg_magazines
```

On first run, you'll be prompted to enter the verification code sent to your Telegram account.

### Command-Line Options

```bash
# Use a custom config file
python -m tg_magazines --config my_config.yaml

# Process only a specific channel
python -m tg_magazines --channel newscientistmag

# Preview what would be downloaded (dry run)
python -m tg_magazines --dry-run

# Enable verbose logging
python -m tg_magazines --verbose

# Combine options
python -m tg_magazines --channel economistpdfs --dry-run --verbose
```

### Command Reference

| Option | Description |
|--------|-------------|
| `--config PATH` | Path to configuration file (default: `config.yaml`) |
| `--channel USERNAME` | Process only this channel (useful for testing) |
| `--dry-run` | Simulate downloads without actually downloading files |
| `--verbose` or `-v` | Enable detailed debug logging |
| `--version` | Show version information |
| `--help` or `-h` | Show help message |

## Project Structure

```
tg-pdf-downloader/
├── src/
│   └── tg_magazines/          # Main package
│       ├── __init__.py        # Package initialization
│       ├── __main__.py        # Entry point for python -m
│       ├── cli.py             # Command-line interface
│       ├── config.py          # Configuration loading
│       ├── state.py           # State management
│       ├── downloader.py      # Core download logic
│       └── utils.py           # Utility functions
├── state/                     # State files (auto-created)
│   └── *.json                 # Per-channel state files
├── logs/                      # Log files (auto-created)
│   └── tg_magazines.log       # Detailed logs
├── downloads/                 # Downloaded files (auto-created)
│   ├── NewScientist/          # Channel-specific folders
│   └── TheEconomist/
├── .env                       # Your credentials (DO NOT COMMIT)
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
├── config.yaml                # Your configuration
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## How It Works

1. **Authentication**: On first run, authenticates with Telegram using your credentials
2. **Session Management**: Stores session locally (no need to re-authenticate)
3. **Channel Scanning**: For each configured channel:
   - Reads the last processed message ID from state file
   - Fetches new messages since last run
   - Filters messages for PDF documents
   - Checks file size requirements
   - Downloads new PDFs to channel-specific folders
4. **State Tracking**: Updates state files after each successful download
5. **Logging**: Records all operations to console and log file

## Integration with Calibre

This tool is designed to work seamlessly with [Calibre](https://calibre-ebook.com/)'s "Add books from directories" feature:

1. Install Calibre
2. In Calibre preferences, go to **Adding books** → **Automatic adding**
3. Add the `download_root` directory (e.g., `D:/Magazines`) as a watched folder
4. Configure Calibre to:
   - Monitor the folder for new files
   - Automatically import new PDFs
   - Optionally delete files after import

**Result**: New magazines downloaded by this tool will automatically appear in your Calibre library!

## Configuration Reference

### `config.yaml` Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `download_root` | string | Root directory for downloads | `./downloads` |
| `min_file_size_mb` | number | Minimum file size in MB | `3` |
| `max_messages_per_channel` | number | Max messages to check on first run | `200` |
| `channels` | list | List of channel configurations | `[]` |
| `channels[].username` | string | Telegram channel username | required |
| `channels[].subfolder` | string | Local folder name for this channel | required |

### Environment Variables (`.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `API_ID` | Telegram API ID | `12345678` |
| `API_HASH` | Telegram API hash | `0123456789abcdef...` |
| `PHONE_NUMBER` | Your phone number with country code | `+1234567890` |

## Troubleshooting

### "API_ID not found in environment variables"

Make sure you have:
1. Created a `.env` file (copy from `.env.example`)
2. Added your credentials to `.env`
3. The `.env` file is in the same directory where you run the command

### "Channel not found"

- Verify the channel username is correct (check the URL)
- Ensure the channel is public (not private)
- Try accessing the channel in Telegram first to confirm it exists

### "Failed to authorize with Telegram"

- Check your phone number format (include country code with `+`)
- Verify API_ID and API_HASH are correct
- Try deleting `tg_magazines.session` and re-authenticating

### Files Not Downloading

- Check the `min_file_size_mb` setting (files below this size are skipped)
- Use `--verbose` to see detailed logs
- Check `logs/tg_magazines.log` for error messages
- Try `--dry-run` to see what would be downloaded

### Permission Errors

- Ensure you have write permissions for `download_root`, `state/`, and `logs/` directories
- On Windows, avoid using system directories or folders requiring admin rights

## Logging

Logs are written to two locations:

1. **Console**: Summary information (INFO level by default)
2. **File**: Detailed logs in `logs/tg_magazines.log` (includes DEBUG information)

Use `--verbose` flag to see DEBUG logs in console as well.

## State Management

State files in `state/` directory track the last processed message ID for each channel:

```json
{
  "last_message_id": 123456789,
  "channel_username": "newscientistmag"
}
```

To re-download all files from a channel:
1. Delete the corresponding state file (e.g., `state/newscientistmag.json`)
2. Run the tool again

## Security & Privacy

- **Credentials**: Never commit `.env` to version control
- **Session Files**: The `*.session` files contain authentication tokens - keep them secure
- **Public Channels Only**: This tool is designed for public channels only
- **Local Only**: Runs entirely on your computer, no data sent to third parties

## Limitations

- Only works with **public** Telegram channels
- Only downloads **PDF** files (other document types are ignored)
- Requires manual authentication on first run
- Does not support private groups or restricted channels

## Future Enhancements (TODO)

These features are planned but not yet implemented:

- [ ] **Date-based Filenames**: Automatically prefix files with download date (e.g., `2025-11-24_Economist.pdf`)
- [ ] **AI Integration**: Extract table of contents and generate summaries using LLMs
- [ ] **Keyword Filtering**: Exclude files containing specific keywords in filename
- [ ] **Multiple Format Support**: Support EPUB, MOBI, and other ebook formats
- [ ] **Web Dashboard**: Simple web UI for monitoring and configuration
- [ ] **Notification System**: Email or push notifications for new downloads
- [ ] **Cloud Storage**: Automatically upload to Google Drive, Dropbox, etc.
- [ ] **Scheduled Runs**: Built-in scheduling (currently use system cron/Task Scheduler)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details

## Disclaimer

This tool is for personal use only. Respect copyright laws and only download content you have the right to access. The authors are not responsible for any misuse of this tool.

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review logs in `logs/tg_magazines.log`
3. Run with `--verbose` flag for detailed output
4. Open an issue on GitHub with error details

---

**Happy Reading!** 📚
