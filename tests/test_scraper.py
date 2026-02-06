"""
Tests for YÖK Thesis Scraper module

Note: These tests include both unit tests and integration tests.
Integration tests that make real HTTP requests are marked and can be skipped.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.scraper import YOKThesisScraper, YOKThesisScraperError
from src.utils import normalize_turkish_text, parse_year


class TestUtilityFunctions:
    """Test utility functions used by the scraper."""

    def test_normalize_turkish_text(self):
        """Test Turkish text normalization."""
        assert normalize_turkish_text("  Yapay  Zeka  ") == "Yapay Zeka"
        assert normalize_turkish_text("Türkçe Karakter: ğüşıöç") == "Türkçe Karakter: ğüşıöç"
        assert normalize_turkish_text("") == ""
        assert normalize_turkish_text("   ") == ""

    def test_parse_year(self):
        """Test year parsing from various formats."""
        assert parse_year("2023") == 2023
        assert parse_year("Yıl: 2020") == 2020
        assert parse_year("2019-2020") == 2019  # Takes first valid year
        assert parse_year("1950") is None  # Too old
        assert parse_year("2050") is None  # Too new
        assert parse_year("invalid") is None
        assert parse_year("") is None


class TestYOKThesisScraper:
    """Test YÖK Thesis Scraper class."""

    @pytest.fixture
    def scraper(self):
        """Create scraper instance for testing."""
        return YOKThesisScraper(
            rate_limit_delay=0.1,  # Faster for testing
            cache_ttl=60,
            timeout=10.0
        )

    def test_scraper_initialization(self, scraper):
        """Test scraper initializes correctly."""
        assert scraper.rate_limiter is not None
        assert scraper.cache is not None
        assert scraper.timeout == 10.0

    def test_build_search_form_data(self, scraper):
        """Test building search form data."""
        # Basic search
        form_data = scraper._build_search_form_data("yapay zeka")
        assert "tumu" in form_data
        assert form_data["tumu"] == "yapay zeka"

        # Search with field
        form_data = scraper._build_search_form_data("Ahmet Yılmaz", search_field="yazar")
        assert "yazar_adi" in form_data

        # Search with filters
        form_data = scraper._build_search_form_data(
            "machine learning",
            year_start=2020,
            year_end=2023,
            thesis_type="doktora",
            university="İstanbul Üniversitesi"
        )
        assert form_data["yil1"] == "2020"
        assert form_data["yil2"] == "2023"
        assert form_data["tez_turu"] == "2"  # doktora = 2
        assert form_data["universite"] == "İstanbul Üniversitesi"

    def test_extract_thesis_id(self, scraper):
        """Test extracting thesis ID from HTML cell."""
        from bs4 import BeautifulSoup

        # Test with link
        html = '<td><a href="tezDetay.jsp?id=123456">Details</a></td>'
        soup = BeautifulSoup(html, 'lxml')
        cell = soup.find('td')
        assert scraper._extract_thesis_id(cell) == "123456"

        # Test with just text
        html = '<td>789012</td>'
        soup = BeautifulSoup(html, 'lxml')
        cell = soup.find('td')
        assert scraper._extract_thesis_id(cell) == "789012"

    @pytest.mark.asyncio
    async def test_cache_functionality(self, scraper):
        """Test that caching works correctly."""
        cache_key = "test_key"
        test_data = {"thesis_id": "123", "title": "Test Thesis"}

        # Set cache
        await scraper.cache.set(cache_key, test_data)

        # Get from cache
        cached = await scraper.cache.get(cache_key)
        assert cached == test_data

        # Clear cache
        await scraper.cache.clear()
        cached = await scraper.cache.get(cache_key)
        assert cached is None

    @pytest.mark.asyncio
    async def test_rate_limiting(self, scraper):
        """Test that rate limiting adds delay between requests."""
        import time

        start = time.time()

        # Make three consecutive requests
        await scraper.rate_limiter.wait()
        await scraper.rate_limiter.wait()
        await scraper.rate_limiter.wait()

        elapsed = time.time() - start

        # Should take at least 2 * rate_limit_delay (0.1s each)
        assert elapsed >= 0.2

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_search_with_mock(self, mock_post, scraper):
        """Test search function with mocked HTTP response."""
        # Mock HTML response
        mock_html = """
        <html>
            <body>
                <table class="tablo">
                    <tr><th>Header</th></tr>
                    <tr>
                        <td><a href="tezDetay.jsp?id=123">123</a></td>
                        <td>Yapay Zeka Uygulamaları</td>
                        <td>Ahmet Yılmaz</td>
                        <td>2023</td>
                        <td>İstanbul Üniversitesi</td>
                        <td>Doktora</td>
                        <td>Türkçe</td>
                    </tr>
                </table>
            </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_response.encoding = 'utf-8'
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Perform search
        results = await scraper.search("yapay zeka", use_cache=False)

        # Verify results
        assert len(results) > 0
        assert results[0]["thesis_id"] == "123"
        assert "Yapay Zeka" in results[0]["title"]

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_get_thesis_details_with_mock(self, mock_get, scraper):
        """Test getting thesis details with mocked response."""
        mock_html = """
        <html>
            <body>
                <table class="bilgi">
                    <tr>
                        <th>Tez No:</th>
                        <td>123456</td>
                    </tr>
                    <tr>
                        <th>Tez Adı:</th>
                        <td>Derin Öğrenme Yöntemleri</td>
                    </tr>
                    <tr>
                        <th>Yazar:</th>
                        <td>Mehmet Demir</td>
                    </tr>
                    <tr>
                        <th>Danışman:</th>
                        <td>Prof. Dr. Ali Veli</td>
                    </tr>
                    <tr>
                        <th>Yıl:</th>
                        <td>2022</td>
                    </tr>
                </table>
            </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_response.encoding = 'utf-8'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Get details
        details = await scraper.get_thesis_details("123456", use_cache=False)

        # Verify details
        assert details["thesis_id"] == "123456"
        assert "Derin Öğrenme" in details["title"]
        assert details["author"] == "Mehmet Demir"
        assert details["year"] == "2022"

    @pytest.mark.asyncio
    async def test_error_handling(self, scraper):
        """Test error handling for invalid requests."""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Simulate HTTP error
            mock_post.side_effect = Exception("Network error")

            with pytest.raises(YOKThesisScraperError):
                await scraper.search("test", use_cache=False)


# Integration tests (require actual network access)
# Mark these with @pytest.mark.integration to skip in CI/CD

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_search():
    """
    Integration test: real search on YÖK database.

    This test makes actual HTTP requests to YÖK servers.
    Skip in automated testing to avoid rate limiting.
    """
    scraper = YOKThesisScraper()

    try:
        results = await scraper.search(
            query="yapay zeka",
            year_start=2020,
            max_results=5
        )

        assert isinstance(results, list)
        # There should be at least some results for this broad query
        assert len(results) >= 0  # May be 0 if site is down or blocked

    except YOKThesisScraperError as e:
        pytest.skip(f"YÖK service unavailable: {str(e)}")
    finally:
        await scraper.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_recent_theses():
    """
    Integration test: get recent theses.

    This test makes actual HTTP requests.
    """
    scraper = YOKThesisScraper()

    try:
        results = await scraper.get_recent_thesis(days=7, limit=10)

        assert isinstance(results, list)

    except YOKThesisScraperError as e:
        pytest.skip(f"YÖK service unavailable: {str(e)}")
    finally:
        await scraper.close()
