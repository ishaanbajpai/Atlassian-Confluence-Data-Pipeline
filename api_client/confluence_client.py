"""
Confluence API client for fetching pages and spaces.
"""
import requests
import logging
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

        self.auth = (CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
        self.session = requests.Session()
        self.session.auth = self.auth

    def _make_request(self, endpoint, params=None, method="GET"):
        """Make a request to the Confluence API.

        Args:
            endpoint (str): API endpoint to call
            params (dict, optional): Query parameters
            method (str, optional): HTTP method. Defaults to "GET".

        Returns:
            dict: JSON response from the API
        """
        # Ensure proper URL joining with slashes
        if not self.api_url.endswith('/'):
            self.api_url += '/'
        url = urljoin(self.api_url, endpoint)

        try:
            logger.debug(f"Making {method} request to {url} with params: {params}")

            if method == "GET":
                response = self.session.get(url, params=params)
            else:
                response = self.session.request(method, url, json=params)

            # Log the full URL that was requested (including query parameters)
            logger.debug(f"Full URL requested: {response.url}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            logger.error(f"API request failed with status code {status_code}: {e}")

            if status_code == 404:
                logger.error(f"404 Not Found: The requested resource could not be found. URL: {response.url}")
                logger.error("This could be due to an incorrect API version, endpoint, or the resource doesn't exist.")
                logger.error(f"Try changing the CONFLUENCE_API_VERSION in your .env file (current: {CONFLUENCE_API_VERSION})")
            elif status_code == 401:
                logger.error("401 Unauthorized: Authentication failed. Check your username and API token.")
            elif status_code == 403:
                logger.error("403 Forbidden: You don't have permission to access this resource.")
            elif status_code == 400:
                logger.error("400 Bad Request: The request was malformed or contains invalid parameters.")

            if hasattr(e.response, 'text'):
                logger.error(f"Response body: {e.response.text}")

            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

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
            all_pages.extend(pages)

            # Check if there are more pages
            if len(pages) < limit:
                break

            start += limit

            # Add a small delay to avoid rate limiting
            time.sleep(0.5)

        # If recursive, get child pages
        if recursive and all_pages:
            child_pages = []
            for page in all_pages:
                if page.get("children") and page["children"].get("page") and page["children"]["page"].get("results"):
                    for child in page["children"]["page"]["results"]:
                        # Fetch full child page data
                        child_page = self.get_page_by_id(child["id"])
                        if child_page:
                            child_pages.append(child_page)
                            # Add a small delay to avoid rate limiting
                            time.sleep(0.5)

            all_pages.extend(child_pages)

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
                    logger.warning(f"Error fetching updated pages with global query: {e}")
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
                            logger.warning(f"Error fetching updated pages in space '{space_key}': {e}")
                            # Continue with the next space
                            break

        except Exception as e:
            logger.error(f"Failed to fetch updated pages: {e}")

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

        # Check if the page has children
        if not parent_page.get("children") or not parent_page["children"].get("page") or not parent_page["children"]["page"].get("results"):
            logger.info(f"Page with ID {page_id} has no child pages")
            return all_pages

        # Get immediate child pages
        child_pages = []
        for child in parent_page["children"]["page"]["results"]:
            # Fetch full child page data
            child_page = self.get_page_by_id(child["id"])
            if child_page:
                child_pages.append(child_page)
                # Add a small delay to avoid rate limiting
                time.sleep(0.5)

        all_pages.extend(child_pages)

        # If recursive, get grandchild pages
        if recursive and child_pages:
            for child_page in child_pages:
                grandchild_pages = self.get_child_pages(child_page["id"], recursive)
                # Remove the child page itself from the results to avoid duplication
                if grandchild_pages and len(grandchild_pages) > 1:
                    all_pages.extend(grandchild_pages[1:])

        logger.info(f"Found {len(all_pages) - 1} child pages for page with ID {page_id}")
        return all_pages

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
            logger.error(f"Failed to download attachment '{filename}' from page {page_id}: {e}")
            return None


