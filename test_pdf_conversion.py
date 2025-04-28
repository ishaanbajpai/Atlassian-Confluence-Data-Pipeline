#!/usr/bin/env python3
"""
Test script for HTML to PDF conversion.
"""
import os
import logging
import sys
from pathlib import Path

from output_generator.html_to_pdf_converter import HTMLToPDFConverter, convert_html_to_pdf

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

def main():
    """Main entry point for the script."""
    # Check if any HTML files exist in the output/html directory
    html_dir = Path("output/html")
    if not html_dir.exists():
        logger.error(f"HTML directory not found: {html_dir}")
        return 1
        
    html_files = list(html_dir.glob("**/*.html"))
    if not html_files:
        logger.error(f"No HTML files found in {html_dir}")
        return 1
        
    logger.info(f"Found {len(html_files)} HTML files")
    
    # Try to find wkhtmltopdf in common locations
    wkhtmltopdf_paths = [
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
        r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
        "/usr/bin/wkhtmltopdf",
        "/usr/local/bin/wkhtmltopdf",
    ]
    
    wkhtmltopdf_path = None
    for path in wkhtmltopdf_paths:
        if os.path.exists(path):
            logger.info(f"Found wkhtmltopdf at: {path}")
            wkhtmltopdf_path = path
            break
    
    if not wkhtmltopdf_path:
        # Try to run wkhtmltopdf --version to see if it's in the PATH
        try:
            import subprocess
            result = subprocess.run(
                ["wkhtmltopdf", "--version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            if result.returncode == 0:
                logger.info(f"Found wkhtmltopdf in PATH: {result.stdout.strip()}")
                wkhtmltopdf_path = "wkhtmltopdf"  # Just use the command name
        except Exception as e:
            logger.error(f"Could not find wkhtmltopdf: {e}")
    
    if not wkhtmltopdf_path:
        logger.error("wkhtmltopdf not found. Please install it or specify the path manually.")
        logger.error("You can edit this script to set wkhtmltopdf_path to the correct path.")
        return 1
    
    # Create a converter with the found wkhtmltopdf path
    converter = HTMLToPDFConverter(wkhtmltopdf_path)
    
    # Process the first HTML file as a test
    test_file = html_files[0]
    logger.info(f"Converting test file: {test_file}")
    
    pdf_path = converter.convert_file(test_file)
    if pdf_path:
        logger.info(f"Successfully converted to PDF: {pdf_path}")
        return 0
    else:
        logger.error("PDF conversion failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
