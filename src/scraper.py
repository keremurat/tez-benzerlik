"""
Web scraper for YÖK National Thesis Center (Ulusal Tez Merkezi)

Handles HTTP requests, form submissions, and HTML parsing for thesis search
and retrieval from https://tez.yok.gov.tr/UlusalTezMerkezi/
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup

from .utils import (
    RateLimiter,
    SimpleCache,
    normalize_turkish_text,
    parse_year,
    build_cache_key,
    retry_async,
    RetryConfig
)

logger = logging.getLogger(__name__)


class YOKThesisScraperError(Exception):
    """Base exception for YÖK scraper errors."""
    pass


class YOKThesisScraper:
    """
    Scraper for YÖK National Thesis Center.

    Provides methods to search theses, get details, and retrieve recent additions.
    Includes rate limiting, caching, and error handling.
    """

    # YÖK Tez Merkezi URLs
    BASE_URL = "https://tez.yok.gov.tr"
    SEARCH_URL = f"{BASE_URL}/UlusalTezMerkezi/tarama.jsp"
    DETAIL_URL = f"{BASE_URL}/UlusalTezMerkezi/tezDetay.jsp"

    # Form parameters mapping
    SEARCH_TYPES = {
        "detayli": "tabs-1",  # Detailed search
        "gelismis": "tabs-2",  # Advanced search
        "son_eklenen": "tabs-3",  # Recently added
        "hazirlanan": "tabs-4"  # In preparation
    }

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
        rate_limit_delay: float = 1.5,
        cache_ttl: int = 3600,
        timeout: float = 30.0
    ):
        """
        Initialize YÖK thesis scraper.

        Args:
            rate_limit_delay: Minimum delay between requests in seconds
            cache_ttl: Cache time-to-live in seconds
            timeout: HTTP request timeout in seconds
        """
        self.rate_limiter = RateLimiter(min_delay=rate_limit_delay)
        self.cache = SimpleCache(default_ttl=cache_ttl)
        self.timeout = timeout

        # HTTP client configuration
        self.client_config = {
            "timeout": httpx.Timeout(timeout),
            "follow_redirects": True,
            "headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://tez.yok.gov.tr/UlusalTezMerkezi/",
                "Origin": "https://tez.yok.gov.tr",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
            }
        }

        logger.info("YÖK Thesis Scraper initialized")

    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Make HTTP request with rate limiting and retry logic.

        Args:
            method: HTTP method (GET or POST)
            url: Request URL
            data: Form data for POST requests
            params: Query parameters for GET requests

        Returns:
            Response HTML content

        Raises:
            YOKThesisScraperError: If request fails after retries
        """
        async def _request() -> str:
            async with httpx.AsyncClient(**self.client_config) as client:
                if method.upper() == "POST":
                    response = await client.post(url, data=data)
                else:
                    response = await client.get(url, params=params)

                response.raise_for_status()

                # Ensure UTF-8 encoding for Turkish characters
                response.encoding = 'utf-8'
                return response.text

        try:
            await self.rate_limiter.wait()
            html = await retry_async(_request, RetryConfig(max_attempts=3))
            logger.debug(f"Request successful: {method} {url}")
            return html

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {url}")
            raise YOKThesisScraperError(f"HTTP {e.response.status_code}: {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {url} - {str(e)}")
            raise YOKThesisScraperError(f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {url} - {str(e)}")
            raise YOKThesisScraperError(f"Unexpected error: {str(e)}")

    def _build_search_form_data(
        self,
        query: str,
        search_field: str = "tumu",
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        thesis_type: Optional[str] = None,
        university: Optional[str] = None,
        language: Optional[str] = None,
        permission_status: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Build form data for thesis search.

        Args:
            query: Search query
            search_field: Field to search in (tez_adi, yazar, danisman, konu, tumu)
            year_start: Start year
            year_end: End year
            thesis_type: Thesis type
            university: University name
            language: Thesis language
            permission_status: Permission status

        Returns:
            Form data dictionary
        """
        form_data = {
            "searchtype": "detayli",  # Default to detailed search
            "submit": "Ara",  # Submit button value
        }

        # Map search field to form parameter
        field_mapping = {
            "tez_adi": "tez_adi",
            "yazar": "yazar_adi",
            "danisman": "danisman",
            "konu": "konu",
            "tumu": "tumu"  # Search in all fields
        }

        if search_field in field_mapping:
            form_data[field_mapping[search_field]] = query
        else:
            form_data["tumu"] = query

        # Add optional filters
        if year_start:
            form_data["yil1"] = str(year_start)
        if year_end:
            form_data["yil2"] = str(year_end)

        if thesis_type and thesis_type in self.THESIS_TYPES:
            form_data["tez_turu"] = self.THESIS_TYPES[thesis_type]

        if university:
            form_data["universite"] = university

        if language:
            form_data["dil"] = language.lower()

        if permission_status and permission_status in self.PERMISSION_STATUS:
            form_data["izin_durumu"] = self.PERMISSION_STATUS[permission_status]

        return form_data

    def _parse_search_results(self, html: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Parse search results from HTML response.

        Args:
            html: HTML content
            max_results: Maximum number of results to return

        Returns:
            List of thesis dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        results = []

        # Find the results table
        # Note: Actual selectors need to be adjusted based on real YÖK HTML structure
        table = soup.find('table', {'class': 'tablo'}) or soup.find('table', {'id': 'resulttable'})

        if not table:
            logger.warning("No results table found in HTML")
            return results

        rows = table.find_all('tr')[1:]  # Skip header row

        for row in rows[:max_results]:
            try:
                cells = row.find_all('td')
                if len(cells) < 5:
                    continue

                # Extract thesis information
                # Adjust indices based on actual table structure
                thesis_data = {
                    "thesis_id": self._extract_thesis_id(cells[0]),
                    "title": normalize_turkish_text(cells[1].get_text()),
                    "author": normalize_turkish_text(cells[2].get_text()),
                    "year": parse_year(cells[3].get_text()),
                    "university": normalize_turkish_text(cells[4].get_text()),
                    "thesis_type": cells[5].get_text().strip() if len(cells) > 5 else None,
                    "language": cells[6].get_text().strip() if len(cells) > 6 else None,
                }

                results.append(thesis_data)

            except (IndexError, AttributeError) as e:
                logger.warning(f"Failed to parse row: {str(e)}")
                continue

        logger.info(f"Parsed {len(results)} thesis results")
        return results

    def _extract_thesis_id(self, cell) -> Optional[str]:
        """
        Extract thesis ID from table cell.

        Args:
            cell: BeautifulSoup cell element

        Returns:
            Thesis ID or None
        """
        # Look for link with thesis ID
        link = cell.find('a')
        if link and 'href' in link.attrs:
            href = link['href']
            # Extract ID from URL (e.g., tezDetay.jsp?id=123456)
            if 'id=' in href:
                return href.split('id=')[-1].split('&')[0]

        # Fallback: try to get text content
        text = cell.get_text().strip()
        if text.isdigit():
            return text

        return None

    def _parse_thesis_detail(self, html: str) -> Dict[str, Any]:
        """
        Parse detailed thesis information from detail page.

        Args:
            html: HTML content of detail page

        Returns:
            Thesis detail dictionary
        """
        soup = BeautifulSoup(html, 'lxml')
        details = {}

        # Find detail table or div
        # Adjust selectors based on actual YÖK structure
        detail_table = soup.find('table', {'class': 'bilgi'}) or soup.find('div', {'class': 'thesis-detail'})

        if not detail_table:
            logger.warning("No detail table found")
            return details

        # Extract key-value pairs
        rows = detail_table.find_all('tr')
        for row in rows:
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = normalize_turkish_text(cells[0].get_text()).rstrip(':')
                    value = normalize_turkish_text(cells[1].get_text())

                    # Map Turkish keys to English
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
                        'Özet': 'abstract',
                        'Anahtar Kelimeler': 'keywords',
                    }

                    english_key = key_mapping.get(key, key.lower().replace(' ', '_'))
                    details[english_key] = value

            except (IndexError, AttributeError) as e:
                logger.warning(f"Failed to parse detail row: {str(e)}")
                continue

        # Special handling for abstract (might be in a separate section)
        abstract_div = soup.find('div', {'class': 'ozet'}) or soup.find('div', {'id': 'abstract'})
        if abstract_div:
            details['abstract'] = normalize_turkish_text(abstract_div.get_text())

        logger.info(f"Parsed thesis details: {details.get('thesis_id', 'unknown')}")
        return details

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
        Search for theses in YÖK database.

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

        Raises:
            YOKThesisScraperError: If search fails
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

        # Build form data
        form_data = self._build_search_form_data(
            query=query,
            search_field=search_field,
            year_start=year_start,
            year_end=year_end,
            thesis_type=thesis_type,
            university=university,
            language=language,
            permission_status=permission_status
        )

        logger.info(f"Searching YÖK for: {query} (field: {search_field})")

        # Make request
        html = await self._make_request("POST", self.SEARCH_URL, data=form_data)

        # Parse results
        results = self._parse_search_results(html, max_results=max_results)

        # Cache results
        if use_cache and results:
            await self.cache.set(cache_key, results)

        return results

    async def get_thesis_details(
        self,
        thesis_id: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific thesis.

        Args:
            thesis_id: Thesis ID number
            use_cache: Whether to use cache

        Returns:
            Thesis detail dictionary

        Raises:
            YOKThesisScraperError: If retrieval fails
        """
        # Build cache key
        cache_key = build_cache_key("detail", thesis_id)

        # Check cache
        if use_cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached thesis details for: {thesis_id}")
                return cached_result

        logger.info(f"Fetching thesis details for ID: {thesis_id}")

        # Make request
        params = {"id": thesis_id}
        html = await self._make_request("GET", self.DETAIL_URL, params=params)

        # Parse details
        details = self._parse_thesis_detail(html)

        if not details:
            raise YOKThesisScraperError(f"No details found for thesis ID: {thesis_id}")

        # Cache result
        if use_cache:
            await self.cache.set(cache_key, details)

        return details

    async def get_recent_thesis(
        self,
        days: int = 15,
        limit: int = 50,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recently added theses.

        Args:
            days: Number of days to look back
            limit: Maximum number of results
            use_cache: Whether to use cache

        Returns:
            List of recent thesis dictionaries

        Raises:
            YOKThesisScraperError: If retrieval fails
        """
        # Build cache key
        cache_key = build_cache_key("recent", days, limit)

        # Check cache (shorter TTL for recent theses)
        if use_cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached recent theses (last {days} days)")
                return cached_result

        logger.info(f"Fetching recent theses (last {days} days)")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Build form data for recent theses
        form_data = {
            "searchtype": "son_eklenen",
            "gun": str(days),
            "submit": "Ara"
        }

        # Make request
        html = await self._make_request("POST", self.SEARCH_URL, data=form_data)

        # Parse results
        results = self._parse_search_results(html, max_results=limit)

        # Cache with shorter TTL (1 hour for recent theses)
        if use_cache and results:
            await self.cache.set(cache_key, results, ttl=3600)

        return results

    async def get_statistics(
        self,
        university: Optional[str] = None,
        year: Optional[int] = None,
        thesis_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get thesis statistics based on filters.

        Note: This is a derived statistic from search results,
        not a dedicated YÖK API endpoint.

        Args:
            university: University filter
            year: Year filter
            thesis_type: Thesis type filter

        Returns:
            Statistics dictionary with counts and breakdowns
        """
        logger.info(f"Calculating statistics (university={university}, year={year}, type={thesis_type})")

        # Perform a broad search with filters
        results = await self.search(
            query="*",  # Wildcard search
            university=university,
            year_start=year,
            year_end=year,
            thesis_type=thesis_type,
            max_results=1000,  # Get more results for statistics
            use_cache=True
        )

        # Calculate statistics
        stats = {
            "total_count": len(results),
            "by_type": {},
            "by_year": {},
            "by_university": {},
            "by_language": {}
        }

        for thesis in results:
            # Count by type
            t_type = thesis.get('thesis_type', 'unknown')
            stats['by_type'][t_type] = stats['by_type'].get(t_type, 0) + 1

            # Count by year
            t_year = thesis.get('year')
            if t_year:
                stats['by_year'][t_year] = stats['by_year'].get(t_year, 0) + 1

            # Count by university
            t_uni = thesis.get('university', 'unknown')
            stats['by_university'][t_uni] = stats['by_university'].get(t_uni, 0) + 1

            # Count by language
            t_lang = thesis.get('language', 'unknown')
            stats['by_language'][t_lang] = stats['by_language'].get(t_lang, 0) + 1

        logger.info(f"Statistics calculated: {stats['total_count']} theses analyzed")
        return stats

    async def close(self) -> None:
        """Clean up resources."""
        await self.cache.clear()
        logger.info("YÖK Thesis Scraper closed")
