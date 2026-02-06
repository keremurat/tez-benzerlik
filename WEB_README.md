# YÖK Tez Web Arayüzü

Modern, responsive web arayüzü ile YÖK Ulusal Tez Merkezi'nde tez arama.

## 🌟 Özellikler

### Frontend
- ✨ Modern, responsive tasarım (Tailwind CSS)
- 🔍 Gelişmiş arama ve filtreleme
- 📱 Mobil uyumlu
- 🎨 Güzel kullanıcı arayüzü
- ⚡ Hızlı ve akıcı
- 🎯 Kolay kullanım

### Backend
- 🚀 FastAPI ile yüksek performanslı API
- 📚 RESTful endpoint'ler
- 🔄 Otomatik API dokümantasyonu (Swagger)
- ⚡ Async/await desteği
- 🛡️ CORS desteği
- 📊 Hata yönetimi

## 📁 Proje Yapısı

```
├── backend/
│   ├── __init__.py
│   └── api.py              # FastAPI backend server
├── frontend/
│   ├── index.html          # Ana sayfa
│   └── app.js             # JavaScript logic
├── start_backend.sh        # Backend başlatma script'i
├── start_frontend.sh       # Frontend başlatma script'i
└── start_all.sh           # Her ikisini birden başlat
```

## 🚀 Hızlı Başlangıç

### Adım 1: Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### Adım 2: Sunucuları Başlatın

#### Otomatik (Her İkisi Birden)
```bash
./start_all.sh
```

#### Manuel (Ayrı Terminallerde)

**Terminal 1 - Backend:**
```bash
./start_backend.sh
```

**Terminal 2 - Frontend:**
```bash
./start_frontend.sh
```

### Adım 3: Tarayıcıda Açın

Frontend: http://localhost:3000
Backend API: http://localhost:8000
API Docs: http://localhost:8000/docs

## 📖 Kullanım

### 1. Temel Arama

1. Ana sayfayı açın (http://localhost:3000)
2. Arama kutusuna terimi girin (örn: "yapay zeka")
3. "Ara" butonuna tıklayın
4. Sonuçları görüntüleyin

### 2. Gelişmiş Filtreleme

1. "Gelişmiş Filtreler" butonuna tıklayın
2. İstediğiniz filtreleri seçin:
   - Arama alanı (tez adı, yazar, danışman, vb.)
   - Yıl aralığı
   - Tez türü (Yüksek Lisans, Doktora, vb.)
   - Üniversite
   - Dil
   - İzin durumu
3. "Ara" butonuna tıklayın

### 3. Tez Detaylarını Görme

1. Arama sonuçlarında bir teze tıklayın
2. Modal pencerede detaylı bilgileri görün:
   - Başlık, yazar, danışman
   - Üniversite, enstitü, bölüm
   - Özet ve anahtar kelimeler
   - Diğer metadata

### 4. Son Eklenen Tezler

1. Ana sayfadaki "Son Eklenenler" kartına tıklayın
2. Son 15 günde eklenen tezleri görün

### 5. İstatistikler

1. "İstatistikler" kartına tıklayın
2. Tez istatistiklerini görüntüleyin:
   - Toplam tez sayısı
   - Tür bazında dağılım
   - Yıl bazında dağılım
   - Dil bazında dağılım

### 6. Popüler Üniversiteler

1. Hızlı arama için üniversite butonlarına tıklayın
2. İstanbul Üniversitesi, Boğaziçi, ODTÜ, vb.

## 🔌 API Endpoints

### GET `/`
API bilgisi ve endpoint listesi

### GET `/health`
Sağlık kontrolü

### POST `/api/search`
Tez arama

**Request Body:**
```json
{
  "query": "yapay zeka",
  "search_field": "tumu",
  "year_start": 2020,
  "year_end": 2024,
  "thesis_type": "doktora",
  "max_results": 20
}
```

### GET `/api/search?query=...`
Tez arama (GET method)

### GET `/api/thesis/{thesis_id}`
Tez detayları

### GET `/api/recent?days=15&limit=50`
Son eklenen tezler

### GET `/api/statistics?university=...&year=...`
İstatistikler

## 🛠️ Geliştirme

### Backend Geliştirme

Backend kodu: `backend/api.py`

Değişiklikleri yaptıktan sonra, uvicorn otomatik olarak reload eder (--reload flag sayesinde).

```bash
cd backend
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Geliştirme

Frontend dosyaları:
- `frontend/index.html` - HTML yapısı
- `frontend/app.js` - JavaScript logic

Değişiklikler anında tarayıcıda görünür (F5 ile refresh).

### API Dokümantasyonu

FastAPI otomatik olarak Swagger UI sağlar:
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/redoc - ReDoc

## 🎨 Özelleştirme

### Tailwind CSS

Frontend Tailwind CSS kullanır. Stilleri değiştirmek için:

1. `index.html` içindeki Tailwind sınıflarını düzenleyin
2. Özel stiller için `<style>` bloğuna ekleyin

### API Base URL

Frontend'in API'ye bağlanması için `frontend/app.js` içinde:

```javascript
const API_BASE_URL = 'http://localhost:8000';
```

Production için bunu değiştirin.

## 🐛 Sorun Giderme

### Backend Başlamıyor

```bash
# Python ve pip sürümlerini kontrol edin
python --version
pip --version

# Bağımlılıkları yeniden yükleyin
pip install --upgrade -r requirements.txt

# Manuel başlatma
cd backend
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

### CORS Hatası

Backend'de CORS ayarları zaten yapılmıştır. Eğer hala sorun varsa:

`backend/api.py` içinde:
```python
allow_origins=["*"]  # Geliştirme için tüm origin'ler
# Production'da: allow_origins=["https://yourdomain.com"]
```

### Frontend API'ye Bağlanamıyor

1. Backend'in çalıştığından emin olun: http://localhost:8000/health
2. Console'da hata kontrolü yapın (F12)
3. `app.js` içindeki `API_BASE_URL`'i kontrol edin

### Port Zaten Kullanımda

Backend için farklı port:
```bash
cd backend
python -m uvicorn api:app --host 0.0.0.0 --port 8001
```

Frontend için farklı port:
```bash
cd frontend
python3 -m http.server 3001
```

## 📦 Production Deployment

### Option 1: Docker (Önerilen)

Docker compose file'ı oluşturun:

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1

  frontend:
    image: nginx:alpine
    volumes:
      - ./frontend:/usr/share/nginx/html
    ports:
      - "80:80"
```

### Option 2: Systemd Service

Backend için systemd service:

```ini
[Unit]
Description=YÖK Tez API
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/yok-tez-mcp/backend
ExecStart=/path/to/venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Option 3: Nginx + Gunicorn

```bash
# Gunicorn ile backend
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.api:app

# Nginx ile frontend serve
# nginx.conf'a frontend path'i ekleyin
```

## 🔒 Güvenlik

Production'da:

1. ✅ CORS'u spesifik domain'lere kısıtlayın
2. ✅ HTTPS kullanın
3. ✅ Rate limiting ekleyin
4. ✅ API key/token authentication ekleyin
5. ✅ Input validation güçlendirin

## 📊 Performans

- Backend caching (1 saat TTL)
- Rate limiting (1.5s/request)
- Async operations
- Connection pooling

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun
3. Commit yapın
4. Pull request gönderin

## 📝 Lisans

MIT License - Detaylar için `LICENSE` dosyasına bakın.

## 📧 Destek

Sorunlar için GitHub Issues kullanın.

---

## 🎉 Hazır!

Artık modern bir web arayüzü ile YÖK Tez Merkezi'nde arama yapabilirsiniz!

**Backend:** http://localhost:8000
**Frontend:** http://localhost:3000
**API Docs:** http://localhost:8000/docs
