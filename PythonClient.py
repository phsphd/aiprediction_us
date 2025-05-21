#!/usr/bin/env python3
import requests
import json
import logging
import argparse
import sys
from datetime import datetime, timedelta
import urllib.parse

# Configure detailed HTTP debugging if needed
try:
    import http.client as http_client
except ImportError:
    pass

class APIClient:
    """Client for accessing the V53a API with token authentication"""
    
    def __init__(self, base_url, username=None, password=None, debug=False, http_debug=False):
        """Initialize client with base URL and optional credentials"""
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.username = username
        self.password = password
        self.token = None
        self.token_expiry = None
        self.debug = debug
        
        # Configure very detailed HTTP debugging if requested
        if http_debug:
            http_client.HTTPConnection.debuglevel = 1
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
        
        # Configure logger
        self.logger = logging.getLogger(__name__)
        if self.debug or http_debug:
            logging.basicConfig(level=logging.DEBUG, 
                             format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        else:
            logging.basicConfig(level=logging.INFO, 
                             format='%(asctime)s - %(levelname)s - %(message)s')
    
    def authenticate(self, username=None, password=None, auth_endpoint=None):
        """Authenticate with the API and get a token"""
        # Update credentials if provided
        if username:
            self.username = username
        if password:
            self.password = password
            
        # Ensure we have credentials
        if not self.username or not self.password:
            self.logger.error("No credentials provided for authentication")
            return False
            
        # Determine authentication URL
        if auth_endpoint:
            url = f"{self.base_url}/{auth_endpoint.lstrip('/')}"
        else:
            url = f"{self.base_url}/api-token-auth/"
            
        self.logger.info(f"Authenticating to URL: {url}")
            
        # Try different authentication methods
        return self._try_auth_methods(url)
    
    def _try_auth_methods(self, url):
        """Try different authentication methods to find one that works"""
        methods = [
            {"name": "JSON data", "method": self._try_json_auth},
            {"name": "Form data", "method": self._try_form_auth},
            {"name": "URL encoded form", "method": self._try_urlencoded_auth},
            {"name": "Basic Auth", "method": self._try_basic_auth}
        ]
        
        for method in methods:
            self.logger.info(f"Trying authentication method: {method['name']}")
            success = method["method"](url)
            if success:
                self.logger.info(f"Authentication succeeded with method: {method['name']}")
                return True
                
        self.logger.error("All authentication methods failed")
        return False
    
    def _try_json_auth(self, url):
        """Try JSON authentication"""
        json_data = {
            "username": self.username,
            "password": self.password
        }
        
        headers = {"Content-Type": "application/json"}
        
        self.logger.debug(f"POST request to {url} with JSON data: {json_data}")
        try:
            response = requests.post(url, json=json_data, headers=headers)
            self._log_response_details(response)
            
            if response.status_code == 200:
                return self._process_auth_response(response)
        except Exception as e:
            self.logger.error(f"Error during JSON authentication: {str(e)}")
        return False
    
    def _try_form_auth(self, url):
        """Try form data authentication"""
        form_data = {
            "username": self.username,
            "password": self.password
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        self.logger.debug(f"POST request to {url} with form data: {form_data}")
        try:
            response = requests.post(url, data=form_data, headers=headers)
            self._log_response_details(response)
            
            if response.status_code == 200:
                return self._process_auth_response(response)
        except Exception as e:
            self.logger.error(f"Error during form authentication: {str(e)}")
        return False
    
    def _try_urlencoded_auth(self, url):
        """Try URL-encoded authentication"""
        form_data = urllib.parse.urlencode({
            "username": self.username,
            "password": self.password
        })
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        self.logger.debug(f"POST request to {url} with URL-encoded data")
        try:
            response = requests.post(url, data=form_data, headers=headers)
            self._log_response_details(response)
            
            if response.status_code == 200:
                return self._process_auth_response(response)
        except Exception as e:
            self.logger.error(f"Error during URL-encoded authentication: {str(e)}")
        return False
    
    def _try_basic_auth(self, url):
        """Try HTTP Basic Authentication"""
        self.logger.debug(f"POST request to {url} with Basic Auth")
        try:
            response = requests.post(url, auth=(self.username, self.password))
            self._log_response_details(response)
            
            if response.status_code == 200:
                return self._process_auth_response(response)
        except Exception as e:
            self.logger.error(f"Error during Basic Auth authentication: {str(e)}")
        return False
    
    def _log_response_details(self, response):
        """Log detailed information about the response"""
        self.logger.debug(f"Response status: {response.status_code}")
        self.logger.debug(f"Response headers: {response.headers}")
        
        if self.debug:
            try:
                if 'application/json' in response.headers.get('Content-Type', ''):
                    self.logger.debug(f"Response JSON: {json.dumps(response.json(), indent=2)}")
                else:
                    self.logger.debug(f"Response content: {response.text}")
            except:
                self.logger.debug(f"Raw response content: {response.content}")
    
    def _process_auth_response(self, response):
        """Process successful authentication response"""
        try:
            # Try to parse as JSON
            try:
                data = response.json()
                self.logger.debug(f"Auth response parsed as JSON: {json.dumps(data)}")
            except json.JSONDecodeError:
                # If not JSON, try to use the raw text
                self.logger.debug("Response is not valid JSON, trying alternative formats")
                text_content = response.text.strip()
                
                # Check if it's just a token string
                if len(text_content) > 10 and ' ' not in text_content and '\n' not in text_content:
                    self.logger.debug("Response looks like a plain token string")
                    data = {"token": text_content}
                else:
                    self.logger.error("Unable to parse authentication response")
                    return False
            
            # Extract token
            self.token = data.get("token")
            if not self.token:
                self.logger.error("Token not found in response")
                return False
            
            # Parse expiry time
            expires_at = data.get("expires_at")
            if expires_at:
                try:
                    self.token_expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    # Default 24-hour expiry
                    self.token_expiry = datetime.now() + timedelta(hours=24)
            else:
                # Default 24-hour expiry
                self.token_expiry = datetime.now() + timedelta(hours=24)
            
            self.logger.info(f"Authentication successful. Token valid until {self.token_expiry}")
            return True
        except Exception as e:
            self.logger.error(f"Error processing authentication response: {str(e)}")
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
        
        # Make both datetime objects timezone-aware by using timezone-aware now()
        import pytz
        now = datetime.now(pytz.UTC)
        
        return now + buffer_time < self.token_expiry
    
    def ensure_authenticated(self):
        """Ensure we have a valid authentication token, refreshing if needed"""
        if self.is_token_valid():
            return True
            
        # Token is invalid or expired, try to refresh
        self.logger.info("Token expired or invalid. Refreshing...")
        return self.authenticate()
    
    def get_headers(self):
        """Get HTTP headers with authentication token"""
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_v53a_list(self, page=1, page_size=10, **filters):
        """Get a paginated list of V53a records with optional filtering"""
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
            self.logger.debug(f"Requesting: GET {url} with params {params}")
            response = requests.get(url, headers=self.get_headers(), params=params)
            self._log_response_details(response)
            
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
                self.logger.error(f"Error fetching V53a list: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Exception fetching V53a list: {str(e)}")
            return None
    
    def get_v53a_detail(self, record_id):
        """Get details for a specific V53a record"""
        if not self.ensure_authenticated():
            return None
            
        url = f"{self.base_url}/api/v53a/{record_id}/"
        
        try:
            self.logger.debug(f"Requesting: GET {url}")
            response = requests.get(url, headers=self.get_headers())
            self._log_response_details(response)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token might be expired - try refreshing and retrying
                if self.authenticate():
                    response = requests.get(url, headers=self.get_headers())
                    if response.status_code == 200:
                        return response.json()
                
                self.logger.error(f"Authentication failed after token refresh")
                return None
            elif response.status_code == 404:
                self.logger.warning(f"Record {record_id} not found")
                return None
            else:
                self.logger.error(f"Error fetching V53a detail: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Exception fetching V53a detail: {str(e)}")
            return None
    
    def get_last_elements(self, did):
        """Get the last elements for a specific V53a record by DID"""
        if not self.ensure_authenticated():
            return None
            
        url = f"{self.base_url}/api/v53a/{did}/last-elements/"
        
        try:
            self.logger.debug(f"Requesting: GET {url}")
            response = requests.get(url, headers=self.get_headers())
            self._log_response_details(response)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token might be expired - try refreshing and retrying
                if self.authenticate():
                    response = requests.get(url, headers=self.get_headers())
                    if response.status_code == 200:
                        return response.json()
                
                self.logger.error(f"Authentication failed after token refresh")
                return None
            elif response.status_code == 404:
                self.logger.warning(f"Record with DID {did} not found")
                return None
            else:
                self.logger.error(f"Error fetching last elements: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Exception fetching last elements: {str(e)}")
            return None


def display_results(data, format_type="json"):
    """Display results in the specified format"""
    if format_type == "json":
        print(json.dumps(data, indent=2))
    else:
        # Simple table format
        if isinstance(data, dict):
            if "results" in data:
                # This is a list response
                print(f"Total records: {data['count']}")
                print(f"Page: {data['page']} of {(data['count'] + data['page_size'] - 1) // data['page_size']}")
                
                for i, item in enumerate(data['results']):
                    print(f"\n--- Record {i+1} ---")
                    for key, value in item.items():
                        print(f"{key}: {value}")
            elif "last_elements" in data:
                # This is a last_elements response
                print(f"Record ID: {data['ID']}, DID: {data['DID']}")
                print(f"Lookup method: {data['lookup_method']}")
                print(f"Creation time: {data['ctime']}")
                print("\nLast Elements:")
                for key, value in data['last_elements'].items():
                    print(f"{key}: {value}")
            else:
                # Generic dict
                for key, value in data.items():
                    print(f"{key}: {value}")
        elif isinstance(data, list):
            # List of records
            for i, item in enumerate(data):
                print(f"\n--- Record {i+1} ---")
                for key, value in item.items():
                    print(f"{key}: {value}")


def main():
    """Main entry point for the command-line script"""
    # Configure argument parser
    parser = argparse.ArgumentParser(description='V53a API Client')
    parser.add_argument('username', help='Username for API authentication')
    parser.add_argument('password', help='Password for API authentication')
    parser.add_argument('--url', '-u', default='http://aiprediction.us', 
                      help='Base URL of the API (default: http://aiprediction.us)')
    parser.add_argument('--format', '-f', choices=['json', 'table'], default='table',
                      help='Output format (default: table)')
    parser.add_argument('--debug', '-d', action='store_true',
                      help='Enable debug output')
    parser.add_argument('--http-debug', action='store_true',
                      help='Enable detailed HTTP debugging')
    parser.add_argument('--auth-endpoint', default='api-token-auth/',
                      help='Authentication endpoint (default: api-token-auth/)')
    
    # Command subparsers
    subparsers = parser.add_subparsers(dest='command', help='API command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='Get paginated list of V53a records')
    list_parser.add_argument('--page', '-p', type=int, default=1, help='Page number')
    list_parser.add_argument('--page-size', '-s', type=int, default=10, help='Page size')
    list_parser.add_argument('--id', type=int, help='Filter by ID')
    list_parser.add_argument('--did', type=int, help='Filter by DID')
    
    # Detail command
    detail_parser = subparsers.add_parser('detail', help='Get details for a specific V53a record')
    detail_parser.add_argument('record_id', type=int, help='Record ID')
    
    # Last elements command
    last_parser = subparsers.add_parser('last', help='Get last elements for a specific record')
    last_parser.add_argument('did', type=int, help='Record DID')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create client with debug options
    client = APIClient(args.url, debug=args.debug, http_debug=args.http_debug)
    
    # Debug info
    if args.debug:
        print(f"API URL: {args.url}")
        print(f"Auth endpoint: {args.auth_endpoint}")
        print(f"Username: {args.username}")
        print(f"Password: {'*' * len(args.password)}")
    
    # Authenticate with custom endpoint if provided
    if not client.authenticate(args.username, args.password, args.auth_endpoint):
        print("\nAuthentication failed. Please check your credentials, API URL, and auth endpoint.")
        print("\nPossible solutions:")
        print("1. Check if the API server is running and accessible")
        print("2. Verify your username and password are correct")
        print("3. Try a different authentication endpoint with --auth-endpoint")
        print("4. Check API logs for more details on the server side")
        print("5. Ensure you have network connectivity to the API server")
        
        if not args.debug and not args.http_debug:
            print("\nTry running with --debug or --http-debug to see more information.")
        sys.exit(1)
    
    # Execute command
    result = None
    if args.command == 'list':
        # Build filters
        filters = {}
        if args.id:
            filters['id'] = args.id
        if args.did:
            filters['did'] = args.did
        
        result = client.get_v53a_list(page=args.page, page_size=args.page_size, **filters)
    elif args.command == 'detail':
        result = client.get_v53a_detail(args.record_id)
    elif args.command == 'last':
        result = client.get_last_elements(args.did)
    else:
        # Default to list if no command specified
        result = client.get_v53a_list()
    
    # Display results
    if result:
        display_results(result, args.format)
    else:
        print("No data returned. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
