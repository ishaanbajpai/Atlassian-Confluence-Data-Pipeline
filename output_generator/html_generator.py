"""
HTML generator for Confluence pages.
Extracts and saves HTML content from Confluence pages.
"""
import logging
import re
import base64
import os
from pathlib import Path

from setup.config_conf import HTML_OUTPUT_DIR, NEW_CONTENT_DIR, UPDATED_CONTENT_DIR
from utilities.html_cleaner import clean_html
from api_client.confluence_client import ConfluenceClient

logger = logging.getLogger(__name__)

class HTMLGenerator:
    """Generator for HTML output from Confluence pages."""

    def __init__(self):
        """Initialize the HTML generator."""
        self.confluence_client = ConfluenceClient()

    def generate_html(self, page, output_path=None, content_type=None):
        """Generate an HTML file for a Confluence page.

        Args:
            page (dict): Page data from the Confluence API
            output_path (str, optional): Custom output path. If None, uses default location.
            content_type (str, optional): Type of content ('new' or 'updated'). If None, saves to the space directory.

        Returns:
            str: Path to the generated HTML file or None if generation failed
        """
        try:
            page_id = page["id"]
            page_title = page["title"]
            space_key = page["space"]["key"]

            # Get HTML content from the page
            if "body" not in page or "storage" not in page["body"] or "value" not in page["body"]["storage"]:
                logger.error(f"Page '{page_title}' (ID: {page_id}) does not have HTML content")
                return None

            html_content = page["body"]["storage"]["value"]

            # Create a safe filename
            safe_title = self._sanitize_filename(page_title)

            # Determine output path
            if output_path is None:
                # Create space directory if it doesn't exist
                space_dir = HTML_OUTPUT_DIR / space_key
                space_dir.mkdir(exist_ok=True)

                # If content_type is specified, create and use the appropriate subdirectory
                if content_type in [NEW_CONTENT_DIR, UPDATED_CONTENT_DIR]:
                    # Create the content type subdirectory if it doesn't exist
                    content_type_dir = space_dir / content_type
                    content_type_dir.mkdir(exist_ok=True)

                    output_path = content_type_dir / f"{safe_title}_{page_id}.html"
                else:
                    output_path = space_dir / f"{safe_title}_{page_id}.html"
            else:
                output_path = Path(output_path)

            logger.info(f"Generating HTML for page '{page_title}' (ID: {page_id})")

            try:
                # Clean the HTML content to properly handle images and code blocks
                cleaned_content = clean_html(html_content)

                # Replace PAGE_ID placeholder with the actual page ID
                cleaned_content = cleaned_content.replace("PAGE_ID", page_id)

                # Embed images as base64 data URLs in the HTML
                cleaned_content = self._embed_images(cleaned_content, page_id)

                # Create a complete HTML document
                full_html = self._create_html_document(page_title, cleaned_content)

                # Write HTML to file
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(full_html)

                logger.info(f"HTML saved to {output_path}")
                return str(output_path)
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Failed to generate HTML for page '{page_title}' (ID: {page_id}): {e}")
                logger.error(f"Stack trace:\n{error_trace}")
                return None
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Failed to process page for HTML generation: {e}")
            logger.error(f"Stack trace:\n{error_trace}")
            return None

    def _create_html_document(self, title, content):
        """Create a complete HTML document with the given content.

        Args:
            title (str): Page title
            content (str): HTML content (already cleaned)

        Returns:
            str: Complete HTML document
        """
        # The content is already cleaned by the calling method

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 20px;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
            overflow-x: auto;
            display: block;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        figure {{
            text-align: center;
            margin: 1em 0;
        }}
        figcaption {{
            font-style: italic;
            font-size: 0.9em;
            margin-top: 0.5em;
        }}
        pre {{
            background-color: #f5f5f5;
            padding: 10px;
            overflow-x: auto;
            border-radius: 3px;
            white-space: pre;
            font-family: monospace;
        }}
        code {{
            font-family: monospace;
            background-color: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        .code-block {{
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre;
            font-family: monospace;
        }}
        /* Syntax highlighting */
        .keyword {{ color: #0000ff; }}
        .string {{ color: #a31515; }}
        .comment {{ color: #008000; }}
        .function {{ color: #795e26; }}
        .number {{ color: #098658; }}
        .type {{ color: #267f99; }}
        .class {{ color: #267f99; }}
        .variable {{ color: #001080; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="content">
        {content}
    </div>
</body>
</html>"""

    def _embed_images(self, html_content, page_id):
        """Embed images directly in the HTML content using base64 encoding.

        Args:
            html_content (str): HTML content with image references
            page_id (str): ID of the Confluence page

        Returns:
            str: HTML content with embedded images
        """
        # Find all img tags with Confluence attachments
        img_pattern = re.compile(r'<img[^>]*?src="[^"]*?/download/attachments/[^"]*?"[^>]*?>')

        # Process each image
        for img_tag in re.findall(img_pattern, html_content):
            try:
                # Extract the src attribute
                src_match = re.search(r'src="([^"]*?)"', img_tag)
                if not src_match:
                    continue

                src = src_match.group(1)

                # Extract the filename from the URL
                filename_match = re.search(r'/([^/]+)$', src)
                if not filename_match:
                    continue

                filename = filename_match.group(1)

                # Download the image
                image_data = self.confluence_client.download_attachment(page_id, filename)
                if not image_data:
                    logger.warning(f"Failed to download image: {filename} from page {page_id}")
                    continue

                # Determine the MIME type based on file extension
                mime_type = self._get_mime_type(filename)

                # Encode the image as base64
                base64_data = base64.b64encode(image_data).decode('utf-8')
                data_url = f"data:{mime_type};base64,{base64_data}"

                # Create a new img tag with the embedded image
                new_img_tag = img_tag.replace(src, data_url)

                # Replace the old img tag with the new one
                html_content = html_content.replace(img_tag, new_img_tag)

                logger.debug(f"Embedded image {filename} in HTML content")
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Error embedding image: {e}")
                logger.error(f"Stack trace for image embedding error:\n{error_trace}")

        return html_content

    def _get_mime_type(self, filename):
        """Get the MIME type for a file based on its extension.

        Args:
            filename (str): Filename with extension

        Returns:
            str: MIME type
        """
        extension = os.path.splitext(filename)[1].lower()

        # Map common image extensions to MIME types
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.ico': 'image/x-icon',
        }

        return mime_types.get(extension, 'application/octet-stream')

    def _sanitize_filename(self, filename):
        """Sanitize a filename to be safe for all operating systems.

        Args:
            filename (str): Original filename

        Returns:
            str: Sanitized filename
        """
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Limit length
        if len(filename) > 200:
            filename = filename[:197] + "..."

        return filename
