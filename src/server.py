"""
MCP Server for YÖK National Thesis Center

Provides tools for searching and retrieving thesis information from
Turkish Higher Education Council's National Thesis Center.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .scraper import YOKThesisScraper, YOKThesisScraperError

logger = logging.getLogger(__name__)

# Initialize scraper
scraper = YOKThesisScraper(
    rate_limit_delay=1.5,
    cache_ttl=3600,
    timeout=30.0
)

# Create MCP server instance
app = Server("yok-tez-mcp")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """
    List available tools for YÖK Thesis Center.

    Returns:
        List of tool definitions
    """
    return [
        Tool(
            name="search_thesis",
            description=(
                "Search for theses in YÖK National Thesis Center database. "
                "Supports filtering by author, advisor, subject, university, year range, "
                "thesis type, language, and permission status."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query term (required)"
                    },
                    "search_field": {
                        "type": "string",
                        "enum": ["tez_adi", "yazar", "danisman", "konu", "tumu"],
                        "description": (
                            "Field to search in: tez_adi (thesis title), yazar (author), "
                            "danisman (advisor), konu (subject), tumu (all fields). "
                            "Default: tumu"
                        ),
                        "default": "tumu"
                    },
                    "year_start": {
                        "type": "integer",
                        "description": "Start year for filtering (optional)",
                        "minimum": 1980,
                        "maximum": 2030
                    },
                    "year_end": {
                        "type": "integer",
                        "description": "End year for filtering (optional)",
                        "minimum": 1980,
                        "maximum": 2030
                    },
                    "thesis_type": {
                        "type": "string",
                        "enum": ["yuksek_lisans", "doktora", "tipta_uzmanlik", "sanatta_yeterlik"],
                        "description": (
                            "Thesis type: yuksek_lisans (master's), doktora (PhD), "
                            "tipta_uzmanlik (medical specialty), sanatta_yeterlik (proficiency in art)"
                        )
                    },
                    "university": {
                        "type": "string",
                        "description": "University name filter (optional)"
                    },
                    "language": {
                        "type": "string",
                        "description": "Thesis language (e.g., tr, en, de, fr)"
                    },
                    "permission_status": {
                        "type": "string",
                        "enum": ["izinli", "izinsiz"],
                        "description": "Permission status: izinli (permitted), izinsiz (not permitted)"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 20)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_thesis_details",
            description=(
                "Get detailed information about a specific thesis using its ID number. "
                "Returns comprehensive details including abstract, keywords, advisor, "
                "institute, department, and more."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "thesis_id": {
                        "type": "string",
                        "description": "Thesis ID number (required)"
                    }
                },
                "required": ["thesis_id"]
            }
        ),
        Tool(
            name="get_recent_thesis",
            description=(
                "Get a list of recently added theses from YÖK database. "
                "Useful for staying updated with new thesis submissions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 15)",
                        "default": 15,
                        "minimum": 1,
                        "maximum": 90
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 50)",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 200
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_thesis_statistics",
            description=(
                "Get statistical information about theses based on specified filters. "
                "Returns counts and breakdowns by type, year, university, and language."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "university": {
                        "type": "string",
                        "description": "Filter by university name (optional)"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Filter by specific year (optional)",
                        "minimum": 1980,
                        "maximum": 2030
                    },
                    "thesis_type": {
                        "type": "string",
                        "enum": ["yuksek_lisans", "doktora", "tipta_uzmanlik", "sanatta_yeterlik"],
                        "description": "Filter by thesis type (optional)"
                    }
                },
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """
    Handle tool calls from MCP client.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of text content responses

    Raises:
        ValueError: If tool name is unknown or arguments are invalid
    """
    try:
        if name == "search_thesis":
            return await handle_search_thesis(arguments)
        elif name == "get_thesis_details":
            return await handle_get_thesis_details(arguments)
        elif name == "get_recent_thesis":
            return await handle_get_recent_thesis(arguments)
        elif name == "get_thesis_statistics":
            return await handle_get_thesis_statistics(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    except YOKThesisScraperError as e:
        logger.error(f"Scraper error in {name}: {str(e)}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}\n\nPlease check your parameters and try again."
        )]
    except Exception as e:
        logger.error(f"Unexpected error in {name}: {str(e)}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Unexpected error: {str(e)}\n\nPlease contact support if this persists."
        )]


async def handle_search_thesis(arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Handle search_thesis tool call.

    Args:
        arguments: Search parameters

    Returns:
        Formatted search results
    """
    # Extract and validate arguments
    query = arguments.get("query")
    if not query:
        raise ValueError("Query parameter is required")

    search_field = arguments.get("search_field", "tumu")
    year_start = arguments.get("year_start")
    year_end = arguments.get("year_end")
    thesis_type = arguments.get("thesis_type")
    university = arguments.get("university")
    language = arguments.get("language")
    permission_status = arguments.get("permission_status")
    max_results = arguments.get("max_results", 20)

    logger.info(f"Searching theses: query='{query}', field={search_field}")

    # Perform search
    results = await scraper.search(
        query=query,
        search_field=search_field,
        year_start=year_start,
        year_end=year_end,
        thesis_type=thesis_type,
        university=university,
        language=language,
        permission_status=permission_status,
        max_results=max_results
    )

    # Format results
    if not results:
        return [TextContent(
            type="text",
            text=f"No theses found for query: '{query}'\n\nTry broadening your search criteria."
        )]

    # Build formatted response
    response_lines = [
        f"Found {len(results)} thesis(es) for '{query}':",
        "=" * 80,
        ""
    ]

    for i, thesis in enumerate(results, 1):
        response_lines.extend([
            f"{i}. {thesis.get('title', 'N/A')}",
            f"   Author: {thesis.get('author', 'N/A')}",
            f"   University: {thesis.get('university', 'N/A')}",
            f"   Year: {thesis.get('year', 'N/A')}",
            f"   Type: {thesis.get('thesis_type', 'N/A')}",
            f"   ID: {thesis.get('thesis_id', 'N/A')}",
            ""
        ])

    response_lines.append(f"Showing {len(results)} of potentially more results.")

    return [TextContent(type="text", text="\n".join(response_lines))]


async def handle_get_thesis_details(arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Handle get_thesis_details tool call.

    Args:
        arguments: Detail request parameters

    Returns:
        Formatted thesis details
    """
    thesis_id = arguments.get("thesis_id")
    if not thesis_id:
        raise ValueError("thesis_id parameter is required")

    logger.info(f"Fetching thesis details: ID={thesis_id}")

    # Get details
    details = await scraper.get_thesis_details(thesis_id)

    # Format response
    response_lines = [
        f"Thesis Details (ID: {thesis_id})",
        "=" * 80,
        ""
    ]

    # Define field order and labels
    field_order = [
        ("title", "Title"),
        ("author", "Author"),
        ("advisor", "Advisor"),
        ("year", "Year"),
        ("university", "University"),
        ("institute", "Institute"),
        ("department", "Department"),
        ("thesis_type", "Thesis Type"),
        ("language", "Language"),
        ("page_count", "Page Count"),
        ("keywords", "Keywords"),
        ("abstract", "Abstract"),
    ]

    for key, label in field_order:
        value = details.get(key)
        if value:
            if key == "abstract":
                # Format abstract with proper line breaks
                response_lines.extend([
                    f"{label}:",
                    "-" * 40,
                    value,
                    ""
                ])
            else:
                response_lines.append(f"{label}: {value}")

    # Add any additional fields not in the predefined order
    for key, value in details.items():
        if key not in [k for k, _ in field_order] and value:
            response_lines.append(f"{key.title()}: {value}")

    return [TextContent(type="text", text="\n".join(response_lines))]


async def handle_get_recent_thesis(arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Handle get_recent_thesis tool call.

    Args:
        arguments: Recent thesis parameters

    Returns:
        Formatted list of recent theses
    """
    days = arguments.get("days", 15)
    limit = arguments.get("limit", 50)

    logger.info(f"Fetching recent theses: days={days}, limit={limit}")

    # Get recent theses
    results = await scraper.get_recent_thesis(days=days, limit=limit)

    # Format results
    if not results:
        return [TextContent(
            type="text",
            text=f"No theses added in the last {days} days."
        )]

    response_lines = [
        f"Recent Theses (Last {days} days) - {len(results)} found:",
        "=" * 80,
        ""
    ]

    for i, thesis in enumerate(results, 1):
        response_lines.extend([
            f"{i}. {thesis.get('title', 'N/A')}",
            f"   Author: {thesis.get('author', 'N/A')}",
            f"   University: {thesis.get('university', 'N/A')}",
            f"   Year: {thesis.get('year', 'N/A')}",
            f"   Type: {thesis.get('thesis_type', 'N/A')}",
            f"   ID: {thesis.get('thesis_id', 'N/A')}",
            ""
        ])

    return [TextContent(type="text", text="\n".join(response_lines))]


async def handle_get_thesis_statistics(arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Handle get_thesis_statistics tool call.

    Args:
        arguments: Statistics parameters

    Returns:
        Formatted statistics
    """
    university = arguments.get("university")
    year = arguments.get("year")
    thesis_type = arguments.get("thesis_type")

    logger.info(f"Getting statistics: university={university}, year={year}, type={thesis_type}")

    # Get statistics
    stats = await scraper.get_statistics(
        university=university,
        year=year,
        thesis_type=thesis_type
    )

    # Format response
    response_lines = [
        "Thesis Statistics",
        "=" * 80,
        ""
    ]

    # Add filters
    filters = []
    if university:
        filters.append(f"University: {university}")
    if year:
        filters.append(f"Year: {year}")
    if thesis_type:
        filters.append(f"Type: {thesis_type}")

    if filters:
        response_lines.extend([
            "Filters Applied:",
            *[f"  - {f}" for f in filters],
            ""
        ])

    # Total count
    response_lines.extend([
        f"Total Theses: {stats['total_count']}",
        ""
    ])

    # By type
    if stats['by_type']:
        response_lines.extend([
            "By Thesis Type:",
            *[f"  - {t}: {count}" for t, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True)],
            ""
        ])

    # By year (top 10)
    if stats['by_year']:
        response_lines.append("By Year (Top 10):")
        sorted_years = sorted(stats['by_year'].items(), key=lambda x: x[1], reverse=True)[:10]
        response_lines.extend([f"  - {year}: {count}" for year, count in sorted_years])
        response_lines.append("")

    # By university (top 10)
    if stats['by_university']:
        response_lines.append("By University (Top 10):")
        sorted_unis = sorted(stats['by_university'].items(), key=lambda x: x[1], reverse=True)[:10]
        response_lines.extend([f"  - {uni}: {count}" for uni, count in sorted_unis])
        response_lines.append("")

    # By language
    if stats['by_language']:
        response_lines.extend([
            "By Language:",
            *[f"  - {lang}: {count}" for lang, count in sorted(stats['by_language'].items(), key=lambda x: x[1], reverse=True)],
            ""
        ])

    return [TextContent(type="text", text="\n".join(response_lines))]


async def main() -> None:
    """
    Main entry point for the MCP server.
    Runs the server using stdio transport.
    """
    logger.info("Starting YÖK Tez MCP Server...")

    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise
    finally:
        await scraper.close()
        logger.info("YÖK Tez MCP Server stopped")


if __name__ == "__main__":
    # Run the server
    asyncio.run(main())
