"""
Tests for MCP Server module

Tests the MCP server tools and handlers.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.server import (
    handle_search_thesis,
    handle_get_thesis_details,
    handle_get_recent_thesis,
    handle_get_thesis_statistics
)


class TestSearchThesisTool:
    """Test search_thesis tool handler."""

    @pytest.mark.asyncio
    @patch('src.server.scraper')
    async def test_search_thesis_success(self, mock_scraper):
        """Test successful thesis search."""
        # Mock search results
        mock_results = [
            {
                "thesis_id": "123",
                "title": "Yapay Zeka Uygulamaları",
                "author": "Ahmet Yılmaz",
                "year": 2023,
                "university": "İstanbul Üniversitesi",
                "thesis_type": "Doktora"
            },
            {
                "thesis_id": "456",
                "title": "Makine Öğrenmesi Algoritmaları",
                "author": "Ayşe Demir",
                "year": 2022,
                "university": "Ankara Üniversitesi",
                "thesis_type": "Yüksek Lisans"
            }
        ]
        mock_scraper.search = AsyncMock(return_value=mock_results)

        # Call handler
        arguments = {
            "query": "yapay zeka",
            "search_field": "tumu",
            "max_results": 20
        }
        result = await handle_search_thesis(arguments)

        # Verify
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Found 2 thesis(es)" in result[0].text
        assert "Yapay Zeka Uygulamaları" in result[0].text
        assert "Ahmet Yılmaz" in result[0].text

    @pytest.mark.asyncio
    @patch('src.server.scraper')
    async def test_search_thesis_no_results(self, mock_scraper):
        """Test search with no results."""
        mock_scraper.search = AsyncMock(return_value=[])

        arguments = {"query": "nonexistentquery12345"}
        result = await handle_search_thesis(arguments)

        assert "No theses found" in result[0].text

    @pytest.mark.asyncio
    async def test_search_thesis_missing_query(self):
        """Test search without required query parameter."""
        arguments = {}

        with pytest.raises(ValueError, match="Query parameter is required"):
            await handle_search_thesis(arguments)

    @pytest.mark.asyncio
    @patch('src.server.scraper')
    async def test_search_thesis_with_filters(self, mock_scraper):
        """Test search with multiple filters."""
        mock_scraper.search = AsyncMock(return_value=[])

        arguments = {
            "query": "machine learning",
            "search_field": "tez_adi",
            "year_start": 2020,
            "year_end": 2023,
            "thesis_type": "doktora",
            "university": "Boğaziçi Üniversitesi",
            "language": "en",
            "permission_status": "izinli",
            "max_results": 50
        }

        await handle_search_thesis(arguments)

        # Verify scraper was called with correct arguments
        mock_scraper.search.assert_called_once_with(
            query="machine learning",
            search_field="tez_adi",
            year_start=2020,
            year_end=2023,
            thesis_type="doktora",
            university="Boğaziçi Üniversitesi",
            language="en",
            permission_status="izinli",
            max_results=50
        )


class TestGetThesisDetailsTool:
    """Test get_thesis_details tool handler."""

    @pytest.mark.asyncio
    @patch('src.server.scraper')
    async def test_get_thesis_details_success(self, mock_scraper):
        """Test successful thesis detail retrieval."""
        mock_details = {
            "thesis_id": "123456",
            "title": "Derin Öğrenme Yöntemleri",
            "author": "Mehmet Öz",
            "advisor": "Prof. Dr. Ali Veli",
            "year": 2023,
            "university": "ODTÜ",
            "institute": "Fen Bilimleri Enstitüsü",
            "department": "Bilgisayar Mühendisliği",
            "thesis_type": "Doktora",
            "language": "Türkçe",
            "page_count": "150",
            "keywords": "derin öğrenme, yapay sinir ağları, görüntü işleme",
            "abstract": "Bu tez derin öğrenme yöntemlerini incelemektedir..."
        }
        mock_scraper.get_thesis_details = AsyncMock(return_value=mock_details)

        arguments = {"thesis_id": "123456"}
        result = await handle_get_thesis_details(arguments)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Derin Öğrenme Yöntemleri" in result[0].text
        assert "Mehmet Öz" in result[0].text
        assert "Prof. Dr. Ali Veli" in result[0].text
        assert "Abstract:" in result[0].text

    @pytest.mark.asyncio
    async def test_get_thesis_details_missing_id(self):
        """Test detail retrieval without thesis ID."""
        arguments = {}

        with pytest.raises(ValueError, match="thesis_id parameter is required"):
            await handle_get_thesis_details(arguments)


class TestGetRecentThesisTool:
    """Test get_recent_thesis tool handler."""

    @pytest.mark.asyncio
    @patch('src.server.scraper')
    async def test_get_recent_thesis_success(self, mock_scraper):
        """Test successful recent thesis retrieval."""
        mock_results = [
            {
                "thesis_id": "789",
                "title": "Blokzincir Teknolojisi",
                "author": "Zeynep Kara",
                "year": 2024,
                "university": "Hacettepe Üniversitesi",
                "thesis_type": "Yüksek Lisans"
            }
        ]
        mock_scraper.get_recent_thesis = AsyncMock(return_value=mock_results)

        arguments = {"days": 15, "limit": 50}
        result = await handle_get_recent_thesis(arguments)

        assert len(result) == 1
        assert "Recent Theses" in result[0].text
        assert "Last 15 days" in result[0].text
        assert "Blokzincir Teknolojisi" in result[0].text

    @pytest.mark.asyncio
    @patch('src.server.scraper')
    async def test_get_recent_thesis_no_results(self, mock_scraper):
        """Test recent thesis with no results."""
        mock_scraper.get_recent_thesis = AsyncMock(return_value=[])

        arguments = {"days": 1, "limit": 10}
        result = await handle_get_recent_thesis(arguments)

        assert "No theses added in the last 1 days" in result[0].text

    @pytest.mark.asyncio
    @patch('src.server.scraper')
    async def test_get_recent_thesis_defaults(self, mock_scraper):
        """Test recent thesis with default parameters."""
        mock_scraper.get_recent_thesis = AsyncMock(return_value=[])

        arguments = {}
        result = await handle_get_recent_thesis(arguments)

        # Verify defaults were used
        mock_scraper.get_recent_thesis.assert_called_once_with(
            days=15,
            limit=50
        )


class TestGetThesisStatisticsTool:
    """Test get_thesis_statistics tool handler."""

    @pytest.mark.asyncio
    @patch('src.server.scraper')
    async def test_get_statistics_success(self, mock_scraper):
        """Test successful statistics retrieval."""
        mock_stats = {
            "total_count": 150,
            "by_type": {
                "Doktora": 80,
                "Yüksek Lisans": 70
            },
            "by_year": {
                2023: 50,
                2022: 60,
                2021: 40
            },
            "by_university": {
                "İstanbul Üniversitesi": 30,
                "Ankara Üniversitesi": 25,
                "ODTÜ": 20
            },
            "by_language": {
                "Türkçe": 120,
                "İngilizce": 30
            }
        }
        mock_scraper.get_statistics = AsyncMock(return_value=mock_stats)

        arguments = {"university": "İstanbul Üniversitesi", "year": 2023}
        result = await handle_get_thesis_statistics(arguments)

        assert len(result) == 1
        assert "Thesis Statistics" in result[0].text
        assert "Total Theses: 150" in result[0].text
        assert "By Thesis Type:" in result[0].text
        assert "Doktora: 80" in result[0].text
        assert "By Year" in result[0].text

    @pytest.mark.asyncio
    @patch('src.server.scraper')
    async def test_get_statistics_with_filters(self, mock_scraper):
        """Test statistics with multiple filters."""
        mock_scraper.get_statistics = AsyncMock(return_value={
            "total_count": 0,
            "by_type": {},
            "by_year": {},
            "by_university": {},
            "by_language": {}
        })

        arguments = {
            "university": "Boğaziçi Üniversitesi",
            "year": 2022,
            "thesis_type": "doktora"
        }
        result = await handle_get_thesis_statistics(arguments)

        assert "Filters Applied:" in result[0].text
        assert "University: Boğaziçi Üniversitesi" in result[0].text
        assert "Year: 2022" in result[0].text
        assert "Type: doktora" in result[0].text


class TestToolErrorHandling:
    """Test error handling in tool handlers."""

    @pytest.mark.asyncio
    @patch('src.server.scraper')
    async def test_search_scraper_error(self, mock_scraper):
        """Test handling of scraper errors."""
        from src.scraper import YOKThesisScraperError

        mock_scraper.search = AsyncMock(
            side_effect=YOKThesisScraperError("Network error")
        )

        # Import the actual call_tool function to test error handling
        from src.server import call_tool

        result = await call_tool("search_thesis", {"query": "test"})

        assert "Error:" in result[0].text
        assert "Network error" in result[0].text
