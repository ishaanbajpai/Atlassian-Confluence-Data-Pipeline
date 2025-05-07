# Cookie Management for Confluence Data Pipeline

This document explains how to manage cookies for the Confluence Data Pipeline to avoid CAPTCHA challenges.

## Overview

The Confluence Data Pipeline requires valid cookies to access the Confluence API without triggering CAPTCHA challenges. This implementation uses a simple approach where cookies are stored in a static text file and loaded automatically by the script.

## How It Works

1. Cookies are stored in a plain text file: `cookies/confluence_cookies.txt`
2. When the script starts, it automatically loads cookies from this file
3. If a CAPTCHA challenge is detected, the script provides instructions for updating the cookie file
4. After updating the cookie file, you can run the script again

## Initial Setup

1. Run the script once. It will create an empty cookie file if it doesn't exist:
   ```
   python master_script.py --space YourSpace
   ```

2. When the script encounters a CAPTCHA challenge, it will:
   - Display instructions in the log
   - Open your Confluence site in a browser
   - Provide steps to extract and update cookies

3. Follow the instructions to update the cookie file:
   - Log in to Confluence in your browser
   - Open developer tools (F12 or right-click > Inspect)
   - Go to the Network tab
   - Refresh the page
   - Click on any request to confluence.atlassian.net
   - Find the 'Cookie:' header in the request headers
   - Copy the entire cookie string
   - Paste it into the file: `cookies/confluence_cookies.txt`

4. Run the script again. It should now work without CAPTCHA challenges.

### Example Cookie

Here's an example of what a cookie string might look like (this is a simplified example - real cookies will be much longer):

```
cloud.session.token=eyJraWQiOiJzZXNzaW9uLXNlcnZpY2VcL3Nlc3Npb24tc2VydmljZSIsImFsZyI6IlJTMjU2In0.eyJhc3NvY2lhdGlvbnMiOltdLCJzdWIiOiI1NDM4OTc6MTcwNzM4OTM4MDQyMDpjMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAwIiwiZW1haWxEb21haW4iOiJleGFtcGxlLmNvbSIsImltcGVyc29uYXRpb24iOltdLCJjcmVhdGVkIjoxNzA3Mzg5MzgwLCJyZWZyZXNoVGltZW91dCI6MTcwNzM5MDI4MCwiaXNzIjoic2Vzc2lvbi1zZXJ2aWNlIiwidG9rZW5DbGFzcyI6ImFjY2VzcyIsImV4cCI6MTcwNzM5MDI4MCwiaWF0IjoxNzA3Mzg5MzgwLCJqdGkiOiJjMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAiLCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJuYmYiOjE3MDczODkzODB9.Signature; atlassian.xsrf.token=ABCD-1234-WXYZ-5678|abcdefghijklmnopqrstuvwxyz123456789|lin; _ga=GA1.2.1234567890.1234567890; _gid=GA1.2.1234567890.1234567890; ajs_anonymous_id=abcdef12-3456-7890-abcd-ef1234567890; ajs_user_id=1234567890abcdef; OptanonConsent=isGpcEnabled=0&datestamp=20240507T123456Z&version=202309.1.0&isIABGlobal=false&hosts=&consentId=abcdef12-3456-7890-abcd-ef1234567890&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&geolocation=US%3BCA&AwaitingReconsent=false
```

**Important Note**: The example above is for illustration only. Your actual cookie string will be much longer and contain different values. Always use the cookie string from your own browser session.

## Updating Cookies

Cookies typically expire after some time. When they expire, you'll need to update them:

1. If the script encounters a CAPTCHA challenge, it will log instructions for updating cookies
2. Follow the same steps as in the initial setup to extract and update cookies
3. Run the script again

## Manual Cookie Update

You can also update cookies manually at any time:

1. Open your Confluence site in a browser
2. Log in if necessary
3. Open developer tools and go to the Network tab
4. Refresh the page
5. Find a request to confluence.atlassian.net
6. Copy the Cookie header value
7. Replace the content of `cookies/confluence_cookies.txt` with the copied value

## Troubleshooting

### CAPTCHA Still Appears

If you still encounter CAPTCHA challenges after updating cookies:

1. Make sure you copied the entire cookie string
2. Check that the cookie file is saved correctly
3. Try logging out and logging back in to Confluence before copying cookies
4. Try using a different browser to log in and extract cookies

### API Errors

If you see API errors like 401 Unauthorized or 403 Forbidden:

1. Your cookies may have expired - update them following the steps above
2. Check that your Confluence credentials in the `.env` file are correct
3. Make sure you have the necessary permissions to access the content

## No Cookie Refresh Script Needed

With this approach, you do not need to run any separate cookie refresh script. The system is designed to:

1. Automatically load cookies from the static file (`cookies/confluence_cookies.txt`)
2. Detect when cookies are invalid or expired (when CAPTCHA challenges appear)
3. Provide clear instructions for manually updating the cookie file

This simplifies the process by eliminating the need for browser automation or additional scripts. You only need to manually update the cookie file when prompted by the system.

## Scheduled Tasks

For scheduled tasks, you'll need to:

1. Update cookies manually before they expire (typically every few weeks)
2. Set up a reminder to update cookies regularly
3. Consider setting up a separate monitoring script to check and notify when cookies need updating

## Security Considerations

1. The cookie file contains sensitive authentication information
2. Ensure the cookie file has appropriate permissions
3. Do not share or commit the cookie file to version control
4. Consider encrypting the cookie file for additional security
