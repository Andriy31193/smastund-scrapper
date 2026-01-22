from flask import Flask, request, jsonify
from scraper import VinnustundScraper
import logging
import os
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
scraper = VinnustundScraper(cookies=cookies, headers=headers)

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

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
