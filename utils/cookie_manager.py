"""
Cookie management utilities for the Confluence API client.
"""
import os
import pickle
import logging
import argparse
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def save_cookies(session, cookie_file):
    """Save the current session cookies to a file.

    Args:
        session: The requests session containing cookies
        cookie_file (str): Path to the cookie file

    Returns:
        bool: True if cookies were successfully saved, False otherwise
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(cookie_file), exist_ok=True)

        # Save the cookies
        with open(cookie_file, 'wb') as f:
            pickle.dump(session.cookies, f)
        logger.info(f"Saved cookies to {cookie_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save cookies: {e}")
        return False

def load_cookies(session, cookie_file):
    """Load cookies from file into the current session.

    Args:
        session: The requests session to update with cookies
        cookie_file (str): Path to the cookie file

    Returns:
        bool: True if cookies were successfully loaded, False otherwise
    """
    if not os.path.exists(cookie_file):
        logger.info("No saved cookies found")
        return False

    try:
        with open(cookie_file, 'rb') as f:
            cookies = pickle.load(f)
            session.cookies.update(cookies)
        logger.info(f"Loaded cookies from {cookie_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to load cookies: {e}")
        return False

def import_browser_cookies(session, cookie_text, base_url):
    """Import cookies from browser developer tools.

    Args:
        session: The requests session to update with cookies
        cookie_text (str): Cookie header text copied from browser developer tools
            Format should be like: "cookie1=value1; cookie2=value2; ..."
        base_url (str): The base URL for the domain

    Returns:
        bool: True if cookies were successfully imported, False otherwise
    """
    try:
        # Parse the domain from the URL
        domain = urlparse(base_url).netloc

        # Split the cookie text into individual cookies
        cookie_parts = cookie_text.split(';')

        # Process each cookie
        for part in cookie_parts:
            if '=' in part:
                name, value = part.strip().split('=', 1)
                # Add the cookie to the session
                session.cookies.set(name, value, domain=domain)

        logger.info(f"Imported {len(cookie_parts)} cookies from browser")
        return True
    except Exception as e:
        logger.error(f"Failed to import browser cookies: {e}")
        return False

def main(mode=None):
    """Command-line interface for cookie management.

    Args:
        mode (str, optional): Operation mode. Can be 'import', 'view', 'clear', or None.
            If None, uses command-line arguments.
    """
    import requests
    from utils.logger import setup_logging
    from setup.config import CONFLUENCE_URL
    import webbrowser

    # Set up logging
    setup_logging()

    # Set up cookie file path
    cookie_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies")
    os.makedirs(cookie_dir, exist_ok=True)
    cookie_file = os.path.join(cookie_dir, "confluence_cookies.pkl")

    # Create a session
    session = requests.Session()

    # Parse command-line arguments if mode is not specified
    if mode is None:
        parser = argparse.ArgumentParser(description="Confluence API Cookie Manager")
        parser.add_argument("--import", dest="import_cookies", action="store_true",
                            help="Import cookies from browser")
        parser.add_argument("--refresh", action="store_true",
                            help="Refresh cookies by opening browser and guiding through import")
        parser.add_argument("--view", action="store_true",
                            help="View saved cookies")
        parser.add_argument("--clear", action="store_true",
                            help="Clear saved cookies")
        args = parser.parse_args()

        # Determine mode from arguments
        if args.import_cookies:
            mode = 'import'
        elif args.refresh:
            mode = 'refresh'
        elif args.view:
            mode = 'view'
        elif args.clear:
            mode = 'clear'

    # Handle different modes
    if mode == 'import' or mode == 'refresh':
        print("=" * 80)
        print("COOKIE IMPORT UTILITY")
        print("=" * 80)
        print("Please follow these steps to import cookies from your browser:")
        print("1. Log in to Confluence in your browser")
        print("2. Open developer tools (F12 or right-click > Inspect)")
        print("3. Go to the Network tab")
        print("4. Refresh the page")
        print("5. Click on any request to confluence.atlassian.net")
        print("6. Find the 'Cookie:' header in the request headers")
        print("7. Copy the entire cookie string")
        print("8. Paste it below")
        print("=" * 80)

        # If refresh mode, open the browser to the Confluence URL
        if mode == 'refresh':
            print(f"Opening browser to {CONFLUENCE_URL}...")
            webbrowser.open(CONFLUENCE_URL)

        cookie_text = input("Paste the cookie string here: ")

        if import_browser_cookies(session, cookie_text, CONFLUENCE_URL):
            save_cookies(session, cookie_file)
            print("Cookies imported and saved successfully!")
            return True
        else:
            print("Failed to import cookies.")
            return False

    elif mode == 'view':
        if os.path.exists(cookie_file):
            try:
                with open(cookie_file, 'rb') as f:
                    cookies = pickle.load(f)
                print(f"Found {len(cookies)} saved cookies:")
                for cookie in cookies:
                    print(f"  {cookie.name}: {cookie.value[:10]}...")
                return True
            except Exception as e:
                print(f"Error reading cookies: {e}")
                return False
        else:
            print("No saved cookies found.")
            return False

    elif mode == 'clear':
        if os.path.exists(cookie_file):
            try:
                os.remove(cookie_file)
                print("Cookies cleared successfully.")
                return True
            except Exception as e:
                print(f"Error clearing cookies: {e}")
                return False
        else:
            print("No saved cookies found.")
            return False

    else:
        if mode is None:
            parser.print_help()
        else:
            print(f"Unknown mode: {mode}")
        return False

if __name__ == "__main__":
    main()
