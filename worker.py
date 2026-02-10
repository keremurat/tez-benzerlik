"""
Cloudflare Workers entry point for YOK Tez MCP Server
Handles /tools, /mcp, /api/search, /api/thesis routes
"""

import json
import re
from urllib.parse import urlparse, parse_qs, quote

from workers import WorkerEntrypoint, Response

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# ─── Tool Definitions ───────────────────────────────────────────────

TOOLS = [
    {
        "name": "search_theses",
        "description": "Search for theses in Turkey's YOK (Council of Higher Education) National Thesis Center database. Returns thesis ID, title, author, year, and type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (thesis title, author name, keyword, etc.)"
                },
                "search_field": {
                    "type": "string",
                    "description": "Field to search in",
                    "enum": ["tez_adi", "yazar", "danisman", "konu", "tumu"],
                    "default": "tumu"
                },
                "year_start": {
                    "type": "integer",
                    "description": "Filter by start year"
                },
                "year_end": {
                    "type": "integer",
                    "description": "Filter by end year"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 20
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_thesis_details",
        "description": "Get detailed information about a specific thesis by its ID. Returns title, author, advisor, university, abstract, and more.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "thesis_id": {
                    "type": "string",
                    "description": "The YOK thesis ID number"
                }
            },
            "required": ["thesis_id"]
        }
    }
]

# ─── Constants ───────────────────────────────────────────────────────

BASE_URL = "https://tez.yok.gov.tr"
SEARCH_URL = f"{BASE_URL}/UlusalTezMerkezi/tarama.jsp"
DETAIL_URL = f"{BASE_URL}/UlusalTezMerkezi/tezDetay.jsp"

CORS_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://tez.yok.gov.tr/UlusalTezMerkezi/tarama.jsp",
}

FIELD_MAP = {
    "tez_adi": "TezAd",
    "yazar": "AdSoyad",
    "danisman": "DanismanAdSoyad",
    "konu": "Dizin",
    "tumu": "keyword",
}


# ─── Worker Entry Point ─────────────────────────────────────────────

class Default(WorkerEntrypoint):
    """Cloudflare Workers entry point."""

    async def fetch(self, request):
        parsed = urlparse(request.url)
        path = parsed.path.rstrip("/") or "/"
        method = request.method

        # CORS preflight
        if method == "OPTIONS":
            return Response(None, status=204, headers=CORS_HEADERS)

        # Route: Server info
        if path == "/" and method == "GET":
            return self._json({
                "name": "yok-tez-mcp",
                "version": "2.0.0",
                "description": "YOK Thesis Center MCP Server (Cloudflare Workers)",
                "status": "online",
                "endpoints": {
                    "tools": "/tools",
                    "mcp": "/mcp (POST)",
                    "search": "/api/search?q=query",
                    "thesis": "/api/thesis/{id}",
                }
            })

        # Route: List tools
        if path == "/tools" and method == "GET":
            return self._json({"tools": TOOLS})

        # Route: MCP JSON-RPC protocol
        if path == "/mcp" and method == "POST":
            return await self._handle_mcp(request)

        # Route: REST API - search
        if path == "/api/search" and method == "GET":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            if not query:
                return self._json({"error": "Missing query parameter 'q'"}, 400)
            search_field = params.get("field", ["tumu"])[0]
            year_start = params.get("year_start", [None])[0]
            year_end = params.get("year_end", [None])[0]
            max_results = int(params.get("max_results", ["20"])[0])
            results = await self._search_yok(query, search_field, year_start, year_end, max_results)
            return self._json({"results": results, "total": len(results)})

        # Route: REST API - thesis details
        if path.startswith("/api/thesis/") and method == "GET":
            thesis_id = path.split("/api/thesis/", 1)[1]
            if thesis_id:
                details = await self._get_thesis_detail(thesis_id)
                return self._json(details)
            return self._json({"error": "Missing thesis_id"}, 400)

        # 404
        return self._json({
            "error": "Not found",
            "available_endpoints": ["/", "/tools", "/mcp", "/api/search?q=...", "/api/thesis/{id}"]
        }, 404)

    # ─── Helpers ─────────────────────────────────────────────────────

    def _json(self, data, status=200):
        """Return a JSON response with CORS headers."""
        return Response(
            json.dumps(data, ensure_ascii=False, indent=2),
            status=status,
            headers=CORS_HEADERS
        )

    # ─── MCP Protocol Handler ───────────────────────────────────────

    async def _handle_mcp(self, request):
        """Handle MCP JSON-RPC protocol requests."""
        try:
            body = await request.text()
            data = json.loads(body)

            jsonrpc = data.get("jsonrpc", "2.0")
            request_id = data.get("id")
            method = data.get("method")
            params = data.get("params", {})

            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "yok-tez-mcp", "version": "2.0.0"}
                }
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self._call_tool(tool_name, arguments)
            else:
                return self._json({
                    "jsonrpc": jsonrpc,
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Unknown method: {method}"}
                })

            return self._json({"jsonrpc": jsonrpc, "id": request_id, "result": result})

        except Exception as e:
            return self._json({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }, 500)

    async def _call_tool(self, tool_name, arguments):
        """Execute a tool by name."""
        if tool_name == "search_theses":
            query = arguments.get("query", "")
            results = await self._search_yok(
                query=query,
                search_field=arguments.get("search_field", "tumu"),
                year_start=arguments.get("year_start"),
                year_end=arguments.get("year_end"),
                max_results=arguments.get("max_results", 20),
            )
            if not results:
                text = f"No theses found for: {query}"
            else:
                text = f"Found {len(results)} theses:\n\n"
                for i, t in enumerate(results, 1):
                    text += f"{i}. {t.get('title', 'N/A')}\n"
                    text += f"   ID: {t.get('thesis_id')}, Author: {t.get('author')}\n"
                    text += f"   Year: {t.get('year')}, Type: {t.get('thesis_type')}\n\n"
            return {"content": [{"type": "text", "text": text}]}

        elif tool_name == "get_thesis_details":
            thesis_id = arguments.get("thesis_id", "")
            details = await self._get_thesis_detail(thesis_id)
            if not details or details.get("title") == "Detaylar yuklenemedi":
                text = f"Thesis {thesis_id} not found"
            else:
                text = f"# Thesis {thesis_id}: {details.get('title')}\n\n"
                text += f"**Author:** {details.get('author')}\n"
                text += f"**Year:** {details.get('year')}\n"
                text += f"**University:** {details.get('university')}\n\n"
                if details.get("abstract"):
                    text += f"**Abstract:** {details['abstract'][:500]}...\n"
            return {"content": [{"type": "text", "text": text}]}

        return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]}

    # ─── YOK Scraper ────────────────────────────────────────────────

    async def _fetch_with_cookies(self, url, method="GET", body=None, extra_headers=None):
        """Make an HTTP request to YOK with session cookie handling."""
        from js import fetch, Object, Headers
        from pyodide.ffi import to_js as _to_js

        def to_js(obj):
            return _to_js(obj, dict_converter=Object.fromEntries)

        # Step 1: Visit the search page to get session cookies
        init_opts = to_js({
            "method": "GET",
            "headers": BROWSER_HEADERS,
            "redirect": "manual",
        })
        init_resp = await fetch(SEARCH_URL, init_opts)

        # Extract Set-Cookie headers
        cookies = ""
        try:
            raw_cookies = init_resp.headers.get("set-cookie")
            if raw_cookies:
                cookies = raw_cookies
        except Exception:
            pass

        # Step 2: Make the actual request with cookies
        headers = {**BROWSER_HEADERS}
        if cookies:
            headers["Cookie"] = cookies
        if extra_headers:
            headers.update(extra_headers)

        opts = {"method": method, "headers": headers}
        if body is not None:
            opts["body"] = body

        response = await fetch(url, to_js(opts))
        html = await response.text()
        return html

    async def _search_yok(self, query, search_field="tumu", year_start=None, year_end=None, max_results=20):
        """Search YOK thesis database."""
        try:
            input_field = FIELD_MAP.get(search_field, "keyword")

            # Build form data
            form_parts = [f"{input_field}={quote(str(query))}", "-find=Bul", "submitted=1"]
            if year_start:
                form_parts.append(f"yil1={year_start}")
            if year_end:
                form_parts.append(f"yil2={year_end}")
            form_body = "&".join(form_parts)

            html = await self._fetch_with_cookies(
                SEARCH_URL,
                method="POST",
                body=form_body,
                extra_headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            return _parse_search_results(html, max_results)

        except Exception as e:
            return [{"error": str(e)}]

    async def _get_thesis_detail(self, thesis_id):
        """Get thesis details by ID."""
        try:
            html = await self._fetch_with_cookies(f"{DETAIL_URL}?id={thesis_id}")
            return _parse_thesis_detail(html, thesis_id)
        except Exception as e:
            return {
                "thesis_id": thesis_id,
                "title": "Detaylar yuklenemedi",
                "error": str(e)
            }


# ─── HTML Parsers (module-level functions) ───────────────────────────

def _normalize(text):
    """Normalize text: strip whitespace, collapse spaces."""
    if not text:
        return ""
    return " ".join(text.strip().split())


def _parse_search_results(html, max_results=20):
    """Parse search results from YOK HTML response."""
    results = []

    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        table = (
            soup.find("table", class_="watable")
            or soup.find("table", class_="table-striped")
            or soup.find("table", {"class": "tablo"})
            or soup.find("table", {"id": "resulttable"})
        )

        if not table:
            return results

        tbody = table.find("tbody")
        if not tbody:
            return results

        rows = tbody.find_all("tr")
        for row in rows[:max_results]:
            try:
                cells = row.find_all("td")
                if len(cells) < 6:
                    continue

                thesis_id = None
                span = cells[1].find("span")
                if span:
                    onclick = span.get("onclick", "")
                    id_match = re.search(r"tezDetay\('(\d+)'\)", onclick)
                    if id_match:
                        thesis_id = id_match.group(1)

                if not thesis_id:
                    thesis_id = _normalize(cells[1].get_text())

                results.append({
                    "thesis_id": thesis_id,
                    "author": _normalize(cells[2].get_text()) if len(cells) > 2 else "",
                    "year": _normalize(cells[3].get_text()) if len(cells) > 3 else None,
                    "title": _normalize(cells[4].get_text()) if len(cells) > 4 else "",
                    "thesis_type": _normalize(cells[5].get_text()) if len(cells) > 5 else None,
                })
            except Exception:
                continue
    else:
        # Fallback: regex parsing when BeautifulSoup is not available
        row_pattern = r"<tr[^>]*>(.*?)</tr>"
        rows = re.findall(row_pattern, html, re.DOTALL)
        for row_html in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.DOTALL)
            if len(cells) >= 6:
                thesis_id_match = re.search(r"tezDetay\('(\d+)'\)", cells[1])
                thesis_id = thesis_id_match.group(1) if thesis_id_match else re.sub(r"<[^>]+>", "", cells[1]).strip()

                results.append({
                    "thesis_id": thesis_id,
                    "author": re.sub(r"<[^>]+>", "", cells[2]).strip(),
                    "year": re.sub(r"<[^>]+>", "", cells[3]).strip(),
                    "title": re.sub(r"<[^>]+>", "", cells[4]).strip(),
                    "thesis_type": re.sub(r"<[^>]+>", "", cells[5]).strip(),
                })

                if len(results) >= max_results:
                    break

    return results


def _parse_thesis_detail(html, thesis_id):
    """Parse thesis detail page."""
    details = {
        "thesis_id": thesis_id,
        "title": None,
        "author": None,
        "advisor": None,
        "year": None,
        "university": None,
        "institute": None,
        "department": None,
        "thesis_type": None,
        "language": None,
        "page_count": None,
        "keywords": None,
        "abstract": None,
    }

    key_mapping = {
        "tez no": "thesis_id",
        "tez adi": "title",
        "tez adı": "title",
        "yazar": "author",
        "danisman": "advisor",
        "danışman": "advisor",
        "yil": "year",
        "yıl": "year",
        "universite": "university",
        "üniversite": "university",
        "enstitu": "institute",
        "enstitü": "institute",
        "anabilim dali": "department",
        "anabilim dalı": "department",
        "tez turu": "thesis_type",
        "tez türü": "thesis_type",
        "dil": "language",
        "sayfa sayisi": "page_count",
        "sayfa sayısı": "page_count",
        "anahtar kelimeler": "keywords",
    }

    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")

        detail_table = (
            soup.find("table", {"class": "bilgi"})
            or soup.find("div", {"class": "thesis-detail"})
            or soup.find("div", {"id": "iceriktablo"})
        )

        if detail_table:
            for row in detail_table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    key = _normalize(cells[0].get_text()).rstrip(":").lower()
                    value = _normalize(cells[1].get_text())
                    english_key = key_mapping.get(key)
                    if english_key and english_key in details:
                        details[english_key] = value

        # Extract abstract
        for selector in [{"class": "ozet"}, {"class": "abstract"}, {"id": "ozet"}, {"id": "abstract"}]:
            elem = soup.find(["div", "p", "section"], selector)
            if elem:
                text = elem.get_text().strip()
                if len(text) > 100:
                    details["abstract"] = _normalize(text)
                    break

        if not details["abstract"]:
            for row in soup.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    label = cells[0].get_text().strip().lower()
                    if "ozet" in label or "özet" in label or "abstract" in label:
                        text = cells[1].get_text().strip()
                        if len(text) > 100:
                            details["abstract"] = _normalize(text)
                            break
    else:
        # Regex fallback
        for key_tr, key_en in key_mapping.items():
            pattern = rf"{re.escape(key_tr)}\s*:?\s*</(?:td|th)>\s*<td[^>]*>(.*?)</td>"
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                details[key_en] = re.sub(r"<[^>]+>", "", match.group(1)).strip()

    return details
