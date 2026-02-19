"""
Example configuration file.
Copy this to config.py and update with your credentials and settings.
"""

# Login credentials (used for automatic relogin when session expires)
USERNAME = "your_username"
PASSWORD = "your_password"

# Session refresh behavior
# If True: relogin automatically every Automatic_Refresh_Period hours
# If False: relogin only when a request is made and the current session is expired
REFRESH_AUTOMATICALLY = False

# How often to perform automatic relogin (in hours). Only used when REFRESH_AUTOMATICALLY is True.
AUTOMATIC_REFRESH_PERIOD_HOURS = 8

# Optional: Custom headers (usually default headers work fine)
CUSTOM_HEADERS = {
    "Referer": "https://kopavogur.vinnustund.is/",
}
