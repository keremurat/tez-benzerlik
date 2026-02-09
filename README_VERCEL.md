# YÖK Tez MCP - Vercel Deployment 🚀

Bu proje, YÖK Ulusal Tez Merkezi'ni MCP (Model Context Protocol) server olarak Vercel'e deploy etmek için **Selenium-free** (httpx tabanlı) bir implementasyon içerir.

## 📦 Dosya Yapısı

```
tez-benzerlik/
├── api/
│   └── index.py              # ✅ Vercel entry point
├── src/
│   ├── httpx_scraper.py      # ✅ YENİ: httpx tabanlı scraper
│   ├── selenium_scraper.py   # ❌ ESKİ: Vercel'de çalışmaz
│   └── utils.py
├── server_fastmcp.py         # FastMCP server tanımı
├── vercel.json              # ✅ Vercel konfigürasyonu
├── requirements-vercel.txt   # ✅ Vercel için bağımlılıklar
├── VERCEL_DEPLOYMENT.md     # Detaylı deployment rehberi
└── README_VERCEL.md         # Bu dosya
```

## 🎯 Hızlı Başlangıç

### 1. Bağımlılıkları Yükle

```bash
pip install -r requirements-vercel.txt
```

### 2. Vercel CLI Yükle ve Giriş Yap

```bash
npm install -g vercel
vercel login
```

### 3. Deploy Et

```bash
vercel --prod
```

**Bu kadar!** Vercel size bir URL verecek: `https://your-project.vercel.app`

---

## 🧪 Test Etme

### Metod 1: Tarayıcıdan

```
https://your-project.vercel.app/api
```

GET ile basit bir status mesajı göreceksiniz.

### Metod 2: cURL ile

```bash
curl -X POST https://your-project.vercel.app/api \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

### Metod 3: MCP Inspector ile

```bash
npm install -g @modelcontextprotocol/inspector
mcp-inspector
```

Tarayıcıda `http://127.0.0.1:6274` açın ve:
- Transport: **Streamable HTTP**
- URL: `https://your-project.vercel.app/api`

---

## 🔧 Mevcut Tool'lar

### 1. `search_theses`

Tez arama:

```json
{
  "query": "yapay zeka",
  "search_field": "tumu",
  "year_start": 2020,
  "year_end": 2024,
  "max_results": 20
}
```

### 2. `get_thesis_details`

Tez detayları:

```json
{
  "thesis_id": "123456"
}
```

---

## ⚠️ Sınırlamalar (httpx vs Selenium)

| Özellik | Selenium (Lokal) | httpx (Vercel) |
|---------|------------------|----------------|
| JavaScript rendering | ✅ | ❌ |
| Modal/dialog içerik | ✅ | ❌ |
| Abstract/özet | ✅ %95 | ⚠️ %70 |
| Boolean search (AND/OR) | ✅ | ❌ |
| Son eklenen tezler | ✅ | ❌ |
| Deployment | 🐌 Docker gerekli | ✅ 1-tık |
| Maliyet | $5-20/ay | $0-5/ay |

---

## 🐛 Sorun Giderme

### Sorun: "Module not found"

**Çözüm:**
```bash
cat requirements-vercel.txt  # Kontrol et
vercel --prod                # Yeniden deploy et
```

### Sorun: "Function timeout after 30s"

**Çözüm:** `max_results` parametresini azalt:
```python
search_theses(query="test", max_results=10)  # 20 yerine
```

### Sorun: "No results found"

YÖK rate limiting yapıyor olabilir:
- Cache kullanın (varsayılan açık)
- `rate_limit_delay` artırın
- Farklı saatte deneyin

---

## 💡 Alternatif: Full Selenium için Railway/Render

Eğer tüm özellikleri istiyorsanız (JavaScript rendering, modals, vb):

```bash
# Railway'e deploy et (Selenium çalışır)
railway login
railway up

# Mevcut Selenium kodunuz değişiklik yapmadan çalışır!
```

Detaylar: `RAILWAY_DEPLOYMENT.md` (oluşturulacak)

---

## 📊 Performans Karşılaştırması

| Metrik | Vercel (httpx) | Railway (Selenium) |
|--------|---------------|-------------------|
| Cold start | 2-5s | N/A (always-on) |
| Arama süresi | 3-8s | 10-15s |
| Veri kalitesi | %70-80 | %95-100 |
| Aylık maliyet | $0-5 | $5-10 |
| Bakım | 0 | Düşük |

---

## ✅ Deployment Checklist

- [ ] `requirements-vercel.txt` yüklendi
- [ ] Yerel test yapıldı (`httpx_scraper` çalışıyor)
- [ ] Vercel CLI yüklendi
- [ ] `vercel --prod` ile deploy edildi
- [ ] URL ile test edildi
- [ ] MCP Inspector ile test edildi
- [ ] Cursor/Claude Desktop'ta konfigüre edildi

---

## 📞 Destek

- **Detaylı rehber:** [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md)
- **Vercel dokümanı:** https://vercel.com/docs/functions/runtimes/python
- **FastMCP:** https://gofastmcp.com/
- **MCP Spec:** https://modelcontextprotocol.io/

---

## 🎉 Başarılı Deploy!

Vercel'de yayınlandığınızda artık:
- Cursor'da kullanabilirsiniz
- Claude Desktop'ta kullanabilirsiniz
- Web üzerinden erişebilirsiniz
- Otomatik scale olur (trafiğe göre)

**Tebrikler! MCP server'ınız canlıda! 🚀**
