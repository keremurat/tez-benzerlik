#!/usr/bin/env python3
"""
YÖK National Thesis Center MCP Server

This MCP server provides tools to search and retrieve thesis information
from Turkey's National Thesis Center (YÖK Ulusal Tez Merkezi).

Tools:
- search_theses: Search for theses by keyword, author, year, etc.
- get_thesis_details: Get detailed information about a specific thesis
- advanced_search: Perform advanced multi-criteria search
- get_recent_theses: Get recently added theses
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import AnyUrl

from src.selenium_scraper import SeleniumYOKScraper, YOKThesisScraperError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
app = Server("yok-tez-mcp")

# Global scraper instance
scraper: Optional[SeleniumYOKScraper] = None


async def initialize_scraper():
    """Initialize the Selenium scraper"""
    global scraper
    if scraper is None:
        logger.info("Initializing YÖK Thesis Scraper...")
        scraper = SeleniumYOKScraper(
            rate_limit_delay=3.0,
            cache_ttl=3600,
            timeout=30.0,
            headless=True
        )
        logger.info("Scraper initialized successfully")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="search_theses",
            description=(
                "Search for theses in Turkey's National Thesis Center. "
                "Search by keyword, author, advisor, subject, or all fields. "
                "Filter by year range, thesis type, university, and language."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (required)"
                    },
                    "search_field": {
                        "type": "string",
                        "enum": ["tez_adi", "yazar", "danisman", "konu", "tumu"],
                        "default": "tumu",
                        "description": "Field to search in (tez_adi=title, yazar=author, danisman=advisor, konu=subject, tumu=all)"
                    },
                    "year_start": {
                        "type": "integer",
                        "description": "Start year (e.g., 2020)"
                    },
                    "year_end": {
                        "type": "integer",
                        "description": "End year (e.g., 2024)"
                    },
                    "thesis_type": {
                        "type": "string",
                        "enum": ["yuksek_lisans", "doktora", "tipta_uzmanlik", "sanatta_yeterlik"],
                        "description": "Thesis type (yuksek_lisans=masters, doktora=phd, tipta_uzmanlik=medical specialty, sanatta_yeterlik=proficiency in art)"
                    },
                    "university": {
                        "type": "string",
                        "description": "University name"
                    },
                    "language": {
                        "type": "string",
                        "description": "Language (e.g., Türkçe, İngilizce)"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 20,
                        "description": "Maximum number of results (1-100)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_thesis_details",
            description=(
                "Get detailed information about a specific thesis by its ID. "
                "Returns full metadata including title, author, advisor, abstract, "
                "purpose, methodology, and keywords."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "thesis_id": {
                        "type": "string",
                        "description": "The thesis ID number (e.g., '921717')"
                    }
                },
                "required": ["thesis_id"]
            }
        ),
        Tool(
            name="advanced_search",
            description=(
                "Perform advanced multi-criteria search with up to 3 keywords "
                "and boolean operators (AND, OR, NOT). Includes extensive filters "
                "for year, type, language, status, and more."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword1": {"type": "string"},
                    "searchField1": {
                        "type": "string",
                        "enum": ["1", "2", "3", "4", "5", "6", "7"],
                        "description": "1=Title, 2=Author, 3=Advisor, 4=Subject, 5=Index, 6=Abstract, 7=All"
                    },
                    "searchType1": {
                        "type": "string",
                        "enum": ["1", "2"],
                        "description": "1=Exact match, 2=Contains"
                    },
                    "operator2": {
                        "type": "string",
                        "enum": ["and", "or", "not"]
                    },
                    "keyword2": {"type": "string"},
                    "searchField2": {"type": "string"},
                    "searchType2": {"type": "string"},
                    "operator3": {
                        "type": "string",
                        "enum": ["and", "or", "not"]
                    },
                    "keyword3": {"type": "string"},
                    "searchField3": {"type": "string"},
                    "searchType3": {"type": "string"},
                    "yearFrom": {"type": "string"},
                    "yearTo": {"type": "string"},
                    "thesisType": {"type": "string"},
                    "language": {"type": "string"},
                    "university": {"type": "string"}
                }
            }
        ),
        Tool(
            name="get_recent_theses",
            description="Get recently added theses from the last N days",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "default": 15,
                        "description": "Number of days to look back (1-90)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Maximum results (1-200)"
                    }
                },
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    await initialize_scraper()

    try:
        if name == "search_theses":
            return await search_theses_tool(arguments)
        elif name == "get_thesis_details":
            return await get_thesis_details_tool(arguments)
        elif name == "advanced_search":
            return await advanced_search_tool(arguments)
        elif name == "get_recent_theses":
            return await get_recent_theses_tool(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Error calling tool {name}: {str(e)}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def search_theses_tool(args: Dict[str, Any]) -> list[TextContent]:
    """Search theses tool implementation"""
    query = args["query"]
    search_field = args.get("search_field", "tumu")
    year_start = args.get("year_start")
    year_end = args.get("year_end")
    thesis_type = args.get("thesis_type")
    university = args.get("university")
    language = args.get("language")
    max_results = args.get("max_results", 20)

    logger.info(f"Searching for: {query} in {search_field}")

    results = await scraper.search(
        query=query,
        search_field=search_field,
        year_start=year_start,
        year_end=year_end,
        thesis_type=thesis_type,
        university=university,
        language=language,
        max_results=max_results,
        use_cache=False
    )

    if not results:
        return [TextContent(
            type="text",
            text=f"No theses found for query: {query}"
        )]

    # Format results
    output = f"Found {len(results)} theses:\n\n"
    for i, thesis in enumerate(results, 1):
        output += f"{i}. **{thesis.get('title', 'N/A')}**\n"
        output += f"   - ID: {thesis.get('thesis_id', 'N/A')}\n"
        output += f"   - Author: {thesis.get('author', 'N/A')}\n"
        output += f"   - Year: {thesis.get('year', 'N/A')}\n"
        output += f"   - Type: {thesis.get('thesis_type', 'N/A')}\n"
        output += f"   - University: {thesis.get('university', 'N/A')}\n"
        output += "\n"

    return [TextContent(type="text", text=output)]


async def get_thesis_details_tool(args: Dict[str, Any]) -> list[TextContent]:
    """Get thesis details tool implementation"""
    thesis_id = args["thesis_id"]

    logger.info(f"Fetching details for thesis: {thesis_id}")

    details = await scraper.get_thesis_details(thesis_id, use_cache=False)

    if not details or details.get('title') in [None, "Detaylar yüklenemedi"]:
        return [TextContent(
            type="text",
            text=f"Thesis {thesis_id} not found or could not be retrieved"
        )]

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

    return [TextContent(type="text", text=output)]


async def advanced_search_tool(args: Dict[str, Any]) -> list[TextContent]:
    """Advanced search tool implementation"""
    logger.info("Performing advanced search")

    result = await scraper.advanced_search(args)

    if isinstance(result, dict):
        results = result.get("results", [])
        total_found = result.get("total_found", len(results))
    else:
        results = result
        total_found = len(results)

    if not results:
        return [TextContent(
            type="text",
            text="No theses found matching the search criteria"
        )]

    # Format results
    output = f"Found {len(results)} theses (Total: {total_found}):\n\n"
    for i, thesis in enumerate(results[:50], 1):  # Limit to 50 for readability
        output += f"{i}. **{thesis.get('title', 'N/A')}**\n"
        output += f"   - ID: {thesis.get('thesis_id', 'N/A')}\n"
        output += f"   - Author: {thesis.get('author', 'N/A')}\n"
        output += f"   - Year: {thesis.get('year', 'N/A')}\n\n"

    if len(results) > 50:
        output += f"\n... and {len(results) - 50} more results\n"

    return [TextContent(type="text", text=output)]


async def get_recent_theses_tool(args: Dict[str, Any]) -> list[TextContent]:
    """Get recent theses tool implementation"""
    days = args.get("days", 15)
    limit = args.get("limit", 50)

    logger.info(f"Fetching recent theses from last {days} days")

    results = await scraper.get_recent_thesis(days=days, limit=limit, use_cache=False)

    if not results:
        return [TextContent(
            type="text",
            text=f"No recent theses found in the last {days} days"
        )]

    # Format results
    output = f"Recent theses from last {days} days ({len(results)} found):\n\n"
    for i, thesis in enumerate(results, 1):
        output += f"{i}. **{thesis.get('title', 'N/A')}**\n"
        output += f"   - ID: {thesis.get('thesis_id', 'N/A')}\n"
        output += f"   - Author: {thesis.get('author', 'N/A')}\n"
        output += f"   - Year: {thesis.get('year', 'N/A')}\n\n"

    return [TextContent(type="text", text=output)]


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
