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

# Try to load cookies from config if available
cookies = None
headers = None
try:
    if os.path.exists('config.py'):
        from config import COOKIES, CUSTOM_HEADERS
        cookies = COOKIES
        headers = CUSTOM_HEADERS
        logger.info("Loaded cookies and headers from config.py")
    else:
        logger.warning("config.py not found. You'll need to set cookies manually using scraper.set_cookies()")
except ImportError:
    logger.warning("Could not import config. Using default settings.")

# Initialize scraper instance (reused across requests)
# Keep-alive is enabled by default (runs every 3 minutes to prevent inactivity expiration)
# Cookie expiration extended to 70 years (2096) by default
# Note: More frequent keep-alive helps prevent server-side inactivity expiration
scraper = VinnustundScraper(
    cookies=cookies, 
    headers=headers, 
    keep_alive_interval=180,  # 3 minutes - more frequent to prevent inactivity expiration
    enable_keep_alive=True,
    cookie_expiration_years=70  # Extend cookies to ~2096
)

# Register cleanup function to stop keep-alive thread on shutdown
def cleanup():
    logger.info("Shutting down, stopping keep-alive thread...")
    scraper.stop_keep_alive()

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
            'message': 'Authentication successful' if auth_success else 'Authentication failed - check cookies'
        })
    except Exception as e:
        logger.error(f"Error testing auth: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'authenticated': False,
            'error': str(e)
        }), 500

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
    
    return jsonify({
        'status': 'healthy',
        'keep_alive_enabled': scraper.enable_keep_alive,
        'keep_alive_interval': scraper.keep_alive_interval,
        'keep_alive_running': scraper.keep_alive_running if hasattr(scraper, 'keep_alive_running') else False,
        'cookie_expiration_years': scraper.cookie_expiration_years,
        'session_status': {
            'last_successful_request': last_success.isoformat() if last_success else None,
            'hours_since_last_success': round(time_since_success / 3600, 2),
            'consecutive_failures': consecutive_failures,
            'warning': consecutive_failures >= 3 or time_since_success > 3600 * 24  # Warn if failures or >24h
        }
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
