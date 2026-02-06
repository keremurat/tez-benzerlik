#!/usr/bin/env python3
"""
Quick test script for Selenium YÖK scraper
Tests basic search functionality with real YÖK data
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.selenium_scraper import SeleniumYOKScraper, YOKThesisScraperError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_basic_search():
    """Test basic search functionality."""
    scraper = None
    try:
        logger.info("=" * 60)
        logger.info("Testing Selenium YÖK Scraper")
        logger.info("=" * 60)

        # Initialize scraper
        logger.info("\n1. Initializing scraper...")
        scraper = SeleniumYOKScraper(
            rate_limit_delay=2.0,
            cache_ttl=3600,
            timeout=30.0,
            headless=True  # Set to False to see browser in action
        )
        logger.info("✓ Scraper initialized")

        # Test search
        logger.info("\n2. Testing search for 'yapay zeka'...")
        results = await scraper.search(
            query="yapay zeka",
            search_field="tumu",
            max_results=5
        )

        logger.info(f"✓ Search completed! Found {len(results)} results")

        if results:
            logger.info("\nFirst result:")
            first = results[0]
            for key, value in first.items():
                logger.info(f"  {key}: {value}")
        else:
            logger.warning("No results found - this might be normal if search returns no matches")

        # Test thesis details if we got results
        if results and results[0].get('thesis_id'):
            thesis_id = results[0]['thesis_id']
            logger.info(f"\n3. Testing thesis details for ID: {thesis_id}...")

            details = await scraper.get_thesis_details(thesis_id)
            logger.info(f"✓ Details retrieved!")
            logger.info(f"  Title: {details.get('title', 'N/A')}")
            logger.info(f"  Author: {details.get('author', 'N/A')}")
            logger.info(f"  Year: {details.get('year', 'N/A')}")

        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL TESTS PASSED!")
        logger.info("=" * 60)
        return True

    except YOKThesisScraperError as e:
        logger.error(f"✗ Scraper error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {str(e)}", exc_info=True)
        return False
    finally:
        if scraper:
            logger.info("\nClosing scraper...")
            await scraper.close()
            logger.info("✓ Scraper closed")


if __name__ == "__main__":
    success = asyncio.run(test_basic_search())
    sys.exit(0 if success else 1)
