/**
 * Client for accessing the V53a API with token authentication
 */
class ApiClient {
  /**
   * Initialize client with base URL and optional credentials
   * @param {string} baseUrl - Base URL of the API (e.g., 'http://aiprediction.us')
   * @param {string} [username=null] - Username for authentication
   * @param {string} [password=null] - Password for authentication
   */
  constructor(baseUrl, username = null, password = null) {
    this.baseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    this.username = username;
    this.password = password;
    this.token = null;
    this.tokenExpiry = null;

    // Check for stored token in localStorage
    this._loadStoredToken();
  }

  /**
   * Load token from localStorage if available
   * @private
   */
  _loadStoredToken() {
    if (typeof localStorage !== 'undefined') {
      const storedToken = localStorage.getItem('api_token');
      const storedExpiry = localStorage.getItem('api_token_expiry');
      
      if (storedToken && storedExpiry) {
        this.token = storedToken;
        this.tokenExpiry = new Date(storedExpiry);
        
        // If token is expired, clear it
        if (!this.isTokenValid()) {
          this._clearStoredToken();
        }
      }
    }
  }

  /**
   * Save token to localStorage
   * @private
   */
  _saveToken() {
    if (typeof localStorage !== 'undefined' && this.token && this.tokenExpiry) {
      localStorage.setItem('api_token', this.token);
      localStorage.setItem('api_token_expiry', this.tokenExpiry.toISOString());
    }
  }

  /**
   * Clear token from localStorage
   * @private
   */
  _clearStoredToken() {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('api_token');
      localStorage.removeItem('api_token_expiry');
    }
    this.token = null;
    this.tokenExpiry = null;
  }

  /**
   * Check if the current token is valid and not expired
   * @returns {boolean} True if token is valid, false otherwise
   */
  isTokenValid() {
    if (!this.token || !this.tokenExpiry) {
      return false;
    }
    
    // Add a 5-minute buffer to avoid edge cases
    const now = new Date();
    const bufferTime = 5 * 60 * 1000; // 5 minutes in milliseconds
    return (this.tokenExpiry - now) > bufferTime;
  }

  /**
   * Authenticate with the API and get a token
   * @param {string} [username=null] - Override the username set in constructor
   * @param {string} [password=null] - Override the password set in constructor
   * @returns {Promise<boolean>} True if authentication was successful
   * @throws {Error} If authentication fails
   */
  async authenticate(username = null, password = null) {
    // Update credentials if provided
    if (username) this.username = username;
    if (password) this.password = password;
    
    // Ensure we have credentials
    if (!this.username || !this.password) {
      throw new Error('No credentials provided for authentication');
    }
    
    // Make authentication request
    const url = `${this.baseUrl}/api-token-auth/`;
    const data = {
      username: this.username,
      password: this.password
    };
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });
      
      if (response.ok) {
        const data = await response.json();
        this.token = data.token;
        
        // Parse expiry time
        try {
          this.tokenExpiry = new Date(data.expires_at);
        } catch (e) {
          // If no expiry or invalid format, set default 24-hour expiry
          this.tokenExpiry = new Date(new Date().getTime() + 24 * 60 * 60 * 1000);
        }
        
        // Save token to localStorage
        this._saveToken();
        
        console.log(`Authentication successful! Token valid until ${this.tokenExpiry}`);
        return true;
      } else {
        const errorText = await response.text();
        throw new Error(`Authentication failed: ${response.status} - ${errorText}`);
      }
    } catch (error) {
      console.error('Error during authentication:', error);
      throw error;
    }
  }

  /**
   * Ensure we have a valid authentication token, refreshing if needed
   * @returns {Promise<boolean>} True if we have a valid token after this call
   */
  async ensureAuthenticated() {
    if (this.isTokenValid()) {
      return true;
    }
    
    // Token is invalid or expired, try to refresh
    console.log('Token expired or invalid. Refreshing...');
    
    try {
      return await this.authenticate();
    } catch (error) {
      console.error('Failed to refresh token:', error);
      return false;
    }
  }

  /**
   * Get HTTP headers with authentication token
   * @returns {Object} Headers for API requests
   */
  getHeaders() {
    return {
      'Authorization': `Token ${this.token}`,
      'Content-Type': 'application/json'
    };
  }

  /**
   * Make an authenticated API request
   * @param {string} endpoint - API endpoint path (without base URL)
   * @param {string} [method='GET'] - HTTP method
   * @param {Object} [params=null] - Query parameters
   * @param {Object} [body=null] - Request body (for POST, PUT, etc.)
   * @returns {Promise<Object>} API response data
   * @throws {Error} If request fails
   */
  async request(endpoint, method = 'GET', params = null, body = null) {
    // Ensure we're authenticated
    const isAuthenticated = await this.ensureAuthenticated();
    if (!isAuthenticated) {
      throw new Error('Not authenticated');
    }
    
    // Build URL with query parameters
    let url = `${this.baseUrl}/${endpoint.startsWith('/') ? endpoint.substring(1) : endpoint}`;
    
    if (params) {
      const queryParams = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        queryParams.append(key, value);
      }
      url += `?${queryParams.toString()}`;
    }
    
    // Prepare request options
    const options = {
      method,
      headers: this.getHeaders()
    };
    
    if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      options.body = JSON.stringify(body);
    }
    
    try {
      // Make the request
      let response = await fetch(url, options);
      
      // Handle 401 Unauthorized - token might be expired
      if (response.status === 401) {
        // Clear token and try to authenticate again
        this._clearStoredToken();
        const refreshed = await this.authenticate();
        
        if (refreshed) {
          // Retry the request with new token
          options.headers = this.getHeaders();
          response = await fetch(url, options);
        } else {
          throw new Error('Authentication failed after token refresh');
        }
      }
      
      // Handle successful response
      if (response.ok) {
        return await response.json();
      }
      
      // Handle error response
      const errorText = await response.text();
      throw new Error(`API request failed: ${response.status} - ${errorText}`);
    } catch (error) {
      console.error(`Error in ${method} request to ${url}:`, error);
      throw error;
    }
  }

  /**
   * Get a paginated list of V53a records with optional filtering
   * @param {number} [page=1] - Page number
   * @param {number} [pageSize=10] - Number of items per page
   * @param {Object} [filters={}] - Optional filters (e.g., {id: 123, did: 456})
   * @returns {Promise<Object>} API response data
   */
  async getV53aList(page = 1, pageSize = 10, filters = {}) {
    const params = {
      page,
      page_size: pageSize,
      ...filters
    };
    
    return this.request('api/v53a/', 'GET', params);
  }

  /**
   * Get details for a specific V53a record
   * @param {number} recordId - ID of the record to retrieve
   * @returns {Promise<Object>} API response data
   */
  async getV53aDetail(recordId) {
    return this.request(`api/v53a/${recordId}/`);
  }

  /**
   * Get the last elements for a specific V53a record by DID
   * @param {number} did - DID of the record to retrieve last elements for
   * @returns {Promise<Object>} API response data
   */
  async getLastElements(did) {
    return this.request(`api/v53a/${did}/last-elements/`);
  }

  /**
   * Logout - clear the current token
   */
  logout() {
    this._clearStoredToken();
    console.log('Logged out successfully');
  }
}

// Usage example
async function example() {
  try {
    // Create client instance
    const client = new ApiClient('http://aiprediction.us');
    
    // Authenticate
    await client.authenticate('your_username', 'your_password');
    
    // Get V53a list with pagination
    const data = await client.getV53aList(1, 5);
    console.log(`Total records: ${data.count}`);
    console.log(`Records on page: ${data.results.length}`);
    
    // Get record details
    const recordId = 123; // Replace with actual record ID
    try {
      const record = await client.getV53aDetail(recordId);
      console.log('Record details:', record);
    } catch (error) {
      console.error(`Failed to get record ${recordId}:`, error.message);
    }
    
    // Get last elements
    const did = 250520; // Replace with actual DID
    try {
      const elements = await client.getLastElements(did);
      console.log('Last elements:', elements);
    } catch (error) {
      console.error(`Failed to get last elements for DID ${did}:`, error.message);
    }
    
    // Logout when done
    client.logout();
    
  } catch (error) {
    console.error('API client error:', error.message);
  }
}

// Run the example
// example();
