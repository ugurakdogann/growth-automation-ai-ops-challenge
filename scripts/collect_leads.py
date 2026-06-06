"""
Lead Collector — SerpAPI ile HR Profili Toplama
================================================

Büyük Türk şirketlerindeki İK profesyonellerini LinkedIn'den toplar.
Google Search sonuçlarını SerpAPI üzerinden çeker. API key güvenlik nedeniyle
repo'ya eklenmez; --api-key ile verilebilir veya SERPAPI_KEY environment
variable olarak ayarlanabilir.

Kullanım:
    # API key ile çalıştır
    python scripts/collect_leads.py --api-key YOUR_SERPAPI_KEY

    # veya environment variable ile
    set SERPAPI_KEY=YOUR_SERPAPI_KEY
    python scripts/collect_leads.py
    
    # Farklı şirket listesi ile
    python scripts/collect_leads.py --api-key KEY --companies companies.txt
    
    # Sonuçları farklı dosyaya yaz
    python scripts/collect_leads.py --api-key KEY --output data/benim_leads.json

Çıktı: data/input_leads.json (standart pipeline formatı)
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


# Varsayılan şirket listesi — büyük Türk şirketleri
DEFAULT_COMPANIES = [
    "Trendyol", "Turkcell", "Koç Holding", "Sabancı Holding", "Garanti BBVA",
    "İş Bankası", "Akbank", "Getir", "Hepsiburada", "Arçelik",
    "Vestel", "LC Waikiki", "Migros", "BİM", "THY", "Pegasus",
    "Vodafone Turkey", "Unilever Turkey", "P&G Turkey", "Şişecam",
    "Ford Otosan", "Tofaş", "Eczacıbaşı", "Türk Telekom", "Enerjisa",
    "Allianz Turkey", "Eti", "Ülker", "TAV", "Siemens Turkey",
    "MediaMarkt Turkey", "Boyner", "Defacto", "Nestlé Turkey", "Borusan",
    "Yıldız Holding", "Zorlu Holding", "Doğuş Grubu", "Anadolu Grubu",
    "Kariyer.net", "Peak Games", "Dream Games", "Papara", "Yemeksepeti",
    "Socar Turkey", "CCI", "Kale Grubu", "İş Bankası",
]

# HR arama terimleri
SEARCH_TERMS = ["İK", "İnsan Kaynakları", "HR", "Human Resources"]


def _extract_title(page_title: str, snippet: str, fallback_term: str, company: str) -> str:
    """
    LinkedIn sayfa başlığı ve snippet'ından gerçek ünvanı çıkar.
    
    Sayfa başlığı formatı: "İsim - Ünvan | ..." veya "İsim - Şirket"
    Snippet: "Ünvan · Deneyim: Şirket · ..."
    """
    # Yöntem 1: Sayfa başlığından "İsim - ÜNVAN" kısmını al
    parts = page_title.split(" - ", 1)
    if len(parts) > 1:
        rest = parts[1].split(" | ")[0].strip()
        hr_keywords = [
            "ik ", "i̇k ", "insan kaynak", "human resource", "hr ",
            "talent", "people", "chro", "i̇şe alım", "recruit",
            "i̇se alim", "işe alım", "kariyer", "career"
        ]
        if any(kw in rest.lower() for kw in hr_keywords) and len(rest) < 80:
            return rest[:70]
    
    # Yöntem 2: Snippet'tan ünvan keyword'leri ile biten ifadeyi bul
    m = re.search(
        r'([\w\sğüşıöçĞÜŞİÖÇ&/]+(?:Uzmanı|Müdürü|Direktörü|Yöneticisi|Sorumlusu|Lideri|'
        r'Manager|Director|Specialist|Partner|Generalist|Chief|Head|Lead|VP|'
        r'Business Partner|Officer|Recruiter|Consultant|Assistant|Executive|'
        r'İş Ortağı|Profesyoneli|Koordinatörü))\b',
        snippet, re.IGNORECASE
    )
    if m:
        title = m.group(1).strip()
        return title[:70] if len(title) < 80 else title.split(" ve ")[0].strip()[:70]
    
    return fallback_term


def search_company(api_key: str, company: str, term: str, max_results: int = 3) -> list[dict]:
    """Bir şirket için SerpAPI'de LinkedIn profillerini ara."""
    params = {
        "engine": "google",
        "q": f'site:linkedin.com/in/ "{term}" "{company}"',
        "api_key": api_key,
        "num": max_results,
        "hl": "tr",
        "gl": "tr",
    }
    
    resp = requests.get("https://serpapi.com/search", params=params, timeout=10)
    data = resp.json()
    
    leads = []
    for result in data.get("organic_results", []):
        link = result.get("link", "")
        title = result.get("title", "")
        
        # LinkedIn kullanıcı adını çıkar
        match = re.search(r'linkedin\.com/in/([^/?]+)', link)
        if not match:
            continue
        
        username = match.group(1)
        name = title.split(" - ")[0].split(" | ")[0].strip()
        
        if len(name) < 3:
            continue
        
        # Gerçek ünvanı sayfa başlığı + snippet'dan çıkar
        page_title = result.get("title", "")
        snippet = result.get("snippet", "")
        real_title = _extract_title(page_title, snippet, term, company)
        
        leads.append({
            "full_name": name,
            "title": real_title,
            "company": company,
            "linkedin_url": link.split("?")[0],
            "source": "serpapi"
        })
    
    return leads


def collect(api_key: str, companies: list[str], output: str, 
            max_per_company: int = 3, delay: float = 0.3) -> int:
    """
    Tüm şirketler için lead topla.
    
    Returns: toplanan benzersiz lead sayısı
    """
    all_leads = []
    seen_urls = set()
    total = len(companies) * len(SEARCH_TERMS[:1])  # sadece ilk terim
    
    print(f"🔍 {len(companies)} şirket × 1 arama terimi")
    print(f"   Her şirketten max {max_per_company} profil")
    print(f"   Toplam ~{len(companies) * max_per_company} lead hedefi\n")
    
    for i, company in enumerate(companies, 1):
        term = SEARCH_TERMS[0]  # "İK"
        print(f"[{i}/{len(companies)}] {company}...", end=" ")
        
        try:
            leads = search_company(api_key, company, term, max_per_company)
            
            new_count = 0
            for lead in leads:
                url = lead["linkedin_url"]
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_leads.append(lead)
                    new_count += 1
            
            print(f"✅ {new_count} yeni lead")
        except Exception as e:
            print(f"❌ {str(e)[:50]}")
        
        time.sleep(delay)
    
    # Kaydet
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_leads, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ {len(all_leads)} lead → {output_path}")
    print(f"🚀 Şimdi çalıştır: python main.py --input {output}")
    print("📧 Email enrichment için: python scripts/email_enrich.py && python main.py")
    
    return len(all_leads)


def main():
    parser = argparse.ArgumentParser(
        description="SerpAPI ile LinkedIn HR profillerini topla"
    )
    parser.add_argument(
        "--api-key", "-k",
        default=os.getenv("SERPAPI_KEY"),
        help="SerpAPI key. Alternatif: SERPAPI_KEY environment variable.",
    )
    parser.add_argument("--companies", "-c", 
                        help="Şirket listesi dosyası (her satır bir şirket)")
    parser.add_argument("--output", "-o", default="data/input_leads.json",
                        help="Çıktı dosyası (varsayılan: data/input_leads.json)")
    parser.add_argument("--max", "-m", type=int, default=3,
                        help="Şirket başına max profil (varsayılan: 3)")
    parser.add_argument("--delay", "-d", type=float, default=0.3,
                        help="Sorgular arası bekleme saniyesi")
    args = parser.parse_args()

    if not args.api_key:
        parser.error(
            "SerpAPI key gerekli. --api-key YOUR_KEY kullanın veya "
            "SERPAPI_KEY environment variable ayarlayın. Güvenlik nedeniyle "
            "repo içinde API key bırakılmamıştır."
        )
    
    # Şirket listesini yükle
    if args.companies:
        with open(args.companies, "r", encoding="utf-8") as f:
            companies = [line.strip() for line in f if line.strip()]
    else:
        companies = DEFAULT_COMPANIES
    
    count = collect(
        api_key=args.api_key,
        companies=companies,
        output=args.output,
        max_per_company=args.max,
        delay=args.delay,
    )
    
    if count >= 100:
        print("\n✅ 100+ lead toplandı, challenge hedefi karşılandı!")
    else:
        print(f"\n⚠️  {count} lead toplandı. Daha fazlası için --max değerini artırın.")


if __name__ == "__main__":
    main()
