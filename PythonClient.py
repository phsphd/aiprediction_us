#!/usr/bin/env python3
import requests
import json
import logging
from datetime import datetime, timedelta
import pytz  # Install with: pip install pytz

# Configure logging
logging.basicConfig(level=logging.INFO, 
                  format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class APIClient:
    """Client for accessing the V53a API with token authentication"""
    
    def __init__(self, base_url):
        """Initialize client with base URL"""
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.token = None
        self.token_expiry = None
    
    def authenticate(self, username, password):
        """Authenticate with the API and get a token"""
        url = f"{self.base_url}/api-token-auth/"
        data = {
            "username": username,
            "password": password
        }
        
        try:
            logger.info(f"Authenticating to {url}")
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["token"]
                
                # Parse expiry time
                try:
                    self.token_expiry = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
                    logger.info(f"Token obtained, valid until {self.token_expiry}")
                except (ValueError, KeyError):
                    # If no expiry or invalid format, set default 24-hour expiry
                    self.token_expiry = datetime.now(pytz.UTC) + timedelta(hours=24)
                    logger.info(f"Token obtained with default expiry {self.token_expiry}")
                
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return False
    
    def get_headers(self):
        """Get HTTP headers with authentication token"""
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_last_elements(self, did):
        """
        Get the last elements for a specific V53a record by DID
        
        Args:
            did (int): DID of the record to retrieve last elements for
            
        Returns:
            dict: API response data or None if request failed
        """
        if not self.token:
            logger.error("Not authenticated. Call authenticate() first.")
            return None
            
        url = f"{self.base_url}/api/v53a/{did}/last-elements/"
        
        try:
            logger.info(f"Requesting: GET {url}")
            response = requests.get(url, headers=self.get_headers())
            
            if response.status_code == 200:
                logger.info("Request successful")
                return response.json()
            else:
                logger.error(f"Error fetching last elements: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception fetching last elements: {str(e)}")
            return None


def main():
    """Main function to test the API"""
    # API URL
    base_url = "http://aiprediction.us"
    
    # Create client
    client = APIClient(base_url)
    
    # Authentication credentials
    username = input("Enter username: ")
    password = input("Enter password: ")
    
    # Authenticate
    if not client.authenticate(username, password):
        logger.error("Authentication failed. Exiting.")
        return
    
    # Test get_last_elements for DID 250520
    did = 250520
    logger.info(f"Testing get_last_elements for DID {did}")
    
    result = client.get_last_elements(did)
    
    if result:
        print("\n--- API Response ---")
        print(json.dumps(result, indent=2))
        
        # Print specific last element values
        if "last_elements" in result:
            print("\n--- Last Elements Values ---")
            for key, value in result["last_elements"].items():
                print(f"{key}: {value}")
    else:
        logger.error("Failed to get data. Check logs for details.")


if __name__ == "__main__":
    main()
