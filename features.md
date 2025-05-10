# Confluence Data Pipeline Features

This document outlines the complete feature set of the Confluence Data Pipeline, a comprehensive tool for fetching, processing, and exporting Confluence content.

## Core Features

### Content Fetching

- **Selective Content Retrieval**
  - Fetch content by space key
  - Fetch content by page ID
  - Fetch content by page title
  - Fetch content updated within a specific time period (e.g., last N days)

- **Recursive Content Retrieval**
  - Automatically fetch child pages when retrieving a parent page
  - Option to disable recursive fetching with `--no_recursive` flag

- **Differential Updates**
  - Track previously fetched content in a state file
  - Only fetch new or updated content since last run
  - Option to check for pages missing from state file
  - Option to skip checking for missing pages with `--no_check_missing` flag

- **Batch Processing**
  - Process multiple spaces in a single run
  - Process multiple pages in a single run
  - Automatic rate limiting to prevent API throttling

### Content Processing

- **HTML Generation**
  - Convert Confluence storage format to clean HTML
  - Process Confluence macros (code blocks, panels, etc.)
  - Handle Confluence-specific markup
  - Embed images as base64 data URLs
  - Clean and format HTML for better readability

- **PDF Generation**
  - Convert HTML content to PDF using wkhtmltopdf
  - Maintain formatting and styling in PDF output
  - Option to skip PDF generation with `--skip_pdf` flag
  - Configurable PDF output options

- **Organized Output Structure**
  - Separate directories for HTML and PDF output
  - Content organized by space
  - Separate directories for new and updated content
  - Consistent file naming based on page titles

### Authentication & Security

- **Secure Cookie Management**
  - Support for cookie-based authentication
  - Encryption of stored cookies
  - Automatic cookie expiration detection
  - Secure cookie file cleanup after loading
  - Audit logging of cookie operations

- **API Token Support**
  - Support for Atlassian API token authentication
  - Environment variable configuration for credentials
  - No hardcoded credentials in code

### Logging & Reporting

- **Comprehensive Logging**
  - Detailed logs of all operations
  - Error logging with stack traces
  - Configurable log levels
  - Timestamped log files

- **Operation Summary**
  - Summary of processed pages
  - Counts of new and updated pages
  - Counts of processed, skipped, and failed HTML files
  - Counts of processed, skipped, and failed PDF files
  - Total pages returned from API

## Command-Line Interface

### Basic Usage

```
python master_script.py [options]
```

### Options

- **Content Selection**
  - `--space SPACE_KEY`: Fetch content from a specific space
  - `--page_id PAGE_ID`: Fetch a specific page by ID
  - `--page_title PAGE_TITLE`: Fetch a specific page by title
  - `--no_days N`: Fetch content updated in the last N days

- **Processing Control**
  - `--no_recursive`: Disable recursive fetching of child pages
  - `--no_check_missing`: Skip checking for pages missing from state file
  - `--skip_pdf`: Skip PDF generation
  - `--log_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Set logging level

### Examples

```
# Fetch all updated content from all spaces in the last day
python master_script.py

# Fetch content from a specific space
python master_script.py --space SPACEKEY

# Fetch a specific page and its children
python master_script.py --page_id 123456

# Fetch content updated in the last 7 days
python master_script.py --no_days 7

# Fetch content from a space but skip PDF generation
python master_script.py --space SPACEKEY --skip_pdf
```

## Technical Features

### Modular Architecture

- **API Client Module**
  - Handles all Confluence API interactions
  - Manages authentication and session handling
  - Implements rate limiting and retry logic

- **HTML Generator Module**
  - Processes Confluence content into clean HTML
  - Handles Confluence-specific markup and macros
  - Embeds images and processes attachments

- **PDF Converter Module**
  - Converts HTML to PDF using wkhtmltopdf
  - Configurable PDF generation options
  - Error handling for PDF conversion issues

- **State Management Module**
  - Tracks processed pages and their metadata
  - Enables differential updates
  - Persists state between runs

### Error Handling

- **Robust Error Recovery**
  - Graceful handling of API errors
  - Retry logic for transient failures
  - Detailed error reporting
  - Continues processing after non-fatal errors

- **Authentication Error Handling**
  - Detection of expired cookies
  - Prompts for cookie refresh when needed
  - Handles CAPTCHA and human verification challenges

### Performance Optimizations

- **Efficient API Usage**
  - Batch API requests where possible
  - Only fetch necessary content
  - Implement rate limiting to prevent throttling

- **Parallel Processing**
  - Process multiple pages concurrently
  - Balance performance with API rate limits

## Configuration

- **Environment Variables**
  - `CONFLUENCE_URL`: Base URL of your Confluence instance
  - `CONFLUENCE_USERNAME`: Username for authentication
  - `CONFLUENCE_API_TOKEN`: API token for authentication
  - `CONFLUENCE_API_VERSION`: API version to use (default: 1.0)

- **Directory Structure**
  - `confluence_output/`: Base output directory
  - `confluence_output/html/`: HTML output
  - `confluence_output/pdf/`: PDF output
  - `logs/`: Log files
  - `cookies/`: Cookie storage (encrypted)

## Security Considerations

- No hardcoded credentials
- Sensitive data stored in environment variables
- Cookies encrypted when stored
- Cookie files cleared after loading
- Audit logging for security-related operations
- JavaScript disabled in PDF generation to prevent DOS attacks
