"""
HTML cleaner utility for Confluence content.
Handles image URLs and code blocks properly.
"""
import logging
from bs4 import BeautifulSoup
from setup.config import CONFLUENCE_URL

logger = logging.getLogger(__name__)

def clean_html(html_content: str) -> str:
    """
    Clean HTML content for better readability and proper rendering of images and code blocks.

    Args:
        html_content: The HTML content to clean

    Returns:
        The cleaned HTML content
    """
    try:
        # Parse the HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove scripts and styles
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        # Process images
        process_images(soup)

        # Process code blocks
        process_code_blocks(soup)

        # Return the cleaned HTML
        html_result = str(soup)

        # Post-processing to remove CDATA tags
        html_result = html_result.replace("<![CDATA[", "").replace("]]>", "")

        return html_result
    except Exception as e:
        logger.error(f"Error cleaning HTML: {e}")
        # Return the original content if cleaning fails
        return html_content

def process_images(soup):
    """
    Process images in the HTML content.

    Args:
        soup: BeautifulSoup object containing the HTML
    """
    # Process Confluence-specific ac:image tags with ri:attachment
    for ac_image in soup.find_all("ac:image"):
        # Extract attributes from ac:image tag
        align = ac_image.get("ac:align", "center")
        alt_text = ac_image.get("ac:alt", "")
        width = ac_image.get("ac:width", "")
        original_width = ac_image.get("ac:original-width", "")
        original_height = ac_image.get("ac:original-height", "")

        # Find the ri:attachment tag inside ac:image
        ri_attachment = ac_image.find("ri:attachment")

        if ri_attachment:
            # Extract the filename from ri:attachment
            filename = ri_attachment.get("ri:filename", "")

            if filename:
                # Create a new img tag
                img = soup.new_tag("img")

                # Set the src attribute to a relative path that will be handled by the standard image processing
                # This will be converted to a proper URL by the code below
                img["src"] = f"attachments/{filename}"

                # Set alt text
                img["alt"] = alt_text if alt_text else filename

                # Set width and height if available
                if width:
                    img["width"] = width
                elif original_width:
                    img["width"] = original_width

                if original_height:
                    img["height"] = original_height

                # Set alignment
                if align == "center":
                    img["style"] = "display: block; margin: 0 auto; max-width: 100%; height: auto;"
                elif align == "left":
                    img["style"] = "float: left; margin-right: 10px; max-width: 100%; height: auto;"
                elif align == "right":
                    img["style"] = "float: right; margin-left: 10px; max-width: 100%; height: auto;"
                else:
                    img["style"] = "max-width: 100%; height: auto;"

                # Add data attributes to preserve original information
                img["data-confluence-image"] = "true"
                img["data-original-filename"] = filename

                # Replace the ac:image tag with the new img tag
                ac_image.replace_with(img)

                # Log the replacement
                logger.debug(f"Replaced ac:image tag with img tag for {filename}")

    # Fix relative URLs for images and handle Confluence-specific image URLs
    for img in soup.find_all("img"):
        src = img.get("src", "")

        # Handle Confluence download URLs
        if "download/attachments" in src or "download/thumbnails" in src or "wiki/download" in src:
            # These are already absolute URLs, but we need to ensure they have authentication
            # Add a custom attribute to identify these as Confluence attachments
            img["data-confluence-attachment"] = "true"

            # Add responsive styling if not already set
            if not img.get("style"):
                img["style"] = "max-width: 100%; height: auto;"

            # Add alt text if missing
            if not img.get("alt"):
                img["alt"] = "Confluence attachment"

        # Handle Confluence attachment references (from ac:image tags)
        elif src.startswith("attachments/"):
            # Extract the filename
            filename = src.replace("attachments/", "")

            # Construct a proper URL to the attachment
            # For Confluence Cloud, the URL structure is:
            # https://your-domain.atlassian.net/wiki/download/attachments/pageId/filename
            # We need to get the page ID from the context, but since we don't have it here,
            # we'll use a placeholder that will be replaced when the page is processed

            # Make sure we don't duplicate 'wiki' in the URL
            base_url = CONFLUENCE_URL
            if base_url.endswith('/wiki'):
                img["src"] = f"{base_url}/download/attachments/PAGE_ID/{filename}"
            else:
                img["src"] = f"{base_url}/wiki/download/attachments/PAGE_ID/{filename}"
            img["data-confluence-attachment"] = "true"

            # Add responsive styling if not already set
            if not img.get("style"):
                img["style"] = "max-width: 100%; height: auto;"

            # Add alt text if missing
            if not img.get("alt"):
                img["alt"] = filename

        # Handle Confluence default images (often from CDN)
        elif "wac-cdn.atlassian.com" in src or "atlassian.net/wiki" in src:
            # These are Confluence default images
            img["data-confluence-default"] = "true"

            # Add responsive styling if not already set
            if not img.get("style"):
                img["style"] = "max-width: 100%; height: auto;"

        # Handle relative URLs
        elif src and not src.startswith(("http://", "https://", "data:")):
            img["src"] = f"{CONFLUENCE_URL}{src if src.startswith('/') else '/' + src}"

            # Add responsive styling if not already set
            if not img.get("style"):
                img["style"] = "max-width: 100%; height: auto;"

        # Handle absolute URLs
        else:
            # Add responsive styling if not already set
            if not img.get("style"):
                img["style"] = "max-width: 100%; height: auto;"

        # Add a figure and caption for images with titles
        if img.get("title") and img.parent.name != "figure":
            # Create a figure element
            figure = soup.new_tag("figure")
            figure["style"] = "text-align: center; margin: 1em 0;"

            # Create a figcaption element
            figcaption = soup.new_tag("figcaption")
            figcaption.string = img["title"]
            figcaption["style"] = "font-style: italic; font-size: 0.9em; margin-top: 0.5em;"

            # Replace the img with the figure containing the img and figcaption
            img_copy = img.copy()
            img.replace_with(figure)
            figure.append(img_copy)
            figure.append(figcaption)

def process_code_blocks(soup):
    """
    Process code blocks in the HTML content.

    Args:
        soup: BeautifulSoup object containing the HTML
    """
    # Handle Confluence structured macros for code
    for macro in soup.find_all("ac:structured-macro", {"ac:name": "code"}):
        # Get the language if specified
        language = ""
        lang_param = macro.find("ac:parameter", {"ac:name": "language"})
        if lang_param and lang_param.string:
            language = lang_param.string.strip()

        # Get the code content
        code_content = ""
        code_body = macro.find("ac:plain-text-body")
        if code_body and code_body.string:
            # Remove CDATA wrapper if present
            code_text = code_body.string
            if "![CDATA[" in code_text and "]]" in code_text:
                code_text = code_text.replace("![CDATA[", "").replace("]]", "")
            code_content = code_text

        # Create a pre element with the code
        pre = soup.new_tag("pre")
        pre["class"] = f"code-block {language}"
        pre["style"] = "white-space: pre; font-family: monospace; background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;"

        # Add language as a data attribute
        if language:
            pre["data-language"] = language

        # Set the code content without CDATA tags
        if "<![CDATA[" in code_content and "]]>" in code_content:
            code_content = code_content.replace("<![CDATA[", "").replace("]]>", "")
        pre.string = code_content

        # Replace the macro with the pre element
        macro.replace_with(pre)

    # Special handling for code blocks
    for pre in soup.find_all("pre"):
        # Add a class to identify this as a code block
        if "class" in pre.attrs:
            if isinstance(pre["class"], list):
                if "code-block" not in pre["class"]:
                    pre["class"].append("code-block")
            else:
                if "code-block" not in pre["class"]:
                    pre["class"] = [pre["class"], "code-block"]
        else:
            pre["class"] = "code-block"

        # Preserve whitespace and formatting
        pre["style"] = "white-space: pre; font-family: monospace; background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;"

        # If there's a code tag inside, make sure it preserves formatting too
        for code in pre.find_all("code"):
            code["style"] = "white-space: pre; font-family: monospace;"

    # Handle standalone code tags
    for code in soup.find_all("code"):
        if code.parent.name != "pre":
            code["style"] = "font-family: monospace; background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px;"

    # Handle Confluence code macros at the top level
    # Look for the table structure that Confluence uses for code blocks with line numbers
    for table in soup.find_all("table", class_=["syntaxhighlighter", "highlighterTable"]):
        # Extract the code content from the table
        code_content = ""
        for tr in table.find_all("tr"):
            line_num_td = tr.find("td", class_=["line-numbers", "gutter"])
            code_td = tr.find("td", class_=["code", "syntaxhighlighter"])

            if line_num_td and code_td:
                code_line = code_td.get_text()
                code_content += f"{code_line}\n"

        # If we extracted code content, replace the table with a pre element
        if code_content.strip():
            pre = soup.new_tag("pre")
            pre["class"] = "code-block"
            pre["style"] = "white-space: pre; font-family: monospace; background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;"
            pre.string = code_content
            table.replace_with(pre)

    # Handle Confluence code macros (they often use div with specific classes)
    for div in soup.find_all("div", class_=["code-block", "codeContent", "syntaxhighlighter", "code", "CodeBlock", "CodeMacro"]):
        div["style"] = "white-space: pre; font-family: monospace; background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;"
        div["class"] = "code-block"

        # Make sure all line numbers and code lines are preserved
        for line_div in div.find_all("div", class_=["line", "code-line", "container"]):
            line_div["style"] = "white-space: pre; display: block;"

        # Handle Confluence's code macro structure
        # Look for the table structure that Confluence uses for code blocks with line numbers
        code_tables = div.find_all("table", class_=["syntaxhighlighter", "highlighterTable"])
        for table in code_tables:
            # Extract the code content from the table
            code_content = ""
            for tr in table.find_all("tr"):
                line_num_td = tr.find("td", class_=["line-numbers", "gutter"])
                code_td = tr.find("td", class_=["code", "syntaxhighlighter"])

                if line_num_td and code_td:
                    code_line = code_td.get_text()
                    code_content += f"{code_line}\n"

            # If we extracted code content, replace the table with a pre element
            if code_content.strip():
                pre = soup.new_tag("pre")
                pre["class"] = "code-block"
                pre["style"] = "white-space: pre; font-family: monospace; background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;"
                pre.string = code_content
                table.replace_with(pre)

        # Preserve syntax highlighting spans
        for span in div.find_all("span", class_=["keyword", "string", "comment", "function", "number", "type", "class", "variable"]):
            # Keep any existing style and add white-space: pre
            existing_style = span.get("style", "")
            span["style"] = f"{existing_style}; white-space: pre;"

        # Look for Confluence's specific code macro structure
        # They sometimes use a div with class="code" containing a table
        code_divs = div.find_all("div", class_="code")
        for code_div in code_divs:
            # Check if it contains a table
            table = code_div.find("table")
            if table:
                # Extract the code content
                code_content = ""
                for tr in table.find_all("tr"):
                    tds = tr.find_all("td")
                    if len(tds) >= 2:  # Line number and code
                        code_line = tds[1].get_text()
                        code_content += f"{code_line}\n"

                # If we extracted code content, replace the table with a pre element
                if code_content.strip():
                    pre = soup.new_tag("pre")
                    pre["class"] = "code-block"
                    pre["style"] = "white-space: pre; font-family: monospace; background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;"
                    pre.string = code_content
                    table.replace_with(pre)
