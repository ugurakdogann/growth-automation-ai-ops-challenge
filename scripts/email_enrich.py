"""
Email Enrichment v3 — Evidence-Based Public Email Discovery + Pattern Estimation
=================================================================================

Her lead için web'de public email kanıtı arar:
  1. Lead'in kendi email'i bulunursa → found_public (confidence 95)
  2. Aynı şirketten çalışan email örneği varsa → estimated_from_employee_pattern (85)
  3. Şirket domain/pattern kanıtı varsa → estimated_from_company_domain (70)
  4. Hiç kanıt yoksa → low_confidence_guess (50)

Kurallar:
  - estimated_email ASLA email kolonuna yazılmaz
  - email sadece public bulunan gerçek email ise dolar
  - Her tahmin için status, confidence, evidence_url tutulur
  - Arama sorguları rapora yazılır
"""

import csv
import json
import re
import sys
import unicodedata
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
# EVIDENCE verisini import et
sys.path.insert(0, str(PROJECT_ROOT))
import scripts.email_evidence as _ev
COMPANY_EVIDENCE_SOURCE = _ev.COMPANY_EVIDENCE
# ===========================================================================
# COMPANY DOMAINS
# ===========================================================================
COMPANY_DOMAINS = {
    "Trendyol": "trendyol.com", "Getir": "getir.com", "Hepsiburada": "hepsiburada.com",
    "Insider": "useinsider.com", "Papara": "papara.com",
    "Peak Games": "peak.com", "Dream Games": "dreamgames.com",
    "Masomo": "masomo.com", "Spyke Games": "spykegames.com",
    "İş Bankası": "isbank.com.tr", "Garanti BBVA": "garantibbva.com.tr",
    "Akbank": "akbank.com", "Allianz Turkey": "allianz.com.tr",
    "Turkcell": "turkcell.com.tr", "Vodafone Turkey": "vodafone.com.tr",
    "Türk Telekom": "turktelekom.com.tr",
    "Sabancı Holding": "sabanci.com", "Koç Holding": "koc.com.tr",
    "Borusan Holding": "borusan.com", "Yıldız Holding": "yildizholding.com.tr",
    "Zorlu Holding": "zorlu.com.tr", "Anadolu Grubu": "anadolugrubu.com.tr",
    "Doğuş Grubu": "dogusgrubu.com.tr", "Eczacıbaşı": "eczacibasi.com.tr",
    "LC Waikiki": "lcwaikiki.com", "Defacto": "defacto.com.tr",
    "Migros": "migros.com.tr", "BİM": "bim.com.tr", "Boyner": "boyner.com.tr",
    "Tofaş": "tofas.com.tr", "Ford Otosan": "fordotosan.com.tr",
    "Arçelik": "arcelik.com", "Vestel": "vestel.com",
    "Ülker": "ulker.com.tr", "Nestlé Turkey": "nestle.com.tr",
    "Eti": "eti.com.tr", "CCI": "cci.com.tr",
    "THY": "thy.com", "Pegasus": "flypgs.com", "TAV": "tav.aero",
    "Enerjisa": "enerjisa.com.tr", "Socar Turkey": "socar.com.tr",
    "Siemens Turkey": "siemens.com.tr", "MediaMarkt Turkey": "mediamarkt.com.tr",
    "Şişecam": "sisecam.com", "Kale": "kale.com.tr",
    "Kariyer.net": "kariyer.net", "P&G Turkey": "pg.com",
    "Unilever Turkey": "unilever.com.tr", "Yemeksepeti": "yemeksepeti.com",
    "iyzico": "iyzico.com", "Paraşüt": "parasut.com",
    "Şok Marketler": "sokmarket.com.tr",
}

# Company name aliases (CSV'deki kısa isim → COMPANY_DOMAINS anahtarı)
COMPANY_ALIASES = {
    "Anadolu": "Anadolu Grubu",
    "Borusan": "Borusan Holding",
    "Doğuş": "Doğuş Grubu",
}

# ===========================================================================
# EVIDENCE DATABASE — Web araştırması ile bulunan kanıtlar
# ===========================================================================
# Evidence data (imported from email_evidence.py)
COMPANY_EVIDENCE = COMPANY_EVIDENCE_SOURCE

# Company name aliases
# TÜRKÇE NORMALİZASYON
# ===========================================================================
def normalize_for_email(text: str) -> str:
    tr_chars = {'İ': 'i', 'ı': 'i', 'I': 'i', 'ş': 's', 'Ş': 's',
                'ç': 'c', 'Ç': 'c', 'ğ': 'g', 'Ğ': 'g', 'ü': 'u', 'Ü': 'u', 'ö': 'o', 'Ö': 'o'}
    for tr, asc in tr_chars.items():
        text = text.replace(tr, asc)
    text = "".join(
        ch for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )
    return text.lower()


def extract_first_last(full_name: str):
    if not full_name: return "", ""
    name = normalize_for_email(full_name.strip()).replace(".", "").replace(",", "")
    parts = [p for p in name.split() if p not in ("dr", "prof", "mr", "ms", "mrs")]
    if not parts: return "", ""
    clean = [p for p in parts if len(p) > 1 or p == parts[-1]] or parts
    return clean[0], clean[-1] if len(clean) >= 2 else ""


# ===========================================================================
# EMAIL VALİDASYON
# ===========================================================================
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}$')
PERSONAL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com",
                    "icloud.com", "me.com", "protonmail.com", "yandex.com"}


def validate_email(email: str, company_domain: str = "") -> dict:
    if not email: return {"valid": False, "reason": "empty", "is_personal": False}
    email = email.strip().lower()
    if not EMAIL_REGEX.match(email):
        return {"valid": False, "reason": "invalid_format", "is_personal": False}
    domain = email.split("@")[1] if "@" in email else ""
    if domain in PERSONAL_DOMAINS:
        return {"valid": False, "reason": "personal_domain", "is_personal": True}
    return {"valid": True, "reason": "", "is_personal": False}


# ===========================================================================
# PATTERN UYGULAMA
# ===========================================================================
def apply_pattern(first: str, last: str, domain: str, pattern: str) -> str:
    if pattern == "first.last": return f"{first}.{last}@{domain}" if last else ""
    elif pattern == "firstlast": return f"{first}{last}@{domain}" if last else ""
    elif pattern == "f.last": return f"{first[0]}.{last}@{domain}" if last else ""
    elif pattern == "flast": return f"{first[0]}{last}@{domain}" if last else ""
    elif pattern == "first": return f"{first}@{domain}"
    elif pattern == "first_last": return f"{first}_{last}@{domain}" if last else ""
    return f"{first}.{last}@{domain}" if last else ""


# ===========================================================================
# ANA ENRICHER
# ===========================================================================
class EmailEnricher:
    
    def __init__(self):
        self.stats = Counter()
        self.search_log = []
        self.company_searches = defaultdict(list)
    
    def get_domain(self, company: str) -> str:
        company = COMPANY_ALIASES.get(company, company)
        if company in COMPANY_DOMAINS: return COMPANY_DOMAINS[company]
        company_lower = company.lower()
        for name, domain in COMPANY_DOMAINS.items():
            if name.lower() in company_lower or company_lower in name.lower():
                return domain
        return ""
    
    def generate_search_queries(self, lead: dict, domain: str) -> list[str]:
        """Lead için arama sorguları üret."""
        full_name = lead.get("full_name", "")
        company = lead.get("company", "")
        first, last = extract_first_last(full_name)
        queries = [
            f'"{full_name}" "{company}" email',
            f'"{full_name}" "@{domain}"',
        ]
        if first and last:
            queries.append(f'site:{domain} "{first}.{last}"')
        queries.extend([
            f'site:{domain} "@{domain}"',
            f'"{company}" "email" "human resources"',
            f'"{company}" "ik" "email"',
            f'"{company}" filetype:pdf "@{domain}"',
            f'"{company}" "firstname.lastname"',
        ])
        return queries
    
    def enrich(self, leads: list[dict]) -> list[dict]:
        print(f"\n📧 Email Enricher v3 başladı — {len(leads)} lead")
        
        # Company-level evidence toplama
        companies_processed = set()
        for lead in leads:
            company = lead.get("company", "")
            if company not in companies_processed:
                companies_processed.add(company)
                self._collect_company_evidence(company, lead)
        
        enriched = []
        for i, lead in enumerate(leads):
            result = dict(lead)
            full_name = lead.get("full_name", "")
            company = lead.get("company", "")
            domain = self.get_domain(company)
            first, last = extract_first_last(full_name)
            
            # Varsayılan değerler
            result["email"] = ""
            result["estimated_email"] = ""
            result["email_status"] = "low_confidence_guess"
            result["email_confidence"] = 50
            result["email_evidence_url"] = ""
            result["email_pattern"] = "first.last"
            result["email_pattern_source_note"] = ""
            result["email_notes"] = ""
            result["searched_queries"] = ""
            result["found_urls"] = ""
            
            if not domain:
                result["email_status"] = "low_confidence_guess"
                result["email_confidence"] = 0
                result["email_notes"] = "Company domain not found"
                enriched.append(result)
                continue
            
            # Arama sorgularını kaydet
            queries = self.generate_search_queries(lead, domain)
            result["searched_queries"] = " || ".join(queries[:5])
            
            # Company evidence kontrolü — alias'ları da dene
            lookup_company = COMPANY_ALIASES.get(company, company)
            evidence = COMPANY_EVIDENCE.get(lookup_company, COMPANY_EVIDENCE.get(company, {}))
            evidence_type = evidence.get("evidence_type", "none")
            evidence_url = evidence.get("evidence_url", "")
            sample_emails = evidence.get("sample_emails", [])
            pattern = evidence.get("pattern", "first.last")
            source_note = evidence.get("source_note", "")
            
            if evidence_type == "found_public_lead_email":
                # Lead'in kendi email'i bulundu
                found_email = evidence.get("matched_email", "")
                result["email"] = found_email
                result["email_status"] = "found_public"
                result["email_confidence"] = 95
                result["email_evidence_url"] = evidence_url
                result["email_pattern"] = pattern
                result["email_pattern_source_note"] = source_note
                result["found_urls"] = evidence_url
                result["email_notes"] = "Public email found on web"
            
            elif evidence_type == "employee_email_sample":
                # Aynı şirketten çalışan email örneği var
                estimated = apply_pattern(first, last, domain, pattern)
                result["estimated_email"] = estimated
                result["email_status"] = "estimated_from_employee_pattern"
                result["email_confidence"] = 85
                result["email_evidence_url"] = evidence_url
                result["email_pattern"] = pattern
                result["email_pattern_source_note"] = f"same-company public employee email pattern ({', '.join(sample_emails[:2])})"
                result["found_urls"] = evidence_url
                result["email_notes"] = f"Pattern from {len(sample_emails)} employee email samples"
            
            elif evidence_type == "company_domain_evidence":
                # Şirket dokümanlarında domain/pattern kanıtı var
                estimated = apply_pattern(first, last, domain, pattern)
                result["estimated_email"] = estimated
                result["email_status"] = "estimated_from_company_domain"
                result["email_confidence"] = 70
                result["email_evidence_url"] = evidence_url
                result["email_pattern"] = pattern
                result["email_pattern_source_note"] = source_note
                result["found_urls"] = evidence_url
                result["email_notes"] = "Domain evidence found; email pattern is inferred"
            
            else:
                # Hiç kanıt yok, düşük güvenli tahmin
                estimated = apply_pattern(first, last, domain, "first.last")
                result["estimated_email"] = estimated if first and last else ""
                result["email_status"] = "low_confidence_guess"
                result["email_confidence"] = 50
                result["email_pattern"] = "first.last"
                result["email_pattern_source_note"] = "Default pattern — no evidence found"
                result["email_notes"] = "No evidence found — low confidence guess"
            
            # Validation
            if result.get("email"):
                v = validate_email(result["email"], domain)
                if not v["valid"]:
                    result["email_status"] = "low_confidence_guess"
                    result["email_notes"] = f"Found email invalid: {v['reason']}"
            if result.get("estimated_email"):
                v = validate_email(result["estimated_email"], domain)
                if not v["valid"]:
                    result["estimated_email"] = ""
            
            enriched.append(result)
            if (i + 1) % 50 == 0:
                print(f"  {i+1}/{len(leads)} lead işlendi...")
        
        self._compute_stats(enriched)
        print(f"  Tamamlandı: {len(enriched)} lead")
        self._print_stats()
        return enriched
    
    def _collect_company_evidence(self, company: str, lead: dict):
        """Şirket için kanıt araştırması yap."""
        # Bu fonksiyon manuel olarak doldurulan COMPANY_EVIDENCE'ı kullanır
        # Kanıtlar browser/web_search ile toplanıp bu dict'e eklenir
        pass
    
    def _compute_stats(self, leads: list[dict]):
        self.stats.clear()
        for lead in leads:
            self.stats[lead.get("email_status", "low_confidence_guess")] += 1
        self.stats["total"] = len(leads)
    
    def _print_stats(self):
        print(f"  found_public:                 {self.stats.get('found_public', 0)}")
        print(f"  estimated_from_employee:      {self.stats.get('estimated_from_employee_pattern', 0)}")
        print(f"  estimated_from_company_domain:{self.stats.get('estimated_from_company_domain', 0)}")
        print(f"  low_confidence_guess:         {self.stats.get('low_confidence_guess', 0)}")
    
    def save(self, leads: list[dict], filepath: str):
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(leads[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)
        print(f"💾 {len(leads)} lead → {filepath}")
    
    def generate_report(self, leads: list[dict]) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        total = len(leads)
        
        status_counts = Counter(l.get("email_status", "?") for l in leads)
        found = status_counts.get("found_public", 0)
        employee_pat = status_counts.get("estimated_from_employee_pattern", 0)
        company_dom = status_counts.get("estimated_from_company_domain", 0)
        low_conf = status_counts.get("low_confidence_guess", 0)
        
        lines = [
            "# Email Enrichment Raporu v3",
            f"**Tarih:** {now} | **Toplam lead:** {total}",
            "",
            "## Özet",
            f"| Durum | Sayı | Oran |",
            f"|-------|------|------|",
            f"| found_public | {found} | %{100*found/total:.1f} |",
            f"| estimated_from_employee_pattern | {employee_pat} | %{100*employee_pat/total:.1f} |",
            f"| estimated_from_company_domain | {company_dom} | %{100*company_dom/total:.1f} |",
            f"| low_confidence_guess | {low_conf} | %{100*low_conf/total:.1f} |",
            "",
            "## Confidence Dağılımı",
        ]
        
        conf_counts = Counter()
        for l in leads:
            try: conf_counts[int(l.get("email_confidence", 0))] += 1
            except: pass
        for conf in sorted(conf_counts, key=int, reverse=True):
            lines.append(f"- **{conf}:** {conf_counts[conf]} lead")
        lines.append("")
        
        # Evidence URL kontrolü
        high_conf_no_evidence = []
        for l in leads:
            try:
                if int(l.get("email_confidence", 0)) >= 70 and not l.get("email_evidence_url", "").strip():
                    high_conf_no_evidence.append(l)
            except: pass
        
        if high_conf_no_evidence:
            lines.append("## ⚠️ UYARI: Yüksek confidence ama evidence_url eksik!")
            for l in high_conf_no_evidence[:10]:
                lines.append(f"- {l['full_name']} ({l['company']}) — conf:{l['email_confidence']} status:{l['email_status']}")
            lines.append("")
        
        # Şirket bazlı
        lines.append("## Şirket Bazlı Dağılım")
        companies = defaultdict(lambda: Counter())
        for l in leads:
            companies[l.get("company", "?")][l.get("email_status", "?")] += 1
        for company in sorted(companies):
            stats = companies[company]
            found_c = stats.get("found_public", 0)
            emp_c = stats.get("estimated_from_employee_pattern", 0)
            dom_c = stats.get("estimated_from_company_domain", 0)
            low_c = stats.get("low_confidence_guess", 0)
            lines.append(f"- **{company}**: {found_c}F {emp_c}E {dom_c}D {low_c}L")
        lines.append("")
        
        # Evidence summary
        lines.append("## Evidence Summary")
        evidence_by_company = defaultdict(list)
        for l in leads:
            if l.get("email_evidence_url", "").strip():
                evidence_by_company[l["company"]].append(l["email_evidence_url"])
        for company in sorted(evidence_by_company):
            urls = list(set(evidence_by_company[company]))
            lines.append(f"- **{company}**: {len(urls)} evidence URL(s)")
            for u in urls[:2]:
                lines.append(f"  - {u}")
        lines.append("")
        
        # Örnek kayıtlar
        lines.append("## Örnek Kayıtlar")
        lines.append("| Ad Soyad | Şirket | Email | Tahmini | Status | Conf | Evidence |")
        lines.append("|----------|--------|-------|---------|--------|------|----------|")
        for l in leads[:10]:
            ev = l.get("email_evidence_url", "")[:40] + "..." if len(l.get("email_evidence_url", "")) > 40 else l.get("email_evidence_url", "")
            lines.append(f"| {l.get('full_name','?')} | {l.get('company','?')} | "
                        f"{l.get('email','')} | {l.get('estimated_email','')[:30]} | "
                        f"{l.get('email_status','?')} | {l.get('email_confidence','?')} | {ev} |")
        lines.append("")
        
        # Metodoloji
        lines.append("## Metodoloji")
        lines.append("1. **found_public (95):** Lead'in email'i web'de açıkça bulundu")
        lines.append("2. **estimated_from_employee_pattern (85):** Aynı şirketten public çalışan email örneğinden pattern çıkarıldı")
        lines.append("3. **estimated_from_company_domain (70):** Şirket kariyer/iletişim sayfalarında domain kanıtı var; email pattern inferred")
        lines.append("4. **low_confidence_guess (50):** Hiç kanıt yok, sadece yaygın `first.last` pattern tahmini")
        lines.append("")
        lines.append("⚠️ estimated_email ASLA email kolonuna yazılmadı. Sadece public bulunan gerçek email'ler email kolonundadır.")
        
        return "\n".join(lines)


# ===========================================================================
# YARDIMCI: Kanıt ekleme
# ===========================================================================
def add_company_evidence(company: str, evidence_type: str, evidence_url: str,
                         pattern: str = "first.last", sample_emails: list = None,
                         source_note: str = ""):
    """COMPANY_EVIDENCE'a şirket kanıtı ekle."""
    COMPANY_EVIDENCE[company] = {
        "evidence_type": evidence_type,
        "evidence_url": evidence_url,
        "pattern": pattern,
        "sample_emails": sample_emails or [],
        "source_note": source_note,
    }


# ===========================================================================
# MAIN
# ===========================================================================
def load_leads(filepath: str) -> list[dict]:
    path = Path(filepath)
    if not path.exists():
        print(f"❌ Dosya bulunamadı: {filepath}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Email enrichment v3 — evidence-based")
    parser.add_argument("--input", "-i", default="data/leads_enriched.csv")
    parser.add_argument("--output", "-o", default="data/leads_email_enriched.csv")
    parser.add_argument("--report", "-r", default="data/email_enrichment_report.md")
    args = parser.parse_args()
    
    input_path = PROJECT_ROOT / args.input
    output_path = PROJECT_ROOT / args.output
    report_path = PROJECT_ROOT / args.report
    
    leads = load_leads(str(input_path))
    print(f"📂 {len(leads)} lead yüklendi ({input_path.name})")
    
    enricher = EmailEnricher()
    enriched = enricher.enrich(leads)
    enricher.save(enriched, str(output_path))
    
    report = enricher.generate_report(enriched)
    report_path.write_text(report, encoding="utf-8")
    print(f"📋 Rapor → {report_path}")
    
    print("\n" + "=" * 50)
    print("  EMAIL ENRICHMENT v3 TAMAMLANDI")
    print("=" * 50)


if __name__ == "__main__":
    main()
