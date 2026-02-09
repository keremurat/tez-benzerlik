# YÖK Tez MCP Server - Vercel Deployment Guide

This guide explains how to deploy the YÖK Thesis MCP Server to Vercel using the httpx-based implementation (without Selenium).

## 🎯 What Changed

### ❌ Removed (Not Compatible with Vercel)
- **Selenium WebDriver** - Requires browser binaries (150MB+)
- **ChromeDriver** - Not available in serverless
- **JavaScript rendering** - Not supported in httpx mode
- **Modal interactions** - Requires browser automation

### ✅ Added (Vercel-Compatible)
- **httpx** - Pure Python HTTP client
- **FastMCP** - Streamable HTTP MCP server
- **Simplified scraping** - HTML parsing only
- **Serverless optimization** - 30s timeout limits

---

## 📋 Prerequisites

1. **Vercel Account** - Sign up at [vercel.com](https://vercel.com)
2. **Vercel CLI** - Install: `npm install -g vercel`
3. **Python 3.10+** - Required for FastMCP
4. **Git repository** - Push code to GitHub/GitLab

---

## 🚀 Deployment Steps

### Step 1: Install Dependencies

```bash
# Install Vercel-specific requirements
pip install -r requirements-vercel.txt
```

### Step 2: Test Locally (Optional)

```bash
# Test the httpx scraper
python -c "
import asyncio
from src.httpx_scraper import HttpxYOKScraper

async def test():
    scraper = HttpxYOKScraper()
    results = await scraper.search('yapay zeka', max_results=5)
    print(f'Found {len(results)} results')
    print(results[0] if results else 'No results')
    await scraper.close()

asyncio.run(test())
"
```

### Step 3: Login to Vercel

```bash
vercel login
```

### Step 4: Deploy to Vercel

```bash
# Deploy to production
vercel --prod

# Or deploy for testing first
vercel
```

Vercel will:
1. Detect `vercel.json` configuration
2. Build Python function from `api/index.py`
3. Install dependencies from `requirements-vercel.txt`
4. Deploy to a URL like `https://your-project.vercel.app`

---

## 🔧 Configuration

### Vercel Environment Variables (Optional)

You can set these in Vercel dashboard:

```bash
# Set via CLI
vercel env add RATE_LIMIT_DELAY production
# Enter value: 2.0

vercel env add CACHE_TTL production
# Enter value: 3600
```

### File Structure

```
tez-benzerlik/
├── api/
│   └── index.py           # Vercel serverless entry point
├── src/
│   ├── httpx_scraper.py   # New httpx-based scraper
│   ├── selenium_scraper.py # Old (not used on Vercel)
│   └── utils.py
├── server_fastmcp.py       # FastMCP server definition
├── vercel.json            # Vercel configuration
├── requirements-vercel.txt # Vercel dependencies
└── VERCEL_DEPLOYMENT.md   # This file
```

---

## 🧪 Testing the Deployed Server

### Method 1: MCP Inspector

1. Install MCP Inspector:
   ```bash
   npm install -g @modelcontextprotocol/inspector
   ```

2. Run inspector:
   ```bash
   mcp-inspector
   ```

3. Open `http://127.0.0.1:6274`

4. Connect to your Vercel server:
   - Transport: **Streamable HTTP**
   - URL: `https://your-project.vercel.app/api`

5. Click "Connect" and test tools

### Method 2: cURL

```bash
# Health check
curl https://your-project.vercel.app/api

# Test MCP endpoint (requires proper MCP protocol headers)
curl -X POST https://your-project.vercel.app/api \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### Method 3: Configure in Cursor/Claude Desktop

Add to `.cursor/mcp.json` or Claude Desktop config:

```json
{
  "mcpServers": {
    "yok-tez": {
      "url": "https://your-project.vercel.app/api"
    }
  }
}
```

---

## ⚠️ Known Limitations

### 1. **No JavaScript Rendering**
   - **Impact:** Some thesis details may be incomplete
   - **Workaround:** Basic info (title, author, year) still available

### 2. **No Modal Interactions**
   - **Impact:** Abstract/purpose fields may be empty
   - **Workaround:** Direct detail page parsing (limited)

### 3. **Simplified Advanced Search**
   - **Impact:** Boolean operators (AND/OR/NOT) don't work
   - **Workaround:** Use basic search with filters

### 4. **Recent Theses Feature Disabled**
   - **Impact:** `get_recent_theses` returns empty
   - **Workaround:** Use `search_theses` with year filters

### 5. **30-Second Timeout**
   - **Impact:** Large searches may timeout
   - **Workaround:** Reduce `max_results` parameter

---

## 🐛 Troubleshooting

### Error: "Module not found"

```bash
# Make sure requirements-vercel.txt is complete
vercel env ls
# Check if dependencies are listed
```

### Error: "Function timeout"

Reduce search scope:
```python
# Instead of:
search_theses(query="test", max_results=100)

# Use:
search_theses(query="test", max_results=20)
```

### Error: "No results found"

The httpx scraper may be blocked by YÖK's rate limiting:
- Add delays between requests
- Use caching (enabled by default)
- Consider using search on off-peak hours

---

## 📊 Performance Expectations

| Metric | Vercel (httpx) | Local (Selenium) |
|--------|---------------|------------------|
| Cold start | 2-5s | N/A |
| Search request | 3-8s | 10-15s |
| Detail request | 2-5s | 8-12s |
| Results quality | 70-80% | 95-100% |
| Cost | $0-20/month | $0 (self-host) |

---

## 🔄 Updating the Deployment

```bash
# Make changes to code
git add .
git commit -m "Update MCP server"
git push

# Redeploy
vercel --prod
```

Vercel will automatically rebuild and deploy.

---

## 💡 Alternative: Use Railway/Render Instead

If you need full Selenium support, consider Railway or Render:

```bash
# Railway deployment (keeps Selenium)
railway login
railway init
railway up

# Your Selenium code works unchanged!
```

See `RAILWAY_DEPLOYMENT.md` for full guide (if you want to switch).

---

## 📞 Support

- **Vercel Docs:** https://vercel.com/docs/functions/runtimes/python
- **FastMCP Docs:** https://gofastmcp.com/
- **httpx Docs:** https://www.python-httpx.org/

---

## ✅ Checklist

- [ ] Installed `requirements-vercel.txt`
- [ ] Tested locally with httpx scraper
- [ ] Logged in to Vercel CLI
- [ ] Deployed with `vercel --prod`
- [ ] Tested with MCP Inspector
- [ ] Configured in Cursor/Claude Desktop
- [ ] Verified search functionality
- [ ] Checked Vercel logs for errors

**Congratulations! Your MCP server is live on Vercel! 🎉**
