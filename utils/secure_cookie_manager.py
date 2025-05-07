"""
Secure cookie management utilities for the Confluence API client.
This module handles loading cookies from a static file, encrypting them,
and managing their lifecycle securely.
"""
import logging
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Set up logger
logger = logging.getLogger(__name__)

# Define file paths
COOKIE_FILE = Path("cookies/confluence_cookies.txt")
ENCRYPTED_COOKIE_FILE = Path("cookies/secure_cookies.enc")
COOKIE_AUDIT_LOG = Path("logs/cookie_audit.log")
SALT_FILE = Path("cookies/.salt")

# Cookie expiration time (14 days in seconds)
COOKIE_EXPIRATION = 14 * 24 * 60 * 60  # 14 days

class SecureCookieManager:
    """Manages cookies securely with encryption and audit logging."""
    
    def __init__(self):
        """Initialize the secure cookie manager."""
        self._ensure_directories()
        self._init_encryption()
        self.last_loaded = 0
        self.cookie_expiration_time = None
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        Path("cookies").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
    
    def _init_encryption(self):
        """Initialize encryption with a secure key."""
        # Generate or load salt
        if not SALT_FILE.exists():
            self._generate_salt()
        
        # Load salt
        with open(SALT_FILE, 'rb') as f:
            salt = f.read()
        
        # Use a fixed passphrase combined with environment-specific data
        # This is more secure than hardcoding a key but still allows automated decryption
        base_passphrase = "ConfluenceDataPipeline"
        machine_specific = os.environ.get('COMPUTERNAME', '') + os.environ.get('USERNAME', '')
        passphrase = (base_passphrase + machine_specific).encode()
        
        # Generate key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase))
        self.cipher = Fernet(key)
    
    def _generate_salt(self):
        """Generate a new salt for encryption and save it."""
        salt = os.urandom(16)
        with open(SALT_FILE, 'wb') as f:
            f.write(salt)
        logger.info("Generated new encryption salt")
        self._audit_log("Generated new encryption salt")
    
    def _audit_log(self, message):
        """Write an entry to the audit log.
        
        Args:
            message (str): The message to log
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(COOKIE_AUDIT_LOG, 'a') as f:
            f.write(f"{timestamp} - {message}\n")
    
    def _encrypt_cookies(self, cookie_data):
        """Encrypt cookie data.
        
        Args:
            cookie_data (dict): Cookie data to encrypt
            
        Returns:
            bytes: Encrypted cookie data
        """
        # Add expiration timestamp
        cookie_data['_expiration_time'] = time.time() + COOKIE_EXPIRATION
        
        # Convert to JSON and encrypt
        json_data = json.dumps(cookie_data).encode()
        return self.cipher.encrypt(json_data)
    
    def _decrypt_cookies(self):
        """Decrypt cookie data from file.
        
        Returns:
            dict: Decrypted cookie data or None if decryption fails
        """
        if not ENCRYPTED_COOKIE_FILE.exists():
            return None
        
        try:
            with open(ENCRYPTED_COOKIE_FILE, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            cookie_data = json.loads(decrypted_data.decode())
            
            # Check if cookies have expired
            if '_expiration_time' in cookie_data:
                self.cookie_expiration_time = cookie_data['_expiration_time']
                if time.time() > cookie_data['_expiration_time']:
                    logger.warning("Stored cookies have expired")
                    self._audit_log("Detected expired cookies")
                    return None
            
            return cookie_data
        except Exception as e:
            logger.error(f"Failed to decrypt cookies: {e}")
            self._audit_log(f"Decryption error: {str(e)[:100]}")
            return None
    
    def load_cookies_to_session(self, session, base_url):
        """Load cookies into the session, prompting for new ones if needed.
        
        Args:
            session: The requests session to update with cookies
            base_url (str): The base URL for the domain
            
        Returns:
            bool: True if cookies were successfully loaded, False otherwise
        """
        # Record this operation
        self._audit_log("Attempting to load cookies")
        
        # Try to load encrypted cookies first
        cookie_data = self._decrypt_cookies()
        
        if cookie_data:
            # Cookies are valid, load them into the session
            domain = urlparse(base_url).netloc
            cookie_count = 0
            
            for name, value in cookie_data.items():
                # Skip metadata fields
                if name.startswith('_'):
                    continue
                
                session.cookies.set(name, value, domain=domain)
                cookie_count += 1
            
            expiry_date = datetime.fromtimestamp(self.cookie_expiration_time).strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Loaded {cookie_count} cookies from encrypted storage (expires: {expiry_date})")
            self._audit_log(f"Loaded {cookie_count} cookies from encrypted storage")
            self.last_loaded = time.time()
            return True
        
        # No valid encrypted cookies, check for cookies in the text file
        if COOKIE_FILE.exists():
            try:
                with open(COOKIE_FILE, 'r') as f:
                    cookie_text = f.read().strip()
                
                if cookie_text and not cookie_text.startswith('#'):
                    # Parse and store cookies
                    cookie_data = self._parse_cookie_string(cookie_text)
                    
                    if cookie_data:
                        # Encrypt and save cookies
                        encrypted_data = self._encrypt_cookies(cookie_data)
                        with open(ENCRYPTED_COOKIE_FILE, 'wb') as f:
                            f.write(encrypted_data)
                        
                        # Truncate the original cookie file for security
                        self._truncate_cookie_file()
                        
                        # Log the operation
                        logger.info("Encrypted and saved new cookies")
                        self._audit_log("Encrypted and saved new cookies from text file")
                        
                        # Now load the cookies into the session
                        return self.load_cookies_to_session(session, base_url)
            except Exception as e:
                logger.error(f"Error processing cookie file: {e}")
                self._audit_log(f"Error processing cookie file: {str(e)[:100]}")
        
        # If we get here, we couldn't load cookies
        logger.warning("No valid cookies found")
        self._create_empty_cookie_file_with_instructions()
        return False
    
    def _parse_cookie_string(self, cookie_text):
        """Parse a cookie string into a dictionary.
        
        Args:
            cookie_text (str): The cookie string from the browser
            
        Returns:
            dict: Parsed cookies as a dictionary
        """
        cookie_data = {}
        cookie_parts = cookie_text.split(';')
        
        for part in cookie_parts:
            part = part.strip()
            if '=' in part:
                name, value = part.split('=', 1)
                cookie_data[name.strip()] = value.strip()
        
        if cookie_data:
            logger.info(f"Successfully parsed {len(cookie_data)} cookies")
            self._audit_log(f"Parsed {len(cookie_data)} cookies from text input")
            return cookie_data
        
        return None
    
    def _truncate_cookie_file(self):
        """Truncate the cookie file after loading for security."""
        try:
            with open(COOKIE_FILE, 'w') as f:
                f.write("# Paste your Confluence cookies here when prompted\n")
                f.write("# This file will be cleared after cookies are loaded for security\n")
            logger.info("Truncated cookie file for security")
            self._audit_log("Truncated cookie file after loading")
            return True
        except Exception as e:
            logger.error(f"Failed to truncate cookie file: {e}")
            self._audit_log(f"Failed to truncate cookie file: {str(e)[:100]}")
            return False
    
    def _create_empty_cookie_file_with_instructions(self):
        """Create an empty cookie file with instructions."""
        try:
            with open(COOKIE_FILE, 'w') as f:
                f.write("# Paste your Confluence cookies here (the entire cookie string from the Cookie header)\n")
                f.write("# Example: cloud.session.token=abc123; atlassian.xsrf.token=xyz789\n\n")
                f.write("# IMPORTANT: This file will be cleared after cookies are loaded for security\n")
                f.write("# Follow the instructions in the logs to obtain your cookies\n")
            logger.info("Created empty cookie file with instructions")
            self._audit_log("Created empty cookie file with instructions")
            return True
        except Exception as e:
            logger.error(f"Failed to create empty cookie file: {e}")
            self._audit_log(f"Failed to create empty cookie file: {str(e)[:100]}")
            return False
    
    def is_cookie_refresh_needed(self):
        """Check if cookies need to be refreshed based on expiration.
        
        Returns:
            bool: True if cookies need to be refreshed, False otherwise
        """
        # Check if we have encrypted cookies
        if not ENCRYPTED_COOKIE_FILE.exists():
            return True
        
        # Try to decrypt to check expiration
        cookie_data = self._decrypt_cookies()
        if not cookie_data:
            return True
        
        # Cookies are still valid
        return False
    
    def clear_encrypted_cookies(self):
        """Clear encrypted cookies (for testing or security purposes)."""
        if ENCRYPTED_COOKIE_FILE.exists():
            try:
                ENCRYPTED_COOKIE_FILE.unlink()
                logger.info("Cleared encrypted cookies")
                self._audit_log("Manually cleared encrypted cookies")
                return True
            except Exception as e:
                logger.error(f"Failed to clear encrypted cookies: {e}")
                self._audit_log(f"Failed to clear encrypted cookies: {str(e)[:100]}")
                return False
        return True
