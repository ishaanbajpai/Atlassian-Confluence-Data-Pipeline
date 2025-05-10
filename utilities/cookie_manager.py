"""
Simple cookie management utilities for the Confluence API client.
This module handles loading cookies from a static file.
"""
import logging
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Define the cookie file path
COOKIE_FILE = Path("cookies/confluence_cookies.txt")

def ensure_cookie_dir():
    """Ensure the cookie directory exists."""
    cookie_dir = Path("cookies")
    cookie_dir.mkdir(exist_ok=True)
    return cookie_dir

def load_cookies_from_file(session, base_url):
    """Load cookies from the static cookie file into the session.

    Args:
        session: The requests session to update with cookies
        base_url (str): The base URL for the domain

    Returns:
        bool: True if cookies were successfully loaded, False otherwise
    """
    # Ensure cookie directory exists
    ensure_cookie_dir()

    if not COOKIE_FILE.exists():
        logger.warning(f"Cookie file not found: {COOKIE_FILE}")
        logger.warning("Please create this file with your Confluence cookies.")
        logger.warning("Instructions:")
        logger.warning("1. Log in to Confluence in your browser")
        logger.warning("2. Open developer tools (F12 or right-click > Inspect)")
        logger.warning("3. Go to the Network tab")
        logger.warning("4. Refresh the page")
        logger.warning("5. Click on any request to confluence.atlassian.net")
        logger.warning("6. Find the 'Cookie:' header in the request headers")
        logger.warning("7. Copy the entire cookie string")
        logger.warning("8. Paste it into the file: cookies/confluence_cookies.txt")
        return False

    try:
        # Parse the domain from the URL
        domain = urlparse(base_url).netloc

        # Read the cookie string from the file
        with open(COOKIE_FILE, 'r') as f:
            cookie_text = f.read().strip()

        if not cookie_text:
            logger.warning("Cookie file is empty. Please add your cookies.")
            return False

        # Split the cookie text into individual cookies
        cookie_parts = cookie_text.split(';')

        # Process each cookie
        cookie_count = 0
        for part in cookie_parts:
            if '=' in part:
                name, value = part.strip().split('=', 1)
                # Add the cookie to the session
                session.cookies.set(name, value, domain=domain)
                cookie_count += 1

        logger.info(f"Loaded {cookie_count} cookies from file")
        return True
    except Exception as e:
        logger.error(f"Failed to load cookies from file: {e}")
        return False

def create_empty_cookie_file():
    """Create an empty cookie file with instructions if it doesn't exist."""
    # Ensure cookie directory exists
    ensure_cookie_dir()

    if not COOKIE_FILE.exists():
        try:
            with open(COOKIE_FILE, 'w') as f:
                f.write("# Paste your Confluence cookies here (the entire cookie string from the Cookie header)\n")
                f.write("# Example: cookie1=value1; cookie2=value2; cookie3=value3\n\n")
            logger.info(f"Created empty cookie file: {COOKIE_FILE}")
            return True
        except Exception as e:
            logger.error(f"Failed to create empty cookie file: {e}")
            return False
    return True

def check_cookie_file_exists():
    """Check if the cookie file exists and create it if it doesn't."""
    return create_empty_cookie_file()

if __name__ == "__main__":
    # Create empty cookie file if it doesn't exist
    create_empty_cookie_file()
