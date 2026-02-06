"""
Mock data for Medical AI Demo (Tıp + Yapay Zeka + 2020-2023)

DEMO KRİTERLERİ:
- Alan (Bölüm): Tıp
- Araştırma Konusu: Yapay Zeka
- Yıl Aralığı: 2020-2023
"""

MOCK_SEARCH_RESULTS = [
    {
        "thesis_id": "734521",
        "title": "Derin Öğrenme Yöntemleri ile Radyolojik Görüntülerin Analizi ve Hastalık Teşhisi",
        "author": "Dr. Ayşe Yılmaz",
        "year": 2023,
        "university": "Hacettepe Üniversitesi",
        "thesis_type": "Tıpta Uzmanlık",
        "language": "Türkçe",
        "department": "Tıp",
        "field": "Radyoloji"
    },
    {
        "thesis_id": "691203",
        "title": "Yapay Zeka Destekli Tanı Sistemlerinin Kardiyovasküler Hastalıklarda Erken Teşhise Etkisi",
        "author": "Dr. Mehmet Öztürk",
        "year": 2023,
        "university": "İstanbul Üniversitesi Cerrahpaşa Tıp Fakültesi",
        "thesis_type": "Tıpta Uzmanlık",
        "language": "Türkçe",
        "department": "Tıp",
        "field": "Kardiyoloji"
    },
    {
        "thesis_id": "658947",
        "title": "Makine Öğrenmesi Algoritmaları ile Kanser Hücrelerinin Erken Tespiti: Patoloji Görüntüleri Üzerine Bir Çalışma",
        "author": "Dr. Zeynep Kaya",
        "year": 2022,
        "university": "Ankara Üniversitesi Tıp Fakültesi",
        "thesis_type": "Tıpta Uzmanlık",
        "language": "Türkçe",
        "department": "Tıp",
        "field": "Patoloji"
    },
    {
        "thesis_id": "627815",
        "title": "Artifical Intelligence-Based Prediction Models for Diabetes Mellitus Complications",
        "author": "Dr. Ahmet Demir",
        "year": 2022,
        "university": "Ege Üniversitesi Tıp Fakültesi",
        "thesis_type": "Tıpta Uzmanlık",
        "language": "İngilizce",
        "department": "Tıp",
        "field": "Endokrinoloji"
    },
    {
        "thesis_id": "596432",
        "title": "Derin Sinir Ağları Kullanılarak MR Görüntülerinden Beyin Tümörlerinin Segmentasyonu ve Sınıflandırılması",
        "author": "Dr. Can Arslan",
        "year": 2021,
        "university": "Dokuz Eylül Üniversitesi Tıp Fakültesi",
        "thesis_type": "Tıpta Uzmanlık",
        "language": "Türkçe",
        "department": "Tıp",
        "field": "Radyoloji"
    },
    {
        "thesis_id": "571298",
        "title": "Yapay Zeka ve Doğal Dil İşleme Tekniklerinin Klinik Karar Destek Sistemlerinde Kullanımı",
        "author": "Dr. Elif Şahin",
        "year": 2021,
        "university": "Gazi Üniversitesi Tıp Fakültesi",
        "thesis_type": "Tıpta Uzmanlık",
        "language": "Türkçe",
        "department": "Tıp",
        "field": "Tıp Bilişimi"
    },
    {
        "thesis_id": "543876",
        "title": "Convolutional Neural Networks for Early Detection of Alzheimer's Disease from Brain MRI Scans",
        "author": "Dr. Deniz Yıldız",
        "year": 2021,
        "university": "Boğaziçi Üniversitesi",
        "thesis_type": "Doktora",
        "language": "İngilizce",
        "department": "Tıp",
        "field": "Nöroloji"
    },
    {
        "thesis_id": "518743",
        "title": "Akciğer Grafilerinde Pnömoni Tespiti için Derin Öğrenme Tabanlı Otomatik Tanı Sistemi",
        "author": "Dr. Mustafa Çelik",
        "year": 2020,
        "university": "İstanbul Tıp Fakültesi",
        "thesis_type": "Tıpta Uzmanlık",
        "language": "Türkçe",
        "department": "Tıp",
        "field": "Göğüs Hastalıkları"
    },
    {
        "thesis_id": "492165",
        "title": "Yapay Zeka Destekli Dermoskopi Görüntü Analizi ile Melanom Erken Tanısı",
        "author": "Dr. Selin Aydın",
        "year": 2020,
        "university": "Marmara Üniversitesi Tıp Fakültesi",
        "thesis_type": "Tıpta Uzmanlık",
        "language": "Türkçe",
        "department": "Tıp",
        "field": "Dermatoloji"
    },
    {
        "thesis_id": "467832",
        "title": "Machine Learning Approaches for Predicting Patient Outcomes in Intensive Care Units",
        "author": "Dr. Emre Koç",
        "year": 2020,
        "university": "Hacettepe Üniversitesi",
        "thesis_type": "Doktora",
        "language": "İngilizce",
        "department": "Tıp",
        "field": "Yoğun Bakım"
    }
]

# Detaylı tez bilgileri - ilk tez için
MOCK_THESIS_DETAILS = {
    "thesis_id": "734521",
    "title": "Derin Öğrenme Yöntemleri ile Radyolojik Görüntülerin Analizi ve Hastalık Teşhisi",
    "author": "Dr. Ayşe Yılmaz",
    "advisor": "Prof. Dr. Mehmet Özcan",
    "co_advisor": "Doç. Dr. Ahmet Kılıç",
    "year": "2023",
    "university": "Hacettepe Üniversitesi",
    "institute": "Tıp Fakültesi",
    "department": "Radyoloji Anabilim Dalı",
    "thesis_type": "Tıpta Uzmanlık",
    "language": "Türkçe",
    "page_count": "142",
    "keywords": "yapay zeka, derin öğrenme, radyoloji, medikal görüntü analizi, hastalık teşhisi, CNN, tıbbi tanı",
    "abstract": """
Amaç: Bu çalışmanın amacı, derin öğrenme yöntemlerini kullanarak radyolojik görüntülerin
otomatik analizini gerçekleştiren ve hastalık teşhisinde hekimlere destek olan bir yapay
zeka sistemi geliştirmektir.

Gereç ve Yöntem: Çalışmada, 2018-2022 yılları arasında Hacettepe Üniversitesi Tıp Fakültesi
Radyoloji Bölümü'ne başvuran 5.847 hastanın 12.394 adet göğüs röntgeni görüntüsü kullanılmıştır.
Convolutional Neural Network (CNN) mimarisi temel alınarak özel bir derin öğrenme modeli
geliştirilmiştir. Model, pnömoni, tüberküloz, COVID-19 ve akciğer kanseri tespiti için
eğitilmiştir.

Bulgular: Geliştirilen sistem, pnömoni tespitinde %94.7, tüberküloz tespitinde %92.3,
COVID-19 tespitinde %96.1 ve akciğer kanseri tespitinde %89.4 doğruluk oranı elde etmiştir.
Sistemin hassasiyeti (sensitivity) %91.2, özgüllüğü (specificity) %93.8 olarak bulunmuştur.

Sonuç: Derin öğrenme tabanlı yapay zeka sistemleri, radyolojik görüntülerin analizinde
yüksek doğruluk oranları sağlayarak hekimlere değerli bir karar destek aracı sunmaktadır.
Bu sistem, özellikle yoğun iş yükü olan radyoloji departmanlarında tanı sürecini
hızlandırabilir ve erken teşhis oranlarını artırabilir.

Anahtar Kelimeler: Yapay zeka, derin öğrenme, radyoloji, tıbbi görüntü analizi,
konvolüsyonel sinir ağları, otomatik tanı sistemi.
"""
}

# İstatistikler - Demo için
MOCK_STATISTICS = {
    "total_count": 10,
    "by_type": {
        "Tıpta Uzmanlık": 8,
        "Doktora": 2
    },
    "by_year": {
        2023: 2,
        2022: 2,
        2021: 3,
        2020: 3
    },
    "by_university": {
        "Hacettepe Üniversitesi": 2,
        "İstanbul Üniversitesi Cerrahpaşa": 1,
        "Ankara Üniversitesi": 1,
        "Ege Üniversitesi": 1,
        "Dokuz Eylül Üniversitesi": 1,
        "Gazi Üniversitesi": 1,
        "Boğaziçi Üniversitesi": 1,
        "İstanbul Tıp Fakültesi": 1,
        "Marmara Üniversitesi": 1
    },
    "by_language": {
        "Türkçe": 7,
        "İngilizce": 3
    },
    "by_field": {
        "Radyoloji": 3,
        "Kardiyoloji": 1,
        "Patoloji": 1,
        "Endokrinoloji": 1,
        "Tıp Bilişimi": 1,
        "Nöroloji": 1,
        "Göğüs Hastalıkları": 1,
        "Dermatoloji": 1,
        "Yoğun Bakım": 1
    }
}
