import requests
import json
import datetime
import logging
from datetime import datetime, timedelta

class APIClient:
    """Client for accessing the V53a API with token authentication"""
    
    def __init__(self, base_url, username=None, password=None):
        """
        Initialize client with base URL and optional credentials
        
        Args:
            base_url (str): Base URL of the API (e.g., 'http://aiprediction.us')
            username (str, optional): Username for authentication
            password (str, optional): Password for authentication
        """
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.username = username
        self.password = password
        self.token = None
        self.token_expiry = None
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self, username=None, password=None):
        """
        Authenticate with the API and get a token
        
        Args:
            username (str, optional): Override the username set in constructor
            password (str, optional): Override the password set in constructor
            
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        # Update credentials if provided
        if username:
            self.username = username
        if password:
            self.password = password
            
        # Ensure we have credentials
        if not self.username or not self.password:
            self.logger.error("No credentials provided for authentication")
            return False
            
        # Make authentication request
        url = f"{self.base_url}/api-token-auth/"
        data = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["token"]
                
                # Parse expiry time
                try:
                    self.token_expiry = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
                except (ValueError, KeyError):
                    # If no expiry or invalid format, set default 24-hour expiry
                    self.token_expiry = datetime.now() + timedelta(hours=24)
                
                self.logger.info(f"Authentication successful. Token valid until {self.token_expiry}")
                return True
            else:
                self.logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during authentication: {str(e)}")
            return False
    
    def is_token_valid(self):
        """
        Check if the current token is valid and not expired
        
        Returns:
            bool: True if token is valid, False otherwise
        """
        if not self.token or not self.token_expiry:
            return False
            
        # Add a 5-minute buffer to avoid edge cases
        buffer_time = timedelta(minutes=5)
        return datetime.now() + buffer_time < self.token_expiry
    
    def ensure_authenticated(self):
        """
        Ensure we have a valid authentication token, refreshing if needed
        
        Returns:
            bool: True if we have a valid token, False otherwise
        """
        if self.is_token_valid():
            return True
            
        # Token is invalid or expired, try to refresh
        self.logger.info("Token expired or invalid. Refreshing...")
        return self.authenticate()
    
    def get_headers(self):
        """
        Get HTTP headers with authentication token
        
        Returns:
            dict: Headers for API requests
        """
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_v53a_list(self, page=1, page_size=10, **filters):
        """
        Get a paginated list of V53a records with optional filtering
        
        Args:
            page (int): Page number
            page_size (int): Number of items per page
            **filters: Optional filters (e.g., id=123, did=456)
            
        Returns:
            dict: API response data or None if request failed
        """
        if not self.ensure_authenticated():
            return None
            
        url = f"{self.base_url}/api/v53a/"
        
        # Add pagination parameters
        params = {
            "page": page,
            "page_size": page_size
        }
        
        # Add filters
        params.update(filters)
        
        try:
            response = requests.get(url, headers=self.get_headers(), params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token might be expired - try refreshing and retrying
                if self.authenticate():
                    response = requests.get(url, headers=self.get_headers(), params=params)
                    if response.status_code == 200:
                        return response.json()
                
                self.logger.error(f"Authentication failed after token refresh: {response.status_code}")
                return None
            else:
                self.logger.error(f"Error fetching V53a list: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Exception fetching V53a list: {str(e)}")
            return None
    
    def get_v53a_detail(self, record_id):
        """
        Get details for a specific V53a record
        
        Args:
            record_id (int): ID of the record to retrieve
            
        Returns:
            dict: API response data or None if request failed
        """
        if not self.ensure_authenticated():
            return None
            
        url = f"{self.base_url}/api/v53a/{record_id}/"
        
        try:
            response = requests.get(url, headers=self.get_headers())
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token might be expired - try refreshing and retrying
                if self.authenticate():
                    response = requests.get(url, headers=self.get_headers())
                    if response.status_code == 200:
                        return response.json()
                
                self.logger.error(f"Authentication failed after token refresh: {response.status_code}")
                return None
            elif response.status_code == 404:
                self.logger.warning(f"Record {record_id} not found")
                return None
            else:
                self.logger.error(f"Error fetching V53a detail: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Exception fetching V53a detail: {str(e)}")
            return None
    
    def get_last_elements(self, did):
        """
        Get the last elements for a specific V53a record by DID
        
        Args:
            did (int): DID of the record to retrieve last elements for
            
        Returns:
            dict: API response data or None if request failed
        """
        if not self.ensure_authenticated():
            return None
            
        url = f"{self.base_url}/api/v53a/{did}/last-elements/"
        
        try:
            response = requests.get(url, headers=self.get_headers())
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token might be expired - try refreshing and retrying
                if self.authenticate():
                    response = requests.get(url, headers=self.get_headers())
                    if response.status_code == 200:
                        return response.json()
                
                self.logger.error(f"Authentication failed after token refresh: {response.status_code}")
                return None
            elif response.status_code == 404:
                self.logger.warning(f"Record with DID {did} not found")
                return None
            else:
                self.logger.error(f"Error fetching last elements: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Exception fetching last elements: {str(e)}")
            return None


# Usage example
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create client instance
    client = APIClient("http://aiprediction.us")
    
    # Authenticate
    if client.authenticate("your_username", "your_password"):
        print(f"Authentication successful! Token valid until {client.token_expiry}")
        
        # Get V53a list with pagination
        data = client.get_v53a_list(page=1, page_size=5)
        if data:
            print(f"Total records: {data['count']}")
            print(f"Records on page: {len(data['results'])}")
            
        # Get record details
        record_id = 123  # Replace with actual record ID
        record = client.get_v53a_detail(record_id)
        if record:
            print(f"Record details: {json.dumps(record, indent=2)}")
            
        # Get last elements
        did = 250520  # Replace with actual DID
        elements = client.get_last_elements(did)
        if elements:
            print(f"Last elements: {json.dumps(elements, indent=2)}")
    else:
        print("Authentication failed!")
