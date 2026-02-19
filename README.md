# Smastund Scraper

A Flask-based web scraper for retrieving shift data from kopavogur.vinnustund.is attendance system.

## Features

- **Login-based session**: Uses username/password from config to log in; no manual cookie copying.
- **Automatic relogin**: When a request hits an expired session, the scraper relogins and retries once.
- **Optional scheduled refresh**: Can relogin every X hours in the background (`REFRESH_AUTOMATICALLY`).
- Browser-like headers and random delays to avoid bot detection.
- RESTful API endpoint for retrieving shifts.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure credentials:
   - Copy `config_example.py` to `config.py`
   - Set `USERNAME` and `PASSWORD` (your Notendanafn and Lykilorð for kopavogur.vinnustund.is)
   - Optionally set `REFRESH_AUTOMATICALLY` and `AUTOMATIC_REFRESH_PERIOD_HOURS` (see below)

Session cookies (JSESSIONID, sessionPersist, TS01780571) are obtained and updated automatically after each login; no manual cookie configuration is needed.

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

## Session management and refresh

- **Login**: Session is obtained by POSTing username/password to the site’s login page. Cookies `JSESSIONID`, `sessionPersist`, and `TS01780571` are updated from the response.
- **On request**: If a work-schedule request is made and the current session is expired, the scraper relogins, then retries the request once before returning.
- **Config options** (in `config.py`):
  - **`REFRESH_AUTOMATICALLY`** (bool): If `True`, a background thread relogins every `AUTOMATIC_REFRESH_PERIOD_HOURS`. If `False`, relogin only when a request is made and the session is expired.
  - **`AUTOMATIC_REFRESH_PERIOD_HOURS`** (float): Used only when `REFRESH_AUTOMATICALLY` is `True`; period in hours between automatic relogins.

### Keep-alive

- Optional background keep-alive thread (e.g. every 3 minutes) can be enabled to hit the site periodically.
- Relogin (on demand or on schedule) is the main way to refresh the session; keep-alive only helps reduce inactivity-based expiry.

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

- The scraper mimics browser behavior to avoid detection.
- Set `USERNAME` and `PASSWORD` in `config.py`; session is refreshed via login (on expiry or on schedule).
- Date format must be `dd.MM.yyyy` (e.g., "01.01.2026").
- The scraper automatically handles login, form submission, and table parsing.

## Legal Notice

This scraper is for personal use only. Ensure you comply with the website's Terms of Service and applicable laws.
