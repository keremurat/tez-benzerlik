"""
Cloudflare Workers entry point for YOK Tez MCP Server
Tools: advanced_search, get_thesis_details
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
        "name": "advanced_search",
        "description": "Perform advanced multi-criteria search with up to 3 keywords and boolean operators (AND, OR, NOT) in Turkey's YOK National Thesis Center.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword1": {"type": "string", "description": "First search keyword (required)"},
                "searchField1": {
                    "type": "string",
                    "enum": ["1", "2", "3", "4", "5", "6", "7"],
                    "default": "7",
                    "description": "1=Title, 2=Author, 3=Advisor, 4=Subject, 5=Index, 6=Abstract, 7=All"
                },
                "operator2": {"type": "string", "enum": ["and", "or", "not"], "description": "Boolean operator for second keyword"},
                "keyword2": {"type": "string", "description": "Second search keyword"},
                "searchField2": {"type": "string", "description": "Search field for second keyword"},
                "operator3": {"type": "string", "enum": ["and", "or", "not"], "description": "Boolean operator for third keyword"},
                "keyword3": {"type": "string", "description": "Third search keyword"},
                "searchField3": {"type": "string", "description": "Search field for third keyword"},
                "yearFrom": {"type": "string", "description": "Start year filter"},
                "yearTo": {"type": "string", "description": "End year filter"},
                "thesisType": {"type": "string", "description": "Thesis type filter"},
                "language": {"type": "string", "description": "Language filter"},
                "university": {"type": "string", "description": "University filter"}
            },
            "required": ["keyword1"]
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
    "Referer": "https://tez.yok.gov.tr/UlusalTezMerkezi/tarama.jsp",
}


# ─── Worker Entry Point ─────────────────────────────────────────────

class Default(WorkerEntrypoint):

    async def fetch(self, request):
        parsed = urlparse(request.url)
        path = parsed.path.rstrip("/") or "/"
        method = request.method

        if method == "OPTIONS":
            return Response(None, status=204, headers=CORS_HEADERS)

        if path == "/" and method == "GET":
            return self._json({
                "name": "yok-tez-mcp",
                "version": "2.0.0",
                "description": "YOK Thesis Center MCP Server",
                "status": "online",
                "endpoints": {
                    "tools": "/tools",
                    "mcp": "/mcp (POST)",
                }
            })

        if path == "/tools" and method == "GET":
            return self._json({"tools": TOOLS})

        if path == "/mcp" and method == "POST":
            return await self._handle_mcp(request)

        return self._json({"error": "Not found"}, 404)

    def _json(self, data, status=200):
        return Response(
            json.dumps(data, ensure_ascii=False, indent=2),
            status=status,
            headers=CORS_HEADERS
        )

    # ─── MCP Protocol ───────────────────────────────────────────────

    async def _handle_mcp(self, request):
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
                    "jsonrpc": jsonrpc, "id": request_id,
                    "error": {"code": -32601, "message": f"Unknown method: {method}"}
                })

            return self._json({"jsonrpc": jsonrpc, "id": request_id, "result": result})

        except Exception as e:
            return self._json({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32603, "message": str(e)}
            }, 500)

    async def _call_tool(self, tool_name, arguments):
        if tool_name == "advanced_search":
            return await self._advanced_search(arguments)
        elif tool_name == "get_thesis_details":
            return await self._get_thesis_details_tool(arguments)
        return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]}

    # ─── Tool Implementations ────────────────────────────────────────

    async def _advanced_search(self, args):
        keyword1 = args.get("keyword1", "")
        if not keyword1:
            return {"content": [{"type": "text", "text": "keyword1 is required"}]}

        results = await self._search_yok(
            query=keyword1,
            year_start=args.get("yearFrom"),
            year_end=args.get("yearTo"),
        )

        if not results:
            text = f"No theses found for: {keyword1}"
        else:
            text = f"Found {len(results)} theses:\n\n"
            for i, t in enumerate(results, 1):
                text += f"{i}. {t.get('title', 'N/A')}\n"
                text += f"   ID: {t.get('thesis_id')}, Author: {t.get('author')}\n"
                text += f"   Year: {t.get('year')}, Type: {t.get('thesis_type')}\n\n"
        return {"content": [{"type": "text", "text": text}]}

    async def _get_thesis_details_tool(self, args):
        thesis_id = args.get("thesis_id", "")
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

    # ─── YOK Fetch ───────────────────────────────────────────────────

    async def _fetch_with_cookies(self, url, method="GET", body=None, extra_headers=None):
        from js import fetch, Object
        from pyodide.ffi import to_js as _to_js

        def to_js(obj):
            return _to_js(obj, dict_converter=Object.fromEntries)

        init_opts = to_js({"method": "GET", "headers": BROWSER_HEADERS, "redirect": "manual"})
        init_resp = await fetch(SEARCH_URL, init_opts)

        cookies = ""
        try:
            raw_cookies = init_resp.headers.get("set-cookie")
            if raw_cookies:
                cookies = raw_cookies
        except Exception:
            pass

        headers = {**BROWSER_HEADERS}
        if cookies:
            headers["Cookie"] = cookies
        if extra_headers:
            headers.update(extra_headers)

        opts = {"method": method, "headers": headers}
        if body is not None:
            opts["body"] = body

        response = await fetch(url, to_js(opts))
        return await response.text()

    async def _search_yok(self, query, year_start=None, year_end=None, max_results=20):
        try:
            form_parts = [f"keyword={quote(str(query))}", "-find=Bul", "submitted=1"]
            if year_start:
                form_parts.append(f"yil1={year_start}")
            if year_end:
                form_parts.append(f"yil2={year_end}")

            html = await self._fetch_with_cookies(
                SEARCH_URL, method="POST", body="&".join(form_parts),
                extra_headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            return _parse_search_results(html, max_results)
        except Exception as e:
            return [{"error": str(e)}]

    async def _get_thesis_detail(self, thesis_id):
        try:
            html = await self._fetch_with_cookies(f"{DETAIL_URL}?id={thesis_id}")
            return _parse_thesis_detail(html, thesis_id)
        except Exception as e:
            return {"thesis_id": thesis_id, "title": "Detaylar yuklenemedi", "error": str(e)}


# ─── HTML Parsers ────────────────────────────────────────────────────

def _normalize(text):
    if not text:
        return ""
    return " ".join(text.strip().split())


def _parse_search_results(html, max_results=20):
    results = []
    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_="watable") or soup.find("table", class_="table-striped")
        if not table:
            return results
        tbody = table.find("tbody")
        if not tbody:
            return results
        for row in tbody.find_all("tr")[:max_results]:
            try:
                cells = row.find_all("td")
                if len(cells) < 6:
                    continue
                thesis_id = None
                span = cells[1].find("span")
                if span:
                    m = re.search(r"tezDetay\('(\d+)'\)", span.get("onclick", ""))
                    if m:
                        thesis_id = m.group(1)
                if not thesis_id:
                    thesis_id = _normalize(cells[1].get_text())
                results.append({
                    "thesis_id": thesis_id,
                    "author": _normalize(cells[2].get_text()),
                    "year": _normalize(cells[3].get_text()),
                    "title": _normalize(cells[4].get_text()),
                    "thesis_type": _normalize(cells[5].get_text()),
                })
            except Exception:
                continue
    return results


def _parse_thesis_detail(html, thesis_id):
    details = {
        "thesis_id": thesis_id, "title": None, "author": None, "advisor": None,
        "year": None, "university": None, "institute": None, "department": None,
        "thesis_type": None, "language": None, "page_count": None,
        "keywords": None, "abstract": None,
    }
    key_map = {
        "tez no": "thesis_id", "tez adı": "title", "tez adi": "title",
        "yazar": "author", "danışman": "advisor", "danisman": "advisor",
        "yıl": "year", "yil": "year", "üniversite": "university",
        "universite": "university", "enstitü": "institute", "enstitu": "institute",
        "anabilim dalı": "department", "anabilim dali": "department",
        "tez türü": "thesis_type", "tez turu": "thesis_type",
        "dil": "language", "sayfa sayısı": "page_count", "sayfa sayisi": "page_count",
        "anahtar kelimeler": "keywords",
    }
    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        dt = soup.find("table", {"class": "bilgi"}) or soup.find("div", {"id": "iceriktablo"})
        if dt:
            for row in dt.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    k = _normalize(cells[0].get_text()).rstrip(":").lower()
                    v = _normalize(cells[1].get_text())
                    ek = key_map.get(k)
                    if ek and ek in details:
                        details[ek] = v
        for sel in [{"class": "ozet"}, {"class": "abstract"}, {"id": "ozet"}]:
            elem = soup.find(["div", "p"], sel)
            if elem and len(elem.get_text().strip()) > 100:
                details["abstract"] = _normalize(elem.get_text())
                break
    return details
