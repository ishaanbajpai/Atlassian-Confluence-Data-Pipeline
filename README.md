# Atlassian Confluence Data Pipeline

A modular Python program to fetch Confluence pages and spaces using the Confluence REST API. The program supports both HTML and PDF outputs, maintains a state file to track processed document versions, and is designed to be simple, readable, and easy to maintain.

## Features

- Fetch individual pages by ID or title
- Fetch all pages within a space
- Fetch updated or newly created documents within the last N days
- Support for recursive page fetching
- Output in PDF (default) or HTML format
- State management to avoid reprocessing unchanged documents
- Detailed logging and error handling

## Directory Structure

```
/
├── api_client/            # Code to connect and fetch from Confluence API
├── output_generator/      # Code to generate PDF/HTML outputs
├── utils/                 # Utility functions, logging, state management
├── setup/                 # Configuration files (e.g., API URLs, credentials)
├── output/                # Output directory for generated files
│   ├── pdf/               # PDF output files
│   └── html/              # HTML output files
├── logs/                  # Log files
├── master_script.py       # Main entry point using argparse
├── requirements.txt       # All dependencies
└── README.md              # Documentation
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd atlassian-confluence-data-pipeline
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your Confluence credentials:
   ```
   CONFLUENCE_URL=https://your-domain.atlassian.net
   CONFLUENCE_USERNAME=your-email@example.com
   CONFLUENCE_API_TOKEN=your-api-token
   ```

## Usage

The program is controlled through the `master_script.py` script, which provides various command-line options:

```
python master_script.py [options]
```

### Command-Line Options

- `--page_id [PAGE_ID]`: Fetch a specific page by its ID and its child pages
- `--page_title [PAGE_TITLE]`: Fetch a specific page by its title and its child pages (requires `--space`)
- `--space [SPACE_KEY]`: Fetch all pages within the specified space (or use with `--page_title` to fetch a specific page and its children)
- `--no_recursive`: Disable recursive fetching of child pages (default: recursive is enabled)
- `--html`: Download pages in HTML format only (without PDF conversion)
- `--no_pdf_conversion`: Skip converting HTML files to PDF after processing (only relevant with `--html`)
- `--no_days [N]`: Check for documents updated in the past N days. This option is optional and works with all modes:
  - When fetching a specific page by ID or title, it will only process child pages updated in the past N days
  - When fetching all pages in a space, it will only process pages updated in the past N days
  - When run without other options, it searches for documents updated in the past N days across all spaces (default: 1 day for this mode only)
- `--no_check_missing`: Skip checking for pages missing from state file
- `--verbose`: Enable verbose logging
- `--wkhtmltopdf [PATH]`: Path to wkhtmltopdf executable for HTML to PDF conversion

### Default Behavior

When run without any options, the script will:

1. Search for documents updated in the past day (default) across all accessible spaces
2. Check for documents that exist in Confluence but are missing from the state file
3. Process all found documents (generate HTML and PDF)
4. Update the state file with the processed documents

This default behavior ensures that:
- Recently updated documents are always processed
- Documents that were added to Confluence but not yet processed are eventually included
- The state file remains in sync with Confluence

You can run the script without any options to perform a daily update:
```
python master_script.py
```

### Examples

1. Fetch a specific page by ID and its child pages:
   ```
   python master_script.py --page_id 123456
   ```

2. Fetch a specific page by ID and its child pages without recursion (only immediate children):
   ```
   python master_script.py --page_id 123456 --no_recursive
   ```

3. Fetch a specific page by title and its child pages:
   ```
   python master_script.py --space SPACEKEY --page_title "Page Title"
   ```

4. Fetch all pages in a space:
   ```
   python master_script.py --space SPACEKEY
   ```

5. Fetch all pages in a space without recursively fetching child pages:
   ```
   python master_script.py --space SPACEKEY --no_recursive
   ```

6. Fetch all pages in a space and save as HTML:
   ```
   python master_script.py --space SPACEKEY --html
   ```

7. Fetch all pages updated in the last 7 days across all spaces:
   ```
   python master_script.py --no_days 7
   ```

8. Fetch a specific page and its child pages updated in the last 3 days:
   ```
   python master_script.py --page_id 123456 --no_days 3
   ```

9. Fetch a specific page by title and its child pages updated in the last 5 days:
   ```
   python master_script.py --space SPACEKEY --page_title "Page Title" --no_days 5
   ```

10. Fetch all pages in a space updated in the last 10 days:
   ```
   python master_script.py --space SPACEKEY --no_days 10
   ```

11. Fetch pages as HTML and automatically convert to PDF:
   ```
   python master_script.py --space SPACEKEY --html
   ```

12. Fetch pages as HTML without converting to PDF:
   ```
   python master_script.py --space SPACEKEY --html --no_pdf_conversion
   ```

13. Fetch pages as HTML and specify the wkhtmltopdf path:
   ```
   python master_script.py --space SPACEKEY --html --wkhtmltopdf "C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
   ```

14. Fetch only updated pages without checking for missing pages:
   ```
   python master_script.py --no_days 7 --no_check_missing
   ```

## State Management

The program maintains a state file (`state.json`) that tracks:
- Document ID
- Last processed version
- Last modified date
- Output file paths

This state file is used to avoid reprocessing unchanged documents.

When run without options, the program will:
1. Fetch pages updated within the specified time period (default: last 1 day) across all spaces
2. Check for pages that exist in Confluence but are missing from the state file

This ensures that:
- Recently updated documents are always processed
- Documents that were added to Confluence but not yet processed are eventually included
- The state file remains in sync with Confluence

You can modify this behavior with:
- `--no_days N`: Change the time period to look for updates (e.g., 7 days instead of 1)
- `--no_check_missing`: Skip checking for pages missing from the state file (only process recently updated pages)

When using the `--space` option, the program will:
1. Check if pages in the specified space are in the state file
2. Process pages that are missing from the state file
3. Process pages that have been updated since they were last processed
4. Skip pages that haven't changed since they were last processed

This ensures that all pages in the specified space are processed at least once, while still avoiding unnecessary reprocessing of unchanged content.

## Error Handling

The program logs errors and exceptions to a centralized logs directory. Each run creates a new log file with a timestamp.

## HTML Content Processing

The program includes advanced HTML content processing to ensure that Confluence content is properly rendered in the exported files:

### Image Handling

Images from Confluence are processed to ensure they display correctly:

- Confluence attachments are properly identified and preserved
- Relative URLs are converted to absolute URLs
- Images are made responsive with proper styling
- Images with titles are wrapped in figure elements with captions

### Code Block Handling

Code blocks from Confluence are processed to ensure proper formatting:

- Confluence code macros are properly identified and preserved
- Code blocks maintain their syntax highlighting
- Line numbers are preserved when available
- Code blocks are styled for better readability with proper font and background

## HTML to PDF Conversion

The program uses native HTML to PDF conversion for all documents. The Atlassian PDF export functionality has been removed as it was not working reliably. Here's how the current HTML to PDF conversion works:

1. HTML files are saved to `output/html/{space_key}/` directory
2. PDF files are generated from HTML and saved to `output/pdf/{space_key}/` directory
3. Both paths are tracked in the state file

You can control this behavior with the following options:

- `--html`: Only generate HTML files without converting to PDF
- `--no_pdf_conversion`: Skip PDF conversion even when using `--html` option
- `--wkhtmltopdf`: Specify the path to wkhtmltopdf executable

```
python master_script.py --space SPACEKEY
```

### Standalone Conversion Tool

You can also use the included standalone HTML to PDF conversion tool to convert existing HTML files to PDF:

```
python html_to_pdf.py [input] [options]
```

### Command-Line Options

- `input`: Path to the HTML file or directory containing HTML files
- `--output [OUTPUT]`: Path to the output PDF file or directory
- `--wkhtmltopdf [PATH]`: Path to the wkhtmltopdf executable
- `--recursive`: Process directories recursively
- `--verbose`: Enable verbose logging

### Prerequisites

- Install wkhtmltopdf: https://wkhtmltopdf.org/downloads.html
- Ensure wkhtmltopdf is in your system PATH or specify its path using the `--wkhtmltopdf` option

### Examples

1. Convert a single HTML file to PDF:
   ```
   python html_to_pdf.py output/html/MFS/page.html
   ```

2. Convert all HTML files in a directory to PDF:
   ```
   python html_to_pdf.py output/html/MFS --output output/pdf/MFS
   ```

3. Convert all HTML files recursively:
   ```
   python html_to_pdf.py output/html --output output/pdf --recursive
   ```

## License

[Specify your license here]
