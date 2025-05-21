# V53a API Documentation

## Authentication

### `POST /api-token-auth/`

Authenticate and obtain a token for API access.

**Authentication:** None required

**Request Body:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "token": "your_auth_token",
  "user_id": 123,
  "username": "your_username",
  "is_member": 1,
  "expires_at": "2025-05-21T13:30:41.834Z"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid credentials
- `500 Internal Server Error`: Authentication system error

**Notes:**
- Tokens expire after 24 hours
- `is_member` value of 1 indicates full access

## API Endpoints

### `GET /api/v53a/`

List V53a records with pagination and optional filtering.

**Authentication:** Token required  
**Authorization:** Member access required during working hours

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Number of items per page (default: 10)
- `id`: Filter by ID
- `did`: Date ID in YYMMDD format

**Response:**
```json
{
  "count": 150,
  "page": 1,
  "page_size": 10,
  "results": [
    {
      "id": 363,
      "did": 250520,
      "ctime": "...",
      "ts": "2025-05-20 13:30:41.834525+00:00",
      "sp": [...],
      "es": [...]
    }
  ]
}
```

### `GET /api/v53a/{record_id}/`

Retrieve a specific V53a record by ID.

**Authentication:** Token required  
**Authorization:** Member access required during working hours

**URL Parameters:**
- `record_id`: ID of the record to retrieve

**Response:**
```json
{
  "id": 363,
  "did": 250520,
  "ctime": "...",
  "ts": "2025-05-20 13:30:41.834525+00:00"
}
```

**Error Response:**
- `404 Not Found`: Record not found

### `GET /api/v53a/{did}/last-elements/`

Get the last elements of various data arrays for a specific Date ID.

**Authentication:** Token required

**URL Parameters:**
- `did`: Date ID to fetch the last elements for

**Response:**
```json
{
  "lookup_method": "did",
  "DID": 250520,
  "ID": 363,
  "ctime": "...",
  "last_elements": {
    "sp": 5937.64,
    "es": 5956.0,
    "p1": 5935.0,
    "c1": 5935.0
  }
}
```

**Error Responses:**
- `401 Unauthorized`: Authentication required or invalid token
- `403 Forbidden`: Membership required
- `404 Not Found`: Record not found with the provided DID

## Access Control

The API implements multiple layers of access control:

1. **Time-based restrictions:**
   - Full access granted on weekends (Saturday and Sunday)
   - Restricted access during working hours (5:30 AM to 4:00 PM weekdays)
   - Free access outside working hours

2. **Membership verification:**
   - Active members have full access during all hours
   - Membership status stored in `ChartsUser` model
   - Token includes membership status (`is_member`)

3. **Token expiration:**
   - Tokens expire after 24 hours
   - Automatic validation of token expiration on protected endpoints

## Error Handling

The API provides consistent error responses:

| Status Code | Description | Cause |
|-------------|-------------|-------|
| `400` | Bad Request | Invalid request parameters or body |
| `401` | Unauthorized | Missing or invalid authentication token |
| `403` | Forbidden | Access restricted (non-member during restricted hours) |
| `404` | Not Found | Requested resource not found |
| `500` | Internal Server Error | Server-side errors |

## Data Structure

V53a records contain numerous data fields including:

- `id`: Record identifier
- `did`: Date ID 
- `ctime`: Time data array (formatted string)
- `ts`: Timestamp of record creation
- Various array fields for market data series:
  - `sp`, `spysp`, `spy`: S&P and SPY data 
  - `qqqsp`, `qqq`: QQQ data
  - `es`: E-mini S&P futures
  - `p1`-`p14`: Price data series
  - `c1`-`c14`: Corresponding calculation series
- Additional fields like `strike1`, `strike2` for option strike prices
