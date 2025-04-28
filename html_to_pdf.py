#!/usr/bin/env python3
"""
Command-line script to convert HTML files to PDF using pdfkit and wkhtmltopdf.
"""
import argparse
import logging
import sys
import os
from pathlib import Path

from output_generator.html_to_pdf_converter import HTMLToPDFConverter

def setup_logging(log_level=logging.INFO):
    """Set up logging for the application."""
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger()

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert HTML files to PDF using pdfkit and wkhtmltopdf."
    )
    
    parser.add_argument(
        "input",
        help="Path to the HTML file or directory containing HTML files"
    )
    
    parser.add_argument(
        "--output",
        help="Path to the output PDF file or directory. If not provided, uses the same path as the input but with .pdf extension."
    )
    
    parser.add_argument(
        "--wkhtmltopdf",
        help="Path to the wkhtmltopdf executable. If not provided, tries to find it in the system PATH."
    )
    
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process directories recursively"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()

def process_file(converter, html_path, output_path=None):
    """Process a single HTML file."""
    if output_path and os.path.isdir(output_path):
        # If output_path is a directory, use the same filename as the input but with .pdf extension
        filename = os.path.basename(html_path).replace('.html', '.pdf')
        output_path = os.path.join(output_path, filename)
        
    pdf_path = converter.convert_file(html_path, output_path)
    return pdf_path is not None

def process_directory(converter, directory_path, output_path=None, recursive=False):
    """Process all HTML files in a directory."""
    directory_path = Path(directory_path)
    
    # Create output directory if it doesn't exist
    if output_path:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all HTML files in the directory
    if recursive:
        html_files = list(directory_path.glob('**/*.html'))
    else:
        html_files = list(directory_path.glob('*.html'))
    
    if not html_files:
        logging.warning(f"No HTML files found in {directory_path}")
        return False
    
    success = True
    for html_file in html_files:
        # Determine output path
        if output_path:
            # Preserve directory structure if recursive
            if recursive:
                rel_path = html_file.relative_to(directory_path)
                pdf_file = output_path / rel_path.with_suffix('.pdf')
            else:
                pdf_file = output_path / html_file.name.replace('.html', '.pdf')
        else:
            pdf_file = html_file.with_suffix('.pdf')
        
        # Convert HTML to PDF
        if not converter.convert_file(html_file, pdf_file):
            success = False
    
    return success

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logging(log_level)
    
    # Initialize the converter
    converter = HTMLToPDFConverter(args.wkhtmltopdf)
    
    # Process input
    input_path = args.input
    output_path = args.output
    
    if os.path.isfile(input_path):
        # Process a single file
        if process_file(converter, input_path, output_path):
            logger.info("Conversion completed successfully")
            return 0
        else:
            logger.error("Conversion failed")
            return 1
    elif os.path.isdir(input_path):
        # Process a directory
        if process_directory(converter, input_path, output_path, args.recursive):
            logger.info("Conversion completed successfully")
            return 0
        else:
            logger.error("Some conversions failed")
            return 1
    else:
        logger.error(f"Input path does not exist: {input_path}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
