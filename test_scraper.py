"""
Test script for the scraper (without Flask).
Use this to test the scraper directly before using the Flask API.
"""

from scraper import VinnustundScraper
import json

# Load cookies from config if available
try:
    from config import COOKIES, CUSTOM_HEADERS
    cookies = COOKIES
    headers = CUSTOM_HEADERS
    print("✓ Loaded cookies from config.py")
except ImportError:
    print("⚠ config.py not found. Please create it with your cookies.")
    print("   See config_example.py for reference.")
    cookies = None
    headers = None

# Initialize scraper
scraper = VinnustundScraper(cookies=cookies, headers=headers)

# Test authentication first
print("\n" + "="*60)
print("Testing authentication...")
print("="*60)
auth_success = scraper.test_authentication()

if not auth_success:
    print("\n✗ Authentication failed!")
    print("Please check:")
    print("  1. Cookies in config.py are valid and up-to-date")
    print("  2. Your session hasn't expired")
    print("  3. You're logged into the website in your browser")
    exit(1)

print("\n" + "="*60)
print("Authentication successful! Proceeding to fetch shifts...")
print("="*60)

# Test dates
date_from = "01.01.2026"
date_to = "25.01.2026"

print(f"\nFetching shifts from {date_from} to {date_to}...")

try:
    shifts = scraper.get_shifts(date_from, date_to)
    
    print(f"\n✓ Successfully retrieved {len(shifts)} shifts\n")
    
    # Print first few shifts as example
    for i, shift in enumerate(shifts[:3], 1):
        print(f"Shift {i}:")
        print(f"  Date: {shift.get('date')} ({shift.get('dayOfWeek')})")
        print(f"  Time: {shift.get('timeEntered', 'N/A')}")
        print(f"  Total Hours: {shift.get('totalHours', 'N/A')}")
        print(f"  Status: {shift.get('statusTime', 'N/A')}")
        print()
    
    if len(shifts) > 3:
        print(f"... and {len(shifts) - 3} more shifts\n")
    
    # Save to JSON file
    output_file = 'shifts_output.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(shifts, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved all shifts to {output_file}")
    
except Exception as e:
    print(f"\n✗ Error: {str(e)}")
    print("\nMake sure:")
    print("  1. You have valid cookies in config.py")
    print("  2. Your session is still active")
    print("  3. The date range is valid")
