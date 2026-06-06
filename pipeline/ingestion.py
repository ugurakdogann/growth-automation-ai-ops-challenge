"""
Ingestion — Input Katmanı
=========================

Veri kaynağından bağımsız lead girişi.
CSV veya JSON dosyasını okur, kolon adlarını normalize eder,
zorunlu alanları kontrol eder, duplicate'leri temizler.

Kullanım:
    from pipeline.ingestion import LeadIngestor
    ingestor = LeadIngestor()
    leads, rejected = ingestor.ingest("data/input_leads.csv")
"""

import csv
import json
import re
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Kolon Adı Normalizasyonu
# ---------------------------------------------------------------------------
COLUMN_MAP = {
    # full_name
    "full_name": "full_name",
    "name": "full_name",
    "fullname": "full_name",
    "ad_soyad": "full_name",
    "ad soyad": "full_name",
    "isim": "full_name",
    "person_name": "full_name",
    "contact_name": "full_name",
    
    # title
    "title": "title",
    "job_title": "title",
    "unvan": "title",
    "ünvan": "title",
    "position": "title",
    "role": "title",
    "pozisyon": "title",
    "designation": "title",
    
    # company
    "company": "company",
    "company_name": "company",
    "organization": "company",
    "organisation": "company",
    "şirket": "company",
    "sirket": "company",
    "kurum": "company",
    "employer": "company",
    
    # linkedin_url
    "linkedin_url": "linkedin_url",
    "linkedin": "linkedin_url",
    "linkedin_profile": "linkedin_url",
    "profile_url": "linkedin_url",
    "url": "linkedin_url",
    "linkedin_url_1": "linkedin_url",
    
    # email
    "email": "email",
    "mail": "email",
    "e_mail": "email",
    "eposta": "email",
    "e-posta": "email",
    "email_address": "email",
    "work_email": "email",
    "contact_email": "email",
    
    # source
    "source": "source",
    "source_type": "source",
    "kaynak": "source",
    "data_source": "source",
    
    # source_url
    "source_url": "source_url",
    
    # location
    "location": "location",
    "city": "location",
    "sehir": "location",
    "country": "location",
    "address": "location",
    
    # notes
    "notes": "notes",
    "notlar": "notes",
    "description": "notes",
    "comments": "notes",
}

REQUIRED_FIELDS = ["full_name", "title", "company"]
OPTIONAL_FIELDS = ["linkedin_url", "email", "source", "source_url", "location", "notes"]
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS


class LeadIngestor:
    """Lead verisini herhangi bir CSV/JSON kaynagindan okur ve normalize eder."""
    
    def __init__(self, min_expected: int = 100):
        self.min_expected = min_expected
        self.stats = {"loaded": 0, "normalized": 0, "rejected": 0, "duplicates": 0}
    
    def ingest(self, filepath: str) -> tuple[list[dict], list[dict]]:
        """
        Ana giris fonksiyonu. Dosya tipini otomatik algilar.
        
        Returns:
            (valid_leads, rejected_leads)
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {filepath}")
        
        suffix = path.suffix.lower()
        
        if suffix == ".csv":
            raw = self._read_csv(path)
        elif suffix == ".json":
            raw = self._read_json(path)
        else:
            raise ValueError(f"Unsupported format: {suffix}. Use .csv or .json")
        
        self.stats["loaded"] = len(raw)
        print(f"  📂 {len(raw)} ham kayıt yüklendi ({path.name})")
        
        # Normalize
        normalized = []
        rejected = []
        for record in raw:
            norm = self._normalize(record)
            if self._validate(norm):
                normalized.append(norm)
            else:
                rejected.append(norm)
        
        self.stats["normalized"] = len(normalized)
        self.stats["rejected"] = len(rejected)
        
        if rejected:
            print(f"  ⚠️  {len(rejected)} kayıt zorunlu alan eksik → rejected")
        
        # Duplicate temizle
        before_dedup = len(normalized)
        normalized = self._deduplicate(normalized)
        self.stats["duplicates"] = before_dedup - len(normalized)
        
        if self.stats["duplicates"] > 0:
            print(f"  🔄 {self.stats['duplicates']} duplicate temizlendi")
        
        # Minimum kontrol
        if len(normalized) < self.min_expected:
            print(f"  ⚠️  UYARI: {len(normalized)} kayıt var, hedef {self.min_expected}+")
        
        print(f"  ✅ {len(normalized)} geçerli kayıt hazır")
        return normalized, rejected
    
    def _read_csv(self, path: Path) -> list[dict]:
        """CSV dosyasini dict listesi olarak oku."""
        rows = []
        # Farkli enkodlamalari dene
        for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1254"]:
            try:
                with open(path, "r", encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                if rows:
                    break
            except (UnicodeDecodeError, UnicodeError):
                continue
        return rows
    
    def _read_json(self, path: Path) -> list[dict]:
        """JSON dosyasini dict listesi olarak oku."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Bazen {"people": [...]} veya {"leads": [...]} gibi sarmalanmis olabilir
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ["people", "leads", "contacts", "results", "data"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # Tek bir obje ise listeye cevir
            return [data]
        return []
    
    def _normalize(self, record: dict) -> dict:
        """Kolon adlarini standartlastir, eksik alanlari ekle."""
        normalized = {}
        
        # Once tum opsiyonel alanlari bos string olarak ekle
        for field in ALL_FIELDS:
            normalized[field] = ""
        
        # Mevcut alanlari normalize et
        for key, value in record.items():
            if key is None:
                continue
            clean_key = str(key).strip().lower().replace(" ", "_").replace("-", "_")
            target = COLUMN_MAP.get(clean_key, COLUMN_MAP.get(key.strip(), None))
            
            if target and target in ALL_FIELDS:
                normalized[target] = str(value).strip() if value else ""
        
        # Source yoksa default
        if not normalized.get("source"):
            normalized["source"] = "provided_input"
        
        # LinkedIn URL normalize
        if normalized.get("linkedin_url"):
            url = normalized["linkedin_url"]
            # Sondaki slash'i temizle
            url = url.rstrip("/")
            # http varsa koru, yoksa ekleme (kullanici nasil verdiyse)
            normalized["linkedin_url"] = url
        
        return normalized
    
    def _validate(self, record: dict) -> bool:
        """Zorunlu alanlar dolu mu?"""
        for field in REQUIRED_FIELDS:
            val = record.get(field, "").strip()
            if not val or val.lower() in ["none", "null", "n/a", "-", "?"]:
                return False
        return True
    
    def _deduplicate(self, leads: list[dict]) -> list[dict]:
        """Tekrar eden kayitlari temizle."""
        seen_urls = set()
        seen_keys = set()
        unique = []
        
        for lead in leads:
            url = lead.get("linkedin_url", "").strip().lower()
            key = (lead.get("full_name", "").strip().lower(), 
                   lead.get("company", "").strip().lower())
            
            if url and url in seen_urls:
                continue
            if not url and key in seen_keys:
                continue
            
            unique.append(lead)
            if url:
                seen_urls.add(url)
            seen_keys.add(key)
        
        return unique
    
    def save_rejected(self, rejected: list[dict], filepath: str):
        """Reddedilen kayitlari CSV olarak kaydet."""
        if not rejected:
            return
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        fieldnames = ALL_FIELDS + ["reject_reason"]
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in rejected:
                record["reject_reason"] = "missing_required_fields"
                writer.writerow({k: record.get(k, "") for k in fieldnames})
        
        print(f"  📋 {len(rejected)} rejected kayıt → {filepath}")


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ingestor = LeadIngestor(min_expected=100)
    
    # Test: sample CSV
    sample_path = "data/input_leads_sample.csv"
    if Path(sample_path).exists():
        leads, rejected = ingestor.ingest(sample_path)
        print(f"\nGeçerli: {len(leads)}, Red: {len(rejected)}")
        if leads:
            print(f"İlk kayıt: {leads[0]}")
