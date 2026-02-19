"""
Test script for the scraper (without Flask).
Use this to test the scraper directly before using the Flask API.
Session is obtained via login (USERNAME/PASSWORD from config).
"""

from scraper import VinnustundScraper
import json

try:
    from config import USERNAME, PASSWORD, CUSTOM_HEADERS
    username = USERNAME
    password = PASSWORD
    headers = CUSTOM_HEADERS
    print("✓ Loaded credentials and headers from config.py")
except ImportError:
    print("⚠ config.py not found or missing USERNAME/PASSWORD. Create config from config_example.py")
    username = None
    password = None
    headers = None

scraper = VinnustundScraper(
    username=username,
    password=password,
    headers=headers,
    enable_keep_alive=False,
    refresh_automatically=False,
)

# Ensure we have a session (login if needed)
print("\n" + "=" * 60)
print("Obtaining session (login if needed)...")
print("=" * 60)
if username and password:
    if scraper.login():
        print("✓ Login successful")
    else:
        print("✗ Login failed")
        exit(1)
else:
    print("✗ No USERNAME/PASSWORD in config - cannot login")
    exit(1)

# Test authentication (timesheet page)
print("\n" + "=" * 60)
print("Testing authentication (timesheet access)...")
print("=" * 60)
auth_success = scraper.test_authentication()

if not auth_success:
    print("\n✗ Authentication test failed (session may be invalid after login)")
    exit(1)

print("\n" + "=" * 60)
print("Authentication OK. Fetching shifts...")
print("=" * 60)

date_from = "01.01.2026"
date_to = "25.01.2026"
print(f"\nFetching shifts from {date_from} to {date_to}...")

try:
    shifts = scraper.get_shifts(date_from, date_to)

    print(f"\n✓ Successfully retrieved {len(shifts)} shifts\n")

    for i, shift in enumerate(shifts[:3], 1):
        print(f"Shift {i}:")
        print(f"  Date: {shift.get('date')} ({shift.get('dayOfWeek')})")
        print(f"  Time: {shift.get('timeEntered', 'N/A')}")
        print(f"  Total Hours: {shift.get('totalHours', 'N/A')}")
        print(f"  Status: {shift.get('statusTime', 'N/A')}")
        print()

    if len(shifts) > 3:
        print(f"... and {len(shifts) - 3} more shifts\n")

    output_file = "shifts_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(shifts, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved all shifts to {output_file}")

except Exception as e:
    print(f"\n✗ Error: {str(e)}")
    print("\nCheck USERNAME/PASSWORD in config.py and that the date range is valid.")
    exit(1)
