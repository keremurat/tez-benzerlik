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
            "abstract": None
        }

    def _get_thesis_details_sync(self, thesis_id: str) -> Dict[str, Any]:
        """
        Synchronous thesis detail retrieval using modal approach.

        YÖK workflow:
        1. Search with a broad query to find results
        2. Find the thesis ID in results
        3. Click on it to open modal dialog
        4. Parse modal content
        """
        driver = self._get_driver()

        try:
            logger.info(f"Searching for thesis ID: {thesis_id} using TezNo field")

            # Navigate to search page
            driver.get(self.SEARCH_URL)
            time.sleep(2)

            wait = WebDriverWait(driver, 15)

            # Click detailed search tab (tabs-1) which has TezNo field
            detailed_tab = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tabs-1']"))
            )
            detailed_tab.click()
            logger.info("✓ Clicked detailed search tab")
            time.sleep(1)

            # Enter thesis ID in the TezNo field
            try:
                tez_no_input = driver.find_element(By.NAME, "TezNo")
                tez_no_input.clear()
                tez_no_input.send_keys(thesis_id)
                logger.info(f"✓ Entered thesis ID {thesis_id} in TezNo field")
                time.sleep(0.5)
            except:
                logger.warning("TezNo field not found")
                return self._create_complete_thesis_response(thesis_id)

            # Submit search
            tabs1_div = driver.find_element(By.ID, "tabs-1")
            submit_button = tabs1_div.find_element(By.CSS_SELECTOR, "input[type='submit']")
            submit_button.click()
            logger.info("✓ Submitted thesis ID search")

            # Wait for results
            time.sleep(5)

            # Find thesis in results
            try:
                thesis_span = wait.until(
                    EC.presence_of_element_located((By.XPATH, f"//span[@onclick and contains(text(), '{thesis_id}')]"))
                )
                logger.info(f"✓ Found thesis {thesis_id} in search results")
            except TimeoutException:
                logger.warning(f"Thesis {thesis_id} not found in search results")
                return self._create_complete_thesis_response(thesis_id)

            # Step 3: Click to open modal
            logger.info("Clicking thesis to open modal")
            driver.execute_script("arguments[0].click();", thesis_span)
            time.sleep(3)

            # Step 4: Wait for modal and parse content
            try:
                modal = wait.until(
                    EC.presence_of_element_located((By.ID, "dialog-modal"))
                )
                logger.info("Modal dialog appeared")

                modal_html = modal.get_attribute('innerHTML')
                details = self._parse_modal_content(modal_html, thesis_id)

                logger.info(f"Successfully retrieved details for thesis {thesis_id}")
                return details

            except TimeoutException:
                logger.warning("Modal dialog did not appear")
                return self._create_complete_thesis_response(thesis_id)

        except Exception as e:
            logger.error(f"Error fetching thesis details: {str(e)}", exc_info=True)
            # Return complete minimal data instead of failing
            return self._create_complete_thesis_response(
                thesis_id=thesis_id,
                title=f"Tez #{thesis_id}",
                author="Bilgi alınamadı"
            )

    def _parse_modal_content(self, html: str, thesis_id: str) -> Dict[str, Any]:
        """Parse thesis details from modal dialog content."""
        soup = BeautifulSoup(html, 'lxml')

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
            "abstract": None
        }

        try:
            # Find the main content cell (3rd td in row)
            content_td = soup.find('td', valign='top', string=lambda t: 'Yazar' in str(t) if t else False)
            if not content_td:
                # Try finding by structure
                rows = soup.find_all('tr', class_='renkp')
                if rows:
                    cells = rows[0].find_all('td')
                    if len(cells) >= 3:
                        content_td = cells[2]

            if content_td:
                text = content_td.get_text()

                # Extract title (first line)
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if lines:
                    details['title'] = lines[0].split(' / ')[0].strip()  # English title

                # Extract author
                for line in lines:
                    if 'Yazar:' in line:
                        details['author'] = line.replace('Yazar:', '').strip()
                    elif 'Danışman:' in line or 'Danışman :' in line:
                        advisor = line.replace('Danışman:', '').replace('Danışman :', '').strip()
                        details['advisor'] = advisor
                    elif 'Yer Bilgisi:' in line:
                        # Parse university/institute/department
                        parts = line.replace('Yer Bilgisi:', '').split('/')
                        if len(parts) >= 1:
                            details['university'] = parts[0].strip()
                        if len(parts) >= 2:
                            details['institute'] = parts[1].strip()
                        if len(parts) >= 3:
                            details['department'] = parts[2].strip()
                    elif 'Dizin:' in line:
                        details['keywords'] = line.replace('Dizin:', '').strip()

            # Find status cell (4th td)
            status_cells = soup.find_all('td', valign='top')
            if len(status_cells) >= 4:
                status_td = status_cells[3]
                status_text = status_td.get_text()
                status_lines = [l.strip() for l in status_text.split('\n') if l.strip()]

                for line in status_lines:
                    if 'Doktora' in line or 'Yüksek Lisans' in line or 'Tıpta Uzmanlık' in line:
                        details['thesis_type'] = line.strip()
                    elif 'İngilizce' in line or 'Türkçe' in line:
                        details['language'] = line.strip()
                    elif line.isdigit() and len(line) == 4:  # Year
                        details['year'] = line
                    elif 's.' in line:  # Page count
                        details['page_count'] = line.strip()

        except Exception as e:
            logger.error(f"Error parsing modal content: {str(e)}")

        return details

    def _parse_thesis_detail(self, html: str, thesis_id: str) -> Dict[str, Any]:
        """Parse detailed thesis information."""
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
            "abstract": None
        }

        detail_table = soup.find('table', {'class': 'bilgi'}) or soup.find('div', {'class': 'thesis-detail'})

        if not detail_table:
            logger.warning("No detail table found")
            return details

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

        # Extract abstract
        abstract_div = soup.find('div', {'class': 'ozet'}) or soup.find('div', {'id': 'abstract'})
        if abstract_div:
            details['abstract'] = normalize_turkish_text(abstract_div.get_text())

        return details

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
