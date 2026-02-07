"""
FastAPI Backend for YÖK Tez MCP Server

Exposes the MCP scraper functionality as REST API endpoints
for web frontend consumption.
"""

import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import sys
from pathlib import Path

# Add parent directory to path to import src modules
sys.path.append(str(Path(__file__).parent.parent))

from src.selenium_scraper import SeleniumYOKScraper, YOKThesisScraperError
from backend.mock_data import MOCK_SEARCH_RESULTS, MOCK_THESIS_DETAILS, MOCK_STATISTICS

logger = logging.getLogger(__name__)

# Demo mode - set to True to bypass YÖK's bot protection with mock data
# Set to False to use real YÖK data with Selenium
DEMO_MODE = False  # ✓ USING REAL YÖK DATA - No year restrictions!

# Global scraper instance
scraper: Optional[SeleniumYOKScraper] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - initializes and cleans up scraper."""
    global scraper

    # Startup
    logger.info("Initializing Selenium YÖK Thesis Scraper...")
    scraper = SeleniumYOKScraper(
        rate_limit_delay=3.0,  # Increased to avoid bot detection
        cache_ttl=3600,
        timeout=30.0,
        headless=True  # Run browser in headless mode
    )
    logger.info("Selenium scraper initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down scraper...")
    if scraper:
        await scraper.close()
    logger.info("Scraper closed")


# Create FastAPI app
app = FastAPI(
    title="YÖK Tez API",
    description="REST API for searching Turkish National Thesis Center (YÖK Ulusal Tez Merkezi)",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware - allow all origins for development
# In production, restrict to specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response validation

class SearchRequest(BaseModel):
    """Request model for thesis search."""
    query: str = Field(..., description="Search query term", min_length=1)
    search_field: str = Field(
        "tumu",
        description="Field to search in",
        pattern="^(tez_adi|yazar|danisman|konu|tumu)$"
    )
    year_start: Optional[int] = Field(None, ge=1980, le=2030)
    year_end: Optional[int] = Field(None, ge=1980, le=2030)
    thesis_type: Optional[str] = Field(
        None,
        pattern="^(yuksek_lisans|doktora|tipta_uzmanlik|sanatta_yeterlik)$"
    )
    university: Optional[str] = None
    language: Optional[str] = None
    permission_status: Optional[str] = Field(None, pattern="^(izinli|izinsiz)$")
    max_results: int = Field(20, ge=1, le=100)


class ThesisResponse(BaseModel):
    """Response model for thesis information."""
    thesis_id: Optional[str]
    title: str
    author: str
    year: Optional[int]
    university: str
    thesis_type: Optional[str]
    language: Optional[str]


class ThesisDetailResponse(BaseModel):
    """Response model for detailed thesis information."""
    thesis_id: Optional[str]
    title: Optional[str]
    author: Optional[str]
    advisor: Optional[str]
    year: Optional[str]
    university: Optional[str]
    institute: Optional[str]
    department: Optional[str]
    thesis_type: Optional[str]
    language: Optional[str]
    page_count: Optional[str]
    keywords: Optional[str]
    abstract: Optional[str]


class StatisticsResponse(BaseModel):
    """Response model for thesis statistics."""
    total_count: int
    by_type: Dict[str, int]
    by_year: Dict[int, int]
    by_university: Dict[str, int]
    by_language: Dict[str, int]


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    details: Optional[str] = None


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "YÖK Tez API",
        "version": "0.1.0",
        "description": "REST API for Turkish National Thesis Center",
        "endpoints": {
            "search": "/api/search",
            "details": "/api/thesis/{thesis_id}",
            "recent": "/api/recent",
            "statistics": "/api/statistics",
            "health": "/health"
        },
        "docs": "/docs",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "scraper_initialized": scraper is not None
    }


@app.post("/api/search", response_model=List[ThesisResponse])
async def search_theses(request: SearchRequest):
    """
    Search for theses in YÖK database.

    Args:
        request: Search parameters

    Returns:
        List of matching theses

    Raises:
        HTTPException: If search fails
    """
    if not scraper:
        raise HTTPException(status_code=503, detail="Scraper not initialized")

    try:
        logger.info(f"Search request: {request.query} in field {request.search_field}")

        # DEMO MODE: Return mock data to bypass YÖK's bot protection
        if DEMO_MODE:
            logger.info("Using DEMO MODE with mock data")
            # Filter mock results based on query (simple matching)
            filtered_results = [
                r for r in MOCK_SEARCH_RESULTS
                if request.query.lower() in r['title'].lower() or
                   request.query.lower() in r['author'].lower() or
                   request.query == '*'
            ]
            results = filtered_results[:request.max_results]
            logger.info(f"Found {len(results)} mock results")
            return results

        # Real YÖK search (when DEMO_MODE = False)
        results = await scraper.search(
            query=request.query,
            search_field=request.search_field,
            year_start=request.year_start,
            year_end=request.year_end,
            thesis_type=request.thesis_type,
            university=request.university,
            language=request.language,
            permission_status=request.permission_status,
            max_results=request.max_results
        )

        logger.info(f"Found {len(results)} results")
        return results

    except YOKThesisScraperError as e:
        logger.error(f"Scraper error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"YÖK service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/search", response_model=List[ThesisResponse])
async def search_theses_get(
    query: str = Query(..., description="Search query"),
    search_field: str = Query("tumu", pattern="^(tez_adi|yazar|danisman|konu|tumu)$"),
    year_start: Optional[int] = Query(None, ge=1980, le=2030),
    year_end: Optional[int] = Query(None, ge=1980, le=2030),
    thesis_type: Optional[str] = Query(None, pattern="^(yuksek_lisans|doktora|tipta_uzmanlik|sanatta_yeterlik)$"),
    university: Optional[str] = None,
    language: Optional[str] = None,
    permission_status: Optional[str] = Query(None, pattern="^(izinli|izinsiz)$"),
    max_results: int = Query(20, ge=1, le=100)
):
    """
    Search for theses (GET method for easier testing).

    Same as POST /api/search but using query parameters.
    """
    request = SearchRequest(
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
    return await search_theses(request)


@app.get("/api/thesis/{thesis_id}", response_model=ThesisDetailResponse)
async def get_thesis_details(thesis_id: str):
    """
    Get detailed information about a specific thesis.

    Args:
        thesis_id: Thesis ID number

    Returns:
        Detailed thesis information

    Raises:
        HTTPException: If retrieval fails
    """
    if not scraper:
        raise HTTPException(status_code=503, detail="Scraper not initialized")

    try:
        logger.info(f"Fetching details for thesis ID: {thesis_id}")

        # DEMO MODE: Return mock thesis details
        if DEMO_MODE:
            logger.info("Using DEMO MODE for thesis details")
            # Customize thesis_id in mock data
            details = MOCK_THESIS_DETAILS.copy()
            details['thesis_id'] = thesis_id
            return details

        details = await scraper.get_thesis_details(thesis_id)

        if not details:
            raise HTTPException(status_code=404, detail=f"Thesis {thesis_id} not found")

        logger.info(f"Successfully fetched details for thesis {thesis_id}")
        return details

    except YOKThesisScraperError as e:
        logger.error(f"Scraper error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"YÖK service error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class AdvancedSearchRequest(BaseModel):
    """Request model for advanced thesis search."""
    keyword1: Optional[str] = ""
    searchField1: Optional[str] = "Tumu"
    searchType1: Optional[str] = "0"
    operator2: Optional[str] = "ve"
    keyword2: Optional[str] = ""
    searchField2: Optional[str] = "Tumu"
    searchType2: Optional[str] = "0"
    operator3: Optional[str] = "ve"
    keyword3: Optional[str] = ""
    searchField3: Optional[str] = "Tumu"
    searchType3: Optional[str] = "0"
    yearFrom: Optional[str] = ""
    yearTo: Optional[str] = ""
    thesisType: Optional[str] = ""
    permissionStatus: Optional[str] = ""
    groupType: Optional[str] = ""
    language: Optional[str] = ""
    status: Optional[str] = ""
    university: Optional[str] = ""
    institute: Optional[str] = ""


class AdvancedSearchResult(BaseModel):
    """Single result from advanced search."""
    thesis_id: Optional[str]
    author: Optional[str]
    year: Optional[str]
    title: Optional[str]
    title_tr: Optional[str]
    thesis_type: Optional[str]
    subject: Optional[str]


class AdvancedSearchResponse(BaseModel):
    """Response model for advanced search."""
    results: List[AdvancedSearchResult]
    total: int
    total_found: int = 0


@app.post("/api/advanced-search", response_model=AdvancedSearchResponse)
async def advanced_search(request: AdvancedSearchRequest):
    """
    Advanced search using YÖK's Gelişmiş Tarama form.
    """
    if not scraper:
        raise HTTPException(status_code=503, detail="Scraper not initialized")

    try:
        logger.info(f"Advanced search: keyword1={request.keyword1}")
        data = await scraper.advanced_search(request.dict())
        results = data.get("results", [])
        total_found = data.get("total_found", len(results))
        logger.info(f"Advanced search returned {len(results)} results (total found: {total_found})")
        return AdvancedSearchResponse(results=results, total=len(results), total_found=total_found)

    except YOKThesisScraperError as e:
        logger.error(f"Scraper error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"YÖK service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/recent", response_model=List[ThesisResponse])
async def get_recent_theses(
    days: int = Query(15, ge=1, le=90, description="Number of days to look back"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results")
):
    """
    Get recently added theses.

    Args:
        days: Number of days to look back
        limit: Maximum number of results

    Returns:
        List of recent theses

    Raises:
        HTTPException: If retrieval fails
    """
    if not scraper:
        raise HTTPException(status_code=503, detail="Scraper not initialized")

    try:
        logger.info(f"Fetching recent theses: days={days}, limit={limit}")

        # DEMO MODE: Return mock recent theses
        if DEMO_MODE:
            logger.info("Using DEMO MODE for recent theses")
            return MOCK_SEARCH_RESULTS[:limit]

        results = await scraper.get_recent_thesis(days=days, limit=limit)

        logger.info(f"Found {len(results)} recent theses")
        return results

    except YOKThesisScraperError as e:
        logger.error(f"Scraper error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"YÖK service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/statistics", response_model=StatisticsResponse)
async def get_statistics(
    university: Optional[str] = Query(None, description="Filter by university"),
    year: Optional[int] = Query(None, ge=1980, le=2030, description="Filter by year"),
    thesis_type: Optional[str] = Query(
        None,
        pattern="^(yuksek_lisans|doktora|tipta_uzmanlik|sanatta_yeterlik)$",
        description="Filter by thesis type"
    )
):
    """
    Get thesis statistics.

    Args:
        university: University filter
        year: Year filter
        thesis_type: Thesis type filter

    Returns:
        Statistical information

    Raises:
        HTTPException: If calculation fails
    """
    if not scraper:
        raise HTTPException(status_code=503, detail="Scraper not initialized")

    try:
        logger.info(f"Calculating statistics: university={university}, year={year}, type={thesis_type}")

        # DEMO MODE: Return mock statistics
        if DEMO_MODE:
            logger.info("Using DEMO MODE for statistics (Medical AI 2020-2023)")
            return MOCK_STATISTICS

        stats = await scraper.get_statistics(
            university=university,
            year=year,
            thesis_type=thesis_type
        )

        logger.info(f"Statistics calculated: {stats['total_count']} theses")
        return stats

    except YOKThesisScraperError as e:
        logger.error(f"Scraper error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"YÖK service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Error handlers

@app.exception_handler(YOKThesisScraperError)
async def scraper_error_handler(request, exc):
    """Handle YÖK scraper errors."""
    return JSONResponse(
        status_code=502,
        content={
            "error": "Scraper Error",
            "message": str(exc),
            "details": "Error communicating with YÖK service"
        }
    )


@app.exception_handler(Exception)
async def general_error_handler(request, exc):
    """Handle general errors."""
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "details": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
