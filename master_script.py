#!/usr/bin/env python3
"""
Master script for the Confluence Data Pipeline.
Fetches Confluence pages and spaces and saves them as PDF or HTML.
"""
import argparse
import logging
import sys
import time

from api_client.confluence_client import ConfluenceClient
from output_generator.html_generator import HTMLGenerator
from output_generator.html_to_pdf_converter import HTMLToPDFConverter
from utilities.state_manager import StateManager
from utilities.logger import setup_logging
from setup.config_conf import DEFAULT_DAYS, NEW_CONTENT_DIR, UPDATED_CONTENT_DIR

def parse_arguments():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Fetch Confluence pages and spaces and save them as PDF or HTML."
    )

    parser.add_argument(
        "--page_id",
        help="Fetch a specific page by its ID and its child pages"
    )

    parser.add_argument(
        "--page_title",
        help="Fetch a specific page by its title and its child pages (requires --space)"
    )

    parser.add_argument(
        "--space",
        help="Fetch all pages within the specified space (or use with --page_title to fetch a specific page and its children)"
    )

    parser.add_argument(
        "--no_recursive",
        action="store_true",
        help="Disable recursive fetching of child pages (default: recursive is enabled)"
    )

    parser.add_argument(
        "--html",
        action="store_true",
        help="Download pages in HTML format only (without PDF conversion)"
    )

    parser.add_argument(
        "--no_pdf_conversion",
        action="store_true",
        help="Skip converting HTML files to PDF after processing (only relevant with --html)"
    )

    parser.add_argument(
        "--no_days",
        type=int,
        default=None,
        help=f"Check for documents updated in the past N days. This option works with all modes: when fetching a specific page by ID or title, it will only process child pages updated in the past N days; when fetching all pages in a space, it will only process pages updated in the past N days; when run without other options, it searches for documents updated in the past N days across all spaces (default: {DEFAULT_DAYS} day for the default mode)."
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--wkhtmltopdf",
        help="Path to wkhtmltopdf executable for HTML to PDF conversion"
    )

    parser.add_argument(
        "--no_check_missing",
        action="store_true",
        help="Skip checking for pages missing from state file"
    )

    # No cookie refresh options needed - cookies are managed through a static file

    return parser.parse_args()

def process_page(page, state_manager, html_generator, html_to_pdf_converter=None, html_only=False, force_space=None, force_process=False):
    """Process a single page.

    Args:
        page (dict): Page data from the Confluence API
        state_manager (StateManager): State manager instance
        html_generator (HTMLGenerator): HTML generator instance
        html_to_pdf_converter (HTMLToPDFConverter, optional): HTML to PDF converter instance
        html_only (bool, optional): Whether to generate only HTML. Defaults to False.
        force_space (str, optional): If provided, forces processing of all pages in this space
        force_process (bool, optional): If True, skips state check and forces processing. Useful for first-time processing.

    Returns:
        tuple: (processed, stats_dict) where processed is a boolean indicating if the page was processed,
               and stats_dict contains the processing statistics
    """
    # Initialize stats dictionary
    stats = {
        "html_processed": 0,
        "html_skipped": 0,
        "html_failed": 0,
        "pdf_processed": 0,
        "pdf_skipped": 0,
        "pdf_failed": 0
    }

    page_id = page["id"]
    page_title = page["title"]

    # Determine if the page is new or updated
    content_type = None
    if force_process:
        # If force_process is True, treat as new
        content_type = "new"
    else:
        # Check if the page needs to be processed
        if not state_manager.should_process_page(page, force_space):
            stats["html_skipped"] += 1
            stats["pdf_skipped"] += 1
            return False, stats

        # Determine if the page is new or updated
        page_state = state_manager.get_page_state(page_id)
        if page_state is None:
            # Page is not in state file, so it's new
            content_type = "new"
            logging.info(f"New page: '{page_title}' (ID: {page_id})")
        else:
            # Page is in state file, so it's updated
            content_type = "updated"
            logging.info(f"Updated page: '{page_title}' (ID: {page_id})")

    logging.info(f"Processing {content_type} page '{page_title}' (ID: {page_id})")

    output_paths = {}

    try:
        # Always generate HTML first
        html_path = html_generator.generate_html(page, content_type=content_type)
        if not html_path:
            logging.error(f"Failed to generate HTML for page '{page_title}' (ID: {page_id})")
            stats["html_failed"] += 1
            stats["pdf_skipped"] += 1
            return False, stats

        output_paths["html"] = html_path
        stats["html_processed"] += 1

        # Convert HTML to PDF if requested and converter is available
        if not html_only and html_to_pdf_converter:
            # Create PDF directory structure mirroring HTML structure
            from pathlib import Path
            from setup.config_conf import PDF_OUTPUT_DIR

            # Get the space directory name and subdirectory (if any) from the HTML path
            html_path_obj = Path(html_path)

            # Check if the HTML path includes a content type subdirectory
            if content_type in [NEW_CONTENT_DIR, UPDATED_CONTENT_DIR]:
                # Path structure is: output/html/space_key/content_type/filename.html
                space_dir_name = html_path_obj.parent.parent.name
                content_type_dir = html_path_obj.parent.name  # 'new' or 'updated'

                # Create space and content type directories in PDF output if they don't exist
                pdf_space_dir = PDF_OUTPUT_DIR / space_dir_name
                pdf_space_dir.mkdir(exist_ok=True)

                pdf_content_type_dir = pdf_space_dir / content_type_dir
                pdf_content_type_dir.mkdir(exist_ok=True)

                # Set the PDF output path
                filename = html_path_obj.name.replace(".html", ".pdf")
                pdf_path = str(pdf_content_type_dir / filename)
            else:
                # Standard path structure: output/html/space_key/filename.html
                space_dir_name = html_path_obj.parent.name
                filename = html_path_obj.name.replace(".html", ".pdf")

                # Create space directory in PDF output if it doesn't exist
                pdf_space_dir = PDF_OUTPUT_DIR / space_dir_name
                pdf_space_dir.mkdir(exist_ok=True)

                # Set the PDF output path
                pdf_path = str(pdf_space_dir / filename)

            # Convert HTML to PDF
            logging.info(f"Converting HTML to PDF: {html_path} -> {pdf_path}")
            result = html_to_pdf_converter.convert_file(html_path, pdf_path)

            if result:
                output_paths["pdf"] = pdf_path
                stats["pdf_processed"] += 1
                logging.info(f"Successfully converted HTML to PDF for page '{page_title}' (ID: {page_id})")
            else:
                stats["pdf_failed"] += 1
                logging.error(f"Failed to convert HTML to PDF for page '{page_title}' (ID: {page_id})")
        else:
            # PDF conversion was skipped
            stats["pdf_skipped"] += 1

        # Update state
        state_manager.update_page_state(page, output_paths)
        return True, stats

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logging.error(f"Failed to process page '{page_title}' (ID: {page_id}): {e}")
        logging.error(f"Stack trace for page processing error:\n{error_trace}")
        stats["html_failed"] += 1
        stats["pdf_failed"] += 1
        return False, stats

def main():
    """Main entry point for the script."""
    args = parse_arguments()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logging(log_level)

    # Initialize components
    client = ConfluenceClient()

    state_manager = StateManager()
    html_generator = HTMLGenerator()

    # Initialize HTML to PDF converter if not in HTML-only mode
    html_to_pdf_converter = None
    if not args.html or not args.no_pdf_conversion:
        html_to_pdf_converter = HTMLToPDFConverter(args.wkhtmltopdf)

    # Track statistics
    stats = {
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "html_processed": 0,
        "html_skipped": 0,
        "html_failed": 0,
        "pdf_processed": 0,
        "pdf_skipped": 0,
        "pdf_failed": 0,
        "total_pages_from_api": 0  # Track total pages returned from API
    }

    # Determine recursive flag
    recursive = not args.no_recursive

    try:
        # Case 1: Fetch a specific page by ID and its child pages
        if args.page_id:
            if args.no_days is not None:
                logger.info(f"Fetching page with ID: {args.page_id} and its child pages updated in the last {args.no_days} days")
            else:
                logger.info(f"Fetching page with ID: {args.page_id} and its child pages")

            # Get the page and its child pages
            pages = client.get_child_pages(args.page_id, recursive)

            if not pages:
                logger.error(f"Page with ID {args.page_id} not found")
                stats["failed"] += 1
            else:
                logger.info(f"Found {len(pages)} pages (including the parent page and all child pages)")
                stats["total_pages_from_api"] += len(pages)

                # If no_days is specified, filter pages by last modified date
                if args.no_days is not None:
                    from datetime import datetime, timedelta
                    date_n_days_ago = (datetime.now() - timedelta(days=args.no_days)).strftime("%Y-%m-%d")

                    # Filter pages by last modified date
                    filtered_pages = []
                    for page in pages:
                        last_modified = page["version"].get("when", "")
                        if last_modified and last_modified >= date_n_days_ago:
                            filtered_pages.append(page)

                    logger.info(f"Found {len(filtered_pages)} pages updated in the last {args.no_days} days")
                    pages = filtered_pages

                # Process each page
                for page in pages:
                    processed, page_stats = process_page(page, state_manager, html_generator, html_to_pdf_converter, args.html)
                    # Update global stats
                    for key, value in page_stats.items():
                        stats[key] += value
                    if processed:
                        stats["processed"] += 1
                    else:
                        stats["skipped"] += 1

        # Case 2: Fetch a specific page by title within a space and its child pages
        elif args.page_title and args.space:
            if args.no_days is not None:
                logger.info(f"Fetching page with title '{args.page_title}' in space '{args.space}' and its child pages updated in the last {args.no_days} days")
            else:
                logger.info(f"Fetching page with title '{args.page_title}' in space '{args.space}' and its child pages")

            page = client.get_page_by_title(args.space, args.page_title)

            if page:
                # Get the page and its child pages
                pages = client.get_child_pages(page["id"], recursive)

                if not pages:
                    logger.error(f"Failed to fetch child pages for page '{args.page_title}'")
                    # At least process the parent page

                    # If no_days is specified, check if the parent page was updated in the specified time period
                    if args.no_days is not None:
                        from datetime import datetime, timedelta
                        date_n_days_ago = (datetime.now() - timedelta(days=args.no_days)).strftime("%Y-%m-%d")
                        last_modified = page["version"].get("when", "")

                        if last_modified and last_modified >= date_n_days_ago:
                            processed, page_stats = process_page(page, state_manager, html_generator, html_to_pdf_converter, args.html)
                            # Update global stats
                            for key, value in page_stats.items():
                                stats[key] += value
                            if processed:
                                stats["processed"] += 1
                            else:
                                stats["skipped"] += 1
                        else:
                            logger.info(f"Skipping page '{page['title']}' (ID: {page['id']}) - not updated in the last {args.no_days} days")
                            stats["skipped"] += 1
                            stats["html_skipped"] += 1
                            stats["pdf_skipped"] += 1
                    else:
                        # No time filter, process the parent page
                        processed, page_stats = process_page(page, state_manager, html_generator, html_to_pdf_converter, args.html)
                        # Update global stats
                        for key, value in page_stats.items():
                            stats[key] += value
                        if processed:
                            stats["processed"] += 1
                        else:
                            stats["skipped"] += 1
                else:
                    logger.info(f"Found {len(pages)} pages (including the parent page and all child pages)")
                    stats["total_pages_from_api"] += len(pages)

                    # If no_days is specified, filter pages by last modified date
                    if args.no_days is not None:
                        from datetime import datetime, timedelta
                        date_n_days_ago = (datetime.now() - timedelta(days=args.no_days)).strftime("%Y-%m-%d")

                        # Filter pages by last modified date
                        filtered_pages = []
                        for p in pages:
                            last_modified = p["version"].get("when", "")
                            if last_modified and last_modified >= date_n_days_ago:
                                filtered_pages.append(p)

                        logger.info(f"Found {len(filtered_pages)} pages updated in the last {args.no_days} days")
                        pages = filtered_pages

                    # Process each page
                    for p in pages:
                        processed, page_stats = process_page(p, state_manager, html_generator, html_to_pdf_converter, args.html)
                        # Update global stats
                        for key, value in page_stats.items():
                            stats[key] += value
                        if processed:
                            stats["processed"] += 1
                        else:
                            stats["skipped"] += 1
            else:
                logger.error(f"Page with title '{args.page_title}' not found in space '{args.space}'")
                stats["failed"] += 1

        # Case 3: Fetch all pages in a space
        elif args.space:
            if args.no_days is not None:
                logger.info(f"Fetching pages in space '{args.space}' updated in the last {args.no_days} days")
            else:
                logger.info(f"Fetching all pages in space '{args.space}'")

            pages = client.get_pages_in_space(args.space, recursive)

            # Track total pages from API
            if pages:
                logger.info(f"Found {len(pages)} pages in space '{args.space}'")
                stats["total_pages_from_api"] += len(pages)
            else:
                logger.info(f"No pages found in space '{args.space}'")

            # If no_days is specified, filter pages by last modified date
            if args.no_days is not None:
                from datetime import datetime, timedelta
                date_n_days_ago = (datetime.now() - timedelta(days=args.no_days)).strftime("%Y-%m-%d")

                # Filter pages by last modified date
                filtered_pages = []
                for page in pages:
                    last_modified = page["version"].get("when", "")
                    if last_modified and last_modified >= date_n_days_ago:
                        filtered_pages.append(page)

                logger.info(f"Found {len(filtered_pages)} pages updated in the last {args.no_days} days")
                pages = filtered_pages

            # Check if this is the first time processing this space
            # Get current state to check if pages are already in state
            current_state = state_manager.load_state()

            # Check if any pages from this space are in the state
            space_pages_in_state = any(
                current_state.get(page["id"], {}).get("space_key") == args.space
                for page in pages
            )

            # If this is the first time processing this space, we can optimize
            if not space_pages_in_state and pages:
                logger.info(f"First time processing space '{args.space}' - optimizing state checks")

                # Process all pages without redundant state checks
                for page in pages:
                    # Force processing by passing force_process=True
                    processed, page_stats = process_page(page, state_manager, html_generator,
                                                        html_to_pdf_converter, args.html,
                                                        force_space=args.space, force_process=True)
                    # Update global stats
                    for key, value in page_stats.items():
                        stats[key] += value
                    if processed:
                        stats["processed"] += 1
                    else:
                        stats["skipped"] += 1
            else:
                # Normal processing with state checks
                for page in pages:
                    processed, page_stats = process_page(page, state_manager, html_generator,
                                                        html_to_pdf_converter, args.html,
                                                        force_space=args.space)
                    # Update global stats
                    for key, value in page_stats.items():
                        stats[key] += value
                    if processed:
                        stats["processed"] += 1
                    else:
                        stats["skipped"] += 1

        # Case 4: Fetch updated pages across all spaces and pages missing from state
        # This is the default behavior when no specific options are provided
        else:
            # First, fetch pages updated in the specified time period
            # By default, this will search for documents updated in the past DEFAULT_DAYS (1) day
            # If --no_days N is specified, it will search for documents updated in the past N days
            days_to_check = args.no_days if args.no_days is not None else DEFAULT_DAYS
            logger.info(f"Fetching pages updated in the last {days_to_check} days")
            updated_pages = client.get_updated_pages(days_to_check)

            # Track total pages from API
            if updated_pages:
                logger.info(f"Found {len(updated_pages)} pages updated in the last {days_to_check} days")
                stats["total_pages_from_api"] += len(updated_pages)
            else:
                logger.info(f"No pages found updated in the last {days_to_check} days")

            # Process updated pages
            for page in updated_pages:
                processed, page_stats = process_page(page, state_manager, html_generator, html_to_pdf_converter, args.html)
                # Update global stats
                for key, value in page_stats.items():
                    stats[key] += value
                if processed:
                    stats["processed"] += 1
                else:
                    stats["skipped"] += 1

            # Check for pages missing from state file if not disabled
            if not args.no_check_missing:
                logger.info("Checking for pages missing from state file...")
                spaces = client.get_all_spaces()

                # Track pages we've already seen to avoid duplicates
                processed_page_ids = set()
                for page in updated_pages:
                    processed_page_ids.add(page["id"])

                # Get current state
                current_state = state_manager.load_state()

                # Process each space
                for space in spaces:
                    space_key = space["key"]
                    logger.info(f"Checking space '{space_key}' for pages missing from state file")

                    # Fetch all pages in the space
                    space_pages = client.get_pages_in_space(space_key, recursive)

                    # Track total pages from API
                    if space_pages:
                        logger.info(f"Found {len(space_pages)} pages in space '{space_key}' when checking for missing pages")
                        stats["total_pages_from_api"] += len(space_pages)
                    else:
                        logger.info(f"No pages found in space '{space_key}' when checking for missing pages")
                        continue  # Skip to next space if no pages found

                    # Check if this is the first time processing this space
                    space_pages_in_state = any(
                        current_state.get(page["id"], {}).get("space_key") == space_key
                        for page in space_pages
                    )

                    # Count how many new pages we found in this space
                    new_pages_count = 0

                    # If this is the first time processing this space, we can optimize
                    if not space_pages_in_state:
                        logger.info(f"First time processing space '{space_key}' - optimizing state checks")

                        # Filter out pages we've already processed
                        new_pages = [page for page in space_pages if page["id"] not in processed_page_ids]

                        if new_pages:
                            logger.info(f"Found {len(new_pages)} new pages in space '{space_key}'")
                            new_pages_count = len(new_pages)

                            # Process all pages without redundant state checks
                            for page in new_pages:
                                # Add to processed set to avoid duplicates
                                processed_page_ids.add(page["id"])

                                # Process the page with force_process=True to skip state check
                                processed, page_stats = process_page(page, state_manager, html_generator,
                                                                    html_to_pdf_converter, args.html,
                                                                    force_process=True)
                                # Update global stats
                                for key, value in page_stats.items():
                                    stats[key] += value
                                if processed:
                                    stats["processed"] += 1
                                else:
                                    stats["skipped"] += 1
                    else:
                        # Normal processing with state checks
                        # Process each page that's not in the state file and not already processed
                        for page in space_pages:
                            page_id = page["id"]

                            # Skip if we've already processed this page
                            if page_id in processed_page_ids:
                                continue

                            # Add to processed set to avoid duplicates
                            processed_page_ids.add(page_id)

                            # Check if page is in state file
                            if page_id not in current_state:
                                logger.info(f"Found page '{page['title']}' (ID: {page_id}) missing from state file")
                                new_pages_count += 1

                                # Process the page
                                processed, page_stats = process_page(page, state_manager, html_generator,
                                                                    html_to_pdf_converter, args.html)
                                # Update global stats
                                for key, value in page_stats.items():
                                    stats[key] += value
                                if processed:
                                    stats["processed"] += 1
                                else:
                                    stats["skipped"] += 1

                    logger.info(f"Processed {new_pages_count} new pages in space '{space_key}'")

                    # Add a small delay to avoid rate limiting
                    time.sleep(0.5)
            else:
                logger.info("Skipping check for pages missing from state file (--no_check_missing flag is set)")

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"An error occurred in main script execution: {e}")
        logger.error(f"Stack trace for main script error:\n{error_trace}")
        return 1

    # Print summary of content fetching
    logger.info("=" * 50)
    logger.info("API Response Summary:")
    logger.info(f"  Total Pages from API: {stats['total_pages_from_api']}")
    logger.info("-" * 50)
    logger.info("Content Fetching Summary:")
    logger.info(f"  Processed: {stats['processed']}")
    logger.info(f"  Skipped: {stats['skipped']}")
    logger.info(f"  Failed: {stats['failed']}")
    logger.info("-" * 50)
    logger.info("HTML Processing:")
    logger.info(f"  Processed HTML: {stats['html_processed']}")
    logger.info(f"  Skipped HTML: {stats['html_skipped']}")
    logger.info(f"  Failed HTML: {stats['html_failed']}")
    logger.info("-" * 50)
    logger.info("PDF Processing:")
    logger.info(f"  Processed PDF: {stats['pdf_processed']}")
    logger.info(f"  Skipped PDF: {stats['pdf_skipped']}")
    logger.info(f"  Failed PDF: {stats['pdf_failed']}")
    logger.info("=" * 50)

    return 0

if __name__ == "__main__":
    sys.exit(main())
