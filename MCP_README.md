# YÖK Thesis Search MCP Server 🎓

[![MCP](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Search and retrieve thesis information from Turkey's National Thesis Center (YÖK Ulusal Tez Merkezi) using Claude and MCP.**

This MCP server provides seamless access to thousands of Turkish academic theses through Claude Desktop or any MCP-compatible client.

## 🌟 Features

- **🔍 Search Theses**: Search by keyword, author, advisor, or subject
- **📄 Get Details**: Retrieve full thesis metadata including abstracts and purpose statements
- **🔎 Advanced Search**: Multi-criteria search with boolean operators
- **📅 Recent Theses**: Get recently added theses from the last N days
- **🤖 Selenium-powered**: Bypasses bot protection using real browser automation

## 🛠️ Available Tools

### `search_theses`
Search for theses with various filters:
- **query** (required): Search term
- **search_field**: tez_adi (title), yazar (author), danisman (advisor), konu (subject), tumu (all)
- **year_start/year_end**: Filter by year range
- **thesis_type**: yuksek_lisans (masters), doktora (PhD), tipta_uzmanlik (medical), sanatta_yeterlik (art)
- **university**: Filter by university name
- **language**: Türkçe, İngilizce, etc.
- **max_results**: Number of results (1-100)

### `get_thesis_details`
Get comprehensive information about a thesis:
- **thesis_id** (required): The thesis ID number

Returns: Title, author, advisor, university, abstract, purpose, keywords, and more.

### `advanced_search`
Complex searches with up to 3 keywords and boolean operators (AND/OR/NOT).

### `get_recent_theses`
Get recently added theses:
- **days**: Number of days to look back (1-90)
- **limit**: Maximum results (1-200)

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/yok-tez-mcp.git
cd yok-tez-mcp

# Install dependencies
pip install -e .
```

### Usage with Claude Desktop

1. **Add to Claude Desktop configuration**:

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "yok-tez": {
      "command": "python",
      "args": ["/path/to/yok-tez-mcp/server.py"]
    }
  }
}
```

2. **Restart Claude Desktop**

3. **Start using**:

```
Search for theses about "yapay zeka" from 2023-2024

Get details for thesis 921717

Find recent theses about machine learning
```

### Usage with MCP Inspector (Testing)

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run the server
npx @modelcontextprotocol/inspector python server.py
```

## 📦 Smithery Deployment

This server is ready for deployment on Smithery:

```bash
# Deploy to Smithery
smithery deploy
```

The `smithery.json` configuration is included in the repository.

## 🔧 Development

### Requirements

- Python 3.10+
- Chrome/Chromium (for Selenium)
- ChromeDriver (automatically managed)

### Project Structure

```
yok-tez-mcp/
├── server.py              # MCP server entry point
├── src/
│   ├── selenium_scraper.py # YÖK scraper implementation
│   └── utils.py           # Utility functions
├── backend/               # FastAPI backend (optional)
├── frontend/              # Web frontend (optional)
├── pyproject.toml        # Project configuration
├── smithery.json         # Smithery deployment config
└── README.md             # This file
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/ server.py

# Lint
ruff check src/ server.py

# Type check
mypy src/ server.py
```

## 📖 Example Queries

### Search for AI-related theses
```
Search for theses about "yapay zeka" published between 2020 and 2024
```

### Get thesis details
```
Get full details for thesis ID 947598
```

### Advanced search
```
Find theses with "machine learning" in title AND "healthcare" in abstract,
from medical faculties, published after 2022
```

### Recent theses
```
Show me theses added in the last 30 days about deep learning
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This is an unofficial tool. Please respect YÖK's terms of service and use responsibly.

## 🙏 Acknowledgments

- [YÖK Ulusal Tez Merkezi](https://tez.yok.gov.tr) for providing thesis data
- [Anthropic](https://anthropic.com) for the MCP protocol
- All contributors to this project

---

Made with ❤️ for the Turkish academic community
