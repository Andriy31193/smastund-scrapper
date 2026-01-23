# Smastund Scraper

A Flask-based web scraper for retrieving shift data from kopavogur.vinnustund.is attendance system.

## Features

- Session management with cookie persistence
- Browser-like headers to avoid bot detection
- Random delays to simulate human behavior
- Automatic session validation
- RESTful API endpoint for retrieving shifts

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure cookies:
   - Copy `config_example.py` to `config.py`
   - Open your browser and log into kopavogur.vinnustund.is
   - Open DevTools (F12) > Application/Storage > Cookies
   - Copy all cookies from the site and paste them into `config.py`
   - Or use a browser extension like "EditThisCookie" to export cookies

3. Update `app.py` to load cookies from config (optional):
```python
from config import COOKIES, CUSTOM_HEADERS
scraper = VinnustundScraper(cookies=COOKIES, headers=CUSTOM_HEADERS)
```

## Usage

### Start the Flask server:
```bash
python app.py
```

The server will start on `http://localhost:5000`

### API Endpoints

#### GET/POST `/retrieve_shifts`

Retrieve shifts for a date range.

**Parameters:**
- `dateFrom` (required): Start date in format `dd.MM.yyyy` (e.g., "01.01.2026")
- `dateTo` (required): End date in format `dd.MM.yyyy` (e.g., "25.01.2026")

**Example requests:**

```bash
# GET request
curl "http://localhost:5000/retrieve_shifts?dateFrom=01.01.2026&dateTo=25.01.2026"

# POST request (JSON)
curl -X POST http://localhost:5000/retrieve_shifts \
  -H "Content-Type: application/json" \
  -d '{"dateFrom": "01.01.2026", "dateTo": "25.01.2026"}'

# POST request (form data)
curl -X POST http://localhost:5000/retrieve_shifts \
  -d "dateFrom=01.01.2026&dateTo=25.01.2026"
```

**Response:**
```json
{
  "success": true,
  "dateFrom": "01.01.2026",
  "dateTo": "25.01.2026",
  "shifts": [
    {
      "dayOfWeek": "Fös",
      "date": "02.01.2026",
      "workHours": "",
      "timeEntered": "09:00 - 17:00",
      "calculationMethod": "09:00 - 17:00",
      "totalHours": "08:00",
      "absenceSupplement": "",
      "hoursUnits": "",
      "remark": "asked by",
      "statusShift": "",
      "statusTime": "O",
      "payElements": {
        "payElement1": "",
        "payElement2": "",
        "payElement3": "",
        "payElement4": "",
        "payElement5": "8,00"
      },
      "rawText": "Fös | 02.01.2026 | ..."
    }
  ],
  "count": 1
}
```

#### GET `/test_auth`

Test if the current session is authenticated.

**Response:**
```json
{
  "success": true,
  "authenticated": true,
  "message": "Authentication successful"
}
```

#### GET `/health`

Health check endpoint.

## Session Management

The scraper automatically:
- Maintains session cookies across requests
- Validates session before each request
- Adds random delays (1-3 seconds) to simulate human behavior
- Uses browser-like headers to avoid detection
- Background keep-alive thread (runs every 5 minutes by default)
- Automatic retry logic for connection errors
- Cookie expiration extension (extends to ~2096)

### Important: Server-Side Session Expiration

**Server-side session expiration cannot be overridden by client-side cookie manipulation.**

The server maintains its own session state and may expire sessions:
- After a period of inactivity (e.g., 24 hours)
- After a fixed maximum lifetime (e.g., 30 days)
- Based on server-side policies

**What we can do:**
- ✅ Extend cookie expiration dates (prevents cookie expiration)
- ✅ Keep session active with periodic requests (reduces inactivity expiration)
- ✅ Automatically retry on connection errors
- ❌ Cannot prevent server-side session expiration

**What you need to do:**
- Periodically refresh cookies by logging into the website
- Update `config.py` with fresh cookies when sessions expire
- The keep-alive mechanism helps but may not prevent all server-side expirations

### Updating Cookies

If you get a "Session expired" error (especially "server-side expiration"):
1. Log into the website in your browser
2. Extract fresh cookies using DevTools or EditThisCookie extension
3. Update `config.py` with new cookies
4. Restart the Flask server (or cookies will be updated on next request)

### Keep-Alive

The scraper includes automatic background keep-alive:
- Runs every 5 minutes (configurable)
- Visits random pages to simulate user activity
- Helps reduce inactivity-based session expiration
- Cannot prevent server-side maximum session lifetime expiration

## Logging

The scraper includes extensive logging to help debug issues:

- **Cookie status**: Shows which cookies are loaded and their values (truncated)
- **Session validation**: Logs whether authentication succeeded
- **Request/Response**: Logs HTTP status codes, URLs, and response sizes
- **Table parsing**: Shows how many rows were found and parsed
- **Form fields**: Logs all hidden form fields extracted from the page

To see detailed logs, the Flask app runs with `DEBUG` logging level by default. Check the console output for detailed information about:
- Which cookies are being sent
- Whether authentication succeeded
- What form fields were found
- How many table rows were parsed
- Any errors encountered

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Missing or invalid parameters
- `500`: Server error (check logs for details)

If you get empty shifts, check the logs for:
1. Authentication status (should see "✓ Authentication successful")
2. Whether the table was found (should see "✓ Found table with class 'clsTableControl'")
3. How many rows were parsed (should see "Successfully parsed X shifts")

## Notes

- The scraper mimics browser behavior to avoid detection
- Cookies must be kept up to date for the session to work
- Date format must be `dd.MM.yyyy` (e.g., "01.01.2026")
- The scraper automatically handles form submission and table parsing

## Legal Notice

This scraper is for personal use only. Ensure you comply with the website's Terms of Service and applicable laws.
