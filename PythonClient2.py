class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.token_expiry = None
        
    def login(self, username, password):
        # Get token with expiration info
        response = requests.post(f"{self.base_url}/api-token-auth/", 
                               data={"username": username, "password": password})
        data = response.json()
        self.token = data["token"]
        self.token_expiry = datetime.fromisoformat(data["expires_at"])
        
    def ensure_valid_token(self):
        # Check if token is expired or about to expire
        if not self.token or datetime.now() + timedelta(minutes=5) >= self.token_expiry:
            self.login(self.username, self.password)
