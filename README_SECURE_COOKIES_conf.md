# Secure Cookie Management for Confluence Data Pipeline

This document explains the secure cookie management approach implemented in the Confluence Data Pipeline.

## Overview

The Confluence Data Pipeline uses a secure approach to manage cookies for API authentication:

1. **Manual Cookie Entry**: Users manually enter cookies in a text file when needed
2. **Encryption**: Cookies are encrypted and stored securely after being loaded
3. **Auto-Expiration**: Cookies are automatically detected as expired and refreshed when needed
4. **File Cleanup**: The original cookie text file is cleared after cookies are loaded
5. **Audit Logging**: All cookie operations are logged for security auditing

## How It Works

### Initial Setup

1. When the script runs for the first time, it will:
   - Check for encrypted cookies (none will exist initially)
   - Look for cookies in the text file (`cookies/confluence_cookies.txt`)
   - If no valid cookies are found, it will prompt you to add them

2. When prompted to add cookies:
   - The script will open your Confluence site in a browser
   - You'll need to log in and extract cookies from your browser
   - Paste the cookies into the `cookies/confluence_cookies.txt` file
   - Run the script again

### Cookie Lifecycle

1. **Loading**: When cookies are loaded from the text file, they are:
   - Parsed into individual name-value pairs
   - Encrypted using a secure key
   - Stored in an encrypted file (`cookies/secure_cookies.enc`)
   - The original text file is cleared for security

2. **Usage**: During script execution:
   - Cookies are loaded from the encrypted storage
   - Added to the API session
   - Used for all API requests

3. **Expiration**: When cookies expire:
   - The script detects 401/403 errors or CAPTCHA challenges
   - Prompts you to update the cookies
   - Guides you through the process of obtaining fresh cookies

4. **Refresh**: When refreshing cookies:
   - The encrypted storage is cleared
   - You add new cookies to the text file
   - The process repeats from the loading step

### Security Features

1. **Encryption**: Cookies are encrypted using Fernet symmetric encryption
2. **Key Derivation**: The encryption key is derived using PBKDF2 with a salt
3. **Machine Binding**: The encryption key is partially derived from machine-specific information
4. **File Cleanup**: The plaintext cookie file is cleared after loading
5. **Audit Logging**: All cookie operations are logged to `logs/cookie_audit.log`
6. **Expiration Tracking**: Cookies have an automatic expiration time (14 days by default)

## Usage Instructions

### Adding Cookies for the First Time

1. Run the script. It will create an empty cookie file and prompt you to add cookies
2. Open your Confluence site in a browser
3. Log in if necessary
4. Open developer tools (F12) and go to the Network tab
5. Refresh the page
6. Click on any request to your Confluence domain
7. Find the "Cookie:" header in the request headers
8. Copy the entire cookie string
9. Open `cookies/confluence_cookies.txt`
10. Paste the cookie string (replacing any existing content)
11. Save the file and run the script again

### When Cookies Expire

When cookies expire, the script will:
1. Detect authentication errors
2. Log a message indicating that cookies need to be refreshed
3. Open your Confluence site in a browser
4. Provide instructions for updating cookies

Follow the same steps as the initial setup to add fresh cookies.

## Audit Logging

All cookie operations are logged to `logs/cookie_audit.log` with timestamps. The log includes:

- When cookies are loaded
- When cookies are encrypted and saved
- When cookies are detected as expired
- When the cookie file is truncated
- Any errors during cookie operations

The audit log does NOT include the actual cookie values for security reasons.

## Troubleshooting

### Authentication Errors

If you see authentication errors:
1. Check the logs for messages about expired cookies
2. Follow the instructions to update your cookies
3. Make sure you're copying the entire cookie string from your browser

### Encryption Errors

If you see encryption errors:
1. The encrypted cookie file may be corrupted
2. Delete the `cookies/secure_cookies.enc` file
3. Add fresh cookies to the text file
4. Run the script again

### Permission Issues

If you see permission errors:
1. Make sure you have write access to the `cookies` directory
2. Check that you can create and modify files in this directory
3. Verify that the script has permission to read/write the cookie files

## Security Considerations

1. The cookie file contains sensitive authentication information
2. The file is automatically cleared after loading for security
3. Cookies are stored in encrypted form
4. The encryption key is partially derived from machine-specific information
5. All cookie operations are logged for auditing

For additional security, consider:
1. Setting more restrictive file permissions on the `cookies` directory
2. Implementing a custom passphrase for the encryption key
3. Reducing the cookie expiration time from the default 14 days
