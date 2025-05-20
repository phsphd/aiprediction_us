# Python client example with token expiration handling
import requests
import json
from datetime import datetime, timedelta
import pytz  # Required for timezone handling

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.token_expiry = None
        self.username = None
        self.password = None
    
    def login(self, username, password):
        """
        Log in and obtain a token
        """
        self.username = username
        self.password = password
        return self._obtain_token()
    
    def _obtain_token(self):
        """
        Get a new token from the API
        """
        url = f"{self.base_url}/api-token-auth/"
        payload = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = requests.post(url, data=payload)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["token"]
                # Parse the ISO format datetime string to a datetime object
                self.token_expiry = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
                return True
            else:
                print(f"Authentication error: {response.status_code}")
                print(response.text)
                return False
        except Exception as e:
            print(f"Error in token acquisition: {str(e)}")
            return False
    
    def _ensure_valid_token(self):
        """
        Check if token is about to expire and refresh if needed
        """
        # If we don't have a token yet, get one
        if not self.token or not self.token_expiry:
            return self._obtain_token()
        
        # If token will expire in less than 10 minutes, refresh it
        now = datetime.now(pytz.utc)
        if self.token_expiry - now < timedelta(minutes=10):
            return self._obtain_token()
        
        return True
    
    def get_v53a_data(self, record_id=None):
        """
        Get V53a data, ensuring we have a valid token first
        """
        if not self._ensure_valid_token():
            return None
        
        if record_id:
            url = f"{self.base_url}/api/v53a/{record_id}/"
        else:
            url = f"{self.base_url}/api/v53a/"
        
        headers = {
            "Authorization": f"Token {self.token}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token might be invalid or expired
                print("Token expired or invalid, refreshing...")
                if self._obtain_token():
                    # Retry with new token
                    return self.get_v53a_data(record_id)
                else:
                    return None
            else:
                print(f"API Error: {response.status_code}")
                print(response.text)
                return None
        except Exception as e:
            print(f"Error fetching data: {str(e)}")
            return None
    
    def get_last_elements(self, record_id):
        """
        Get last elements, ensuring we have a valid token
        """
        if not self._ensure_valid_token():
            return None
            
        url = f"{self.base_url}/api/v53a/{record_id}/last-elements/"
        
        headers = {
            "Authorization": f"Token {self.token}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token might be invalid or expired
                print("Token expired or invalid, refreshing...")
                if self._obtain_token():
                    # Retry with new token
                    return self.get_last_elements(record_id)
                else:
                    return None
            else:
                print(f"API Error: {response.status_code}")
                print(response.text)
                return None
        except Exception as e:
            print(f"Error fetching last elements: {str(e)}")
            return None


# Example usage
if __name__ == "__main__":
    client = APIClient("http://aiprediction.us")
    
    if client.login("your_username", "your_password"):
        print(f"Logged in successfully. Token will expire at: {client.token_expiry}")
        
        # Get V53a data
        data = client.get_v53a_data()
        print("V53a Data:", json.dumps(data, indent=2))
        
        # Get last elements of a specific record
        record_id = 250520
        last_elements = client.get_last_elements(record_id)
        print(f"Last Elements for Record {record_id}:", json.dumps(last_elements, indent=2))
    else:
        print("Failed to login")
