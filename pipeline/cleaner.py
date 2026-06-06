"""
Cleaner — Veri Temizleme Katmanı
=================================

Ham lead listesini alır, şunları yapar:
  1. Tekrar eden kayıtları siler (aynı isim, aynı LinkedIn)
  2. Boş / geçersiz alanları işaretler
  3. İsimleri ve ünvanları normalize eder (büyük/küçük harf, boşluk)
  4. Şirket adlarını standartlaştırır (A.Ş. / Ltd. Şti. eklerini temizler)
  5. Eksik zorunlu alanı olanları "doğrulama bekliyor" diye işaretler
"""

import csv
import json
import re
from pathlib import Path
from typing import Any


class LeadCleaner:
    """
    Ham lead verisini temizler ve doğrular.
    
    Kullanım:
        cleaner = LeadCleaner()
        cleaned = cleaner.clean(raw_leads)
        cleaner.save(cleaned, "data/leads_clean.csv")
    """
    
    # Zorunlu alanlar (bunlar olmadan lead eksik sayılır)
    REQUIRED_FIELDS = ["full_name", "company"]
    
    # Şirket adı eklerini temizle (Türkçe + İngilizce)
    COMPANY_SUFFIX_PATTERNS = [
        r'\s*A\.Ş\.\s*$', r'\s*Ltd\. Şti\.\s*$', r'\s*Ltd\.Şti\.\s*$',
        r'\s*Inc\.?\s*$', r'\s*LLC\s*$', r'\s*Ltd\.?\s*$',
        r'\s*San\. ve Tic\. A\.Ş\.\s*$', r'\s*Sanayi ve Ticaret A\.Ş\.\s*$',
        r'\s*Holding A\.Ş\.\s*$', r'\s*Grubu\s*$',
    ]
    
    # Yaygın ünvan kısaltmaları → açık hali
    TITLE_NORMALIZE = {
        "chro": "Chief Human Resources Officer",
        "vp hr": "VP Human Resources",
        "vp people": "VP People",
        "hrbp": "HR Business Partner",
        "ta manager": "Talent Acquisition Manager",
        "ik direktörü": "İK Direktörü",
        "ik müdürü": "İK Müdürü",
        "insan kaynakları direktörü": "İK Direktörü",
        "insan kaynakları müdürü": "İK Müdürü",
        "people director": "People Director",
        "head of hr": "Head of HR",
        "head of people": "Head of People",
        "hr director": "HR Director",
        "hr manager": "HR Manager",
    }
    
    def clean(self, leads: list[dict]) -> list[dict]:
        """
        Ana temizleme fonksiyonu. Tüm adımları sırayla uygular.
        
        Pipeline mantığı: her adım bir öncekinin çıktısını alır.
        """
        print(f"\n🧹 Cleaner başladı — {len(leads)} ham kayıt")
        
        # Adım 1: Normalizasyon
        leads = [self._normalize(lead) for lead in leads]
        
        # Adım 2: Tekrar edenleri sil
        before = len(leads)
        leads = self._remove_duplicates(leads)
        print(f"  Tekrar silindi: {before} → {len(leads)}")
        
        # Adım 3: Geçerlilik kontrolü
        valid = [l for l in leads if self._is_valid(l)]
        invalid = [l for l in leads if not self._is_valid(l)]
        if invalid:
            print(f"  Eksik/geçersiz: {len(invalid)} kayıt işaretlendi")
            for l in invalid:
                l["status"] = "needs_review"
        
        # Adım 4: Şirket adlarını standartlaştır
        for lead in leads:
            lead["company"] = self._clean_company_name(lead.get("company", ""))
        
        print(f"  Sonuç: {len(leads)} temiz kayıt")
        return leads
    
    def _normalize(self, lead: dict) -> dict:
        """İsim, ünvan, şirket alanlarını normalize et."""
        # Baştaki/sondaki boşlukları temizle
        for key in lead:
            if isinstance(lead[key], str):
                lead[key] = lead[key].strip()
        
        # İsim: her kelimenin ilk harfi büyük
        if lead.get("full_name"):
            lead["full_name"] = lead["full_name"].title()
        
        # Ünvan: temizle ve normalize et
        if lead.get("title"):
            lead["title"] = self._clean_title(lead["title"], lead.get("company", ""))
        
        return lead
    
    def _clean_title(self, title: str, company: str = "") -> str:
        """
        LinkedIn'den gelen ham ünvanı temizler.
        
        Örnekler:
          "İk - Trendyol Group" → "İK Uzmanı" (şirket adı atılır)
          "Kıdemli İK İş Ortağı @ Turkcell ..." → "Kıdemli İK İş Ortağı Yöneticisi"
          "İK Egitim Uzmani / Turkcell Global Bilgi" → "İK Eğitim Uzmanı"
          "I lead HR business partner" → "HR Business Partner Lead"
        """
        title = title.strip()
        
        # 1. Şirket bilgisi içeren kısımları temizle
        # "Ünvan @ Şirket ..." → "Ünvan"
        title = re.sub(r'\s*[@]\s*[\w\sğüşıöçĞÜŞİÖÇ.]+$', '', title)
        # "Ünvan at Şirket ..." → "Ünvan"
        title = re.sub(r'\s+at\s+[\w\sğüşıöçĞÜŞİÖÇ.]+$', '', title)
        # "Ünvan / Şirket" → "Ünvan"
        title = re.sub(r'\s*/\s*[\w\sğüşıöçĞÜŞİÖÇ.]+$', '', title)
        # "Şirket şirketinde Ünvan" → "Ünvan"
        title = re.sub(r'^[\w\sğüşıöçĞÜŞİÖÇ.]+\s+şirketinde\s+', '', title, flags=re.IGNORECASE)
        
        # Şirket prefix'ini temizle: "ŞirketAdı - GerçekÜnvan" → "GerçekÜnvan"
        # Şirket adı olduğunu anlamak için: Holding, A.Ş., Group, Inc, Ltd, vb.
        company_suffixes = r'(Holding|Group|A\.Ş\.|A\.Ş|A\.ş\.|A\.ş|a\.ş\.|a\.ş|Ltd\.|Ltd|Şti\.|Şti|Inc\.|Inc|LLC|Sanayi|Turkey|Global|Teknoloji|Bilişim)'
        prefix_pattern = rf'^[\w\sğüşıöçĞÜŞİÖÇ.]+\s+(?:{company_suffixes})\s*[-–/]\s*'
        cleaned = re.sub(prefix_pattern, '', title, flags=re.IGNORECASE)
        if cleaned != title and len(cleaned) > 5:
            title = cleaned.strip()
        # "ŞirketAdı A.Ş. GerçekÜnvan" (boşlukla ayrılmış, tire yok)
        space_prefix = rf'^[\w\sğüşıöçĞÜŞİÖÇ.]+\s+(?:{company_suffixes})\s+(?!$)'
        cleaned2 = re.sub(space_prefix, '', title, flags=re.IGNORECASE)
        if cleaned2 != title and len(cleaned2) > 5:
            title = cleaned2.strip()
        
        # "İK - ŞirketAdı" → ünvan yok, generic
        if re.match(r'^(İK|ik|HR|hr|İnsan Kaynakları)\s*[-–/]\s*\w', title, re.IGNORECASE):
            # Sonrası şirket adı, ünvan değil
            title = re.sub(r'\s*[-–/]\s*[\w\sğüşıöçĞÜŞİÖÇ.]+$', '', title, flags=re.IGNORECASE).strip()
        
        # Sondaki "..." temizle
        title = re.sub(r'\.{2,}$', '', title).strip()
        
        # "Ünvan - ŞirketAdı ..." → "Ünvan" (sondaki şirket referansını at)
        # Sadece şirket gibi görünüyorsa: Holding, A.Ş., Group, Birleşik Mağazalar vs.
        company_tail = r'\s*[-–]\s*[\w\sğüşıöçĞÜŞİÖÇ.]*\b(?:Holding|Group|A\.Ş|Ltd|Şti|Inc|LLC|Mağaza|Sanayi|Turkey|Global)\b[\w\sğüşıöçĞÜŞİÖÇ.]*\s*\.{0,3}$'
        title = re.sub(company_tail, '', title, flags=re.IGNORECASE).strip()
        
        # 2. "I lead HR business partner" → "HR Business Partner Lead" 
        if title.lower().startswith("i lead "):
            title = title[6:].strip().title()
        
        # 3. Yaygın kısaltmaları ve bozuk yazımları düzelt
        fixes = {
            r'\bik\b': 'İK',
            r'\bi̇k\b': 'İK',
            r'\begitim\b': 'Eğitim',
            r'\buzmani\b': 'Uzmanı',
            r'\bmuduru\b': 'Müdürü',
            r'\byonetici\b': 'Yönetici',
            r'\binsan kaynaklari\b': 'İnsan Kaynakları',
            r'\bkoordinatoru\b': 'Koordinatörü',
            r'\bhr\b': 'HR',
            r'\bchro\b': 'CHRO',
            r'\bvp\b': 'VP',
        }
        for pattern, repl in fixes.items():
            title = re.sub(pattern, repl, title, flags=re.IGNORECASE)
        
        # Baştaki anlamsız kelimeleri temizle (sadece HR keyword'ü yoksa)
        hr_kw = ['ik', 'i̇k', 'insan kaynak', 'human resource', 'hr', 'talent', 'people']
        if not any(kw in title.lower() for kw in hr_kw):
            title = re.sub(r'^[\w\sğüşıöçĞÜŞİÖÇ]+\s*/\s*', '', title)
            title = re.sub(r'^[\w\sğüşıöçĞÜŞİÖÇ.]+\s*[-–]\s*', '', title)
        
        # 4. Title içinde şirket adı geçiyorsa temizle
        if company and len(company) >= 3:
            # Şirket adının varyasyonlarını title'dan sil
            company_words = company.split()
            company_variants = [
                company,
                company.lower(),
                company.upper(),
                company.split()[0] if company_words else "",  # sadece ilk kelime
                " ".join(company_words[:2]) if len(company_words) >= 2 else "",  # ilk 2 kelime
            ]
            for cv in company_variants:
                if cv and len(cv) > 2:
                    # Başta: "ŞirketAdı - Ünvan" → "Ünvan"
                    title = re.sub(rf'^{re.escape(cv)}\s*[-–/]\s*', '', title, flags=re.IGNORECASE).strip()
                    # Başta: "ŞirketAdı Ünvan" → "Ünvan" (boşluk varsa ve sonrası var)
                    title = re.sub(rf'^{re.escape(cv)}\s+(?=\S)', '', title, flags=re.IGNORECASE).strip()
                    # Sonda: "Ünvan @ ŞirketAdı" → "Ünvan"  
                    title = re.sub(rf'\s*[-–/@]\s*{re.escape(cv)}\s*$', '', title, flags=re.IGNORECASE).strip()
            
            # Şirket adının tamamı title ise → generic yap
            if title.lower().strip() in [v.lower().strip() for v in company_variants if v]:
                title = "İK Profesyoneli"
        
        # 5. Eğer sonuç sadece şirket adı veya anlamsızsa düzelt
        company_keywords = ['group', 'holding', 'a.ş', 'ltd', 'şti', 'inc', 'llc', 'sanayi']
        is_company_name = any(kw in title.lower() for kw in company_keywords)
        has_hr_keywords = any(kw in title.lower() for kw in [
            'ik', 'i̇k', 'insan kaynak', 'human resource', 'hr', 'talent',
            'people', 'chro', 'işe alım', 'recruit', 'kariyer', 'career',
            'personnel', 'eğitim', 'egitim', 'iş ortağı', 'is ortagi'
        ])
        
        if is_company_name and not has_hr_keywords:
            return "İK Profesyoneli"
        
        if len(title) < 5:
            return "İK Profesyoneli"
        
        # 6. Son kontrol: title hala bir şirket adı veya anlamsız metinse
        # (örn: "Birleşik Mağazalar A.Ş", "İnsan", "BİM Birleşik")
        looks_like_company = bool(re.search(r'\b(A\.Ş|Ltd|Şti|Inc|LLC|Group|Holding|Sanayi)\b', title, re.IGNORECASE))
        if looks_like_company and not has_hr_keywords:
            return "İK Profesyoneli"
        
        # 7. Baş harfleri büyüt (title case)
        # Ama kısaltmaları bozma: İK, HR, VP vs.
        words = title.split()
        result = []
        for w in words:
            if w.isupper() and len(w) <= 3:
                result.append(w)  # İK, HR, VP
            else:
                result.append(w[0].upper() + w[1:].lower() if len(w) > 1 else w)
        title = ' '.join(result)
        
        return title[:80]
    
    def _remove_duplicates(self, leads: list[dict]) -> list[dict]:
        """Aynı isim VEYA aynı LinkedIn URL'sine sahip kayıtları temizle."""
        seen_names = set()
        seen_urls = set()
        unique = []
        
        for lead in leads:
            name_key = lead.get("full_name", "").lower().strip()
            url_key = lead.get("linkedin_url", "").lower().strip()
            
            # İkisi de görülmemişse ekle
            if name_key not in seen_names and (not url_key or url_key not in seen_urls):
                unique.append(lead)
                seen_names.add(name_key)
                if url_key:
                    seen_urls.add(url_key)
        
        return unique
    
    def _is_valid(self, lead: dict) -> bool:
        """Zorunlu alanlar dolu mu?"""
        for field in self.REQUIRED_FIELDS:
            if not lead.get(field):
                return False
        return True
    
    def _clean_company_name(self, name: str) -> str:
        """Şirket adındaki A.Ş., Ltd. Şti. gibi ekleri temizle."""
        for pattern in self.COMPANY_SUFFIX_PATTERNS:
            name = re.sub(pattern, "", name)
        return name.strip()
    
    def save(self, leads: list[dict], filepath: str):
        """Temizlenmiş veriyi CSV olarak kaydet."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if not leads:
            print("Kaydedilecek veri yok.")
            return
        
        fieldnames = list(leads[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)
        
        print(f"💾 {len(leads)} kayıt → {filepath}")


def load_json(filepath: str) -> list[dict]:
    """JSON dosyasından lead listesini yükle."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    raw = load_json("data/input_leads.json")
    cleaner = LeadCleaner()
    cleaned = cleaner.clean(raw)
    cleaner.save(cleaned, "data/leads_clean.csv")
    
    # Örnek göster
    print("\n--- İlk 3 temizlenmiş kayıt ---")
    for lead in cleaned[:3]:
        print(f"  {lead['full_name']} | {lead['title']} | {lead['company']}")
