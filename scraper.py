import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Optional
import random
import threading
from datetime import datetime, timedelta
from http.cookiejar import Cookie

logger = logging.getLogger(__name__)

class VinnustundScraper:
    """
    Scraper for kopavogur.vinnustund.is attendance system.
    Handles session management, cookie persistence, and bot detection avoidance.
    """
    
    BASE_URL = "https://kopavogur.vinnustund.is"
    TIMESHEET_URL = f"{BASE_URL}/VS_MX/starfsmadur/starfsm_timafaerslur_view.jsp"
    
    def __init__(self, cookies: Optional[Dict[str, str]] = None, headers: Optional[Dict[str, str]] = None, 
                 keep_alive_interval: int = 300, enable_keep_alive: bool = True,
                 cookie_expiration_years: int = 70):
        """
        Initialize the scraper with session management.
        
        Args:
            cookies: Dictionary of cookies to use (if None, will need to be set manually)
            headers: Custom headers (if None, uses default browser-like headers)
            keep_alive_interval: Interval in seconds between keep-alive actions (default: 300 = 5 minutes)
            enable_keep_alive: Whether to enable background keep-alive thread (default: True)
            cookie_expiration_years: Number of years to extend cookie expiration (default: 70 = ~2096)
        """
        self.session = requests.Session()
        self.keep_alive_interval = keep_alive_interval
        self.enable_keep_alive = enable_keep_alive
        self.cookie_expiration_years = cookie_expiration_years
        self.keep_alive_thread = None
        self.keep_alive_running = False
        self.last_activity = datetime.now()
        self._lock = threading.Lock()
        
        # Set default browser-like headers
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        if headers:
            self.default_headers.update(headers)
        
        self.session.headers.update(self.default_headers)
        
        # Set cookies if provided
        if cookies:
            self.session.cookies.update(cookies)
            self._extend_cookie_expiration(self.cookie_expiration_years)
            logger.info(f"✓ Cookies loaded into session: {len(cookies)} cookies")
        else:
            logger.warning("⚠ No cookies provided - session may not be authenticated")
        
        # Start keep-alive thread if enabled
        if self.enable_keep_alive:
            self.start_keep_alive()
    
    def _extend_cookie_expiration(self, expiration_years: int = 70):
        """
        Extend expiration dates for session cookies (especially JSESSIONID).
        Sets expiration to a far future date (default: 70 years = ~2096).
        
        Args:
            expiration_years: Number of years in the future to set expiration (default: 70)
        """
        try:
            future_date = datetime.now() + timedelta(days=expiration_years * 365)
            future_timestamp = int(future_date.timestamp())
            
            extended_count = 0
            
            # Get all cookies and update their expiration
            for cookie in list(self.session.cookies):
                try:
                    # Extend expiration for:
                    # 1. JSESSIONID (most important)
                    # 2. Session cookies (expires == 0 or None)
                    # 3. Cookies expiring soon (within 30 days)
                    should_extend = (
                        cookie.name == 'JSESSIONID' or
                        cookie.expires == 0 or
                        cookie.expires is None or
                        (cookie.expires and cookie.expires < time.time() + (30 * 24 * 60 * 60))
                    )
                    
                    if should_extend:
                        # Update the cookie's expiration
                        cookie.expires = future_timestamp
                        # Also update the cookie in the jar
                        self.session.cookies.set_cookie(cookie)
                        extended_count += 1
                        logger.debug(f"Extended expiration for cookie: {cookie.name} to {future_date.strftime('%Y-%m-%d')}")
                        
                except (AttributeError, TypeError) as e:
                    # Some cookies might not have expires attribute or it might be read-only
                    logger.debug(f"Could not extend expiration for {cookie.name}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Unexpected error extending {cookie.name}: {e}")
                    continue
            
            if extended_count > 0:
                logger.debug(f"Extended expiration for {extended_count} cookie(s) to {expiration_years} years in the future")
        except Exception as e:
            logger.warning(f"Error extending cookie expiration: {str(e)}")
    
    def set_cookies(self, cookies: Dict[str, str]):
        """Update cookies in the session and extend their expiration"""
        self.session.cookies.update(cookies)
        self._extend_cookie_expiration(self.cookie_expiration_years)
        logger.info(f"✓ Cookies updated: {len(cookies)} cookies")
    
    def get_cookie_expiration_info(self) -> Dict:
        """
        Get information about cookie expiration dates.
        
        Returns:
            Dictionary with cookie expiration information
        """
        info = {
            'cookies': [],
            'expiration_years': self.cookie_expiration_years
        }
        
        for cookie in self.session.cookies:
            cookie_info = {
                'name': cookie.name,
                'domain': cookie.domain,
            }
            
            if cookie.expires:
                if cookie.expires == 0:
                    cookie_info['expires'] = 'Session cookie (no expiration)'
                    cookie_info['expires_timestamp'] = 0
                else:
                    expires_date = datetime.fromtimestamp(cookie.expires)
                    cookie_info['expires'] = expires_date.strftime('%Y-%m-%d %H:%M:%S')
                    cookie_info['expires_timestamp'] = cookie.expires
                    days_until_expiry = (expires_date - datetime.now()).days
                    cookie_info['days_until_expiry'] = days_until_expiry
            else:
                cookie_info['expires'] = 'No expiration set'
                cookie_info['expires_timestamp'] = None
            
            info['cookies'].append(cookie_info)
        
        return info
    
    def _add_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Add random delay to simulate human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def _check_session_valid(self, response: requests.Response) -> bool:
        """Check if session is still valid based on response"""
        logger.debug(f"Checking session validity - Status: {response.status_code}, URL: {response.url}")
        
        # Check response size - very small responses (< 1000 bytes) often indicate redirects or errors
        if len(response.text) < 1000:
            logger.warning(f"⚠ Suspiciously small response: {len(response.text)} bytes - may indicate session expiration")
            # Check if it's a redirect or error page
            if 'login' in response.text.lower() or 'VSLogin' in response.text or len(response.text) < 500:
                logger.error("✗ Session invalid: Response too small, likely expired")
                return False
        
        # Check for redirects to login or error pages
        if response.status_code in [401, 403]:
            logger.error(f"✗ Session invalid: HTTP {response.status_code}")
            return False
        
        # Check if redirected to login page
        if 'login' in response.url.lower() or 'VSLogin' in response.url:
            logger.error(f"✗ Session invalid: Redirected to login page")
            return False
        
        # Check response content for login indicators
        if response.text:
            # Check for login page indicators
            if 'VSLogin.jsp' in response.text or 'login.jsp' in response.text:
                # But check if it's actually a login form, not just a link
                if 'name="username"' in response.text or 'name="password"' in response.text:
                    logger.error("✗ Session invalid: Login form detected in response")
                    return False
            
            # Check for successful authentication indicators
            if 'starfsm_timafaerslur_view.jsp' in response.url or 'clsTableControl' in response.text or 'detail_form' in response.text:
                logger.info("✓ Session appears valid - found timesheet content")
                return True
        
        logger.warning("⚠ Could not definitively determine session validity")
        return True
    
    def _perform_keep_alive_action(self) -> bool:
        """
        Perform a random keep-alive action to simulate user activity.
        Returns True if successful, False otherwise.
        """
        try:
            # Random delay to simulate human behavior
            self._add_delay(0.5, 2.0)
            
            # List of pages to visit (simulating user navigation)
            keep_alive_urls = [
                self.TIMESHEET_URL + "?sj=true",
                self.BASE_URL + "/VS_MX/starfsmadur/starfsmadur_view.jsp?sj=true",
                self.BASE_URL + "/VS_MX/adalsida.jsp",
            ]
            
            # Randomly select a URL
            url = random.choice(keep_alive_urls)
            
            with self._lock:
                self.session.headers['Referer'] = self.BASE_URL
                response = self.session.get(url, timeout=15)
                # Extend cookie expiration after each request to keep session alive
                self._extend_cookie_expiration(self.cookie_expiration_years)
                self.last_activity = datetime.now()
            
            if self._check_session_valid(response):
                logger.debug(f"Keep-alive action successful: {url}")
                return True
            else:
                logger.warning("Keep-alive action detected session expiration")
                return False
                
        except Exception as e:
            logger.warning(f"Keep-alive action failed: {str(e)}")
            return False
    
    def _keep_alive_worker(self):
        """Background worker thread for keep-alive actions"""
        logger.info(f"Keep-alive thread started (interval: {self.keep_alive_interval}s)")
        
        while self.keep_alive_running:
            try:
                # Wait for the interval
                time.sleep(self.keep_alive_interval)
                
                if not self.keep_alive_running:
                    break
                
                # Check if we need to perform keep-alive
                time_since_activity = (datetime.now() - self.last_activity).total_seconds()
                
                if time_since_activity >= self.keep_alive_interval:
                    logger.debug("Performing scheduled keep-alive action...")
                    self._perform_keep_alive_action()
                else:
                    logger.debug(f"Skipping keep-alive (last activity {int(time_since_activity)}s ago)")
                    
            except Exception as e:
                logger.error(f"Error in keep-alive worker: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
        
        logger.info("Keep-alive thread stopped")
    
    def start_keep_alive(self):
        """Start the background keep-alive thread"""
        if not self.enable_keep_alive:
            return
        
        if self.keep_alive_thread is None or not self.keep_alive_thread.is_alive():
            self.keep_alive_running = True
            self.keep_alive_thread = threading.Thread(target=self._keep_alive_worker, daemon=True)
            self.keep_alive_thread.start()
            logger.info("Background keep-alive thread started")
    
    def stop_keep_alive(self):
        """Stop the background keep-alive thread"""
        if self.keep_alive_running:
            self.keep_alive_running = False
            logger.info("Stopping keep-alive thread...")
            if self.keep_alive_thread:
                self.keep_alive_thread.join(timeout=5)
    
    def _ensure_session_valid(self) -> bool:
        """
        Ensure session is valid before making requests.
        Performs a quick check and refresh if needed.
        """
        try:
            with self._lock:
                # Quick check - visit the main page
                response = self.session.get(
                    self.TIMESHEET_URL + "?sj=true",
                    timeout=15
                )
                # Extend cookie expiration
                self._extend_cookie_expiration(self.cookie_expiration_years)
                
                if not self._check_session_valid(response):
                    logger.warning("Session appears invalid, attempting refresh...")
                    # Try to refresh by visiting base URL first
                    self.session.get(self.BASE_URL, timeout=10)
                    time.sleep(1)
                    # Then try timesheet again
                    response = self.session.get(
                        self.TIMESHEET_URL + "?sj=true",
                        timeout=15
                    )
                    # Extend cookie expiration after refresh
                    self._extend_cookie_expiration(self.cookie_expiration_years)
                    
                    if not self._check_session_valid(response):
                        logger.error("✗ Could not refresh session")
                        return False
                
                self.last_activity = datetime.now()
                return True
                
        except Exception as e:
            logger.error(f"Error ensuring session validity: {str(e)}")
            return False
    
    def get_shifts(self, date_from: str, date_to: str) -> List[Dict]:
        """
        Retrieve shifts for the given date range.
        
        Args:
            date_from: Start date in format dd.MM.yyyy (e.g., "01.01.2026")
            date_to: End date in format dd.MM.yyyy (e.g., "25.01.2026")
        
        Returns:
            List of dictionaries containing shift information
        """
        logger.info("=" * 60)
        logger.info(f"Fetching shifts from {date_from} to {date_to}")
        logger.info("=" * 60)
        
        # Log current session state
        logger.info(f"Current cookies in session: {len(self.session.cookies)} cookies")
        
        # Ensure session is valid before proceeding
        if not self._ensure_session_valid():
            raise Exception("Session expired or invalid. Please update cookies.")
        
        try:
            # Step 1: First GET the page to get the form with all hidden fields
            logger.info("Step 1: Fetching initial page to get form fields...")
            self._add_delay(1.0, 2.0)
            
            with self._lock:
                # Extend cookie expiration after successful request
                self._extend_cookie_expiration(self.cookie_expiration_years)
                self.last_activity = datetime.now()
            
            self.session.headers['Referer'] = self.BASE_URL
            initial_response = self.session.get(
                self.TIMESHEET_URL + "?sj=true",
                timeout=30
            )
            
            logger.info(f"Initial GET - Status: {initial_response.status_code}, URL: {initial_response.url}")
            logger.debug(f"Response length: {len(initial_response.text)} bytes")
            
            # Check session validity
            if not self._check_session_valid(initial_response):
                raise Exception("Session expired or invalid. Please update cookies.")
            
            if initial_response.status_code != 200:
                raise Exception(f"Initial GET failed with status code {initial_response.status_code}")
            
            # Parse the initial page to extract form fields
            initial_soup = BeautifulSoup(initial_response.text, 'html.parser')
            form = initial_soup.find('form', {'name': 'detail_form'})
            
            if not form:
                logger.error("✗ Could not find detail_form on initial page")
                logger.info("Attempting session refresh...")
                
                # Try to refresh session by visiting base URL and then retrying
                try:
                    with self._lock:
                        self.session.get(self.BASE_URL, timeout=10)
                        time.sleep(2)
                        self._add_delay(1.0, 2.0)
                        retry_response = self.session.get(
                            self.TIMESHEET_URL + "?sj=true",
                            timeout=30
                        )
                        # Extend cookie expiration after refresh
                        self._extend_cookie_expiration(self.cookie_expiration_years)
                        self.last_activity = datetime.now()
                    
                    if not self._check_session_valid(retry_response):
                        raise Exception("Session expired or invalid after refresh. Please update cookies.")
                    
                    initial_soup = BeautifulSoup(retry_response.text, 'html.parser')
                    form = initial_soup.find('form', {'name': 'detail_form'})
                    
                    if not form:
                        raise Exception("Could not find form on page even after refresh. Session may be invalid.")
                    
                    logger.info("✓ Session refreshed successfully, form found")
                    initial_response = retry_response
                    
                except Exception as refresh_error:
                    logger.error(f"Session refresh failed: {str(refresh_error)}")
                    raise Exception("Could not find form on page. Session may be invalid.")
            
            logger.info("✓ Found detail_form")
            
            # Extract all hidden input fields from the form
            hidden_inputs = {}
            for input_field in form.find_all('input', type='hidden'):
                name = input_field.get('name')
                value = input_field.get('value', '')
                if name:
                    hidden_inputs[name] = value
            
            logger.info(f"Extracted {len(hidden_inputs)} hidden form fields")
            
            # Step 2: Prepare form data with all hidden fields + our date range
            logger.info("Step 2: Preparing form submission...")
            form_data = hidden_inputs.copy()
            form_data.update({
                'timabilFra': date_from,
                'timabilTil': date_to,
            })
            
            # Ensure required fields are set
            if 'sj' not in form_data:
                form_data['sj'] = 'true'
            if 'showBak' not in form_data:
                form_data['showBak'] = 'true'
            
            logger.info(f"Submitting form with {len(form_data)} fields")
            
            # Step 3: Submit the form
            self._add_delay(1.0, 2.0)
            
            with self._lock:
                self.session.headers['Referer'] = self.TIMESHEET_URL + "?sj=true"
                self.session.headers['Content-Type'] = 'application/x-www-form-urlencoded'
                
                response = self.session.post(
                    self.TIMESHEET_URL,
                    data=form_data,
                    allow_redirects=True,
                    timeout=30
                )
                # Extend cookie expiration after POST request
                self._extend_cookie_expiration(self.cookie_expiration_years)
                self.last_activity = datetime.now()
            
            logger.info(f"POST response - Status: {response.status_code}, URL: {response.url}")
            logger.debug(f"Response length: {len(response.text)} bytes")
            
            # Check if session is still valid
            if not self._check_session_valid(response):
                logger.error("✗ Session validation failed after POST")
                raise Exception("Session expired or invalid. Please update cookies.")
            
            if response.status_code != 200:
                logger.error(f"✗ POST failed with status code {response.status_code}")
                raise Exception(f"Received status code {response.status_code}")
            
            # Check for common indicators in the response
            has_timesheet = 'Timesheet' in response.text or 'timesheet' in response.text.lower()
            has_table_control = 'clsTableControl' in response.text
            has_detail_form = 'detail_form' in response.text
            
            logger.info(f"Response indicators: Timesheet={has_timesheet}, TableControl={has_table_control}, DetailForm={has_detail_form}")
            
            # Parse the HTML
            logger.info("Step 3: Parsing HTML response...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find ALL tables with class clsTableControl (there might be multiple)
            all_tables = soup.find_all('table', class_='clsTableControl')
            logger.info(f"Found {len(all_tables)} table(s) with class 'clsTableControl'")
            
            if not all_tables:
                logger.error("✗ Table with class 'clsTableControl' not found in response")
                # Try to find any table
                all_tables_any = soup.find_all('table')
                logger.warning(f"Found {len(all_tables_any)} tables in response, but none with class 'clsTableControl'")
                for i, tbl in enumerate(all_tables_any[:3]):
                    classes = tbl.get('class', [])
                    logger.debug(f"  Table {i+1}: classes={classes}")
                
                # Log more of the response to help debug
                logger.debug(f"Response contains 'Timesheet': {'Timesheet' in response.text}")
                logger.debug(f"Response contains 'starfsm_timafaerslur': {'starfsm_timafaerslur' in response.text}")
                logger.debug(f"Response contains 'clsTableControl': {'clsTableControl' in response.text}")
                
                return []
            
            # Find the table that actually has data (rows)
            table = None
            for i, tbl in enumerate(all_tables, 1):
                rows = tbl.find_all('tr')
                tbody = tbl.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                
                logger.debug(f"  Table {i}: {len(rows)} rows found")
                
                # Use the table with the most rows (should be the data table)
                if not table or len(rows) > len(table.find_all('tr')):
                    table = tbl
                    logger.debug(f"  → Using table {i} with {len(rows)} rows")
            
            if not table:
                logger.error("✗ No valid table found")
                return []
            
            logger.info(f"✓ Using table with class 'clsTableControl' ({len(table.find_all('tr'))} rows)")
            
            # Check for tbody
            tbody = table.find('tbody')
            if tbody:
                logger.debug("✓ Found tbody element")
                tbody_rows = tbody.find_all('tr', recursive=False)  # Only direct children
                logger.debug(f"Found {len(tbody_rows)} direct child rows in tbody")
                # Also check all rows recursively
                tbody_rows_all = tbody.find_all('tr')
                logger.debug(f"Found {len(tbody_rows_all)} total rows in tbody (recursive)")
            else:
                logger.debug("⚠ No tbody found, looking for rows directly in table")
            
            # Check all rows in table (both direct and nested)
            all_rows_direct = table.find_all('tr', recursive=False)
            all_rows_all = table.find_all('tr')
            logger.debug(f"Total <tr> elements found: {len(all_rows_direct)} direct, {len(all_rows_all)} total (recursive)")
            
            # Check if table might be empty
            table_text = table.get_text(strip=True)
            if not table_text or len(table_text) < 50:
                logger.warning("⚠ Table appears to be empty or nearly empty")
            
            # Parse table rows
            shifts = self._parse_table(table)
            
            logger.info("=" * 60)
            logger.info(f"✓ Successfully retrieved {len(shifts)} shifts")
            logger.info("=" * 60)
            
            return shifts
            
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Request error: {str(e)}")
            raise Exception(f"Failed to retrieve shifts: {str(e)}")
        except Exception as e:
            logger.error(f"✗ Error: {str(e)}")
            raise
    
    def _parse_table(self, table: BeautifulSoup) -> List[Dict]:
        """
        Parse the shifts table and extract shift information.
        
        Args:
            table: BeautifulSoup table element
        
        Returns:
            List of shift dictionaries
        """
        shifts = []
        
        # Try to find rows in tbody first, then fall back to all rows
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            logger.debug(f"Using rows from tbody: {len(rows)} rows")
        else:
            rows = table.find_all('tr')
            logger.debug(f"Using all rows from table: {len(rows)} rows")
        
        logger.info(f"Found {len(rows)} rows in table")
        
        if len(rows) == 0:
            logger.warning("⚠ No rows found in table!")
            return []
        
        # Skip header rows (first two rows are usually headers)
        data_rows = []
        header_count = 0
        total_count = 0
        
        for i, row in enumerate(rows):
            # Check if this is a data row (not a header row)
            if row.find('td', class_='vrTableHeader'):
                header_count += 1
                continue
            
            # Check if this is a total/summary row
            row_text = row.get_text()
            if 'Total' in row_text or 'total' in row_text.lower():
                total_count += 1
                continue
            
            # Check if row has meaningful data (has date column)
            tds = row.find_all('td')
            if len(tds) < 3:
                logger.debug(f"  Row {i+1}: Skipped - only {len(tds)} columns")
                continue
            
            data_rows.append(row)
            logger.debug(f"  Row {i+1}: Added as data row with {len(tds)} columns")
        
        logger.info(f"Table breakdown: {header_count} header rows, {total_count} total/summary rows, {len(data_rows)} data rows")
        
        # Parse each data row
        for i, row in enumerate(data_rows, 1):
            shift = self._parse_shift_row(row)
            if shift:
                shifts.append(shift)
                logger.debug(f"  Parsed shift {i}")
            else:
                logger.debug(f"  Row {i}: Failed to parse")
        
        logger.info(f"Successfully parsed {len(shifts)} shifts from {len(data_rows)} data rows")
        return shifts
    
    def _parse_shift_row(self, row: BeautifulSoup) -> Optional[Dict]:
        """
        Parse a single shift row from the table.
        
        Table structure (based on HTML analysis):
        0: Day of week (Vikudagur)
        1: Date
        2-3: Work Hours (colspan 2)
        4: Note
        5: Clock-in
        6: Time entered
        7: Calculation method
        8: Total hours
        9: Absence/Supplement
        10: Hours/Units
        11: Remark
        12: Status Shift (S)
        13: Status Time (T)
        14-18: Pay elements (5 columns)
        19: Detail link
        
        Args:
            row: BeautifulSoup tr element
        
        Returns:
            Dictionary with shift data or None if invalid
        """
        tds = row.find_all('td')
        
        # Need at least day, date, and some basic info
        if len(tds) < 3:
            return None
        
        # Skip if this looks like a header or summary row
        if row.find('td', class_='vrTableHeader'):
            return None
        
        try:
            shift = {}
            
            # Column 0: Day of week
            day_of_week = tds[0].get_text(strip=True)
            if not day_of_week or day_of_week in ['', '&nbsp;']:
                return None  # Skip empty rows
            shift['dayOfWeek'] = day_of_week
            
            # Column 1: Date
            if len(tds) > 1:
                date_text = tds[1].get_text(strip=True)
                shift['date'] = date_text
            
            # Columns 2-3: Work Hours (colspan 2, but we get both)
            if len(tds) > 2:
                work_hours = tds[2].get_text(strip=True)
                shift['workHours'] = work_hours
                # Also check if there's a link or additional info in column 3
                if len(tds) > 3:
                    work_hours_extra = tds[3].get_text(strip=True)
                    if work_hours_extra:
                        shift['workHoursExtra'] = work_hours_extra
            
            # Column 4: Note
            if len(tds) > 4:
                note = tds[4].get_text(strip=True)
                shift['note'] = note
            
            # Column 5: Clock-in
            if len(tds) > 5:
                clock_in = tds[5].get_text(strip=True)
                shift['clockIn'] = clock_in
            
            # Column 6: Time entered
            if len(tds) > 6:
                time_entered = tds[6].get_text(strip=True)
                shift['timeEntered'] = time_entered
            
            # Column 7: Calculation method
            if len(tds) > 7:
                calc_method = tds[7].get_text(strip=True)
                shift['calculationMethod'] = calc_method
            
            # Column 8: Total hours
            if len(tds) > 8:
                total_hours = tds[8].get_text(strip=True)
                shift['totalHours'] = total_hours
            
            # Column 9: Absence/Supplement
            if len(tds) > 9:
                absence = tds[9].get_text(strip=True)
                shift['absenceSupplement'] = absence
            
            # Column 10: Hours/Units
            if len(tds) > 10:
                hours_units = tds[10].get_text(strip=True)
                shift['hoursUnits'] = hours_units
            
            # Column 11: Remark
            if len(tds) > 11:
                remark = tds[11].get_text(strip=True)
                shift['remark'] = remark
            
            # Column 12: Status Shift (S)
            if len(tds) > 12:
                status_shift = tds[12].get_text(strip=True)
                shift['statusShift'] = status_shift
            
            # Column 13: Status Time (T)
            if len(tds) > 13:
                status_time = tds[13].get_text(strip=True)
                shift['statusTime'] = status_time
            
            # Columns 14-18: Pay elements (5 columns)
            pay_elements = []
            if len(tds) > 14:
                for i in range(14, min(19, len(tds))):
                    pay_text = tds[i].get_text(strip=True)
                    if pay_text and pay_text not in ['', '&nbsp;']:
                        pay_elements.append(pay_text)
            shift['payElements'] = pay_elements
            
            # Try to extract links and additional metadata
            # Look for links in time entered column
            if len(tds) > 6:
                link = tds[6].find('a')
                if link and link.get('title'):
                    shift['timeEnteredTitle'] = link.get('title')
            
            # Look for status titles
            if len(tds) > 12:
                status_span = tds[12].find('span')
                if status_span and status_span.get('title'):
                    shift['statusShiftTitle'] = status_span.get('title')
            
            if len(tds) > 13:
                status_span = tds[13].find('span')
                if status_span and status_span.get('title'):
                    shift['statusTimeTitle'] = status_span.get('title')
            
            # Get full row text for debugging
            shift['rawText'] = row.get_text(separator=' | ', strip=True)
            
            return shift
            
        except Exception as e:
            logger.warning(f"Error parsing row: {str(e)}")
            return None
    
    def test_authentication(self) -> bool:
        """
        Test if the current session is authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        logger.info("Testing authentication...")
        logger.info(f"Current cookies: {len(self.session.cookies)}")
        
        try:
            self._add_delay(0.5, 1.0)
            response = self.session.get(
                self.TIMESHEET_URL + "?sj=true",
                timeout=15
            )
            
            logger.info(f"Auth test - Status: {response.status_code}, URL: {response.url}")
            
            is_valid = self._check_session_valid(response)
            
            if is_valid:
                logger.info("✓ Authentication successful!")
                # Check if we can see the form
                if 'detail_form' in response.text:
                    logger.info("✓ Found detail_form - session is working")
                else:
                    logger.warning("⚠ detail_form not found in response")
            else:
                logger.error("✗ Authentication failed - session invalid")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"✗ Authentication test failed: {str(e)}")
            return False
    
    def keep_alive(self):
        """
        Send a keep-alive request to maintain session.
        Call this periodically (e.g., every 10 minutes) to avoid timeout.
        Note: If enable_keep_alive=True, this is handled automatically in the background.
        """
        return self._perform_keep_alive_action()
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_keep_alive()
