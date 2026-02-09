"""
Selenium-based web scraper for YÖK National Thesis Center
Uses real browser automation to bypass bot protection
"""

import logging
import asyncio
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from .utils import (
    RateLimiter,
    SimpleCache,
    normalize_turkish_text,
    parse_year,
    build_cache_key
)

logger = logging.getLogger(__name__)


class YOKThesisScraperError(Exception):
    """Base exception for YÖK scraper errors."""
    pass


class SeleniumYOKScraper:
    """
    Selenium-based scraper for YÖK National Thesis Center.
    Uses real browser automation to bypass bot detection.
    """

    # YÖK Tez Merkezi URLs
    BASE_URL = "https://tez.yok.gov.tr"
    SEARCH_URL = f"{BASE_URL}/UlusalTezMerkezi/tarama.jsp"
    DETAIL_URL = f"{BASE_URL}/UlusalTezMerkezi/tezDetay.jsp"

    THESIS_TYPES = {
        "yuksek_lisans": "1",
        "doktora": "2",
        "tipta_uzmanlik": "3",
        "sanatta_yeterlik": "4"
    }

    PERMISSION_STATUS = {
        "izinli": "1",
        "izinsiz": "0"
    }

    def __init__(
        self,
        rate_limit_delay: float = 3.0,
        cache_ttl: int = 3600,
        timeout: float = 30.0,
        headless: bool = True
    ):
        """
        Initialize Selenium-based YÖK scraper.

        Args:
            rate_limit_delay: Minimum delay between requests in seconds
            cache_ttl: Cache time-to-live in seconds
            timeout: Page load timeout in seconds
            headless: Run browser in headless mode
        """
        self.rate_limiter = RateLimiter(min_delay=rate_limit_delay)
        self.cache = SimpleCache(default_ttl=cache_ttl)
        self.timeout = timeout
        self.headless = headless
        self.driver = None

        logger.info("Selenium YÖK Thesis Scraper initialized")

    def _get_driver(self) -> webdriver.Chrome:
        """
        Create and configure Chrome WebDriver.

        Returns:
            Configured Chrome WebDriver instance
        """
        if self.driver is None:
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument('--headless=new')

            # Anti-bot detection options
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')

            # User agent
            chrome_options.add_argument(
                'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            )

            # Additional preferences
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 2,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False
            })

            # Install and setup ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # Remove webdriver property
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # Set timeout
            self.driver.set_page_load_timeout(self.timeout)

            logger.info("Chrome WebDriver initialized successfully")

        return self.driver

    async def search(
        self,
        query: str,
        search_field: str = "tumu",
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        thesis_type: Optional[str] = None,
        university: Optional[str] = None,
        language: Optional[str] = None,
        permission_status: Optional[str] = None,
        max_results: int = 20,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for theses using Selenium.

        Args:
            query: Search query
            search_field: Field to search (tez_adi, yazar, danisman, konu, tumu)
            year_start: Start year filter
            year_end: End year filter
            thesis_type: Thesis type filter
            university: University filter
            language: Language filter
            permission_status: Permission status filter
            max_results: Maximum results to return
            use_cache: Whether to use cache

        Returns:
            List of thesis dictionaries
        """
        # Build cache key
        cache_key = build_cache_key(
            "search", query, search_field, year_start, year_end,
            thesis_type, university, language, permission_status, max_results
        )

        # Check cache
        if use_cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached search results for: {query}")
                return cached_result

        await self.rate_limiter.wait()

        try:
            # Run synchronous Selenium code in thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._search_sync,
                query,
                search_field,
                year_start,
                year_end,
                thesis_type,
                university,
                language,
                permission_status,
                max_results
            )

            # Cache results
            if use_cache and results:
                await self.cache.set(cache_key, results)

            return results

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise YOKThesisScraperError(f"Search error: {str(e)}")

    def _search_sync(
        self,
        query: str,
        search_field: str,
        year_start: Optional[int],
        year_end: Optional[int],
        thesis_type: Optional[str],
        university: Optional[str],
        language: Optional[str],
        permission_status: Optional[str],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Synchronous search implementation using Selenium.
        """
        driver = self._get_driver()

        try:
            logger.info(f"Navigating to YÖK search page: {self.SEARCH_URL}")
            driver.get(self.SEARCH_URL)

            # Wait for page to load
            wait = WebDriverWait(driver, 10)

            # Determine which tab to use based on search_field
            # For "tumu" (search all), use Advanced Search (tabs-2) with keyword field
            # For specific fields, use Detailed Search (tabs-1)
            if search_field == "tumu":
                # Use Advanced Search tab (tabs-2) for general search
                try:
                    advanced_tab = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-2'], #ui-id-2"))
                    )
                    advanced_tab.click()
                    logger.info("Clicked advanced search tab")
                    time.sleep(1)

                    # Fill keyword field
                    keyword_input = driver.find_element(By.NAME, "keyword")
                    keyword_input.clear()
                    keyword_input.send_keys(query)
                    logger.info(f"Entered query '{query}' in keyword field")
                except (TimeoutException, NoSuchElementException) as e:
                    logger.warning(f"Could not use advanced search: {e}")
                    raise
            else:
                # Use Detailed Search tab (tabs-1) for specific field search
                try:
                    detailed_tab = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-1'], #ui-id-1"))
                    )
                    detailed_tab.click()
                    logger.info("Clicked detailed search tab")
                    time.sleep(1)

                    # Map search_field to actual YÖK form field names
                    field_mapping = {
                        "tez_adi": "TezAd",
                        "yazar": "AdSoyad",
                        "danisman": "DanismanAdSoyad",
                        "konu": "Dizin"
                    }

                    input_name = field_mapping.get(search_field, "TezAd")
                    search_input = driver.find_element(By.NAME, input_name)
                    search_input.clear()
                    search_input.send_keys(query)
                    logger.info(f"Entered query '{query}' in field '{input_name}'")
                except (TimeoutException, NoSuchElementException) as e:
                    logger.warning(f"Could not use detailed search: {e}")
                    raise

            # Fill year filters if provided (works in both tabs)
            if year_start:
                try:
                    year_start_select = Select(driver.find_element(By.NAME, "yil1"))
                    year_start_select.select_by_value(str(year_start))
                    logger.info(f"Set start year: {year_start}")
                except (NoSuchElementException, Exception) as e:
                    logger.warning(f"Could not set start year: {e}")

            if year_end:
                try:
                    year_end_select = Select(driver.find_element(By.NAME, "yil2"))
                    year_end_select.select_by_value(str(year_end))
                    logger.info(f"Set end year: {year_end}")
                except (NoSuchElementException, Exception) as e:
                    logger.warning(f"Could not set end year: {e}")

            # Set thesis type if provided
            if thesis_type and thesis_type in self.THESIS_TYPES:
                try:
                    thesis_type_select = Select(driver.find_element(By.NAME, "Tur"))
                    thesis_type_select.select_by_value(self.THESIS_TYPES[thesis_type])
                    logger.info(f"Selected thesis type: {thesis_type}")
                except (NoSuchElementException, Exception) as e:
                    logger.warning(f"Could not set thesis type: {e}")

            # Set university if provided
            if university:
                try:
                    university_input = driver.find_element(By.NAME, "uniad")
                    university_input.clear()
                    university_input.send_keys(university)
                    logger.info(f"Set university: {university}")
                except NoSuchElementException:
                    logger.warning("University field not found")

            # Set language if provided
            if language:
                try:
                    language_select = Select(driver.find_element(By.NAME, "Dil"))
                    language_select.select_by_visible_text(language)
                    logger.info(f"Set language: {language}")
                except (NoSuchElementException, Exception) as e:
                    logger.warning(f"Could not set language: {e}")

            # Submit the search form
            # Find submit button within the active tab
            tab_id = "tabs-2" if search_field == "tumu" else "tabs-1"

            try:
                # Find the active tab element
                active_tab = driver.find_element(By.ID, tab_id)

                # Find submit button within this tab
                submit_button = active_tab.find_element(By.CSS_SELECTOR, "input[type='submit'][name='-find']")

                # Scroll to button to ensure it's visible
                driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                time.sleep(0.5)

                # Click the button
                submit_button.click()
                logger.info(f"Clicked 'Bul' (Find) button in {tab_id}")
            except NoSuchElementException:
                logger.warning(f"Submit button not found in {tab_id}")
                raise

            # Wait for results to load
            # YÖK shows results in a table with class 'watable'
            try:
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.watable, table.table-striped"))
                )
                logger.info("Search results loaded")
            except TimeoutException:
                logger.warning("Results table not found after search")

            # Get page source and parse with BeautifulSoup
            html = driver.page_source
            results = self._parse_search_results(html, max_results)

            logger.info(f"Found {len(results)} thesis results")
            return results

        except Exception as e:
            logger.error(f"Error during search: {str(e)}", exc_info=True)
            raise

    def _parse_search_results(self, html: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Parse search results from HTML.

        YÖK results table structure:
        - Table class: 'watable' (also has 'table-striped', 'table-hover', etc.)
        - Columns: [No, Tez No, Yazar, Yıl, Tez Adı, Tez Türü, Konu, ...]
        - Cell indices: 0=Row#, 1=ThesisID, 2=Author, 3=Year, 4=Title, 5=Type, 6=Subject
        """
        soup = BeautifulSoup(html, 'lxml')
        results = []

        # Find the results table - YÖK uses 'watable' class
        table = soup.find('table', class_='watable')

        if not table:
            # Fallback to other possible selectors
            table = (
                soup.find('table', class_='table-striped') or
                soup.find('table', {'class': 'tablo'}) or
                soup.find('table', {'id': 'resulttable'})
            )

        if not table:
            logger.warning("No results table found in HTML")
            return results

        # Find tbody (data rows)
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("No tbody found in results table")
            return results

        rows = tbody.find_all('tr')
        logger.info(f"Found {len(rows)} result rows in table")

        for row in rows[:max_results]:
            try:
                cells = row.find_all('td')
                if len(cells) < 6:
                    continue

                # Extract thesis information based on YÖK table structure
                thesis_data = {
                    "thesis_id": normalize_turkish_text(cells[1].get_text()) if len(cells) > 1 else None,
                    "author": normalize_turkish_text(cells[2].get_text()) if len(cells) > 2 else "",
                    "year": parse_year(cells[3].get_text()) if len(cells) > 3 else None,
                    "title": normalize_turkish_text(cells[4].get_text()) if len(cells) > 4 else "",
                    "thesis_type": cells[5].get_text().strip() if len(cells) > 5 else None,
                    "university": "",  # Not in search results table, need detail page
                    "language": None,  # Not in search results table
                }

                results.append(thesis_data)

            except Exception as e:
                logger.warning(f"Failed to parse row: {str(e)}")
                continue

        logger.info(f"Successfully parsed {len(results)} thesis results")
        return results

    def _extract_thesis_id(self, cell) -> Optional[str]:
        """Extract thesis ID from table cell."""
        link = cell.find('a')
        if link and 'href' in link.attrs:
            href = link['href']
            if 'id=' in href:
                return href.split('id=')[-1].split('&')[0]

        text = cell.get_text().strip()
        if text.isdigit():
            return text

        return None

    async def get_thesis_details(
        self,
        thesis_id: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed thesis information using Selenium.
        """
        cache_key = build_cache_key("detail", thesis_id)

        if use_cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached thesis details for: {thesis_id}")
                return cached_result

        await self.rate_limiter.wait()

        try:
            loop = asyncio.get_event_loop()
            details = await loop.run_in_executor(
                None,
                self._get_thesis_details_sync,
                thesis_id
            )

            if use_cache:
                await self.cache.set(cache_key, details)

            return details

        except Exception as e:
            logger.error(f"Failed to get thesis details: {str(e)}")
            raise YOKThesisScraperError(f"Detail retrieval error: {str(e)}")

    def _create_complete_thesis_response(
        self,
        thesis_id: str,
        title: str = None,
        author: str = None
    ) -> Dict[str, Any]:
        """Create a complete thesis response with all required fields."""
        return {
            "thesis_id": thesis_id,
            "title": title or "Detaylar yüklenemedi",
            "author": author or "Bilinmiyor",
            "advisor": None,
            "year": None,
            "university": None,
            "institute": None,
            "department": None,
            "thesis_type": None,
            "language": None,
            "page_count": None,
            "keywords": None,
            "abstract": None,
            "purpose": None
        }

    def _get_thesis_details_sync(self, thesis_id: str) -> Dict[str, Any]:
        """
        Synchronous thesis detail retrieval using search + modal approach.

        YÖK's direct detail page URLs return errors, so we:
        1. Search for the thesis by ID
        2. Click the thesis to open modal
        3. Parse modal content for basic info
        4. Extract abstract from modal's HTML
        """
        driver = self._get_driver()

        try:
            logger.info(f"Fetching thesis {thesis_id} via search + modal")

            # Navigate to search page
            driver.get(self.SEARCH_URL)
            time.sleep(3)

            wait = WebDriverWait(driver, 15)

            # Click detailed search tab
            detailed_tab = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-1']"))
            )
            detailed_tab.click()
            logger.info("✓ Opened detailed search")
            time.sleep(1)

            # Enter thesis ID
            try:
                tez_no_input = driver.find_element(By.NAME, "TezNo")
                tez_no_input.clear()
                tez_no_input.send_keys(thesis_id)
                logger.info(f"✓ Entered thesis ID: {thesis_id}")
            except:
                logger.warning("TezNo field not found")
                return self._create_complete_thesis_response(thesis_id)

            # Submit search
            tabs1_div = driver.find_element(By.ID, "tabs-1")
            submit_button = tabs1_div.find_element(By.CSS_SELECTOR, "input[type='submit']")
            submit_button.click()
            logger.info("✓ Submitted search")
            time.sleep(5)

            # Find thesis in results
            try:
                thesis_span = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, f"//span[@onclick and contains(text(), '{thesis_id}')]")
                    )
                )
                logger.info(f"✓ Found thesis {thesis_id} in results")
            except TimeoutException:
                logger.warning(f"Thesis {thesis_id} not found in search results")
                return self._create_complete_thesis_response(thesis_id)

            # Click to open modal
            logger.info("Opening modal...")
            driver.execute_script("arguments[0].click();", thesis_span)
            time.sleep(4)

            # Wait for modal
            try:
                modal = wait.until(
                    EC.presence_of_element_located((By.ID, "dialog-modal"))
                )
                logger.info("✓ Modal opened")

                # Scroll within modal to load all content
                driver.execute_script("""
                    var modal = document.getElementById('dialog-modal');
                    if (modal) {
                        modal.scrollTop = modal.scrollHeight;
                    }
                """)
                time.sleep(2)

                # Get modal HTML
                modal_html = modal.get_attribute('innerHTML')

                # Parse modal content
                details = self._parse_modal_content_enhanced(modal_html, thesis_id)

                if details.get('abstract'):
                    logger.info(f"✓ Found abstract: {len(details['abstract'])} chars")
                else:
                    logger.warning(f"⚠ Abstract not found")

                if details.get('purpose'):
                    logger.info(f"✓ Found purpose: {len(details['purpose'])} chars")
                else:
                    logger.warning(f"⚠ Purpose not found")

                return details

            except TimeoutException:
                logger.warning("Modal did not appear")
                return self._create_complete_thesis_response(thesis_id)

        except Exception as e:
            logger.error(f"Error fetching thesis: {str(e)}", exc_info=True)
            return self._create_complete_thesis_response(
                thesis_id=thesis_id,
                title=f"Tez #{thesis_id}",
                author="Bilgi alınamadı"
            )

    def _parse_modal_content(self, html: str, thesis_id: str) -> Dict[str, Any]:
        """Parse thesis details from modal dialog content (legacy method)."""
        return self._parse_modal_content_enhanced(html, thesis_id)

    def _parse_modal_content_enhanced(self, html: str, thesis_id: str) -> Dict[str, Any]:
        """Enhanced modal content parser with improved abstract/purpose extraction."""
        soup = BeautifulSoup(html, 'lxml')
        import re

        # Start with complete response
        details = {
            "thesis_id": thesis_id,
            "title": None,
            "author": None,
            "advisor": None,
            "year": None,
            "university": None,
            "institute": None,
            "department": None,
            "thesis_type": None,
            "language": None,
            "page_count": None,
            "keywords": None,
            "abstract": None,
            "purpose": None
        }

        try:
            # === PARSE BASIC INFO ===
            # Find main content cell
            content_td = soup.find('td', valign='top', string=lambda t: 'Yazar' in str(t) if t else False)
            if not content_td:
                rows = soup.find_all('tr', class_='renkp')
                if rows:
                    cells = rows[0].find_all('td')
                    if len(cells) >= 3:
                        content_td = cells[2]

            if content_td:
                text = content_td.get_text()
                lines = [l.strip() for l in text.split('\n') if l.strip()]

                if lines:
                    # Title is often the first line
                    details['title'] = lines[0].split(' / ')[0].strip()

                # Extract fields
                for line in lines:
                    if 'Yazar:' in line:
                        details['author'] = line.replace('Yazar:', '').strip()
                    elif 'Danışman:' in line or 'Danışman :' in line:
                        details['advisor'] = line.replace('Danışman:', '').replace('Danışman :', '').strip()
                    elif 'Yer Bilgisi:' in line:
                        parts = line.replace('Yer Bilgisi:', '').split('/')
                        if len(parts) >= 1:
                            details['university'] = parts[0].strip()
                        if len(parts) >= 2:
                            details['institute'] = parts[1].strip()
                        if len(parts) >= 3:
                            details['department'] = parts[2].strip()
                    elif 'Dizin:' in line:
                        details['keywords'] = line.replace('Dizin:', '').strip()

            # Status cell
            status_cells = soup.find_all('td', valign='top')
            if len(status_cells) >= 4:
                status_td = status_cells[3]
                status_text = status_td.get_text()
                status_lines = [l.strip() for l in status_text.split('\n') if l.strip()]

                for line in status_lines:
                    if any(t in line for t in ['Doktora', 'Yüksek Lisans', 'Tıpta Uzmanlık', 'Sanatta Yeterlik']):
                        details['thesis_type'] = line.strip()
                    elif any(lang in line for lang in ['İngilizce', 'Türkçe', 'English', 'Turkish']):
                        details['language'] = line.strip()
                    elif line.isdigit() and len(line) == 4:
                        details['year'] = line
                    elif 's.' in line:
                        details['page_count'] = line.strip()

            # === ENHANCED ABSTRACT & PURPOSE EXTRACTION ===
            abstract_text = None
            purpose_text = None
            all_text = soup.get_text()

            # Method 1: Find td with id="td0" - YÖK's structured abstract format
            # This td contains: Amaç, Gereç ve Yöntem, Bulgular, Sonuç, Anahtar Kelimeler
            td0 = soup.find('td', {'id': 'td0'})
            if td0:
                td0_text = td0.get_text().strip()
                logger.info(f"✓ Found td0 with {len(td0_text)} chars")

                # Extract Amaç (Purpose)
                amac_match = re.search(r'Amaç:\s*(.+?)(?=\n\s*(?:Gereç|Yöntem|Method|Material|Bulgular|$))',
                                      td0_text, re.IGNORECASE | re.DOTALL)
                if amac_match:
                    purpose_text = normalize_turkish_text(amac_match.group(1).strip())
                    logger.info(f"✓ Found purpose in td0: {len(purpose_text)} chars")

                # Extract full structured abstract as "abstract"
                # Take everything from Amaç to Anahtar Kelimeler
                abstract_match = re.search(r'(Amaç:.+?)(?=Anahtar Kelimeler|$)',
                                          td0_text, re.IGNORECASE | re.DOTALL)
                if abstract_match:
                    abstract_text = normalize_turkish_text(abstract_match.group(1).strip())
                    logger.info(f"✓ Found structured abstract in td0: {len(abstract_text)} chars")

            # Method 2: Find divs with abstract classes
            if not abstract_text:
                for selector in [{'class': 'ozet'}, {'class': 'abstract'}, {'id': 'ozet'}]:
                    elem = soup.find(['div', 'p', 'span'], selector)
                    if elem:
                        text = elem.get_text().strip()
                        if len(text) > 100:
                            abstract_text = normalize_turkish_text(text)
                            logger.info(f"✓ Found abstract using {selector}")
                            break

            # Method 3: Find by looking for "Özet:" or "Abstract:" labels in table rows
            if not abstract_text:
                all_rows = soup.find_all('tr')
                for row in all_rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text().strip()
                        if any(word in label.lower() for word in ['özet', 'abstract']):
                            text = cells[1].get_text().strip()
                            if len(text) > 100:
                                abstract_text = normalize_turkish_text(text)
                                logger.info("✓ Found abstract in table row")
                                break

            # Method 4: Regex search for abstract patterns
            if not abstract_text:
                patterns = [
                    r'(?:Türkçe\s+)?Özet\s*:?\s*\n?\s*(.+?)(?=\n\s*(?:İngilizce|Abstract|Amaç|Yöntem|Giriş|$))',
                    r'(?:Turkish\s+)?Abstract\s*:?\s*\n?\s*(.+?)(?=\n\s*(?:English|Özet|Purpose|Method|$))',
                    r'Özet\s*:\s*(.{100,}?)(?=\n\s*\n)',
                    r'Abstract\s*:\s*(.{100,}?)(?=\n\s*\n)'
                ]

                for pattern in patterns:
                    match = re.search(pattern, all_text, re.IGNORECASE | re.DOTALL)
                    if match:
                        text = match.group(1).strip()
                        text = re.sub(r'\s+', ' ', text)
                        if len(text) > 100:
                            abstract_text = normalize_turkish_text(text)
                            logger.info("✓ Found abstract via regex")
                            break

            # Method 5: Find paragraphs/divs containing substantial academic text
            if not abstract_text:
                for elem in soup.find_all(['p', 'div', 'td']):
                    elem_text = elem.get_text().strip()
                    if len(elem_text) > 200 and elem_text.count(' ') > 30:
                        indicators = ['amaç', 'yöntem', 'sonuç', 'çalışma', 'bulgular',
                                     'purpose', 'method', 'results', 'study', 'findings']
                        if any(ind in elem_text.lower() for ind in indicators):
                            abstract_text = normalize_turkish_text(elem_text)
                            logger.info("✓ Found abstract by content analysis")
                            break

            if abstract_text:
                details['abstract'] = abstract_text

            # === PURPOSE EXTRACTION (if not found in td0) ===
            if not purpose_text:
                # Method 1: Find in table rows with "Amaç" label
                all_rows = soup.find_all('tr')
                for row in all_rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text().strip().lower()
                        if any(word in label for word in ['amaç', 'purpose', 'objective']):
                            text = cells[1].get_text().strip()
                            if len(text) > 30:
                                purpose_text = normalize_turkish_text(text)
                                logger.info("✓ Found purpose in table")
                                break

            # Method 2: Regex search for purpose
            if not purpose_text:
                patterns = [
                    r'(?:Çalışmanın\s+)?Amaç[ıi]?\s*:\s*(.+?)(?=\n\s*(?:Yöntem|Gereç|Method|Material|Bulgular|$))',
                    r'Purpose\s*:\s*(.+?)(?=\n\s*(?:Method|Material|$))',
                    r'Aim\s*:\s*(.+?)(?=\n\s*(?:Method|Material|$))'
                ]

                for pattern in patterns:
                    match = re.search(pattern, all_text, re.IGNORECASE | re.DOTALL)
                    if match:
                        text = match.group(1).strip()
                        text = re.sub(r'\s+', ' ', text)[:500]
                        if len(text) > 30:
                            purpose_text = normalize_turkish_text(text)
                            logger.info("✓ Found purpose via regex")
                            break

            if purpose_text:
                details['purpose'] = purpose_text

        except Exception as e:
            logger.error(f"Error parsing modal: {str(e)}", exc_info=True)

        return details

    def _parse_thesis_detail(self, html: str, thesis_id: str) -> Dict[str, Any]:
        """Parse detailed thesis information with improved abstract/purpose extraction."""
        soup = BeautifulSoup(html, 'lxml')

        # Start with complete response structure
        details = {
            "thesis_id": thesis_id,
            "title": None,
            "author": None,
            "advisor": None,
            "year": None,
            "university": None,
            "institute": None,
            "department": None,
            "thesis_type": None,
            "language": None,
            "page_count": None,
            "keywords": None,
            "abstract": None,
            "purpose": None
        }

        # Try multiple selectors for the detail table
        detail_table = (
            soup.find('table', {'class': 'bilgi'}) or
            soup.find('div', {'class': 'thesis-detail'}) or
            soup.find('table', class_=lambda x: x and 'tablo' in x) or
            soup.find('div', {'id': 'iceriktablo'})
        )

        if detail_table:
            rows = detail_table.find_all('tr')
            for row in rows:
                try:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = normalize_turkish_text(cells[0].get_text()).rstrip(':')
                        value = normalize_turkish_text(cells[1].get_text())

                        key_mapping = {
                            'Tez No': 'thesis_id',
                            'Tez Adı': 'title',
                            'Yazar': 'author',
                            'Danışman': 'advisor',
                            'Eş Danışman': 'co_advisor',
                            'Yıl': 'year',
                            'Üniversite': 'university',
                            'Enstitü': 'institute',
                            'Anabilim Dalı': 'department',
                            'Tez Türü': 'thesis_type',
                            'Dil': 'language',
                            'Sayfa Sayısı': 'page_count',
                            'Anahtar Kelimeler': 'keywords',
                        }

                        english_key = key_mapping.get(key, key.lower().replace(' ', '_'))
                        if english_key in details:  # Only update if it's a known field
                            details[english_key] = value

                except Exception as e:
                    logger.warning(f"Failed to parse detail row: {str(e)}")
                    continue

        # === ENHANCED ABSTRACT EXTRACTION ===
        abstract_text = None
        import re

        # Method 1: Find all elements containing "Özet" or "Abstract" in their text
        logger.info("Searching for abstract using multiple methods...")

        # Look for specific div/section patterns
        for selector in [
            {'class': 'ozet'},
            {'class': 'abstract'},
            {'class': 'thesis-abstract'},
            {'id': 'ozet'},
            {'id': 'abstract'}
        ]:
            elem = soup.find(['div', 'section', 'p'], selector)
            if elem:
                text = elem.get_text().strip()
                if len(text) > 100:
                    abstract_text = normalize_turkish_text(text)
                    logger.info(f"✓ Found abstract using selector: {selector}")
                    break

        # Method 2: Find by icon classes (YÖK sometimes uses Font Awesome icons)
        if not abstract_text:
            icon_classes = ['fa-align-left', 'fa-file-text', 'fa-paragraph']
            for icon_class in icon_classes:
                icon = soup.find('i', class_=icon_class)
                if icon:
                    parent = icon.find_parent(['div', 'section'])
                    if parent:
                        text = parent.get_text().strip()
                        if 'özet' in text.lower() or 'abstract' in text.lower():
                            # Extract text after the heading
                            text_parts = text.split('\n', 1)
                            if len(text_parts) > 1 and len(text_parts[1]) > 100:
                                abstract_text = normalize_turkish_text(text_parts[1])
                                logger.info(f"✓ Found abstract using icon class: {icon_class}")
                                break

        # Method 3: Find table rows with "Özet" label
        if not abstract_text:
            all_rows = soup.find_all('tr')
            for row in all_rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text().strip().lower()
                    if 'özet' in label or 'abstract' in label:
                        text = cells[1].get_text().strip()
                        if len(text) > 100:
                            abstract_text = normalize_turkish_text(text)
                            logger.info("✓ Found abstract in table row")
                            break

        # Method 4: Search all text content with regex patterns
        if not abstract_text:
            all_text = soup.get_text()

            # Pattern 1: Turkish abstract
            patterns = [
                r'(?:Türkçe\s+)?Özet\s*:?\s*\n\s*(.+?)(?=\n\s*(?:İngilizce|Abstract|Amaç|Yöntem|Giriş|Kaynakça|$))',
                r'(?:Turkish\s+)?Abstract\s*:?\s*\n\s*(.+?)(?=\n\s*(?:English|Özet|Purpose|Method|Introduction|References|$))',
                r'Özet\s*:\s*(.+?)(?=\n\s*\n|\n\s*[A-ZÖÜÇĞİŞ])',
                r'Abstract\s*:\s*(.+?)(?=\n\s*\n|\n\s*[A-Z])'
            ]

            for pattern in patterns:
                match = re.search(pattern, all_text, re.IGNORECASE | re.DOTALL)
                if match:
                    text = match.group(1).strip()
                    # Clean up excessive whitespace
                    text = re.sub(r'\s+', ' ', text)
                    if len(text) > 100:
                        abstract_text = normalize_turkish_text(text)
                        logger.info(f"✓ Found abstract using regex pattern")
                        break

        # Method 5: Look for paragraphs after headings containing "Özet"
        if not abstract_text:
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'])
            for heading in headings:
                heading_text = heading.get_text().strip().lower()
                if 'özet' in heading_text or 'abstract' in heading_text:
                    # Get all next siblings until next heading
                    content_parts = []
                    for sibling in heading.find_next_siblings():
                        if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            break
                        text = sibling.get_text().strip()
                        if text:
                            content_parts.append(text)

                    combined_text = ' '.join(content_parts)
                    if len(combined_text) > 100:
                        abstract_text = normalize_turkish_text(combined_text)
                        logger.info("✓ Found abstract after heading element")
                        break

        if abstract_text:
            details['abstract'] = abstract_text
            logger.info(f"✓ Abstract extracted: {len(abstract_text)} characters")
        else:
            logger.warning("⚠ Could not find abstract in detail page")

        # === ENHANCED PURPOSE EXTRACTION ===
        purpose_text = None
        logger.info("Searching for purpose using multiple methods...")

        # Method 1: Find table rows with "Amaç" label
        all_rows = soup.find_all('tr')
        for row in all_rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text().strip().lower()
                if 'amaç' in label or 'purpose' in label or 'objective' in label:
                    text = cells[1].get_text().strip()
                    if len(text) > 30:
                        purpose_text = normalize_turkish_text(text)
                        logger.info("✓ Found purpose in table row")
                        break

        # Method 2: Search with regex patterns
        if not purpose_text:
            all_text = soup.get_text()
            patterns = [
                r'(?:Çalışmanın\s+)?Amaç[ıi]?\s*:?\s*\n?\s*(.+?)(?=\n\s*(?:Yöntem|Gereç|Bulgular|Sonuç|Method|Material|Results|Conclusion|$))',
                r'Purpose\s*:?\s*\n?\s*(.+?)(?=\n\s*(?:Method|Material|Results|Conclusion|Yöntem|$))',
                r'Objective\s*:?\s*\n?\s*(.+?)(?=\n\s*(?:Method|Material|Results|$))'
            ]

            for pattern in patterns:
                match = re.search(pattern, all_text, re.IGNORECASE | re.DOTALL)
                if match:
                    text = match.group(1).strip()
                    # Clean up and take first reasonable chunk
                    text = re.sub(r'\s+', ' ', text)
                    # Take up to first double newline or 500 chars
                    text = text.split('\n\n')[0][:500]
                    if len(text) > 30:
                        purpose_text = normalize_turkish_text(text)
                        logger.info(f"✓ Found purpose using regex pattern")
                        break

        # Method 3: Look for headings with "Amaç"
        if not purpose_text:
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'])
            for heading in headings:
                heading_text = heading.get_text().strip().lower()
                if 'amaç' in heading_text or 'purpose' in heading_text or 'objective' in heading_text:
                    # Get next paragraph or div
                    next_elem = heading.find_next(['p', 'div', 'span'])
                    if next_elem:
                        text = next_elem.get_text().strip()
                        if len(text) > 30:
                            purpose_text = normalize_turkish_text(text)
                            logger.info("✓ Found purpose after heading element")
                            break

        if purpose_text:
            details['purpose'] = purpose_text
            logger.info(f"✓ Purpose extracted: {len(purpose_text)} characters")
        else:
            logger.warning("⚠ Could not find purpose in detail page")

        return details

    async def advanced_search(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Perform advanced search on YÖK using Gelişmiş Tarama form.
        """
        await self.rate_limiter.wait()

        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._advanced_search_sync,
                params
            )
            return results

        except Exception as e:
            logger.error(f"Advanced search failed: {str(e)}", exc_info=True)
            raise YOKThesisScraperError(f"Advanced search error: {str(e)}")

    def _advanced_search_sync(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Synchronous advanced search using Gelişmiş Tarama."""
        driver = self._get_driver()

        try:
            logger.info("Navigating to YÖK search page for advanced search")
            driver.get(self.SEARCH_URL)
            time.sleep(3)

            wait = WebDriverWait(driver, 15)

            # Click Gelişmiş Tarama tab (tabs-2)
            adv_tab = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-2']"))
            )
            adv_tab.click()
            logger.info("Clicked Gelişmiş Tarama tab")
            time.sleep(1)

            # Get tabs-2 container to scope all element searches within it
            tabs2 = driver.find_element(By.ID, "tabs-2")

            # Helper to find element by name within tabs-2
            def find_in_tabs2(name):
                return tabs2.find_element(By.CSS_SELECTOR, f"[name='{name}']")

            # --- Fill keyword rows ---
            # YÖK form field names: keyword (1st), keyword1 (2nd), keyword2 (3rd)
            kw1 = params.get('keyword1', '')
            if kw1:
                el = find_in_tabs2("keyword")
                el.clear()
                el.send_keys(kw1)
                logger.info(f"Entered keyword: {kw1}")

            # Set search field for 1st keyword (nevi)
            sf1 = params.get('searchField1', '')
            if sf1:
                try:
                    Select(find_in_tabs2("nevi")).select_by_value(str(sf1))
                except Exception:
                    pass

            # Set search type for 1st keyword (tip)
            st1 = params.get('searchType1', '')
            if st1:
                try:
                    Select(find_in_tabs2("tip")).select_by_value(str(st1))
                except Exception:
                    pass

            # Operator between 1st and 2nd (ops_field)
            op2 = params.get('operator2', '')
            if op2:
                try:
                    Select(find_in_tabs2("ops_field")).select_by_value(str(op2))
                except Exception:
                    pass

            # 2nd keyword (keyword1 in YÖK form)
            kw2 = params.get('keyword2', '')
            if kw2:
                el = find_in_tabs2("keyword1")
                el.clear()
                el.send_keys(kw2)

            # Search field for 2nd keyword (nevi2)
            sf2 = params.get('searchField2', '')
            if sf2:
                try:
                    Select(find_in_tabs2("nevi2")).select_by_value(str(sf2))
                except Exception:
                    pass

            # Search type for 2nd keyword (tip2)
            st2 = params.get('searchType2', '')
            if st2:
                try:
                    Select(find_in_tabs2("tip2")).select_by_value(str(st2))
                except Exception:
                    pass

            # Operator between 2nd and 3rd (ops_field1)
            op3 = params.get('operator3', '')
            if op3:
                try:
                    Select(find_in_tabs2("ops_field1")).select_by_value(str(op3))
                except Exception:
                    pass

            # 3rd keyword (keyword2 in YÖK form)
            kw3 = params.get('keyword3', '')
            if kw3:
                el = find_in_tabs2("keyword2")
                el.clear()
                el.send_keys(kw3)

            # Search field for 3rd keyword (nevi3)
            sf3 = params.get('searchField3', '')
            if sf3:
                try:
                    Select(find_in_tabs2("nevi3")).select_by_value(str(sf3))
                except Exception:
                    pass

            # Search type for 3rd keyword (tip3)
            st3 = params.get('searchType3', '')
            if st3:
                try:
                    Select(find_in_tabs2("tip3")).select_by_value(str(st3))
                except Exception:
                    pass

            # --- Set filter dropdowns (scoped within tabs-2) ---
            # Year from (yil1)
            year_from = params.get('yearFrom', '')
            if year_from:
                try:
                    Select(find_in_tabs2("yil1")).select_by_value(str(year_from))
                except Exception:
                    pass

            # Year to (yil2)
            year_to = params.get('yearTo', '')
            if year_to:
                try:
                    Select(find_in_tabs2("yil2")).select_by_value(str(year_to))
                except Exception:
                    pass

            # Thesis type (Tur)
            thesis_type = params.get('thesisType', '')
            if thesis_type:
                try:
                    Select(find_in_tabs2("Tur")).select_by_value(str(thesis_type))
                except Exception:
                    pass

            # Permission status (izin)
            perm = params.get('permissionStatus', '')
            if perm:
                try:
                    Select(find_in_tabs2("izin")).select_by_value(str(perm))
                except Exception:
                    pass

            # Group (EnstituGrubu)
            group = params.get('groupType', '')
            if group:
                try:
                    Select(find_in_tabs2("EnstituGrubu")).select_by_value(str(group))
                except Exception:
                    pass

            # Language (Dil)
            lang = params.get('language', '')
            if lang:
                try:
                    Select(find_in_tabs2("Dil")).select_by_value(str(lang))
                except Exception:
                    pass

            # Status (Durum)
            status = params.get('status', '')
            if status:
                try:
                    Select(find_in_tabs2("Durum")).select_by_value(str(status))
                except Exception:
                    pass

            # Submit search
            submit_btn = tabs2.find_element(By.CSS_SELECTOR, "input[type='submit']")
            submit_btn.click()
            logger.info("Submitted advanced search")

            # Wait for results to load (JavaScript populated)
            time.sleep(6)

            # Extract ALL results from JavaScript source
            # YÖK uses WaTable plugin which only displays 30 rows at a time,
            # but all data is embedded in the page source as var doc = {...}; rows.push(doc);
            html = driver.page_source

            # Extract total found count from page text
            import re
            total_found = 0
            total_match = re.search(r'(\d+)\s*kayıt bulundu', html)
            if total_match:
                total_found = int(total_match.group(1))
                logger.info(f"YÖK reports {total_found} total records found")

            results = self._parse_all_results_from_js(html)
            logger.info(f"Parsed {len(results)} total results from JS source")
            return {"results": results, "total_found": total_found}

        except Exception as e:
            logger.error(f"Advanced search error: {str(e)}", exc_info=True)
            return []

    def _parse_all_results_from_js(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse ALL search results from the JavaScript source code.

        YÖK embeds all results in JS as:
            var doc = {
                rowNum: N,
                userId: "<span onclick=tezDetay(...)>THESIS_ID</span>",
                name: "AUTHOR",
                age: "YEAR",
                weight: "TITLE<br><span>TITLE_TR</span>",
                uni: "UNIVERSITY",
                height: "LANGUAGE",
                important: "THESIS_TYPE",
                someDate: "SUBJECT",
            };
            rows.push(doc);

        WaTable only displays 30 rows at a time, but all data is in the source.
        """
        import re

        results = []

        # Extract all var doc = { ... }; blocks
        doc_pattern = re.compile(
            r'var\s+doc\s*=\s*\{(.*?)\};\s*rows\.push\(doc\)',
            re.DOTALL
        )
        doc_blocks = doc_pattern.findall(html)

        if not doc_blocks:
            logger.warning("No doc blocks found in JS source")
            return results

        logger.info(f"Found {len(doc_blocks)} doc blocks in JS source")

        for block in doc_blocks:
            try:
                # Extract thesis_id from span: >THESIS_ID</span>
                thesis_id = ""
                id_match = re.search(r'>(\d+)</span>', block)
                if id_match:
                    thesis_id = id_match.group(1)

                # name = author
                author = ""
                name_match = re.search(r'name\s*:\s*"([^"]*)"', block)
                if name_match:
                    author = name_match.group(1).strip()

                # age = year
                year = ""
                age_match = re.search(r'age\s*:\s*"([^"]*)"', block)
                if age_match:
                    year = age_match.group(1).strip()

                # weight = title (may contain <br><span>title_tr</span>)
                title = ""
                title_tr = ""
                weight_match = re.search(r'weight\s*:\s*"(.*?)",?\s*\n', block, re.DOTALL)
                if weight_match:
                    raw_title = weight_match.group(1).strip()
                    if '<br>' in raw_title:
                        parts = raw_title.split('<br>', 1)
                        title = re.sub(r'<[^>]+>', '', parts[0]).strip()
                        title_tr = re.sub(r'<[^>]+>', '', parts[1]).strip()
                    else:
                        title = re.sub(r'<[^>]+>', '', raw_title).strip()

                # important = thesis_type
                thesis_type = ""
                imp_match = re.search(r'important\s*:\s*"([^"]*)"', block)
                if imp_match:
                    thesis_type = imp_match.group(1).strip()

                # someDate = subject
                subject = ""
                subj_match = re.search(r'someDate\s*:\s*"([^"]*)"', block)
                if subj_match:
                    subject = subj_match.group(1).strip()

                if thesis_id or title:
                    results.append({
                        "thesis_id": thesis_id,
                        "author": author,
                        "year": year,
                        "title": title,
                        "title_tr": title_tr,
                        "thesis_type": thesis_type,
                        "subject": subject
                    })

            except Exception as e:
                logger.debug(f"Error parsing doc block: {e}")
                continue

        return results

    async def get_recent_thesis(
        self,
        days: int = 15,
        limit: int = 50,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Get recently added theses."""
        cache_key = build_cache_key("recent", days, limit)

        if use_cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached recent theses")
                return cached_result

        await self.rate_limiter.wait()

        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._get_recent_thesis_sync,
                days,
                limit
            )

            if use_cache and results:
                await self.cache.set(cache_key, results, ttl=3600)

            return results

        except Exception as e:
            logger.error(f"Failed to get recent theses: {str(e)}")
            raise YOKThesisScraperError(f"Recent thesis error: {str(e)}")

    def _get_recent_thesis_sync(self, days: int, limit: int) -> List[Dict[str, Any]]:
        """Synchronous recent thesis retrieval."""
        driver = self._get_driver()

        try:
            driver.get(self.SEARCH_URL)

            wait = WebDriverWait(driver, 10)

            # Click on "Son Eklenen" tab (recently added)
            try:
                recent_tab = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-3'], #ui-id-3"))
                )
                recent_tab.click()
                logger.info("Clicked recent theses tab")
            except TimeoutException:
                logger.warning("Could not find recent theses tab")

            # Set days filter
            try:
                days_input = driver.find_element(By.NAME, "gun")
                days_input.clear()
                days_input.send_keys(str(days))
            except NoSuchElementException:
                logger.warning("Days input not found")

            # Submit
            try:
                submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                submit_button.click()
            except NoSuchElementException:
                pass

            # Wait for results
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.tablo")))
            except TimeoutException:
                logger.warning("Results not loaded")

            html = driver.page_source
            results = self._parse_search_results(html, limit)

            return results

        except Exception as e:
            logger.error(f"Error getting recent theses: {str(e)}")
            raise

    async def get_statistics(
        self,
        university: Optional[str] = None,
        year: Optional[int] = None,
        thesis_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get thesis statistics."""
        results = await self.search(
            query="*",
            university=university,
            year_start=year,
            year_end=year,
            thesis_type=thesis_type,
            max_results=1000,
            use_cache=True
        )

        stats = {
            "total_count": len(results),
            "by_type": {},
            "by_year": {},
            "by_university": {},
            "by_language": {}
        }

        for thesis in results:
            t_type = thesis.get('thesis_type', 'unknown')
            stats['by_type'][t_type] = stats['by_type'].get(t_type, 0) + 1

            t_year = thesis.get('year')
            if t_year:
                stats['by_year'][t_year] = stats['by_year'].get(t_year, 0) + 1

            t_uni = thesis.get('university', 'unknown')
            stats['by_university'][t_uni] = stats['by_university'].get(t_uni, 0) + 1

            t_lang = thesis.get('language', 'unknown')
            stats['by_language'][t_lang] = stats['by_language'].get(t_lang, 0) + 1

        return stats

    async def close(self) -> None:
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Chrome WebDriver closed")

        await self.cache.clear()
        logger.info("Selenium YÖK Thesis Scraper closed")
