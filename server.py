#!/usr/bin/env python3
"""
YOK National Thesis Center MCP Server (Local - Selenium)
Tools: advanced_search, get_thesis_details
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

from src.selenium_scraper import SeleniumYOKScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Server("yok-tez-mcp")
scraper: Optional[SeleniumYOKScraper] = None


async def initialize_scraper():
    global scraper
    if scraper is None:
        logger.info("Initializing YOK Thesis Scraper...")
        scraper = SeleniumYOKScraper(
            rate_limit_delay=3.0,
            cache_ttl=3600,
            timeout=30.0,
            headless=True
        )
        logger.info("Scraper initialized successfully")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
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
                    "keyword1": {"type": "string", "description": "First search keyword (required)"},
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
                    "operator2": {"type": "string", "enum": ["and", "or", "not"]},
                    "keyword2": {"type": "string"},
                    "searchField2": {"type": "string"},
                    "searchType2": {"type": "string"},
                    "operator3": {"type": "string", "enum": ["and", "or", "not"]},
                    "keyword3": {"type": "string"},
                    "searchField3": {"type": "string"},
                    "searchType3": {"type": "string"},
                    "yearFrom": {"type": "string"},
                    "yearTo": {"type": "string"},
                    "thesisType": {"type": "string"},
                    "language": {"type": "string"},
                    "university": {"type": "string"}
                },
                "required": ["keyword1"]
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
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    await initialize_scraper()

    try:
        if name == "advanced_search":
            return await advanced_search_tool(arguments)
        elif name == "get_thesis_details":
            return await get_thesis_details_tool(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Error calling tool {name}: {str(e)}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def advanced_search_tool(args: Dict[str, Any]) -> list[TextContent]:
    logger.info("Performing advanced search")

    result = await scraper.advanced_search(args)

    if isinstance(result, dict):
        results = result.get("results", [])
        total_found = result.get("total_found", len(results))
    else:
        results = result
        total_found = len(results)

    if not results:
        return [TextContent(type="text", text="No theses found matching the search criteria")]

    output = f"Found {len(results)} theses (Total: {total_found}):\n\n"
    for i, thesis in enumerate(results[:50], 1):
        output += f"{i}. **{thesis.get('title', 'N/A')}**\n"
        output += f"   - ID: {thesis.get('thesis_id', 'N/A')}\n"
        output += f"   - Author: {thesis.get('author', 'N/A')}\n"
        output += f"   - Year: {thesis.get('year', 'N/A')}\n\n"

    if len(results) > 50:
        output += f"\n... and {len(results) - 50} more results\n"

    return [TextContent(type="text", text=output)]


async def get_thesis_details_tool(args: Dict[str, Any]) -> list[TextContent]:
    thesis_id = args["thesis_id"]
    logger.info(f"Fetching details for thesis: {thesis_id}")

    details = await scraper.get_thesis_details(thesis_id, use_cache=False)

    if not details or details.get('title') in [None, "Detaylar yüklenemedi"]:
        return [TextContent(type="text", text=f"Thesis {thesis_id} not found or could not be retrieved")]

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


async def main():
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
