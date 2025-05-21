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
   * Generate a timestamped filename for saving data
   * @param {string} prefix - Prefix for the filename
   * @param {string|number} [identifier=null] - Optional identifier (e.g., DID, ID)
   * @param {string} [extension='json'] - File extension
   * @returns {string} Generated filename
   * @private
   */
  _generateFilename(prefix, identifier = null, extension = 'json') {
    const timestamp = new Date().toISOString()
      .replace(/:/g, '-')
      .replace(/\..+/, '')
      .replace('T', '_');
    
    let filename = `${prefix}_${timestamp}`;
    if (identifier !== null) {
      filename += `_${identifier}`;
    }
    
    return `${filename}.${extension}`;
  }

  /**
   * Save data to a JSON file
   * @param {Object|Array} data - Data to save
   * @param {string} [filename=null] - Optional filename
   * @param {boolean} [download=true] - Whether to trigger browser download
   * @returns {Promise<string>} Filename or Blob URL if successful
   * @throws {Error} If saving fails
   */
  async saveToJson(data, filename = null, download = true) {
    try {
      // Generate filename if not provided
      if (!filename) {
        // Check if it's a record with a DID
        const identifier = data.did || (data.results?.[0]?.did ? 'all' : null);
        const prefix = identifier === 'all' ? 'records' : 'record';
        filename = this._generateFilename(prefix, identifier);
      }
      
      // Format the data
      const jsonString = JSON.stringify(data, null, 2);
      
      if (download) {
        // Create a blob and trigger download
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        
        // Clean up
        setTimeout(() => {
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
        }, 100);
        
        console.log(`Data saved to ${filename}`);
        return filename;
      } else {
        // Return the data as a blob URL (for preview or other uses)
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        console.log(`Data prepared as blob URL: ${url}`);
        return url;
      }
    } catch (error) {
      console.error('Error saving JSON:', error);
      throw new Error(`Failed to save JSON file: ${error.message}`);
    }
  }

  /**
   * Fetch and save a record by DID
   * @param {number} did - DID of the record to fetch and save
   * @param {string} [filename=null] - Optional filename
   * @param {boolean} [saveAllRecords=false] - Whether to also save all records
   * @returns {Promise<Object>} Object with saved filenames and record data
   */
  async fetchAndSaveRecord(did, filename = null, saveAllRecords = false) {
    try {
      console.log(`Fetching record with DID: ${did}`);
      
      // Get all records first
      const allRecordsData = await this.getV53aList(1, 50, {});
      let records = allRecordsData.results || allRecordsData;
      
      // Find the target record with the specified DID
      const targetRecord = records.find(record => record.did === parseInt(did));
      
      if (!targetRecord) {
        throw new Error(`No record found with DID ${did}`);
      }
      
      console.log(`Found record with DID ${did}`);
      
      // Save files and return results
      const result = {
        targetRecord,
        filenames: {}
      };
      
      // Save target record
      if (filename) {
        result.filenames.record = await this.saveToJson(targetRecord, filename);
      } else {
        result.filenames.record = await this.saveToJson(targetRecord);
      }
      
      // Save all records if requested
      if (saveAllRecords) {
        const allRecordsFilename = filename ? `all_${filename}` : null;
        result.filenames.allRecords = await this.saveToJson(allRecordsData, allRecordsFilename);
      }
      
      return result;
    } catch (error) {
      console.error(`Error fetching and saving record with DID ${did}:`, error);
      throw error;
    }
  }

  /**
   * Debug a record's structure
   * @param {Object} record - Record to debug
   * @returns {Object} Debug information
   */
  debugRecordStructure(record) {
    // Generate record structure info similar to the Python script
    const debug = {
      fields: {},
      arrayFields: {},
      listFields: {}
    };
    
    // Check all fields
    for (const [key, value] of Object.entries(record)) {
      const valueType = Array.isArray(value) ? 'array' : typeof value;
      const valuePreview = JSON.stringify(value).substring(0, 100) + 
        (JSON.stringify(value).length > 100 ? '...' : '');
      
      debug.fields[key] = { type: valueType, preview: valuePreview };
      
      // Check for array fields
      if (Array.isArray(value)) {
        debug.listFields[key] = {
          length: value.length,
          firstElement: value.length > 0 ? value[0] : null,
          lastElement: value.length > 0 ? value[value.length - 1] : null
        };
      }
    }
    
    // Check for expected array fields
    const expectedFields = ['sp_array', 'es_array', 'p1_array', 'c1_array', 'p2_array', 'c2_array', 
                            'p3_array', 'c3_array', 'p4_array', 'c4_array', 'p5_array', 'c5_array', 
                            'p6_array', 'c6_array', 'p7_array', 'c7_array'];
                            
    for (const field of expectedFields) {
      if (field in record) {
        const value = record[field];
        if (Array.isArray(value)) {
          debug.arrayFields[field] = {
            length: value.length,
            firstElement: value.length > 0 ? value[0] : null,
            lastElement: value.length > 0 ? value[value.length - 1] : null
          };
        } else {
          debug.arrayFields[field] = { type: typeof value, isArray: false };
        }
      } else {
        debug.arrayFields[field] = { found: false };
      }
    }
    
    return debug;
  }

  /**
   * Fetch, save, and debug a record by DID
   * @param {number} did - DID of the record to process
   * @param {string} [filename=null] - Optional filename
   * @param {boolean} [saveAllRecords=true] - Whether to also save all records
   * @returns {Promise<Object>} Processing results
   */
  async processRecord(did, filename = null, saveAllRecords = true) {
    try {
      // Fetch and save the record
      const saveResult = await this.fetchAndSaveRecord(did, filename, saveAllRecords);
      
      // Debug the record structure
      const debugInfo = this.debugRecordStructure(saveResult.targetRecord);
      
      // Print debug info
      console.log("\n=== RECORD STRUCTURE ===");
      
      console.log("\nFields in the record:");
      Object.entries(debugInfo.fields).forEach(([key, info]) => {
        console.log(`- ${key} (${info.type}): ${info.preview}`);
      });
      
      console.log("\nLooking for array fields:");
      Object.entries(debugInfo.arrayFields).forEach(([key, info]) => {
        if (info.found === false) {
          console.log(`- ${key}: Not found in record`);
        } else if (info.isArray === false) {
          console.log(`- ${key}: Not an array, but ${info.type}`);
        } else {
          console.log(`- ${key}: Array with ${info.length} elements`);
          if (info.length > 0) {
            console.log(`  First element: ${JSON.stringify(info.firstElement)}`);
            console.log(`  Last element: ${JSON.stringify(info.lastElement)}`);
          } else {
            console.log(`  Array is empty`);
          }
        }
      });
      
      console.log("\nSearching for any list fields:");
      Object.entries(debugInfo.listFields).forEach(([key, info]) => {
        console.log(`- ${key}: List with ${info.length} elements`);
        if (info.length > 0) {
          console.log(`  First element: ${JSON.stringify(info.firstElement)}`);
          console.log(`  Last element: ${JSON.stringify(info.lastElement)}`);
        } else {
          console.log(`  List is empty`);
        }
      });
      
      // Print information about saved files
      console.log("\nRecord saved to file:", saveResult.filenames.record);
      if (saveResult.filenames.allRecords) {
        console.log("All records saved to file:", saveResult.filenames.allRecords);
      }
      
      return {
        record: saveResult.targetRecord,
        debug: debugInfo,
        filenames: saveResult.filenames
      };
    } catch (error) {
      console.error(`Error processing record with DID ${did}:`, error);
      throw error;
    }
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
    
    // Process a record (fetch, save, debug)
    const did = 250520; // Replace with actual DID
    try {
      const result = await client.processRecord(did);
      console.log('Processing complete!');
    } catch (error) {
      console.error(`Failed to process record with DID ${did}:`, error.message);
    }
    
    // Get V53a list with pagination
    const data = await client.getV53aList(1, 5);
    console.log(`Total records: ${data.count}`);
    console.log(`Records on page: ${data.results.length}`);
    
    // Save all records to JSON
    await client.saveToJson(data, 'all_records.json');
    
    // Get record details
    const recordId = 123; // Replace with actual record ID
    try {
      const record = await client.getV53aDetail(recordId);
      console.log('Record details:', record);
      
      // Save record to JSON
      await client.saveToJson(record, `record_${recordId}.json`);
    } catch (error) {
      console.error(`Failed to get record ${recordId}:`, error.message);
    }
    
    // Get last elements
    try {
      const elements = await client.getLastElements(did);
      console.log('Last elements:', elements);
      
      // Save last elements to JSON
      await client.saveToJson(elements, `last_elements_${did}.json`);
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
