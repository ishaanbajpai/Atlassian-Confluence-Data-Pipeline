"""
Confluence API client for fetching pages and spaces.
"""
import requests
import logging
import random
from datetime import datetime, timedelta
from urllib.parse import urljoin
import time

from setup.config import CONFLUENCE_URL, CONFLUENCE_API_TOKEN, CONFLUENCE_USERNAME, CONFLUENCE_API_VERSION

logger = logging.getLogger(__name__)

class ConfluenceClient:
    """Client for interacting with the Confluence REST API."""

    def __init__(self):
        """Initialize the Confluence API client."""
        # Store the original URL
        self.original_url = CONFLUENCE_URL

        # Initialize session
        self._init_session()

        # Initialize secure cookie manager
        from utils.secure_cookie_manager import SecureCookieManager
        self.cookie_manager = SecureCookieManager()

        # Load cookies from secure storage or prompt for new ones
        self.cookie_manager.load_cookies_to_session(self.session, self.original_url)

        # For Confluence Cloud, the API URL structure is different
        if 'atlassian.net' in CONFLUENCE_URL:
            # Confluence Cloud
            # The correct API URL for Confluence Cloud is:
            # https://your-domain.atlassian.net/wiki/rest/api/content

            # Remove trailing slash if present
            base_url = CONFLUENCE_URL.rstrip('/')

            # If URL doesn't end with /wiki, add it
            if not base_url.endswith('/wiki'):
                base_url = f"{base_url}/wiki"

            # Set the base URL for other operations
            self.base_url = base_url

            # Set the API URL
            self.api_url = f"{base_url}/rest/api"
        else:
            # Confluence Server/Data Center
            self.base_url = CONFLUENCE_URL.rstrip('/')
            self.api_url = f"{self.base_url}/rest/api"

        logger.debug(f"Using base URL: {self.base_url}")
        logger.debug(f"Using API URL: {self.api_url}")

    def _init_session(self):
        """Initialize or reinitialize the HTTP session with proper headers and authentication."""
        # Create a session with authentication
        self.session = requests.Session()
        self.session.auth = (CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)

        # Add more comprehensive browser-like headers to avoid bot detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        })

    def refresh_session(self):
        """Refresh the session by reinitializing it and loading cookies from secure storage.

        This can help when the session cookies become invalid or expire.
        """
        logger.info("Refreshing API session...")
        self._init_session()

        # Load cookies from secure storage
        return self.cookie_manager.load_cookies_to_session(self.session, self.original_url)

    def _make_request(self, endpoint, params=None, method="GET", max_retries=3, retry_delay=2):
        """Make a request to the Confluence API with retry logic.

        Args:
            endpoint (str): API endpoint to call
            params (dict, optional): Query parameters
            method (str, optional): HTTP method. Defaults to "GET".
            max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.
            retry_delay (int, optional): Base delay between retries in seconds. Defaults to 2.

        Returns:
            dict: JSON response from the API
        """
        # Ensure proper URL joining with slashes
        if not self.api_url.endswith('/'):
            self.api_url += '/'
        url = urljoin(self.api_url, endpoint)

        # Initialize retry counter
        retry_count = 0

        while retry_count <= max_retries:
            try:
                # Add a random delay between requests to appear more human-like
                if retry_count > 0:
                    # Exponential backoff with jitter
                    sleep_time = retry_delay * (2 ** (retry_count - 1)) + (random.random() * 0.5)
                    logger.info(f"Retry attempt {retry_count}/{max_retries}. Waiting {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)

                logger.debug(f"Making {method} request to {url} with params: {params}")

                if method == "GET":
                    response = self.session.get(url, params=params, timeout=30)
                else:
                    response = self.session.request(method, url, json=params, timeout=30)

                # Log the full URL that was requested (including query parameters)
                logger.debug(f"Full URL requested: {response.url}")

                # Check for human verification page in the response or authentication issues
                if ("Human Verification" in response.text or
                    "captcha" in response.text.lower()):
                    logger.error("Detected CAPTCHA or human verification challenge")
                    logger.error("The Atlassian server is detecting automated requests")

                    # Try manual verification
                    if self._handle_manual_verification(response.url):
                        # If manual verification was successful, try the request again
                        logger.info("Manual verification completed. Retrying request...")
                        continue
                    else:
                        # If manual verification failed or was cancelled
                        logger.error("Manual verification failed or was cancelled")
                        raise Exception("CAPTCHA challenge could not be resolved. Manual verification failed.")

                # Check for successful response
                response.raise_for_status()

                # If we get here, the request was successful
                return response.json()

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                logger.error(f"API request failed with status code {status_code}: {e}")

                # Handle specific status codes
                if status_code == 404:
                    logger.error(f"404 Not Found: The requested resource could not be found. URL: {response.url}")
                    logger.error("This could be due to an incorrect API version, endpoint, or the resource doesn't exist.")
                    logger.error(f"Try changing the CONFLUENCE_API_VERSION in your .env file (current: {CONFLUENCE_API_VERSION})")
                elif status_code == 401:
                    logger.error("401 Unauthorized: Authentication failed. Cookies may have expired.")
                    # Try to refresh cookies
                    if self._handle_manual_verification(response.url):
                        # If cookie refresh was successful, retry the request
                        logger.info("Cookie refresh completed. Retrying request...")
                        if retry_count < max_retries:
                            retry_count += 1
                            continue
                elif status_code == 403:
                    logger.error("403 Forbidden: You don't have permission to access this resource or cookies have expired.")
                    # Try to refresh cookies
                    if self._handle_manual_verification(response.url):
                        # If cookie refresh was successful, retry the request
                        logger.info("Cookie refresh completed. Retrying request...")
                        if retry_count < max_retries:
                            retry_count += 1
                            continue
                elif status_code == 400:
                    logger.error("400 Bad Request: The request was malformed or contains invalid parameters.")
                elif status_code == 405:
                    logger.error("405 Method Not Allowed: The API endpoint doesn't support this HTTP method.")
                elif status_code == 429:
                    logger.error("429 Too Many Requests: Rate limit exceeded.")
                    # Always retry on rate limit errors
                    if retry_count < max_retries:
                        retry_count += 1
                        # Use a longer delay for rate limiting
                        time.sleep(retry_delay * 5)
                        continue

                if hasattr(e.response, 'text'):
                    logger.error(f"Response body: {e.response.text}")

                # Retry on 5xx server errors
                if 500 <= status_code < 600 and retry_count < max_retries:
                    retry_count += 1
                    continue

                # For other errors, don't retry
                raise

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                logger.error(f"Connection error or timeout: {e}")

                # Retry on connection errors
                if retry_count < max_retries:
                    retry_count += 1
                    continue
                raise

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")

                # Retry on general request exceptions
                if retry_count < max_retries:
                    retry_count += 1
                    continue
                raise

            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Unexpected error in API request: {e}")
                logger.error(f"Stack trace for API request error:\n{error_trace}")
                raise

        # If we've exhausted all retries
        logger.error(f"Maximum retries ({max_retries}) reached. Request failed.")
        raise Exception(f"Failed to make request after {max_retries} retries")

    def get_page_by_id(self, page_id):
        """Get a page by its ID.

        Args:
            page_id (str): The ID of the page to fetch

        Returns:
            dict: Page data
        """
        logger.info(f"Fetching page with ID: {page_id}")
        endpoint = f"content/{page_id}"
        params = {
            "expand": "body.storage,version,space,ancestors,children.page"
        }
        return self._make_request(endpoint, params)

    def get_page_by_title(self, space_key, title):
        """Get a page by its title within a space.

        Args:
            space_key (str): The key of the space containing the page
            title (str): The title of the page to fetch

        Returns:
            dict: Page data or None if not found
        """
        logger.info(f"Fetching page with title '{title}' in space '{space_key}'")
        endpoint = "content"
        params = {
            "spaceKey": space_key,
            "title": title,
            "expand": "body.storage,version,space,ancestors,children.page"
        }

        response = self._make_request(endpoint, params)

        if response.get("results") and len(response["results"]) > 0:
            return response["results"][0]

        logger.warning(f"No page found with title '{title}' in space '{space_key}'")
        return None

    def get_pages_in_space(self, space_key, recursive=True):
        """Get all pages in a space.

        Args:
            space_key (str): The key of the space
            recursive (bool, optional): Whether to fetch child pages recursively. Defaults to True.

        Returns:
            list: List of pages in the space
        """
        logger.info(f"Fetching pages in space '{space_key}'")

        # Get top-level pages first
        all_pages = []
        processed_ids = set()  # Track processed page IDs to avoid duplicates
        start = 0
        limit = 100

        while True:
            endpoint = "content"
            params = {
                "spaceKey": space_key,
                "type": "page",
                "status": "current",
                "start": start,
                "limit": limit,
                "expand": "body.storage,version,space,ancestors,children.page"
            }

            response = self._make_request(endpoint, params)

            if not response.get("results"):
                break

            pages = response["results"]

            # Add pages to the list, avoiding duplicates
            for page in pages:
                if page["id"] not in processed_ids:
                    processed_ids.add(page["id"])
                    all_pages.append(page)

            # Check if there are more pages
            if len(pages) < limit:
                break

            start += limit

            # Add a small delay to avoid rate limiting
            time.sleep(0.5)

        # If recursive, get child pages that aren't already in the list
        if recursive and all_pages:
            # Create a queue of pages to process
            pages_to_process = list(all_pages)  # Make a copy to avoid modifying while iterating

            # Process each page in the queue
            for page in pages_to_process:
                if page.get("children") and page["children"].get("page") and page["children"]["page"].get("results"):
                    for child in page["children"]["page"]["results"]:
                        # Only fetch if we haven't processed this ID yet
                        if child["id"] not in processed_ids:
                            # Fetch full child page data
                            child_page = self.get_page_by_id(child["id"])
                            if child_page:
                                processed_ids.add(child_page["id"])
                                all_pages.append(child_page)
                                # Add a small delay to avoid rate limiting
                                time.sleep(0.5)

        logger.info(f"Found {len(all_pages)} pages in space '{space_key}'")
        return all_pages

    def get_updated_pages(self, days=1):
        """Get pages updated within the last N days across all accessible spaces.

        Args:
            days (int, optional): Number of days to look back. Defaults to 1.

        Returns:
            list: List of updated pages
        """
        logger.info(f"Fetching pages updated in the last {days} days")

        # Calculate the date N days ago
        date_n_days_ago = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        updated_pages = []

        try:
            # First approach: Try to get all updated pages across all spaces in one query
            endpoint = "content/search"

            start = 0
            limit = 100

            while True:
                # Use a simpler CQL query that just checks for updates in the date range
                params = {
                    "cql": f"lastmodified>={date_n_days_ago} AND type=page",
                    "start": start,
                    "limit": limit,
                    "expand": "body.storage,version,space,ancestors,children.page"
                }

                try:
                    response = self._make_request(endpoint, params)

                    if not response.get("results"):
                        break

                    pages = response["results"]
                    updated_pages.extend(pages)

                    # Check if there are more pages
                    if len(pages) < limit:
                        break

                    start += limit

                    # Add a small delay to avoid rate limiting
                    time.sleep(0.5)
                except Exception as e:
                    import traceback
                    error_trace = traceback.format_exc()
                    logger.warning(f"Error fetching updated pages with global query: {e}")
                    logger.warning(f"Stack trace for global query error:\n{error_trace}")
                    logger.warning("Falling back to per-space queries")
                    updated_pages = []  # Reset the list
                    break

            # If the first approach didn't work, try the second approach: query each space individually
            if not updated_pages:
                # Get all spaces first
                spaces = self.get_all_spaces()

                for space in spaces:
                    space_key = space["key"]

                    logger.info(f"Fetching updated pages in space '{space_key}'")

                    # Use CQL to search for updated content in this space
                    endpoint = "content/search"

                    start = 0
                    limit = 100

                    while True:
                        try:
                            params = {
                                "cql": f'space="{space_key}" AND lastmodified>={date_n_days_ago} AND type=page',
                                "start": start,
                                "limit": limit,
                                "expand": "body.storage,version,space,ancestors,children.page"
                            }

                            response = self._make_request(endpoint, params)

                            if not response.get("results"):
                                break

                            pages = response["results"]
                            updated_pages.extend(pages)

                            # Check if there are more pages
                            if len(pages) < limit:
                                break

                            start += limit

                            # Add a small delay to avoid rate limiting
                            time.sleep(0.5)
                        except Exception as e:
                            import traceback
                            error_trace = traceback.format_exc()
                            logger.warning(f"Error fetching updated pages in space '{space_key}': {e}")
                            logger.warning(f"Stack trace for space query error:\n{error_trace}")
                            # Continue with the next space
                            break

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Failed to fetch updated pages: {e}")
            logger.error(f"Stack trace for updated pages error:\n{error_trace}")

        logger.info(f"Found {len(updated_pages)} pages updated in the last {days} days")
        return updated_pages

    def get_all_spaces(self):
        """Get all accessible spaces.

        Returns:
            list: List of spaces
        """
        logger.info("Fetching all accessible spaces")

        all_spaces = []
        start = 0
        limit = 100

        while True:
            endpoint = "space"
            params = {
                "start": start,
                "limit": limit,
                "status": "current"
            }

            response = self._make_request(endpoint, params)

            if not response.get("results"):
                break

            spaces = response["results"]
            all_spaces.extend(spaces)

            # Check if there are more spaces
            if len(spaces) < limit:
                break

            start += limit

        logger.info(f"Found {len(all_spaces)} accessible spaces")
        return all_spaces

    def get_child_pages(self, page_id, recursive=True):
        """Get all child pages for a specific page.

        Args:
            page_id (str): The ID of the parent page
            recursive (bool, optional): Whether to fetch child pages recursively. Defaults to True.

        Returns:
            list: List of child pages
        """
        logger.info(f"Fetching child pages for page with ID: {page_id}")

        # Get the parent page first to include it in the results
        parent_page = self.get_page_by_id(page_id)
        if not parent_page:
            logger.error(f"Parent page with ID {page_id} not found")
            return []

        all_pages = [parent_page]
        processed_ids = {parent_page["id"]}  # Track processed page IDs to avoid duplicates

        # Check if the page has children
        if not parent_page.get("children") or not parent_page["children"].get("page") or not parent_page["children"]["page"].get("results"):
            logger.info(f"Page with ID {page_id} has no child pages")
            return all_pages

        # Get immediate child pages
        child_pages = []
        for child in parent_page["children"]["page"]["results"]:
            # Only fetch if we haven't processed this ID yet
            if child["id"] not in processed_ids:
                # Fetch full child page data
                child_page = self.get_page_by_id(child["id"])
                if child_page:
                    processed_ids.add(child_page["id"])
                    child_pages.append(child_page)
                    # Add a small delay to avoid rate limiting
                    time.sleep(0.5)

        all_pages.extend(child_pages)

        # If recursive, get grandchild pages
        if recursive and child_pages:
            for child_page in child_pages:
                # Use a helper function to avoid duplicating the parent page logic
                grandchild_pages = self._get_child_pages_recursive(child_page["id"], processed_ids)
                all_pages.extend(grandchild_pages)

        logger.info(f"Found {len(all_pages) - 1} child pages for page with ID {page_id}")
        return all_pages

    def _get_child_pages_recursive(self, page_id, processed_ids):
        """Helper method to get child pages recursively without duplicating the parent.

        Args:
            page_id (str): The ID of the parent page
            processed_ids (set): Set of already processed page IDs

        Returns:
            list: List of child pages (without the parent)
        """
        # Get the parent page
        parent_page = self.get_page_by_id(page_id)
        if not parent_page:
            return []

        # Skip if we've already processed this page
        if parent_page["id"] in processed_ids:
            return []

        # Mark as processed
        processed_ids.add(parent_page["id"])

        # Check if the page has children
        if not parent_page.get("children") or not parent_page["children"].get("page") or not parent_page["children"]["page"].get("results"):
            return []

        # Get child pages
        child_pages = []
        for child in parent_page["children"]["page"]["results"]:
            # Only fetch if we haven't processed this ID yet
            if child["id"] not in processed_ids:
                # Fetch full child page data
                child_page = self.get_page_by_id(child["id"])
                if child_page:
                    processed_ids.add(child_page["id"])
                    child_pages.append(child_page)

                    # Recursively get grandchildren
                    grandchildren = self._get_child_pages_recursive(child_page["id"], processed_ids)
                    child_pages.extend(grandchildren)

                    # Add a small delay to avoid rate limiting
                    time.sleep(0.5)

        return child_pages

    def download_attachment(self, page_id, filename):
        """Download an attachment from a Confluence page.

        Args:
            page_id (str): The ID of the page containing the attachment
            filename (str): The filename of the attachment

        Returns:
            bytes: The attachment content as bytes, or None if download failed
        """
        try:
            # Construct the URL to download the attachment
            # For Confluence Cloud, the URL structure is:
            # https://your-domain.atlassian.net/wiki/download/attachments/pageId/filename
            if self.base_url.endswith('/wiki'):
                url = f"{self.base_url}/download/attachments/{page_id}/{filename}"
            else:
                url = f"{self.base_url}/wiki/download/attachments/{page_id}/{filename}"

            logger.debug(f"Downloading attachment from URL: {url}")

            # Make the request to download the attachment
            response = self.session.get(url)
            response.raise_for_status()

            # Return the attachment content
            return response.content
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Failed to download attachment '{filename}' from page {page_id}: {e}")
            logger.error(f"Stack trace for attachment download error:\n{error_trace}")
            return None

    def _handle_manual_verification(self, _):
        """Handle manual verification for CAPTCHA challenges.

        This method provides instructions for updating the cookie file
        to bypass CAPTCHA challenges.

        Args:
            _ (str): Unused parameter (kept for compatibility)

        Returns:
            bool: True if verification was successful, False otherwise
        """
        import webbrowser
        from pathlib import Path

        try:
            # Create a login URL - use the main Confluence URL instead of the API URL
            login_url = self.base_url

            # Get the cookie file path
            cookie_file = Path("cookies/confluence_cookies.txt")

            # Clear any existing encrypted cookies to force a refresh
            self.cookie_manager.clear_encrypted_cookies()

            # Display instructions to the user
            logger.error("=" * 80)
            logger.error("CAPTCHA / HUMAN VERIFICATION REQUIRED")
            logger.error("=" * 80)
            logger.error("The Confluence API is detecting automated requests and requiring verification.")
            logger.error("You need to update the cookie file with fresh cookies.")
            logger.error("")
            logger.error("Please follow these steps:")
            logger.error("1. Open your browser and go to your Confluence site")
            logger.error("2. Log in to Confluence if you're not already logged in")
            logger.error("3. Open your browser's developer tools:")
            logger.error("   - Chrome/Edge: Press F12 or right-click > Inspect")
            logger.error("   - Firefox: Press F12 or right-click > Inspect Element")
            logger.error("4. Go to the 'Network' tab in developer tools")
            logger.error("5. Refresh the page")
            logger.error("6. Click on any request to confluence.atlassian.net")
            logger.error("7. In the request headers, find the 'Cookie:' header")
            logger.error("8. Copy the entire cookie string (it's long!)")
            logger.error(f"9. Open the file: {cookie_file.absolute()}")
            logger.error("10. Replace the content with your copied cookie string")
            logger.error("11. Save the file and run the script again")
            logger.error("")
            logger.error("IMPORTANT: For security, the cookie file will be cleared after loading.")
            logger.error("Your cookies will be encrypted and stored securely.")
            logger.error("=" * 80)

            # Open the login URL in the default browser
            webbrowser.open(login_url)

            # Return False to indicate that manual intervention is required
            return False

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error during manual verification: {e}")
            logger.error(f"Stack trace for manual verification error:\n{error_trace}")
            return False


