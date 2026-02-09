"""
Vercel Serverless Function entry point for YÖK Tez MCP Server

This is a simplified HTTP handler that wraps the FastMCP server for Vercel.
FastMCP with stateless_http=True and json_response=True works best for Vercel.
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import FastMCP and scraper
try:
    from fastmcp import FastMCP
    from src.httpx_scraper import HttpxYOKScraper
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Install dependencies: pip install fastmcp httpx beautifulsoup4 lxml")
    raise

# ============================================================================
# Initialize FastMCP Server with Vercel-optimized settings
# ============================================================================

# Enable stateless_http for horizontal scaling in Vercel
mcp = FastMCP(
    name="yok-tez-mcp",
    version="2.0.0",
    stateless_http=True  # ⭐ Critical for serverless!
)

# Global scraper instance (cached across invocations)
_scraper = None

def get_scraper() -> HttpxYOKScraper:
    """Get or create scraper singleton."""
    global _scraper
    if _scraper is None:
        logger.info("Initializing httpx scraper...")
        _scraper = HttpxYOKScraper(
            rate_limit_delay=1.5,
            cache_ttl=3600,
            timeout=25.0
        )
    return _scraper


# ============================================================================
# MCP Tool Definitions
# ============================================================================

@mcp.tool()
async def search_theses(
    query: str,
    search_field: str = "tumu",
    year_start: int = None,
    year_end: int = None,
    max_results: int = 20
) -> str:
    """Search for theses in Turkey's YÖK database."""
    scraper = get_scraper()
    results = await scraper.search(
        query=query,
        search_field=search_field,
        year_start=year_start,
        year_end=year_end,
        max_results=max_results,
        use_cache=True
    )

    if not results:
        return f"No theses found for: {query}"

    output = f"Found {len(results)} theses:\n\n"
    for i, t in enumerate(results, 1):
        output += f"{i}. {t.get('title', 'N/A')}\n"
        output += f"   ID: {t.get('thesis_id')}, Author: {t.get('author')}\n"
        output += f"   Year: {t.get('year')}, Type: {t.get('thesis_type')}\n\n"

    return output


@mcp.tool()
async def get_thesis_details(thesis_id: str) -> str:
    """Get detailed information about a specific thesis."""
    scraper = get_scraper()
    details = await scraper.get_thesis_details(thesis_id, use_cache=True)

    if not details or details.get('title') == "Detaylar yüklenemedi":
        return f"Thesis {thesis_id} not found"

    output = f"# Thesis {thesis_id}: {details.get('title')}\n\n"
    output += f"**Author:** {details.get('author')}\n"
    output += f"**Year:** {details.get('year')}\n"
    output += f"**University:** {details.get('university')}\n\n"

    if details.get('abstract'):
        output += f"**Abstract:** {details['abstract'][:500]}...\n"

    return output


# ============================================================================
# Vercel Handler - Export FastMCP's ASGI app
# ============================================================================

# Create ASGI application for Vercel
# Vercel's Python runtime supports ASGI applications
app = mcp.http_app(
    path="/"  # Root path since Vercel routes /api to this file
)

# Make available for import
__all__ = ['app']
