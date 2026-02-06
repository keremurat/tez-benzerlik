#!/bin/bash

echo "🔧 YÖK Tez MCP - Kurulum Scripti"
echo "=================================="
echo ""

# Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 bulunamadı. Lütfen Python 3.10+ yükleyin."
    exit 1
fi

echo "✅ Python bulundu: $(python3 --version)"

# pip kontrolü
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "❌ pip bulunamadı. Lütfen pip yükleyin."
    exit 1
fi

# pip komutunu belirle
if command -v pip3 &> /dev/null; then
    PIP=pip3
else
    PIP=pip
fi

echo "✅ pip bulundu"
echo ""

# Bağımlılıkları yükle
echo "📦 Bağımlılıklar yükleniyor..."
$PIP install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Kurulum tamamlandı!"
    echo ""
    echo "🚀 Sunucuları başlatmak için:"
    echo "   ./start_all.sh"
    echo ""
    echo "veya ayrı terminallerde:"
    echo "   Terminal 1: ./start_backend.sh"
    echo "   Terminal 2: ./start_frontend.sh"
else
    echo ""
    echo "❌ Kurulum başarısız oldu."
    echo "Manuel olarak deneyin: $PIP install -r requirements.txt"
fi
