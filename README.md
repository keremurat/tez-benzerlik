# YÖK Ulusal Tez Merkezi MCP Sunucusu

[English](#english) | [Türkçe](#türkçe)

---

## Türkçe

YÖK Ulusal Tez Merkezi için Model Context Protocol (MCP) sunucusu. Claude Desktop ve diğer MCP uyumlu AI asistanlarıyla YÖK Tez Merkezi'nde tez arama ve bilgi alma işlemlerini kolaylaştırır.

**🌟 YENİ: Web Arayüzü!** Modern, responsive web arayüzü ile doğrudan tarayıcıdan tez arama yapabilirsiniz. [Web Arayüzü Dokümantasyonu](WEB_README.md)

### 🎯 İki Kullanım Şekli

1. **MCP Sunucusu**: Claude Desktop ile entegre kullanım
2. **Web Arayüzü**: Tarayıcıdan modern arayüz ile kullanım

### 📋 Özellikler

- **🔍 Gelişmiş Tez Arama**: Başlık, yazar, danışman, konu bazlı arama
- **📚 Detaylı Tez Bilgileri**: Özet, anahtar kelimeler, danışman bilgileri
- **🆕 Son Eklenen Tezler**: Güncel tez takibi
- **📊 İstatistiksel Analiz**: Üniversite, yıl, tez türü bazlı istatistikler
- **⚡ Hızlı ve Güvenli**: Rate limiting, caching, retry logic
- **🇹🇷 Türkçe Karakter Desteği**: Tam UTF-8 desteği
- **🌐 Web Arayüzü**: Modern, responsive frontend (YENİ!)

---

## 🌐 Web Arayüzü (Hızlı Başlangıç)

Modern web arayüzü ile tarayıcıdan direkt kullanım!

### Başlatma (3 Adım)

```bash
# 1. Bağımlılıkları yükle
pip install -r requirements.txt

# 2. Sunucuları başlat (otomatik)
./start_all.sh

# 3. Tarayıcıda aç
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

**Detaylı bilgi için:** [WEB_README.md](WEB_README.md)

### Ekran Görüntüleri

- ✨ Modern, responsive tasarım
- 🔍 Gelişmiş arama filtreleri
- 📊 Görsel istatistikler
- 📱 Mobil uyumlu

---

## 🤖 MCP Sunucusu Kullanımı

### 🛠️ Kurulum

#### Gereksinimler

- Python 3.10 veya üzeri
- pip (Python paket yöneticisi)

#### Adım 1: Depoyu Klonlayın

```bash
git clone https://github.com/yourusername/yok-tez-mcp.git
cd yok-tez-mcp
```

#### Adım 2: Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

veya development bağımlılıklarıyla:

```bash
pip install -e ".[dev]"
```

#### Adım 3: Sunucuyu Test Edin

```bash
python -m src.server
```

Sunucu başarıyla başlarsa, stdin/stdout üzerinden MCP protokolü ile iletişime hazırdır.

### 🔌 Claude Desktop ile Entegrasyon

Claude Desktop'ın MCP sunucularını kullanabilmesi için yapılandırma dosyasını düzenlemeniz gerekir.

#### macOS/Linux

`~/.config/claude/claude_desktop_config.json` dosyasını oluşturun veya düzenleyin:

```json
{
  "mcpServers": {
    "yok-tez": {
      "command": "python",
      "args": [
        "-m",
        "src.server"
      ],
      "cwd": "/tam/yol/yok-tez-mcp",
      "env": {}
    }
  }
}
```

#### Windows

`%APPDATA%\Claude\claude_desktop_config.json` dosyasını düzenleyin:

```json
{
  "mcpServers": {
    "yok-tez": {
      "command": "python",
      "args": [
        "-m",
        "src.server"
      ],
      "cwd": "C:\\tam\\yol\\yok-tez-mcp",
      "env": {}
    }
  }
}
```

**Önemli**: `cwd` alanındaki yolu projenizin gerçek konumuna göre güncelleyin.

#### Yapılandırmayı Doğrulama

1. Claude Desktop'ı yeniden başlatın
2. Ayarlar > Developer > MCP Servers bölümüne gidin
3. "yok-tez" sunucusunun listelendiğini ve "Connected" durumunda olduğunu doğrulayın

### 🚀 Kullanım

Claude Desktop'ta entegrasyon tamamlandıktan sonra, Claude'a doğrudan tez aramayla ilgili isteklerde bulunabilirsiniz.

#### Örnek 1: Temel Tez Arama

```
Yapay zeka konusunda 2023 yılında yapılan doktora tezlerini bul.
```

Claude, `search_thesis` aracını kullanarak YÖK veritabanında arama yapacaktır:

```
Query: "yapay zeka"
Search field: "konu"
Year: 2023
Thesis type: "doktora"
```

#### Örnek 2: Belirli Üniversitede Arama

```
İstanbul Üniversitesi'nde makine öğrenmesi alanında yapılan yüksek lisans tezlerini listele.
```

#### Örnek 3: Tez Detaylarını Getirme

```
Tez numarası 654321 olan tezin detaylarını göster.
```

Claude, `get_thesis_details` aracını kullanarak tezin tam bilgilerini getirecektir.

#### Örnek 4: Son Eklenen Tezler

```
Son 15 günde YÖK'e eklenen tezleri göster.
```

#### Örnek 5: İstatistik Analizi

```
Boğaziçi Üniversitesi'nde 2022 yılında yapılan tezlerin istatistiklerini çıkar.
```

### 🔧 Araçlar (Tools)

MCP sunucusu aşağıdaki araçları sağlar:

#### 1. `search_thesis`

Tez arama işlemi gerçekleştirir.

**Parametreler:**

- `query` (zorunlu): Arama terimi
- `search_field` (opsiyonel): Arama alanı (`tez_adi`, `yazar`, `danisman`, `konu`, `tumu`)
- `year_start` (opsiyonel): Başlangıç yılı
- `year_end` (opsiyonel): Bitiş yılı
- `thesis_type` (opsiyonel): Tez türü (`yuksek_lisans`, `doktora`, `tipta_uzmanlik`, `sanatta_yeterlik`)
- `university` (opsiyonel): Üniversite adı
- `language` (opsiyonel): Tez dili (`tr`, `en`, vb.)
- `permission_status` (opsiyonel): İzin durumu (`izinli`, `izinsiz`)
- `max_results` (opsiyonel): Maksimum sonuç sayısı (varsayılan: 20)

**Örnek Çıktı:**

```
Found 15 thesis(es) for 'yapay zeka':
================================================================================

1. Derin Öğrenme Yöntemleriyle Görüntü Sınıflandırma
   Author: Ahmet Yılmaz
   University: İstanbul Teknik Üniversitesi
   Year: 2023
   Type: Doktora
   ID: 123456

2. Yapay Sinir Ağları ile Metin Madenciliği
   Author: Ayşe Kaya
   University: Boğaziçi Üniversitesi
   Year: 2023
   Type: Yüksek Lisans
   ID: 123457
...
```

#### 2. `get_thesis_details`

Belirli bir tezin detaylı bilgilerini getirir.

**Parametreler:**

- `thesis_id` (zorunlu): Tez numarası

**Örnek Çıktı:**

```
Thesis Details (ID: 123456)
================================================================================

Title: Derin Öğrenme Yöntemleriyle Görüntü Sınıflandırma
Author: Ahmet Yılmaz
Advisor: Prof. Dr. Mehmet Demir
Year: 2023
University: İstanbul Teknik Üniversitesi
Institute: Fen Bilimleri Enstitüsü
Department: Bilgisayar Mühendisliği
Thesis Type: Doktora
Language: Türkçe
Page Count: 180
Keywords: derin öğrenme, görüntü işleme, yapay zeka

Abstract:
----------------------------------------
Bu tez çalışmasında, derin öğrenme yöntemlerinin görüntü sınıflandırma
problemlerindeki etkinliği araştırılmıştır...
```

#### 3. `get_recent_thesis`

Son eklenen tezleri listeler.

**Parametreler:**

- `days` (opsiyonel): Kaç günlük tezler (varsayılan: 15)
- `limit` (opsiyonel): Maksimum sonuç sayısı (varsayılan: 50)

#### 4. `get_thesis_statistics`

Belirli kriterlere göre tez istatistikleri hesaplar.

**Parametreler:**

- `university` (opsiyonel): Üniversite filtresi
- `year` (opsiyonel): Yıl filtresi
- `thesis_type` (opsiyonel): Tez türü filtresi

**Örnek Çıktı:**

```
Thesis Statistics
================================================================================

Filters Applied:
  - University: İstanbul Üniversitesi
  - Year: 2023

Total Theses: 250

By Thesis Type:
  - Yüksek Lisans: 180
  - Doktora: 70

By Language:
  - Türkçe: 200
  - İngilizce: 50
```

### 🧪 Test Etme

Testleri çalıştırmak için:

```bash
# Tüm testleri çalıştır
pytest

# Kapsamlı test raporu
pytest --cov=src --cov-report=html

# Sadece unit testleri (integration testleri hariç)
pytest -m "not integration"

# Integration testlerini de dahil et (gerçek YÖK istekleri yapar)
pytest -m integration
```

**Not**: Integration testleri gerçek HTTP istekleri yapar ve YÖK sunucularına yük bindirebilir. CI/CD'de çalıştırırken `-m "not integration"` kullanın.

### 📊 Loglama

Sunucu, tüm işlemleri `yok_tez_mcp.log` dosyasına kaydeder. Log seviyelerini kontrol etmek için:

```python
# src/utils.py içinde
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    ...
)
```

### ⚠️ Önemli Notlar

1. **Rate Limiting**: Sunucu, YÖK sunucularına aşırı yük bindirmemek için istekler arasında 1.5 saniye bekler.

2. **Caching**: Sonuçlar varsayılan olarak 1 saat boyunca önbelleğe alınır. Bu, tekrarlanan sorgularda hızlı yanıt sağlar ve YÖK'e gereksiz yük bindirmez.

3. **Etik Kullanım**: YÖK Ulusal Tez Merkezi resmi bir kamu sitesidir. Lütfen sorumlu kullanım ilkelerine uyun:
   - Aşırı sayıda istek göndermeyin
   - Rate limiting ayarlarını değiştirmeyin
   - Sunucuyu yalnızca araştırma amaçlı kullanın

4. **robots.txt**: YÖK'ün robots.txt politikasına uyum sağlanmıştır.

### 🐛 Sorun Giderme

#### Sunucu Başlamıyor

```bash
# Python sürümünü kontrol edin
python --version  # 3.10+ olmalı

# Bağımlılıkları yeniden yükleyin
pip install --upgrade -r requirements.txt

# Loglara bakın
cat yok_tez_mcp.log
```

#### Claude Desktop Sunucuya Bağlanamıyor

1. `claude_desktop_config.json` dosyasındaki `cwd` yolunun doğru olduğundan emin olun
2. Python'un PATH'te olduğunu doğrulayın: `which python` (Linux/macOS) veya `where python` (Windows)
3. Claude Desktop'ı yeniden başlatın
4. Developer Console'dan (Claude Desktop > View > Toggle Developer Tools) hata loglarını kontrol edin

#### Arama Sonuç Döndürmüyor

- YÖK sitesinin erişilebilir olduğunu kontrol edin: https://tez.yok.gov.tr
- Arama kriterlerinizi genişletin (örn. yıl filtresi kaldırın)
- Loglarda ağ hatası olup olmadığına bakın

#### Encoding Hataları (Türkçe Karakterler)

Genellikle UTF-8 encoding sorunudur. Kodda zaten UTF-8 zorlaması var, ancak sorun devam ederse:

```python
# Terminal encoding'ini kontrol edin
import sys
print(sys.stdout.encoding)  # UTF-8 olmalı
```

### 🤝 Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen:

1. Repo'yu fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

### 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakın.

### 🔗 Bağlantılar

- [YÖK Ulusal Tez Merkezi](https://tez.yok.gov.tr/UlusalTezMerkezi/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai/desktop)

### 📧 İletişim

Sorularınız için GitHub Issues kullanın.

---

## English

MCP Server for YÖK National Thesis Center. Enables thesis search and information retrieval from Turkish Higher Education Council's database through Claude Desktop and other MCP-compatible AI assistants.

### 📋 Features

- **🔍 Advanced Thesis Search**: Search by title, author, advisor, subject
- **📚 Detailed Thesis Information**: Abstracts, keywords, advisor details
- **🆕 Recent Additions**: Track newly added theses
- **📊 Statistical Analysis**: Statistics by university, year, thesis type
- **⚡ Fast and Secure**: Rate limiting, caching, retry logic
- **🇹🇷 Turkish Character Support**: Full UTF-8 support

### 🛠️ Installation

#### Requirements

- Python 3.10 or higher
- pip (Python package manager)

#### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/yok-tez-mcp.git
cd yok-tez-mcp
```

#### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Or with development dependencies:

```bash
pip install -e ".[dev]"
```

#### Step 3: Test the Server

```bash
python -m src.server
```

If successful, the server is ready to communicate via MCP protocol over stdin/stdout.

### 🔌 Integration with Claude Desktop

To use MCP servers with Claude Desktop, you need to edit the configuration file.

#### macOS/Linux

Create or edit `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "yok-tez": {
      "command": "python",
      "args": [
        "-m",
        "src.server"
      ],
      "cwd": "/full/path/to/yok-tez-mcp",
      "env": {}
    }
  }
}
```

#### Windows

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "yok-tez": {
      "command": "python",
      "args": [
        "-m",
        "src.server"
      ],
      "cwd": "C:\\full\\path\\to\\yok-tez-mcp",
      "env": {}
    }
  }
}
```

**Important**: Update the `cwd` path to match your actual project location.

#### Verify Configuration

1. Restart Claude Desktop
2. Go to Settings > Developer > MCP Servers
3. Verify that "yok-tez" server is listed and shows "Connected" status

### 🚀 Usage

Once integrated with Claude Desktop, you can make natural language requests about Turkish theses.

#### Example 1: Basic Thesis Search

```
Find PhD theses about artificial intelligence from 2023.
```

Claude will use the `search_thesis` tool to query YÖK database:

```
Query: "artificial intelligence"
Year: 2023
Thesis type: "doktora" (PhD)
```

#### Example 2: University-Specific Search

```
List master's theses about machine learning from Istanbul University.
```

#### Example 3: Get Thesis Details

```
Show details for thesis ID 654321.
```

Claude will use `get_thesis_details` to fetch comprehensive information.

#### Example 4: Recent Additions

```
Show theses added to YÖK in the last 15 days.
```

#### Example 5: Statistical Analysis

```
Get statistics for theses from Boğaziçi University in 2022.
```

### 🔧 Tools

The MCP server provides the following tools:

#### 1. `search_thesis`

Search for theses in the YÖK database.

**Parameters:**

- `query` (required): Search term
- `search_field` (optional): Search field (`tez_adi`, `yazar`, `danisman`, `konu`, `tumu`)
- `year_start` (optional): Start year
- `year_end` (optional): End year
- `thesis_type` (optional): Thesis type (`yuksek_lisans`, `doktora`, `tipta_uzmanlik`, `sanatta_yeterlik`)
- `university` (optional): University name
- `language` (optional): Thesis language (`tr`, `en`, etc.)
- `permission_status` (optional): Permission status (`izinli`, `izinsiz`)
- `max_results` (optional): Maximum results (default: 20)

#### 2. `get_thesis_details`

Get detailed information about a specific thesis.

**Parameters:**

- `thesis_id` (required): Thesis ID number

#### 3. `get_recent_thesis`

List recently added theses.

**Parameters:**

- `days` (optional): Number of days to look back (default: 15)
- `limit` (optional): Maximum results (default: 50)

#### 4. `get_thesis_statistics`

Calculate thesis statistics based on filters.

**Parameters:**

- `university` (optional): University filter
- `year` (optional): Year filter
- `thesis_type` (optional): Thesis type filter

### 🧪 Testing

Run tests:

```bash
# Run all tests
pytest

# Coverage report
pytest --cov=src --cov-report=html

# Unit tests only (exclude integration tests)
pytest -m "not integration"

# Include integration tests (makes real YÖK requests)
pytest -m integration
```

**Note**: Integration tests make real HTTP requests. Use `-m "not integration"` in CI/CD.

### 📊 Logging

The server logs all operations to `yok_tez_mcp.log`. Control log levels in:

```python
# In src/utils.py
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    ...
)
```

### ⚠️ Important Notes

1. **Rate Limiting**: The server waits 1.5 seconds between requests to avoid overwhelming YÖK servers.

2. **Caching**: Results are cached for 1 hour by default for faster responses and reduced load.

3. **Ethical Use**: YÖK National Thesis Center is an official public service. Please use responsibly:
   - Don't send excessive requests
   - Don't modify rate limiting settings
   - Use only for research purposes

4. **robots.txt**: The scraper complies with YÖK's robots.txt policy.

### 🐛 Troubleshooting

See the Turkish section above for detailed troubleshooting steps.

### 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

### 📝 License

This project is licensed under the MIT License.

### 🔗 Links

- [YÖK National Thesis Center](https://tez.yok.gov.tr/UlusalTezMerkezi/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai/desktop)

### 📧 Contact

Use GitHub Issues for questions and support.
