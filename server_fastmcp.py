#!/usr/bin/env python3
"""
YÖK National Thesis Center MCP Server with FastMCP
Optimized for Vercel serverless deployment

This version uses httpx instead of Selenium for serverless compatibility.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

# FastMCP - Pythonic way to build MCP servers
try:
    from fastmcp import FastMCP
except ImportError:
    print("ERROR: fastmcp not installed. Run: pip install fastmcp")
    raise

from src.httpx_scraper import HttpxYOKScraper, YOKThesisScraperError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    "yok-tez-mcp",
    version="2.0.0",
    description="YÖK National Thesis Center MCP Server (Vercel-optimized)"
)

# Global scraper instance
scraper: Optional[HttpxYOKScraper] = None


def get_scraper() -> HttpxYOKScraper:
    """Get or create scraper instance."""
    global scraper
    if scraper is None:
        logger.info("Initializing httpx YÖK Thesis Scraper...")
        scraper = HttpxYOKScraper(
            rate_limit_delay=2.0,
            cache_ttl=3600,
            timeout=25.0  # Vercel has 30s timeout
        )
        logger.info("Scraper initialized successfully")
    return scraper


@mcp.tool()
async def search_theses(
    query: str,
    search_field: str = "tumu",
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    thesis_type: Optional[str] = None,
    university: Optional[str] = None,
    language: Optional[str] = None,
    max_results: int = 20
) -> str:
    """
    Search for theses in Turkey's National Thesis Center.

    Args:
        query: Search query (required)
        search_field: Field to search in - options: tez_adi (title), yazar (author),
                     danisman (advisor), konu (subject), tumu (all fields)
        year_start: Start year (e.g., 2020)
        year_end: End year (e.g., 2024)
        thesis_type: Thesis type - options: yuksek_lisans (masters), doktora (phd),
                    tipta_uzmanlik (medical specialty), sanatta_yeterlik (proficiency in art)
        university: University name
        language: Language (e.g., Türkçe, İngilizce)
        max_results: Maximum number of results (1-100)

    Returns:
        Formatted search results with thesis information
    """
    try:
        scraper_instance = get_scraper()

        logger.info(f"Searching for: {query} in {search_field}")

        results = await scraper_instance.search(
            query=query,
            search_field=search_field,
            year_start=year_start,
            year_end=year_end,
            thesis_type=thesis_type,
            university=university,
            language=language,
            max_results=max_results,
            use_cache=True
        )

        if not results:
            return f"No theses found for query: {query}"

        # Format results
        output = f"Found {len(results)} theses:\n\n"
        for i, thesis in enumerate(results, 1):
            output += f"{i}. **{thesis.get('title', 'N/A')}**\n"
            output += f"   - ID: {thesis.get('thesis_id', 'N/A')}\n"
            output += f"   - Author: {thesis.get('author', 'N/A')}\n"
            output += f"   - Year: {thesis.get('year', 'N/A')}\n"
            output += f"   - Type: {thesis.get('thesis_type', 'N/A')}\n"
            if thesis.get('university'):
                output += f"   - University: {thesis.get('university')}\n"
            output += "\n"

        return output

    except YOKThesisScraperError as e:
        logger.error(f"Scraper error: {str(e)}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def get_thesis_details(thesis_id: str) -> str:
    """
    Get detailed information about a specific thesis by its ID.

    ⚠️ Note: Due to serverless limitations (no JavaScript rendering),
    some details may be limited compared to Selenium version.

    Args:
        thesis_id: The thesis ID number (e.g., '921717')

    Returns:
        Detailed thesis metadata including title, author, advisor, abstract, etc.
    """
    try:
        scraper_instance = get_scraper()

        logger.info(f"Fetching details for thesis: {thesis_id}")

        details = await scraper_instance.get_thesis_details(thesis_id, use_cache=True)

        if not details or details.get('title') in [None, "Detaylar yüklenemedi"]:
            return f"Thesis {thesis_id} not found or could not be retrieved"

        # Format detailed output
        output = f"# Thesis Details (ID: {thesis_id})\n\n"

        if details.get('title'):
            output += f"## {details['title']}\n\n"

        output += "### Basic Information\n"
        output += f"- **Author:** {details.get('author', 'N/A')}\n"
        output += f"- **Advisor:** {details.get('advisor', 'N/A')}\n"
        output += f"- **Year:** {details.get('year', 'N/A')}\n"
        output += f"- **University:** {details.get('university', 'N/A')}\n"
        output += f"- **Institute:** {details.get('institute', 'N/A')}\n"
        output += f"- **Department:** {details.get('department', 'N/A')}\n"
        output += f"- **Type:** {details.get('thesis_type', 'N/A')}\n"
        output += f"- **Language:** {details.get('language', 'N/A')}\n"
        output += f"- **Pages:** {details.get('page_count', 'N/A')}\n\n"

        if details.get('keywords'):
            output += f"### Keywords\n{details['keywords']}\n\n"

        if details.get('purpose'):
            output += f"### Purpose\n{details['purpose']}\n\n"

        if details.get('abstract'):
            output += f"### Abstract\n{details['abstract']}\n\n"

        if '⚠️' in str(details.get('abstract', '')):
            output += "\n_Note: Some details may be incomplete due to serverless limitations._\n"

        return output

    except YOKThesisScraperError as e:
        logger.error(f"Scraper error: {str(e)}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return f"Unexpected error: {str(e)}"


@mcp.tool()
async def advanced_search(
    keyword1: str,
    search_field1: str = "7",
    search_type1: str = "2",
    operator2: Optional[str] = None,
    keyword2: Optional[str] = None,
    search_field2: Optional[str] = None,
    search_type2: Optional[str] = None,
    operator3: Optional[str] = None,
    keyword3: Optional[str] = None,
    search_field3: Optional[str] = None,
    search_type3: Optional[str] = None,
    year_from: Optional[str] = None,
    year_to: Optional[str] = None,
    thesis_type: Optional[str] = None,
    language: Optional[str] = None,
    university: Optional[str] = None
) -> str:
    """
    Perform advanced multi-criteria search.

    ⚠️ WARNING: Without JavaScript, boolean operators (AND/OR/NOT) have limited support.
    This falls back to basic search functionality.

    Args:
        keyword1: First search keyword (required)
        search_field1: Search field (1=Title, 2=Author, 3=Advisor, 4=Subject, 5=Index, 6=Abstract, 7=All)
        search_type1: Search type (1=Exact match, 2=Contains)
        operator2: Operator between keyword1 and keyword2 (and, or, not)
        keyword2: Second search keyword
        search_field2: Search field for keyword2
        search_type2: Search type for keyword2
        operator3: Operator between keyword2 and keyword3
        keyword3: Third search keyword
        search_field3: Search field for keyword3
        search_type3: Search type for keyword3
        year_from: Start year
        year_to: End year
        thesis_type: Thesis type
        language: Language
        university: University name

    Returns:
        Formatted search results
    """
    try:
        scraper_instance = get_scraper()

        logger.info("Performing advanced search (simplified version)")
        logger.warning("⚠️ Boolean operators not fully supported in serverless mode")

        # Build params dict
        params = {
            'keyword1': keyword1,
            'searchField1': search_field1,
            'searchType1': search_type1,
            'yearFrom': year_from,
            'yearTo': year_to,
            'thesisType': thesis_type,
            'language': language,
            'university': university
        }

        if keyword2:
            params.update({
                'operator2': operator2,
                'keyword2': keyword2,
                'searchField2': search_field2,
                'searchType2': search_type2
            })

        if keyword3:
            params.update({
                'operator3': operator3,
                'keyword3': keyword3,
                'searchField3': search_field3,
                'searchType3': search_type3
            })

        result = await scraper_instance.advanced_search(params)

        if isinstance(result, dict):
            results = result.get("results", [])
            total_found = result.get("total_found", len(results))
            note = result.get("note", "")
        else:
            results = result
            total_found = len(results)
            note = ""

        if not results:
            return "No theses found matching the search criteria"

        # Format results
        output = f"Found {len(results)} theses (Total: {total_found}):\n\n"

        if note:
            output += f"{note}\n\n"

        for i, thesis in enumerate(results[:50], 1):
            output += f"{i}. **{thesis.get('title', 'N/A')}**\n"
            output += f"   - ID: {thesis.get('thesis_id', 'N/A')}\n"
            output += f"   - Author: {thesis.get('author', 'N/A')}\n"
            output += f"   - Year: {thesis.get('year', 'N/A')}\n\n"

        if len(results) > 50:
            output += f"\n... and {len(results) - 50} more results\n"

        return output

    except Exception as e:
        logger.error(f"Advanced search error: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


@mcp.tool()
async def get_recent_theses(days: int = 15, limit: int = 50) -> str:
    """
    Get recently added theses from the last N days.

    ⚠️ Note: This feature requires JavaScript interaction and may not work
    properly in serverless environment.

    Args:
        days: Number of days to look back (1-90)
        limit: Maximum results (1-200)

    Returns:
        List of recently added theses
    """
    try:
        scraper_instance = get_scraper()

        logger.info(f"Fetching recent theses from last {days} days")
        logger.warning("⚠️ Recent theses feature has limited support without JavaScript")

        results = await scraper_instance.get_recent_thesis(
            days=days,
            limit=limit,
            use_cache=True
        )

        if not results:
            return f"⚠️ Recent theses feature requires JavaScript (not available in serverless mode)\n\nTry using search_theses instead with recent year filters."

        # Format results
        output = f"Recent theses from last {days} days ({len(results)} found):\n\n"
        for i, thesis in enumerate(results, 1):
            output += f"{i}. **{thesis.get('title', 'N/A')}**\n"
            output += f"   - ID: {thesis.get('thesis_id', 'N/A')}\n"
            output += f"   - Author: {thesis.get('author', 'N/A')}\n"
            output += f"   - Year: {thesis.get('year', 'N/A')}\n\n"

        return output

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return f"Error: {str(e)}"


# Resource: Server configuration
@mcp.resource("config://server")
def get_server_config() -> str:
    """Get server configuration and capabilities."""
    return """
# YÖK Tez MCP Server Configuration

**Version:** 2.0.0 (Vercel-optimized)
**Transport:** httpx (Selenium-free)
**Platform:** Vercel Serverless Functions

## ⚠️ Known Limitations

Due to serverless/no-JavaScript constraints:

1. **No JavaScript rendering** - Some dynamic content may be missing
2. **Modal content inaccessible** - Thesis details may be limited
3. **Advanced search operators limited** - Boolean AND/OR/NOT may not work fully
4. **Recent theses feature unavailable** - Use year filters with search instead

## Available Tools

- `search_theses`: Basic and filtered search
- `get_thesis_details`: Thesis metadata (limited)
- `advanced_search`: Multi-criteria search (simplified)
- `get_recent_theses`: Recent additions (limited functionality)

## Recommendations

For best results:
- Use basic `search_theses` with filters
- Specify year ranges for recent theses
- Be patient with response times (serverless cold starts)
"""


async def main():
    """
    Run the MCP server in HTTP mode for Vercel deployment.

    For local testing, run with:
        python server_fastmcp.py

    Then connect via MCP inspector at:
        http://localhost:8000/mcp
    """
    logger.info("Starting YÖK Tez FastMCP Server (Vercel mode)...")

    # Run in HTTP mode for Vercel
    # Vercel will proxy requests to this server
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        path="/mcp"
    )


if __name__ == "__main__":
    import sys

    # Check if running on Vercel
    if "VERCEL" in os.environ:
        logger.info("Running on Vercel - using stateless HTTP mode")
        # Vercel will call the FastMCP app directly
        # No need to run asyncio.run(main())
    else:
        # Local development
        logger.info("Running locally - starting HTTP server")
        asyncio.run(main())
