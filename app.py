from flask import Flask, request, jsonify
from scraper import VinnustundScraper
import logging
import os
import atexit
from datetime import datetime

app = Flask(__name__)
# Set logging level to DEBUG for detailed output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Set requests library to be less verbose
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Load config: credentials and session refresh settings (cookies are obtained via login)
username = None
password = None
headers = None
refresh_automatically = False
automatic_refresh_period_hours = 8
try:
    if os.path.exists("config.py"):
        from config import (
            USERNAME,
            PASSWORD,
            CUSTOM_HEADERS,
            REFRESH_AUTOMATICALLY,
            AUTOMATIC_REFRESH_PERIOD_HOURS,
        )
        username = USERNAME
        password = PASSWORD
        headers = CUSTOM_HEADERS
        refresh_automatically = REFRESH_AUTOMATICALLY
        automatic_refresh_period_hours = float(AUTOMATIC_REFRESH_PERIOD_HOURS)
        logger.info(
            "Loaded config: credentials and refresh_automatically=%s, automatic_refresh_period_hours=%s",
            refresh_automatically,
            automatic_refresh_period_hours,
        )
    else:
        logger.warning("config.py not found. Set USERNAME/PASSWORD for login.")
except ImportError as e:
    logger.warning("Could not import config: %s. Using default settings.", e)

# Initialize scraper (session is obtained via login; relogin on expiry or on schedule)
scraper = VinnustundScraper(
    username=username,
    password=password,
    headers=headers,
    keep_alive_interval=180,
    enable_keep_alive=True,
    cookie_expiration_years=70,
    refresh_automatically=refresh_automatically,
    automatic_refresh_period_hours=automatic_refresh_period_hours,
)


def cleanup():
    logger.info("Shutting down, stopping keep-alive and refresh threads...")
    scraper.stop_keep_alive()
    scraper._stop_automatic_refresh()

atexit.register(cleanup)

@app.route('/retrieve_shifts', methods=['GET', 'POST'])
def retrieve_shifts():
    """
    Endpoint to retrieve shifts from the attendance system.
    
    Accepts:
    - dateFrom: Date in format dd.MM.yyyy (e.g., "01.01.2026")
    - dateTo: Date in format dd.MM.yyyy (e.g., "25.01.2026")
    
    Returns JSON with all found shifts in the table.
    """
    try:
        # Get parameters from request
        if request.method == 'POST':
            date_from = request.form.get('dateFrom') or request.json.get('dateFrom') if request.is_json else None
            date_to = request.form.get('dateTo') or request.json.get('dateTo') if request.is_json else None
        else:
            date_from = request.args.get('dateFrom')
            date_to = request.args.get('dateTo')
        
        # Validate input
        if not date_from or not date_to:
            return jsonify({
                'error': 'Missing required parameters',
                'message': 'Both dateFrom and dateTo are required (format: dd.MM.yyyy)'
            }), 400
        
        logger.info(f"Retrieving shifts from {date_from} to {date_to}")
        
        # Scrape the shifts
        shifts = scraper.get_shifts(date_from, date_to)
        
        return jsonify({
            'success': True,
            'dateFrom': date_from,
            'dateTo': date_to,
            'shifts': shifts,
            'count': len(shifts)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving shifts: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/test_auth', methods=['GET'])
def test_auth():
    """Test authentication endpoint"""
    try:
        auth_success = scraper.test_authentication()
        return jsonify({
            'success': auth_success,
            'authenticated': auth_success,
            'message': 'Authentication successful' if auth_success else 'Authentication failed - check credentials or run relogin'
        })
    except Exception as e:
        logger.error(f"Error testing auth: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'authenticated': False,
            'error': str(e)
        }), 500

@app.route("/login", methods=["POST", "GET"])
def trigger_login():
    """Manually trigger relogin to refresh session (JSESSIONID, sessionPersist, TS01780571)."""
    try:
        success = scraper.login()
        return jsonify({
            "success": success,
            "message": "Login successful; session cookies updated" if success else "Login failed - check USERNAME/PASSWORD in config",
        })
    except Exception as e:
        logger.error(f"Error during login: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/keep_alive', methods=['POST', 'GET'])
def trigger_keep_alive():
    """Manually trigger a keep-alive action"""
    try:
        success = scraper.keep_alive()
        return jsonify({
            'success': success,
            'message': 'Keep-alive action completed successfully' if success else 'Keep-alive action failed'
        })
    except Exception as e:
        logger.error(f"Error in keep-alive: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/cookie_info', methods=['GET'])
def cookie_info():
    """Get information about cookie expiration dates"""
    try:
        info = scraper.get_cookie_expiration_info()
        return jsonify({
            'success': True,
            'cookie_info': info
        })
    except Exception as e:
        logger.error(f"Error getting cookie info: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    with scraper._lock:
        last_success = scraper.last_successful_request
        consecutive_failures = scraper.consecutive_failures
        time_since_success = (datetime.now() - last_success).total_seconds() if last_success else 0
    
    last_login = getattr(scraper, "_last_login_at", None)
    return jsonify({
        'status': 'healthy',
        'keep_alive_enabled': scraper.enable_keep_alive,
        'keep_alive_interval': scraper.keep_alive_interval,
        'keep_alive_running': getattr(scraper, 'keep_alive_running', False),
        'refresh_automatically': getattr(scraper, 'refresh_automatically', False),
        'automatic_refresh_period_hours': getattr(scraper, 'automatic_refresh_period_hours', None),
        'cookie_expiration_years': scraper.cookie_expiration_years,
        'session_status': {
            'last_successful_request': last_success.isoformat() if last_success else None,
            'last_login_at': last_login.isoformat() if last_login else None,
            'hours_since_last_success': round(time_since_success / 3600, 2),
            'consecutive_failures': consecutive_failures,
            'warning': consecutive_failures >= 3 or time_since_success > 3600 * 24
        }
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
