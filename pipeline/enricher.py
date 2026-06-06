"""
Enricher v2 — Rule-based Lead Enrichment
=========================================

Temizlenmiş lead verisini alır, her lead için şunları ekler:
  1. Şirket sektörü (teknoloji, bankacılık, perakende...)
  2. Şirket büyüklüğü tahmini
  3. Role dayalı pain point (6 kategori)
  4. Sektör + rol ağırlıklı İngilizce ihtiyaç seviyesi (1-5)
  5. Outreach angle (yaklaşım stratejisi)
  6. Lead score (0-100)
  7. needs_review flag (HR olmayan / şüpheli title'lar)
  8. HR role category (Talent Acquisition, HRBP, L&D, EB, HR Ops, CHRO/Director)
"""

import csv
import json
from pathlib import Path
from typing import Any
from collections import Counter


# ===========================================================================
# COMPANY_DB — Bilinen şirketlerin sektör, büyüklük, odak bilgileri
# ===========================================================================
COMPANY_DB = {
    # Teknoloji / E-ticaret
    "Trendyol":    {"sector": "E-ticaret / Teknoloji",   "size": "5000+", "focus": "dijital dönüşüm, hızlı büyüme"},
    "Getir":       {"sector": "Hızlı Teslimat / Teknoloji", "size": "3000+", "focus": "operasyonel verimlilik, global açılım"},
    "Hepsiburada": {"sector": "E-ticaret",                "size": "3000+", "focus": "müşteri deneyimi, lojistik"},
    "Yemeksepeti": {"sector": "Yemek Teslimatı / Teknoloji", "size": "2000+", "focus": "operasyon, restoran ağı"},
    "Insider":     {"sector": "SaaS / Pazarlama Teknolojisi", "size": "500+", "focus": "global satış, müşteri başarısı"},
    "iyzico":      {"sector": "Fintech / Ödeme Sistemleri", "size": "300+", "focus": "finansal teknoloji, güvenlik"},
    "Paraşüt":     {"sector": "SaaS / Finans",            "size": "200+", "focus": "KOBİ dijitalleşmesi"},
    "Papara":      {"sector": "Fintech",                  "size": "500+", "focus": "finansal kapsayıcılık, genç yetenek"},

    # İK Teknolojisi / İşe Alım
    "Kariyer.net": {"sector": "İK Teknolojisi / İşe Alım", "size": "500+", "focus": "dijital İK, online işe alım platformu"},

    # Oyun
    "Peak Games":  {"sector": "Mobil Oyun",               "size": "200+", "focus": "global pazarlar, yetenek kazanımı"},
    "Dream Games": {"sector": "Mobil Oyun",               "size": "200+", "focus": "yaratıcı yetenek, uluslararası büyüme"},
    "Masomo":      {"sector": "Mobil Oyun",               "size": "100+", "focus": "hızlı prototipleme, global yayıncılık"},
    "Spyke Games": {"sector": "Mobil Oyun",               "size": "100+", "focus": "yetenek savaşı, kreatif ekipler"},

    # Bankacılık / Finans
    "İş Bankası":       {"sector": "Bankacılık",      "size": "20000+", "focus": "dijital bankacılık, kurumsal dönüşüm"},
    "Garanti BBVA":     {"sector": "Bankacılık",      "size": "20000+", "focus": "teknoloji yatırımları, çevik dönüşüm"},
    "Akbank":           {"sector": "Bankacılık",      "size": "10000+", "focus": "inovasyon, dijital yetenek"},
    "Allianz Turkey":   {"sector": "Sigortacılık",    "size": "2000+",  "focus": "dijital sigortacılık, müşteri deneyimi"},

    # Telekom
    "Turkcell":         {"sector": "Telekomünikasyon", "size": "15000+", "focus": "dijital servisler, teknoloji yeteneği"},
    "Vodafone Turkey":  {"sector": "Telekomünikasyon", "size": "3000+",  "focus": "çevik dönüşüm, dijital yetkinlik"},
    "Türk Telekom":     {"sector": "Telekomünikasyon", "size": "30000+", "focus": "altyapı, fiber dönüşüm"},

    # Holdingler
    "Sabancı Holding":  {"sector": "Holding / Konglomera", "size": "60000+", "focus": "sürdürülebilirlik, dijital dönüşüm"},
    "Koç Holding":      {"sector": "Holding / Konglomera", "size": "100000+", "focus": "endüstriyel dönüşüm, inovasyon"},
    "Borusan Holding":  {"sector": "Holding / Konglomera", "size": "10000+", "focus": "lojistik, enerji, otomotiv"},
    "Yıldız Holding":   {"sector": "Gıda / Holding",       "size": "50000+", "focus": "global markalar, tedarik zinciri"},
    "Zorlu Holding":    {"sector": "Holding / Konglomera", "size": "30000+", "focus": "enerji, tekstil, elektronik"},
    "Anadolu Grubu":    {"sector": "Holding / Konglomera", "size": "50000+", "focus": "içecek, otomotiv, perakende"},
    "Doğuş Grubu":      {"sector": "Holding / Konglomera", "size": "30000+", "focus": "turizm, medya, otomotiv"},
    "Eczacıbaşı":       {"sector": "Holding / Konglomera", "size": "10000+", "focus": "sağlık, yapı, tüketim"},

    # Perakende
    "LC Waikiki":       {"sector": "Perakende / Tekstil", "size": "50000+", "focus": "global açılım, tedarik zinciri"},
    "Defacto":          {"sector": "Perakende / Tekstil", "size": "15000+", "focus": "e-ticaret, uluslararası büyüme"},
    "Migros":           {"sector": "Perakende / Gıda",    "size": "40000+", "focus": "dijital market, lojistik"},
    "BİM":              {"sector": "Perakende / Gıda",    "size": "70000+", "focus": "operasyonel verimlilik"},
    "Şok Marketler":    {"sector": "Perakende / Gıda",    "size": "30000+", "focus": "mağaza operasyonları"},
    "Boyner":           {"sector": "Perakende / Moda",    "size": "5000+",  "focus": "omnichannel, müşteri sadakati"},

    # Otomotiv
    "Tofaş":            {"sector": "Otomotiv", "size": "10000+", "focus": "elektrikli araç, endüstri 4.0"},
    "Ford Otosan":      {"sector": "Otomotiv", "size": "20000+", "focus": "elektrikli araç, ihracat"},

    # Beyaz Eşya / Elektronik
    "Arçelik":          {"sector": "Beyaz Eşya / Elektronik", "size": "30000+", "focus": "global markalar, IoT"},
    "Vestel":           {"sector": "Beyaz Eşya / Elektronik", "size": "20000+", "focus": "teknoloji ihracatı"},

    # Gıda / İçecek
    "Ülker":            {"sector": "Gıda",            "size": "10000+", "focus": "global markalar, inovasyon"},
    "Nestlé Turkey":    {"sector": "Gıda / Çokuluslu", "size": "3000+",  "focus": "sürdürülebilirlik, global standartlar"},
    "Eti":              {"sector": "Gıda",            "size": "5000+",  "focus": "marka yenileme, dijital pazarlama"},
    "CCI":              {"sector": "İçecek (Coca-Cola)", "size": "10000+", "focus": "dağıtım ağı, saha satış"},

    # Havacılık
    "THY":              {"sector": "Havacılık",      "size": "40000+", "focus": "global ağ, müşteri deneyimi"},
    "Pegasus":          {"sector": "Havacılık",      "size": "6000+",  "focus": "dijital dönüşüm, düşük maliyet"},
    "TAV":              {"sector": "Havalimanı İşletme", "size": "15000+", "focus": "uluslararası operasyon"},

    # Enerji
    "Enerjisa":         {"sector": "Enerji",          "size": "10000+", "focus": "yenilenebilir enerji, dijitalleşme"},
    "Socar Turkey":     {"sector": "Enerji / Petrol", "size": "5000+",  "focus": "endüstriyel operasyon, güvenlik"},

    # Yapı / İnşaat Malzemeleri
    "Kale":             {"sector": "Yapı / Savunma / Havacılık", "size": "5000+", "focus": "seramik, savunma sanayi, havacılık"},

    # Diğer
    "Siemens Turkey":   {"sector": "Endüstriyel Teknoloji", "size": "3000+", "focus": "endüstri 4.0, otomasyon"},
    "MediaMarkt Turkey": {"sector": "Elektronik Perakende", "size": "3000+", "focus": "omnichannel, müşteri deneyimi"},
    "Şişecam":          {"sector": "Cam / Kimya",          "size": "20000+", "focus": "global üretim, sürdürülebilirlik"},
    "Unilever Turkey":  {"sector": "Tüketim Ürünleri / Çokuluslu", "size": "5000+", "focus": "global yetenek, marka yönetimi"},
    "P&G Turkey":       {"sector": "Tüketim Ürünleri / Çokuluslu", "size": "2000+", "focus": "yetenek gelişimi, global rotasyon"},
}


# ===========================================================================
# TURKISH İ/i NORMALIZATION
# ===========================================================================
def normalize_tr(text: str) -> str:
    """
    Türkçe karakterleri case-insensitive eşleştirme için normalize eder.
    Python'da İ.lower() -> 'i\u0307' (combining dot) üretir, bu da
    düz 'i' ile yazılan pattern'lerle eşleşmez. Bu fonksiyon tüm
    Türkçe karakterleri ASCII karşılıklarına çevirir.
    """
    # Combining dot above (U+0307) — Python'ın İ.lower() kalıntısı
    text = text.replace('\u0307', '')
    # Türkçe karakterleri ASCII'ye çevir
    tr_chars = {
        'İ': 'i', 'ı': 'i', 'I': 'i',
        'ş': 's', 'Ş': 's',
        'ç': 'c', 'Ç': 'c',
        'ğ': 'g', 'Ğ': 'g',
        'ü': 'u', 'Ü': 'u',
        'ö': 'o', 'Ö': 'o',
    }
    for tr, asc in tr_chars.items():
        text = text.replace(tr, asc)
    return text.lower()


# ===========================================================================
# HR ROLE CLASSIFICATION
# ===========================================================================
HR_ROLE_PATTERNS = {
    "Talent Acquisition": [
        "talent acquisition", "ise alim", "ise alım", "recruitment", "recruiter",
        "yetenek kazanimi", "yetenek kazanımı", "yeteneği kazanımı",
        "ise alim uzmani", "ise alım uzmanı", "ise alim yoneticisi",
        "ise alım yöneticisi", "recruiting",
    ],
    "HRBP / İş Ortağı": [
        "hrbp", "business partner", "is ortagi", "iş ortağı",
        "people partner", "hr business partner", "insan kaynaklari is ortagi",
        "insan kaynakları iş ortağı", "ik is ortagi", "ik iş ortağı",
    ],
    "L&D / Eğitim": [
        "learning", "development", "egitim", "eğitim", "training",
        "l&d", "ogrenme", "öğrenme", "gelisim", "gelişim",
        "talent development", "yetenek gelisim", "yetenek gelişim",
        "yetenek gelistirme", "yetenek geliştirme",
        "learning & development", "academy",
        "yetenek yonetimi", "yetenek yönetimi",
    ],
    "Employer Branding": [
        "employer branding", "isveren markasi", "işveren markası",
        "employer brand", "isveren marka", "işveren marka",
    ],
    "HR Operations": [
        "hr operations", "ik operasyon", "people operations",
        "hr ops", "people ops", "bordro", "payroll", "ozluk", "özlük",
        "compensation", "benefits", "yan haklar", "ucret", "ücret",
        "insan kaynaklari operasyon", "insan kaynakları operasyon",
        "ik surec", "ik süreç", "personel", "personnel",
        "endustriyel iliskiler", "endüstriyel ilişkiler",
    ],
    "CHRO / Director / Head": [
        "chief", "chro", "vp people", "vp hr", "vp human",
        "head of hr", "head of people", "people director",
        "director", "direktor", "direktör", "director of hr",
        "insan kaynaklari direktoru", "insan kaynakları direktörü",
        "ik direktoru", "ik direktörü",
        "insan kaynaklari muduru", "insan kaynakları müdürü",
        "ik muduru", "ik müdürü",
        "group hr", "group human", "human resources director",
        "hr director", "hr head", "people head",
        "ik yoneticisi", "ik yöneticisi",
        "insan kaynaklari yoneticisi", "insan kaynakları yöneticisi",
    ],
}

# Generic HR keywords (fallback classification)
GENERIC_HR_KEYWORDS = [
    "ik ", "insan kaynak", "human resource", "hr",
    "people", "chro", "talent", "personnel", "personel",
    "kariyer", "career",
]

# "hr" özel durumu — hem başında/sonunda boşluk olabilir, hem virgül
HR_BOUNDARY_PATTERNS = [" hr", "hr ", ",hr", "hr,", ".hr", "(hr", "hr)"]


def classify_hr_role(title: str) -> str:
    """Title'dan HR rol kategorisini belirle."""
    t = normalize_tr(title).strip()
    words = t.split()
    for category, patterns in HR_ROLE_PATTERNS.items():
        for pat in patterns:
            if pat in t:
                return category
    # Fallback: generic HR keywords var mı?
    if any(kw in t for kw in GENERIC_HR_KEYWORDS):
        return "HR Generalist"
    # "hr" boundary check
    if any(bp in t for bp in HR_BOUNDARY_PATTERNS):
        return "HR Generalist"
    # Tek kelime olarak "ik" veya "hr" kontrolü
    if "ik" in words or "hr" in words:
        return "HR Generalist"
    # "insan" tek başına (kesilmiş title)
    if "insan" in words and len(words) <= 2:
        return "HR Generalist"
    return "Belirsiz"


# ===========================================================================
# PAIN POINTS — Role kategorisine göre çeşitlendirilmiş
# ===========================================================================
PAIN_POINTS = {
    "Talent Acquisition": [
        "Nitelikli aday havuzu daralıyor — teknik roller için başvuru sayısı düşüşte. "
        "İşe alım sürecini hızlandırıp aday deneyimini iyileştirmek kritik.",

        "Yetenek savaşı — özellikle yazılım ve veri bilimi rollerinde kaliteli aday "
        "bulmak giderek zorlaşıyor. Employer branding ve aktif sourcing eksikliği.",

        "Mavi yaka işe alımda yüksek turnover — mevsimsel dalgalanmaları yönetmek "
        "ve sürekli işe alım yapmak operasyonu yoruyor.",
    ],
    "HRBP / İş Ortağı": [
        "İş birimleri İK'yı stratejik ortak değil, operasyonel destek olarak görüyor. "
        "Yeteneği elde tutma ve bağlılık skorları düşüş eğiliminde.",

        "Departmanlar arası yetenek transferi zor — silo yapısı İK'nın bütünsel "
        "strateji geliştirmesini engelliyor. Veriye dayalı İK kararları eksik.",

        "Değişim yönetimi direnci — dijital dönüşüm projelerinde çalışan adaptasyonu "
        "yavaş. Orta kademe yöneticilerin İK okuryazarlığı düşük.",
    ],
    "L&D / Eğitim": [
        "Çalışan gelişim bütçeleri kısıtlı — ölçülebilir ROI göstermek zor. "
        "Geleneksel eğitimler çalışanların ilgisini çekmiyor, tamamlama oranları düşük.",

        "Hızlı değişen teknoloji karşısında iş gücünün yetkinlikleri hızla eskimekte. "
        "Reskilling / upskilling programları kurumsal stratejiyle hizalanmış değil.",

        "Uzaktan çalışma modelinde eğitim etkileşimi düştü. "
        "Mikro-öğrenme ve kişiselleştirilmiş gelişim yol haritalarına ihtiyaç var.",
    ],
    "Employer Branding": [
        "Şirket kültürü dışarıya yansımıyor — potansiyel adayların algısı farklı, "
        "içerideki gerçeklik farklı. Sosyal medyada tutarlı bir işveren markası hikayesi yok.",

        "Yetenek çekme maliyeti artıyor — pazarda negatif yorumlar var. "
        "Çalışan bağlılığını artırmadan employer branding yatırımları boşa gidiyor.",

        "Yeni nesil adaylar sadece maaş değil, amaç ve kültür arıyor. "
        "Şirketin DE&I ve sürdürülebilirlik hikayesi inandırıcı gelmiyor.",
    ],
    "HR Operations": [
        "Operasyonel İK süreçlerinde verimlilik düşük — manuel iş yükü fazla. "
        "İK teknolojileri (HRIS) güncel değil, çalışan self-servis deneyimi zayıf.",

        "Bordro ve özlük hataları çalışan memnuniyetini düşürüyor. "
        "Mevzuat değişikliklerine uyum sağlamak zaman alıyor.",

        "Çoklu lokasyon / vardiya yapısı İK operasyonlarını karmaşıklaştırıyor. "
        "Dijitalleşme ve otomasyonla süreçleri sadeleştirmek şart.",
    ],
    "CHRO / Director / Head": [
        "Yetenek savaşı — kaliteli yazılımcı ve ürüncü bulmakta zorlanıyor. "
        "İngilizce bilen teknik ekip kurmak kritik rekabet avantajı.",

        "Grup şirketleri arası yetenek transferi ve standartlaşma zayıf. "
        "Farklı sektörler için farklı İK stratejisi gerekiyor.",

        "Dijital dönüşüm yetkinliği olan çalışan eksikliği. "
        "Yönetim kuruluna İK metriklerini iş sonuçlarıyla ilişkilendirerek sunmak zor.",
    ],
    "HR Generalist": [
        "İK operasyonlarında dijitalleşme ve otomasyon ihtiyacı — "
        "manuel süreçler zaman kaybettiriyor ve hata riski yaratıyor.",

        "Çalışan bağlılığı ve motivasyonu düşük eğilimde — "
        "özellikle genç yetenekleri elde tutmak giderek zorlaşıyor.",

        "Sınırlı İK bütçesiyle maksimum etki yaratma baskısı. "
        "Stratejik İK girişimlerine kaynak ayırmak zor.",
    ],
    "Belirsiz": [
        "İK operasyonlarında dijitalleşme ve otomasyon ihtiyacı.",
        "Nitelikli iş gücü bulma ve elde tutma zorluğu.",
    ],
}

# Sektöre özel pain point katkıları (append edilir)
SECTOR_PAIN_SUFFIX = {
    "teknoloji": " Özellikle teknik ekiplerde İngilizce iletişim zorunlu hale geliyor.",
    "bankacılık": " Regülasyon ve dijitalleşme arasında denge kurmak kritik.",
    "fintech": " Hızlı büyüme yetenek açığını derinleştiriyor.",
    "havacılık": " Uluslararası standartlar İngilizce yetkinliği zorunlu kılıyor.",
    "holding": " Grup şirketleri arası koordinasyon ek karmaşıklık getiriyor.",
    "çokuluslu": " Global raporlama ve çok kültürlü ekip yönetimi gerekiyor.",
    "perakende": " Yüksek turnover ve mevsimsellik İK planlamasını zorlaştırıyor.",
    "üretim": " Endüstri 4.0 ve dijitalleşme için yetkin iş gücü açığı.",
    "otomotiv": " Elektrikli araç dönüşümü yeni yetkinlikler gerektiriyor.",
    "enerji": " Yeşil dönüşüm ve sürdürülebilirlik odaklı yeni roller doğuyor.",
}


def estimate_role_pain_points(title: str, sector: str) -> str:
    """Role ve sektöre göre ağrı noktasını seç."""
    import random

    role_cat = classify_hr_role(title)
    candidates = PAIN_POINTS.get(role_cat, PAIN_POINTS["Belirsiz"])

    # Deterministik seçim: isim hash'ine göre
    seed = sum(ord(c) for c in title) + len(title)
    pain = candidates[seed % len(candidates)]

    # Sektör suffix'i ekle
    sector_lower = sector.lower()
    for key, suffix in SECTOR_PAIN_SUFFIX.items():
        if key in sector_lower:
            # Suffix'i zaten içermiyorsa ekle
            if suffix.strip() not in pain:
                pain += suffix
            break

    return pain


# ===========================================================================
# ENGLISH NEED — Sektör + rol ağırlıklı scoring
# ===========================================================================
def estimate_english_need(title: str, sector: str) -> int:
    """
    1-5 arası İngilizce ihtiyaç seviyesi.

    Sektör baz skoru:
      - Teknoloji, SaaS, Oyun, Çokuluslu, Havacılık, Holding: 3
      - Bankacılık, Finans, Sigorta, Telekom: 2
      - Diğer: 1

    Rol bonusu:
      - CHRO/Director/Head/VP: +2
      - Manager/BP/Lead: +1
      - Global/Uluslararası keyword: +1
    """
    sector_lower = normalize_tr(sector)
    title_lower = normalize_tr(title)

    # Sektör baz skoru
    high_eng_sectors = [
        "teknoloji", "saas", "yazılım", "oyun", "çokuluslu",
        "havacılık", "holding", "fintech",
    ]
    mid_eng_sectors = [
        "banka", "finans", "sigorta", "telekom", "endüstriyel",
        "elektronik", "e-ticaret",
    ]

    if any(kw in sector_lower for kw in high_eng_sectors):
        base = 3
    elif any(kw in sector_lower for kw in mid_eng_sectors):
        base = 2
    else:
        base = 1

    # Rol seviyesi bonusu
    role_cat = classify_hr_role(title)
    if role_cat == "CHRO / Director / Head":
        base += 2
    elif role_cat in ("HRBP / İş Ortağı", "Talent Acquisition", "HR Operations"):
        base += 1
    # L&D / Eğitim ve Employer Branding ekstra bonus almaz

    # Global keyword bonus
    if any(kw in title_lower for kw in [
        "global", "uluslararasi", "international", "avrupa", "europe",
        "mena", "emea", "apac",
    ]):
        base += 1

    # Senior title bonus
    if any(kw in title_lower for kw in [
        "kidemli", "senior", "lead", "principal", "bas", "grup",
        "group", "executive",
    ]):
        base += 1

    return max(1, min(base, 5))


# ===========================================================================
# NEEDS REVIEW — HR dışı / şüpheli title detection
# ===========================================================================
SUSPICIOUS_NON_HR_KEYWORDS = [
    # Açıkça HR dışı roller
    "satis", "satış", "sales", "muhendis", "mühendis", "engineer",
    "bankacilik", "bankacılık", "banking",
    "deputy general manager", "genel mudur", "genel müdür",
    "ceo", "cto", "cfo",
    "muhasebe", "finans", "finance", "pazarlama", "marketing",
    "yazilim", "yazılım", "software", "developer", "urun", "ürün", "product",
    "lojistik", "logistics", "hukuk", "legal", "avukat",
    "musteri", "müşteri", "customer", "destek", "support", "idari",
    "guvenlik", "güvenlik", "security", "bakim", "bakım", "maintenance",
    "kalite", "quality", "uretim", "üretim", "production",
    # Genel / belirsiz title'lar (HR sinyali olmadan gelirse şüpheli)
    "global", "magaza", "mağaza", "sorumlu yardimcisi", "sorumlu yardımcısı",
    "birlesik magazalar", "birleşik mağazalar", "buyuk magazacilik",
]


def check_needs_review(title: str) -> bool:
    """
    Title HR keyword'ü içermiyorsa VEYA şüpheli non-HR keyword içeriyorsa True.
    Ama HR keyword'ü varsa her zaman False (güvenli).
    """
    t = normalize_tr(title).strip()

    # HR keywords — normalize edilmiş liste
    hr_signals = [
        "ik ", "insan kaynak", "human resource", "hr",
        "people", "chro", "talent", "personnel", "personel",
        "ise alim", "ise alım", "recruit", "headhunt",
        "bordro", "payroll", "ozluk", "özlük",
        "egitim", "eğitim", "training", "learning",
        "is ortagi", "iş ortağı", "business partner",
        "employer branding", "isveren marka", "işveren marka",
        "compensation", "benefits", "yan haklar",
        "kariyer", "career", "insan kaynaklari", "insan kaynakları",
        "endustriyel iliskiler", "endüstriyel ilişkiler",
        "industrial relations", "yetenek", "academy",
    ]

    # HR boundary check (virgül, parantez kenarında "hr")
    hr_boundary = [" hr", "hr ", ",hr", "hr,", ".hr", "(hr", "hr)"]

    has_hr = any(kw in t for kw in hr_signals) or any(bp in t for bp in hr_boundary)

    # Eğer HR keyword varsa güvenli
    if has_hr:
        return False

    # HR keyword yoksa ve şüpheli non-HR keyword varsa → needs_review
    has_suspicious = any(kw in t for kw in SUSPICIOUS_NON_HR_KEYWORDS)
    if has_suspicious:
        return True

    # HR keyword yok ama title kısa/genel → düşük confidence
    return False


# ===========================================================================
# LEAD SCORE — Genişletilmiş keyword seti
# ===========================================================================
def calculate_lead_score(lead: dict) -> int:
    """
    Lead kalitesini 0-100 arası puanla.

    Kriterler:
      - Senior HR rolü: +25
      - Manager/Lead rolü: +15
      - Büyük şirket (5000+): +20
      - Orta şirket (500+): +10
      - english_need 4-5: +20
      - english_need 2-3: +10
      - linkedin_url var: +10
      - email var: +10
      - needs_review: -15 (ceza)
    """
    score = 0
    title = normalize_tr(lead.get("title", ""))
    company_size = lead.get("company_size", "")
    eng = lead.get("english_need", 0)

    # --- Senior HR rolleri (genişletilmiş) ---
    senior_keywords = [
        # İngilizce
        "chief", "chro", "vp people", "vp hr", "vp human",
        "head of hr", "head of people", "people director",
        "director of hr", "director of people", "hr director",
        "group hr", "group human", "global hr",
        # Türkçe
        "direktor", "direktör", "insan kaynaklari direktoru",
        "insan kaynakları direktörü",
        "ik direktoru", "ik direktörü",
        "insan kaynaklari muduru", "insan kaynakları müdürü",
        "ik muduru", "ik müdürü",
        "hr head", "people head", "ik yoneticisi", "ik yöneticisi",
    ]
    if any(kw in title for kw in senior_keywords):
        score += 25
    else:
        # --- Manager/Lead/BP rolleri (genişletilmiş) ---
        manager_keywords = [
            # İngilizce
            "manager", "business partner", "hrbp",
            "talent acquisition", "people partner", "lead",
            "head of", "supervisor", "team lead",
            "employer branding", "learning", "development",
            # Türkçe
            "mudur", "müdür", "yonetici", "yönetici",
            "is ortagi", "iş ortağı",
            "ise alim", "işe alım", "yetenek kazanimi", "yetenek kazanımı",
            "egitim", "eğitim", "ik uzmani", "ik uzmanı",
        ]
        if any(kw in title for kw in manager_keywords):
            score += 15

    # --- Şirket büyüklüğü ---
    try:
        size_str = str(company_size).replace("+", "").replace(".", "").replace(",", "").strip()
        size_num = int(size_str)
        if size_num >= 5000:
            score += 20
        elif size_num >= 500:
            score += 10
    except (ValueError, AttributeError):
        pass

    # --- İngilizce ihtiyacı ---
    try:
        eng_val = int(eng)
        if eng_val >= 4:
            score += 20
        elif eng_val >= 2:
            score += 10
    except (ValueError, TypeError):
        pass

    # --- İletişim bilgisi ---
    if lead.get("linkedin_url", "").strip():
        score += 10
    if lead.get("email", "").strip():
        score += 10

    # --- needs_review cezası ---
    if lead.get("needs_review") == "true":
        score -= 15

    return max(0, min(score, 100))


# ===========================================================================
# OUTREACH ANGLE
# ===========================================================================
def generate_outreach_angle(lead: dict) -> str:
    """Lead'e özel yaklaşım stratejisi."""
    company = lead.get("company", "")
    title = lead.get("title", "")
    eng = lead.get("english_need", 1)
    role_cat = lead.get("hr_role", "")
    pain = lead.get("pain_point", "")

    if hasattr(eng, '__float__') or isinstance(eng, (int, float)):
        eng_val = int(eng)
    else:
        try:
            eng_val = int(str(eng))
        except:
            eng_val = 1

    if eng_val >= 4:
        if role_cat == "Talent Acquisition":
            return (f"{company}'nin global yetenek kazanımı için "
                    f"çalışan İngilizce seviyesini sistematik olarak yükseltmek.")
        elif role_cat == "L&D / Eğitim":
            return (f"{company} bünyesindeki kurumsal İngilizce eğitim programını "
                    f"pratik konuşma odağıyla güçlendirmek.")
        else:
            return (f"{company}'nin uluslararası operasyonları için "
                    f"çalışan İngilizce seviyesini sistematik olarak yükseltmek.")

    elif eng_val >= 2:
        return (f"{company}'de kurumsal İngilizce eğitimle "
                f"müşteri memnuniyetini ve çalışan bağlılığını artırmak.")

    else:
        return (f"{company}'nin sektördeki konumunu güçlendirmek için "
                f"temel İngilizce iletişim becerilerini kurum geneline yaymak.")


# ===========================================================================
# REPORT
# ===========================================================================
def generate_report(leads: list[dict]) -> str:
    """Enrichment sonuç raporu."""
    lines = []
    lines.append("=" * 60)
    lines.append("  ENRICHMENT RAPORU")
    lines.append("=" * 60)
    lines.append(f"  Toplam lead: {len(leads)}")

    # Sector dağılımı
    sectors = Counter(l.get("sector", "Bilinmiyor") for l in leads)
    lines.append(f"\n  📊 Sektör Dağılımı ({len(sectors)} sektör):")
    for sec, cnt in sectors.most_common():
        lines.append(f"     {sec}: {cnt}")

    # english_need dağılımı
    eng_counts = Counter()
    for l in leads:
        try:
            eng_counts[int(l.get("english_need", 0))] += 1
        except:
            eng_counts[0] += 1
    lines.append(f"\n  🇬🇧 English Need Dağılımı:")
    for level in sorted(eng_counts.keys()):
        bar = "█" * eng_counts[level]
        lines.append(f"     Level {level}: {eng_counts[level]:>3} {bar}")

    # lead_score dağılımı
    score_buckets = Counter()
    for l in leads:
        try:
            s = int(l.get("lead_score", 0))
        except:
            s = 0
        bucket = f"{s//10*10}-{s//10*10+9}"
        score_buckets[bucket] += 1
    lines.append(f"\n  🏆 Lead Score Dağılımı:")
    for bucket in sorted(score_buckets.keys()):
        lines.append(f"     {bucket}: {score_buckets[bucket]}")

    # needs_review
    needs_review = [l for l in leads if l.get("needs_review") == "true"]
    lines.append(f"\n  ⚠️  Needs Review: {len(needs_review)} lead")
    if needs_review:
        for l in needs_review:
            lines.append(f"     - {l['full_name']} | {l['title']} | {l['company']}")

    # Unique pain points
    unique_pains = set(l.get("pain_point", "") for l in leads)
    lines.append(f"\n  💡 Unique Pain Point: {len(unique_pains)}")

    # HR role category dağılımı
    role_cats = Counter(l.get("hr_role", "Belirsiz") for l in leads)
    lines.append(f"\n  👥 HR Rol Kategorisi Dağılımı:")
    for cat, cnt in role_cats.most_common():
        lines.append(f"     {cat}: {cnt}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


# ===========================================================================
# MAIN ENRICHER CLASS
# ===========================================================================
class LeadEnricher:
    """Lead'leri kural tabanlı sistemle zenginleştirir."""

    def enrich(self, leads: list[dict]) -> list[dict]:
        """Tüm lead'leri zenginleştir."""
        print(f"\n🤖 Enricher v2 başladı — {len(leads)} lead")

        enriched = []
        for i, lead in enumerate(leads):
            company = lead.get("company", "")
            title = lead.get("title", "")

            # 1. Şirket bilgilerini eşleştir
            company_info = self._match_company(company)

            # 2. Sektör ve büyüklük
            lead["sector"] = company_info.get("sector", "Bilinmiyor")
            lead["company_size"] = company_info.get("size", "Bilinmiyor")
            lead["company_focus"] = company_info.get("focus", "")

            # 3. HR rol kategorisi
            lead["hr_role"] = classify_hr_role(title)

            # 4. Pain point (role + sektör bazlı)
            lead["pain_point"] = estimate_role_pain_points(title, lead["sector"])

            # 5. İngilizce ihtiyaç seviyesi
            lead["english_need"] = estimate_english_need(title, lead["sector"])

            # 6. Outreach angle
            lead["outreach_angle"] = generate_outreach_angle(lead)

            # 7. Needs review check
            lead["needs_review"] = "true" if check_needs_review(title) else "false"

            # 8. Lead scoring (en son, diğer alanları kullanır)
            lead["lead_score"] = calculate_lead_score(lead)

            enriched.append(lead)

            if (i + 1) % 50 == 0:
                print(f"  {i+1}/{len(leads)} lead işlendi...")

        print(f"  Tamamlandı: {len(enriched)} lead zenginleştirildi")
        print(generate_report(enriched))
        return enriched

    def _match_company(self, company_name: str) -> dict:
        """Şirket adını veritabanında ara."""
        if company_name in COMPANY_DB:
            return COMPANY_DB[company_name]

        # Kısmi eşleşme
        company_lower = company_name.lower()
        for name, info in COMPANY_DB.items():
            if name.lower() in company_lower or company_lower in name.lower():
                return info

        # İsimden sektör tahmini
        guessed = {"size": "Bilinmiyor", "focus": ""}
        if any(w in company_lower for w in ["teknoloji", "yazılım", "bilişim"]):
            guessed["sector"] = "Teknoloji"
        elif any(w in company_lower for w in ["banka", "finans", "sigorta"]):
            guessed["sector"] = "Finans"
        elif any(w in company_lower for w in ["gıda", "içecek"]):
            guessed["sector"] = "Gıda / İçecek"
        elif any(w in company_lower for w in ["tekstil", "giyim"]):
            guessed["sector"] = "Tekstil / Perakende"
        elif any(w in company_lower for w in ["otomotiv", "oto"]):
            guessed["sector"] = "Otomotiv"
        elif any(w in company_lower for w in ["enerji", "elektrik"]):
            guessed["sector"] = "Enerji"
        elif any(w in company_lower for w in ["ilaç", "sağlık", "hastane"]):
            guessed["sector"] = "Sağlık"
        elif any(w in company_lower for w in ["inşaat", "yapı"]):
            guessed["sector"] = "İnşaat"
        else:
            guessed["sector"] = "Diğer"

        return guessed

    def save(self, leads: list[dict], filepath: str):
        """Zenginleştirilmiş veriyi CSV olarak kaydet."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = list(leads[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)

        print(f"💾 {len(leads)} zenginleştirilmiş kayıt → {filepath}")


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from cleaner import LeadCleaner

    # Ham veriyi temizle
    raw = json.load(open("data/input_leads.json", "r", encoding="utf-8"))
    cleaner = LeadCleaner()
    cleaned = cleaner.clean(raw)

    # Zenginleştir
    enricher = LeadEnricher()
    enriched = enricher.enrich(cleaned)
    enricher.save(enriched, "data/leads_enriched.csv")

    # Örnek göster
    print("\n--- İlk 3 zenginleştirilmiş lead ---")
    for lead in enriched[:3]:
        print(f"\n  {lead['full_name']} | {lead['title']} | {lead['company']}")
        print(f"  HR Role: {lead.get('hr_role', '?')}")
        print(f"  Score: {lead.get('lead_score', '?')} | Eng: {lead.get('english_need', '?')}")
        print(f"  Review: {lead.get('needs_review', '?')}")
        print(f"  Pain: {lead.get('pain_point', '?')[:120]}...")
