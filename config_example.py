"""
Example configuration file for cookies and headers.
Copy this to config.py and update with your actual cookies.
"""

# Cookies from your browser session
# To get these:
# 1. Open browser DevTools (F12)
# 2. Go to Application/Storage > Cookies
# 3. Copy all cookies from kopavogur.vinnustund.is
# 4. Or use a browser extension like EditThisCookie

COOKIES = {
    'bgid': '97',
    'JSESSIONID': 'YOUR_SESSION_ID_HERE',
    'sessionPersist': 'YOUR_SESSION_PERSIST_HERE',
    'TS01780571': 'YOUR_TS_TOKEN_HERE',
    # Add any other cookies you see in your browser
}

# Optional: Custom headers (usually default headers work fine)
CUSTOM_HEADERS = {
    'Referer': 'https://kopavogur.vinnustund.is/',
    # Add any other custom headers if needed
}
