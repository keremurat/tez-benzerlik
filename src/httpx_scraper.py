"""
httpx-based web scraper for YÖK National Thesis Center
Simplified version for Vercel serverless deployment (no Selenium)

⚠️ LIMITATIONS:
- No JavaScript rendering (some features may not work)
- No anti-bot bypass (may get blocked on heavy usage)
- Simplified parsing (modal content not accessible)
- Best effort approach for serverless environment
"""

import logging
import asyncio
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
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


class HttpxYOKScraper:
    """
    httpx-based scraper for YÖK National Thesis Center.
    Simplified version without Selenium for Vercel deployment.
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
        rate_limit_delay: float = 2.0,
        cache_ttl: int = 3600,
        timeout: float = 30.0
    ):
        """
        Initialize httpx-based YÖK scraper.

        Args:
            rate_limit_delay: Minimum delay between requests in seconds
            cache_ttl: Cache time-to-live in seconds
            timeout: Request timeout in seconds
        """
        self.rate_limiter = RateLimiter(min_delay=rate_limit_delay)
        self.cache = SimpleCache(default_ttl=cache_ttl)
        self.timeout = timeout

        # HTTP headers to mimic browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://tez.yok.gov.tr/UlusalTezMerkezi/tarama.jsp'
        }

        # Persistent client with cookie jar for session management
        self._client = None

        logger.info("httpx YÖK Thesis Scraper initialized")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create a persistent HTTP client with cookies."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self.headers
            )
            # Visit the search page first to get session cookies
            logger.info("Initializing session - visiting search page...")
            try:
                await self._client.get(self.SEARCH_URL)
                logger.info("Session initialized with cookies")
            except Exception as e:
                logger.warning(f"Session init failed: {e}")
        return self._client

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
        Search for theses using httpx.

        ⚠️ Note: This is a simplified version. JavaScript-dependent features
        (like advanced filtering) may not work properly.

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
            # Build form data based on search type
            form_data = self._build_search_form_data(
                query, search_field, year_start, year_end,
                thesis_type, university, language, permission_status
            )

            # Use persistent client with session cookies
            client = await self._get_client()

            logger.info(f"Searching YÖK for: {query}")
            response = await client.post(
                self.SEARCH_URL,
                data=form_data
            )
            response.raise_for_status()

            # Parse results
            results = self._parse_search_results(response.text, max_results)

            # Cache results
            if use_cache and results:
                await self.cache.set(cache_key, results)

            logger.info(f"Found {len(results)} theses for query: {query}")
            return results

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during search: {str(e)}")
            raise YOKThesisScraperError(f"Search request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise YOKThesisScraperError(f"Search error: {str(e)}")

    def _build_search_form_data(
        self,
        query: str,
        search_field: str,
        year_start: Optional[int],
        year_end: Optional[int],
        thesis_type: Optional[str],
        university: Optional[str],
        language: Optional[str],
        permission_status: Optional[str]
    ) -> Dict[str, str]:
        """Build form data for search request."""

        # Map search_field to actual form field names
        field_mapping = {
            "tez_adi": "TezAd",
            "yazar": "AdSoyad",
            "danisman": "DanismanAdSoyad",
            "konu": "Dizin",
            "tumu": "keyword"  # Advanced search uses keyword field
        }

        form_data = {
            "-find": "Bul",
            "submitted": "1"
        }

        # Add search query to appropriate field
        input_field = field_mapping.get(search_field, "keyword")
        form_data[input_field] = query

        # Add filters
        if year_start:
            form_data["yil1"] = str(year_start)
        if year_end:
            form_data["yil2"] = str(year_end)
        if thesis_type and thesis_type in self.THESIS_TYPES:
            form_data["Tur"] = self.THESIS_TYPES[thesis_type]
        if university:
            form_data["uniad"] = university
        if language:
            form_data["Dil"] = language
        if permission_status and permission_status in self.PERMISSION_STATUS:
            form_data["izin"] = self.PERMISSION_STATUS[permission_status]

        return form_data

    def _parse_search_results(self, html: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Parse search results from HTML.

        YÖK results table structure:
        - Table class: 'watable' or 'table-striped'
        - Columns: [No, Tez No, Yazar, Yıl, Tez Adı, Tez Türü, ...]
        """
        soup = BeautifulSoup(html, 'lxml')
        results = []

        # Find the results table
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

                # Extract thesis ID from onclick or text
                thesis_id = None
                if cells[1].find('span'):
                    onclick = cells[1].find('span').get('onclick', '')
                    if 'tezDetay' in onclick:
                        # Extract ID from onclick="tezDetay('123456')"
                        id_match = re.search(r"tezDetay\('(\d+)'\)", onclick)
                        if id_match:
                            thesis_id = id_match.group(1)

                if not thesis_id:
                    thesis_id = normalize_turkish_text(cells[1].get_text())

                # Extract thesis information
                thesis_data = {
                    "thesis_id": thesis_id,
                    "author": normalize_turkish_text(cells[2].get_text()) if len(cells) > 2 else "",
                    "year": parse_year(cells[3].get_text()) if len(cells) > 3 else None,
                    "title": normalize_turkish_text(cells[4].get_text()) if len(cells) > 4 else "",
                    "thesis_type": cells[5].get_text().strip() if len(cells) > 5 else None,
                    "university": "",  # Not available in search results
                    "language": None,  # Not available in search results
                }

                results.append(thesis_data)

            except Exception as e:
                logger.warning(f"Failed to parse row: {str(e)}")
                continue

        logger.info(f"Successfully parsed {len(results)} thesis results")
        return results

    async def get_thesis_details(
        self,
        thesis_id: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed thesis information.

        ⚠️ WARNING: YÖK detail pages often require JavaScript/modal interaction.
        This simplified version attempts direct URL access but may have limited data.

        Args:
            thesis_id: Thesis ID number
            use_cache: Whether to use cache

        Returns:
            Dictionary with thesis details
        """
        cache_key = build_cache_key("detail", thesis_id)

        if use_cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached thesis details for: {thesis_id}")
                return cached_result

        await self.rate_limiter.wait()

        try:
            # Use persistent client with session cookies
            client = await self._get_client()
            detail_url = f"{self.DETAIL_URL}?id={thesis_id}"

            logger.info(f"Fetching details for thesis: {thesis_id}")
            response = await client.get(detail_url)

            # YÖK may return errors or redirect for restricted theses
            if response.status_code == 200:
                details = self._parse_thesis_detail(response.text, thesis_id)
            else:
                logger.warning(f"Detail page returned status {response.status_code}")
                details = self._create_minimal_response(thesis_id)

            if use_cache:
                await self.cache.set(cache_key, details)

            return details

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching details: {str(e)}")
            return self._create_minimal_response(thesis_id, error=str(e))
        except Exception as e:
            logger.error(f"Failed to get thesis details: {str(e)}")
            return self._create_minimal_response(thesis_id, error=str(e))

    def _create_minimal_response(
        self,
        thesis_id: str,
        title: str = None,
        author: str = None,
        error: str = None
    ) -> Dict[str, Any]:
        """Create a minimal thesis response when full details are unavailable."""
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
            "abstract": None if not error else f"⚠️ {error}",
            "purpose": None
        }

    def _parse_thesis_detail(self, html: str, thesis_id: str) -> Dict[str, Any]:
        """
        Parse detailed thesis information from HTML.

        ⚠️ Note: Without JavaScript rendering, some content may be missing.
        """
        soup = BeautifulSoup(html, 'lxml')

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

        # Try to find detail table
        detail_table = (
            soup.find('table', {'class': 'bilgi'}) or
            soup.find('div', {'class': 'thesis-detail'}) or
            soup.find('table', class_=lambda x: x and 'tablo' in x if x else False) or
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

                        # Map Turkish keys to English field names
                        key_mapping = {
                            'Tez No': 'thesis_id',
                            'Tez Adı': 'title',
                            'Yazar': 'author',
                            'Danışman': 'advisor',
                            'Yıl': 'year',
                            'Üniversite': 'university',
                            'Enstitü': 'institute',
                            'Anabilim Dalı': 'department',
                            'Tez Türü': 'thesis_type',
                            'Dil': 'language',
                            'Sayfa Sayısı': 'page_count',
                            'Anahtar Kelimeler': 'keywords',
                        }

                        english_key = key_mapping.get(key)
                        if english_key and english_key in details:
                            details[english_key] = value

                except Exception as e:
                    logger.warning(f"Failed to parse detail row: {str(e)}")
                    continue

        # Try to extract abstract
        abstract_text = self._extract_abstract(soup)
        if abstract_text:
            details['abstract'] = abstract_text

        # Try to extract purpose
        purpose_text = self._extract_purpose(soup)
        if purpose_text:
            details['purpose'] = purpose_text

        return details

    def _extract_abstract(self, soup: BeautifulSoup) -> Optional[str]:
        """Attempt to extract abstract from HTML."""

        # Method 1: Look for common abstract containers
        for selector in [
            {'class': 'ozet'},
            {'class': 'abstract'},
            {'id': 'ozet'},
            {'id': 'abstract'}
        ]:
            elem = soup.find(['div', 'p', 'section'], selector)
            if elem:
                text = elem.get_text().strip()
                if len(text) > 100:
                    return normalize_turkish_text(text)

        # Method 2: Look for table rows with "Özet" label
        all_rows = soup.find_all('tr')
        for row in all_rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text().strip().lower()
                if 'özet' in label or 'abstract' in label:
                    text = cells[1].get_text().strip()
                    if len(text) > 100:
                        return normalize_turkish_text(text)

        # Method 3: Regex search
        all_text = soup.get_text()
        patterns = [
            r'(?:Türkçe\s+)?Özet\s*:?\s*(.+?)(?=\n\s*(?:İngilizce|Abstract|Amaç|$))',
            r'(?:Turkish\s+)?Abstract\s*:?\s*(.+?)(?=\n\s*(?:English|Özet|Purpose|$))',
        ]

        for pattern in patterns:
            match = re.search(pattern, all_text, re.IGNORECASE | re.DOTALL)
            if match:
                text = match.group(1).strip()
                text = re.sub(r'\s+', ' ', text)
                if len(text) > 100:
                    return normalize_turkish_text(text)

        return None

    def _extract_purpose(self, soup: BeautifulSoup) -> Optional[str]:
        """Attempt to extract purpose/aim from HTML."""

        # Method 1: Look for table rows with "Amaç" label
        all_rows = soup.find_all('tr')
        for row in all_rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text().strip().lower()
                if 'amaç' in label or 'purpose' in label or 'objective' in label:
                    text = cells[1].get_text().strip()
                    if len(text) > 30:
                        return normalize_turkish_text(text)

        # Method 2: Regex search
        all_text = soup.get_text()
        patterns = [
            r'(?:Çalışmanın\s+)?Amaç[ıi]?\s*:\s*(.+?)(?=\n\s*(?:Yöntem|Gereç|Method|$))',
            r'Purpose\s*:\s*(.+?)(?=\n\s*(?:Method|Material|$))',
        ]

        for pattern in patterns:
            match = re.search(pattern, all_text, re.IGNORECASE | re.DOTALL)
            if match:
                text = match.group(1).strip()
                text = re.sub(r'\s+', ' ', text)[:500]
                if len(text) > 30:
                    return normalize_turkish_text(text)

        return None

    async def advanced_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform advanced search.

        ⚠️ WARNING: Advanced search heavily relies on JavaScript.
        This implementation may have limited functionality.
        """
        logger.warning("Advanced search has limited support without JavaScript")

        # Try to construct a basic search from advanced params
        keyword1 = params.get('keyword1', '')
        if keyword1:
            # Fall back to basic search
            results = await self.search(
                query=keyword1,
                search_field="tumu",
                year_start=int(params.get('yearFrom', 0)) if params.get('yearFrom') else None,
                year_end=int(params.get('yearTo', 0)) if params.get('yearTo') else None,
                thesis_type=params.get('thesisType'),
                language=params.get('language'),
                max_results=100
            )

            return {
                "results": results,
                "total_found": len(results),
                "note": "⚠️ Simplified search - advanced operators not fully supported"
            }

        return {"results": [], "total_found": 0}

    async def get_recent_thesis(
        self,
        days: int = 15,
        limit: int = 50,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recently added theses.

        ⚠️ Note: This feature requires JavaScript. Returning empty for now.
        """
        logger.warning("get_recent_thesis has limited support without JavaScript")

        cache_key = build_cache_key("recent", days, limit)

        if use_cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        # This would require JavaScript to interact with "Son Eklenen" tab
        # For now, return empty list with note
        return []

    async def get_statistics(
        self,
        university: Optional[str] = None,
        year: Optional[int] = None,
        thesis_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get thesis statistics (simplified version)."""

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
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        await self.cache.clear()
        logger.info("httpx YÖK Thesis Scraper closed")
