"""
Configuration module for Confluence Data Pipeline.
Handles loading of configuration from environment variables and config files.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "confluence_output"
PDF_OUTPUT_DIR = OUTPUT_DIR / "pdf"
HTML_OUTPUT_DIR = OUTPUT_DIR / "html"
LOGS_DIR = BASE_DIR / "logs"
STATE_FILE = BASE_DIR / "state.json"

# Subdirectories for new and updated content
NEW_CONTENT_DIR = "new"
UPDATED_CONTENT_DIR = "updated"

# Ensure directories exist
PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
HTML_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Confluence API configuration
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL", "https://your-domain.atlassian.net")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_VERSION = os.getenv("CONFLUENCE_API_VERSION", "1.0")  # Default to API version 1.0

# No automated cookie refresh is used - cookies are managed through a static file

# Default settings
DEFAULT_DAYS = 1  # Default number of days to look back for updates
DEFAULT_RECURSIVE = True  # Default to recursive fetching

# Validate required configuration
if not CONFLUENCE_API_TOKEN or not CONFLUENCE_USERNAME:
    raise ValueError(
        "Confluence API token and username must be provided. "
        "Set CONFLUENCE_API_TOKEN and CONFLUENCE_USERNAME environment variables."
    )

def get_state():
    """Load the current state from the state file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    """Save the current state to the state file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
