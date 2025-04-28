"""
HTML to PDF converter using pdfkit and wkhtmltopdf.
This module provides a simple way to convert HTML files to PDF.
"""
import os
import logging
import pdfkit
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Default path to wkhtmltopdf executable - modify this to match your installation path
# For Windows, this might be something like:
DEFAULT_WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
# For Linux, this might be something like:
# DEFAULT_WKHTMLTOPDF_PATH = "/usr/bin/wkhtmltopdf"
# Set to None to try to find wkhtmltopdf automatically:
# DEFAULT_WKHTMLTOPDF_PATH = None

def find_wkhtmltopdf():
    """Try to find wkhtmltopdf in the system PATH."""
    try:
        # Try to run wkhtmltopdf --version
        result = subprocess.run(
            ["wkhtmltopdf", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if result.returncode == 0:
            logger.info(f"Found wkhtmltopdf: {result.stdout.strip()}")
            return "wkhtmltopdf"  # Return just the command name
    except Exception as e:
        logger.debug(f"Could not find wkhtmltopdf in PATH: {e}")

    # Check common installation paths
    common_paths = [
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
        r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
        "/usr/bin/wkhtmltopdf",
        "/usr/local/bin/wkhtmltopdf",
    ]

    for path in common_paths:
        if os.path.exists(path):
            logger.info(f"Found wkhtmltopdf at: {path}")
            return path

    return None

class HTMLToPDFConverter:
    """Converter for HTML to PDF using pdfkit and wkhtmltopdf."""

    def __init__(self, wkhtmltopdf_path=None):
        """Initialize the HTML to PDF converter.

        Args:
            wkhtmltopdf_path (str, optional): Path to wkhtmltopdf executable.
                If None, will try to find it automatically.
        """
        # Try to find wkhtmltopdf if path not provided
        if wkhtmltopdf_path is None:
            # First try the default path if set
            if DEFAULT_WKHTMLTOPDF_PATH:
                self.wkhtmltopdf_path = DEFAULT_WKHTMLTOPDF_PATH
            else:
                # Try to find wkhtmltopdf in the system
                self.wkhtmltopdf_path = find_wkhtmltopdf()
        else:
            self.wkhtmltopdf_path = wkhtmltopdf_path

        if self.wkhtmltopdf_path:
            logger.info(f"Using wkhtmltopdf at: {self.wkhtmltopdf_path}")
        else:
            logger.warning("wkhtmltopdf not found. PDF conversion may fail.")
            logger.warning("Please install wkhtmltopdf or specify the path manually.")
            logger.warning("You can set DEFAULT_WKHTMLTOPDF_PATH in the html_to_pdf_converter.py file.")

        # Configure pdfkit options
        self.options = {
            'quiet': '',
            'enable-local-file-access': '',
            'javascript-delay': '2000',  # Wait 2 seconds for any essential JS
            # JavaScript settings
            'enable-javascript': True,    # Enable JavaScript for proper image rendering
            'disable-external-links': False,
            'disable-internal-links': False,
            'print-media-type': True,
            'encoding': 'UTF-8',
            'images': True,              # Explicitly enable images
            'load-error-handling': 'ignore',
            'load-media-error-handling': 'ignore',
            'enable-smart-shrinking': True,
            'image-quality': 100,        # Use highest image quality
            'image-dpi': 300,            # Use high DPI for images
        }

        # Configure pdfkit configuration
        self.config = None
        if self.wkhtmltopdf_path:
            self.config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path)

    def convert_file(self, html_path, pdf_path=None):
        """Convert an HTML file to PDF.

        Args:
            html_path (str): Path to the HTML file
            pdf_path (str, optional): Path for the output PDF file.
                If None, uses the same path as the HTML file but with .pdf extension.

        Returns:
            str: Path to the generated PDF file or None if conversion failed
        """
        # Check if wkhtmltopdf is available
        if not self.wkhtmltopdf_path:
            logger.error("Cannot convert HTML to PDF: wkhtmltopdf not found")
            logger.error("Please install wkhtmltopdf and make sure it's in your PATH")
            logger.error("Or set DEFAULT_WKHTMLTOPDF_PATH in html_to_pdf_converter.py")
            return None

        try:
            html_path = Path(html_path)

            # If no PDF path is provided, use the same path as the HTML file but with .pdf extension
            if pdf_path is None:
                pdf_path = html_path.with_suffix('.pdf')
            else:
                pdf_path = Path(pdf_path)

            logger.info(f"Converting HTML file {html_path} to PDF {pdf_path}")

            # Ensure the output directory exists
            pdf_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert HTML to PDF
            if self.config:
                pdfkit.from_file(
                    str(html_path),
                    str(pdf_path),
                    options=self.options,
                    configuration=self.config
                )
            else:
                pdfkit.from_file(
                    str(html_path),
                    str(pdf_path),
                    options=self.options
                )

            # Verify the PDF was created and is not empty
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                logger.info(f"Successfully converted HTML to PDF: {pdf_path}")
                return str(pdf_path)
            else:
                logger.error(f"PDF file was not created or is empty: {pdf_path}")
                return None

        except Exception as e:
            logger.error(f"Failed to convert HTML to PDF: {e}")
            return None

    def convert_string(self, html_content, pdf_path):
        """Convert HTML content string to PDF.

        Args:
            html_content (str): HTML content as a string
            pdf_path (str): Path for the output PDF file

        Returns:
            str: Path to the generated PDF file or None if conversion failed
        """
        # Check if wkhtmltopdf is available
        if not self.wkhtmltopdf_path:
            logger.error("Cannot convert HTML to PDF: wkhtmltopdf not found")
            logger.error("Please install wkhtmltopdf and make sure it's in your PATH")
            logger.error("Or set DEFAULT_WKHTMLTOPDF_PATH in html_to_pdf_converter.py")
            return None

        try:
            pdf_path = Path(pdf_path)

            logger.info(f"Converting HTML content to PDF {pdf_path}")

            # Ensure the output directory exists
            pdf_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert HTML to PDF
            if self.config:
                pdfkit.from_string(
                    html_content,
                    str(pdf_path),
                    options=self.options,
                    configuration=self.config
                )
            else:
                pdfkit.from_string(
                    html_content,
                    str(pdf_path),
                    options=self.options
                )

            # Verify the PDF was created and is not empty
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                logger.info(f"Successfully converted HTML content to PDF: {pdf_path}")
                return str(pdf_path)
            else:
                logger.error(f"PDF file was not created or is empty: {pdf_path}")
                return None

        except Exception as e:
            logger.error(f"Failed to convert HTML content to PDF: {e}")
            return None


def convert_html_to_pdf(html_path, pdf_path=None, wkhtmltopdf_path=None):
    """Convenience function to convert an HTML file to PDF.

    Args:
        html_path (str): Path to the HTML file
        pdf_path (str, optional): Path for the output PDF file.
            If None, uses the same path as the HTML file but with .pdf extension.
        wkhtmltopdf_path (str, optional): Path to wkhtmltopdf executable.

    Returns:
        str: Path to the generated PDF file or None if conversion failed
    """
    # If wkhtmltopdf_path is not provided, try to use the default path
    if wkhtmltopdf_path is None and DEFAULT_WKHTMLTOPDF_PATH:
        wkhtmltopdf_path = DEFAULT_WKHTMLTOPDF_PATH

    converter = HTMLToPDFConverter(wkhtmltopdf_path)
    return converter.convert_file(html_path, pdf_path)
