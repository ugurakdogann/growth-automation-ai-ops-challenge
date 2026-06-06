"""
main.py — Input-Driven Growth Automation Pipeline
==================================================

Konuşarak Öğren Intern Challenge
Veri kaynağından bağımsız, her türlü CSV/JSON lead listesini işler.

Kullanım:
    python main.py                        # Otomatik input bulur
    python main.py --input data/leads.csv # Belirli dosya
    python main.py --skip-enrich          # Sadece temizle + mesaj
    python main.py --output-dir out/      # Özel çıktı klasörü

Input önceliği:
    1. --input ile belirtilen dosya
    2. data/input_leads.csv
    3. data/input_leads.json
"""

import argparse
import sys
import time
from pathlib import Path

# Windows PowerShell may default to cp1254, which cannot print emoji/status
# glyphs used in this demo. Force UTF-8 for a smooth one-command run.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# Proje kökünü Python yoluna ekle
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.ingestion import LeadIngestor
from pipeline.cleaner import LeadCleaner
from pipeline.enricher import LeadEnricher
from pipeline.generator import OutreachGenerator


def find_input_file(explicit: str = None) -> Path:
    """Input dosyasini otomatik bul."""
    if explicit:
        path = Path(explicit)
        if path.exists():
            return path
        print(f"❌ Belirtilen dosya bulunamadı: {explicit}")
        sys.exit(1)
    
    data_dir = PROJECT_ROOT / "data"
    candidates = [
        data_dir / "input_leads.csv",
        data_dir / "input_leads.json",
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate
    
    print("❌ Hiçbir input dosyası bulunamadı.")
    print("   Şu konumlara bakıldı:")
    for c in candidates:
        print(f"   - {c}")
    print("\n   Kullanım: python main.py --input dosya.csv")
    sys.exit(1)


def merge_email_enrichment(leads: list[dict], email_file: str) -> list[dict]:
    """Email enrichment alanlarını lead'lere merge et."""
    import csv
    
    with open(email_file, "r", encoding="utf-8-sig") as f:
        email_leads = list(csv.DictReader(f))
    
    # linkedin_url → email data index
    email_by_url = {}
    email_by_name_co = {}
    for el in email_leads:
        url = el.get("linkedin_url", "").strip()
        if url:
            email_by_url[url.lower()] = el
        key = (el.get("full_name", "").strip().lower(), 
               el.get("company", "").strip().lower())
        email_by_name_co[key] = el
    
    email_fields = [
        "estimated_email", "email_status", "email_confidence",
        "email_evidence_url", "email_pattern_source_note", "email_pattern",
        "email_notes", "searched_queries", "found_urls",
    ]
    
    merged = 0
    for lead in leads:
        url = lead.get("linkedin_url", "").strip().lower()
        key = (lead.get("full_name", "").strip().lower(),
               lead.get("company", "").strip().lower())
        
        match = email_by_url.get(url) or email_by_name_co.get(key)
        if match:
            for field in email_fields:
                lead[field] = match.get(field, "")
            # email varsa koru, email enrichment'ten gelen gerçek email'i de taşı
            if not lead.get("email", "").strip() and match.get("email", "").strip():
                lead["email"] = match["email"]
            merged += 1
    
    print(f"  {merged}/{len(leads)} lead'e email alanları merge edildi")
    return leads


def run_pipeline(input_file: Path, output_dir: Path, 
                 skip_enrich: bool = False, skip_generate: bool = False):
    """Tüm pipeline'i calistir."""
    start_time = time.time()
    
    print("=" * 60)
    print("  GROWTH AUTOMATION PIPELINE v2")
    print("  Input-Driven | Konuşarak Öğren Challenge")
    print("=" * 60)
    
    # -------------------------------------------------------------------
    # AŞAMA 1: Ingestion
    # -------------------------------------------------------------------
    print(f"\n📥 AŞAMA 1: Input → {input_file.name}")
    ingestor = LeadIngestor(min_expected=100)
    leads, rejected = ingestor.ingest(str(input_file))
    
    if rejected:
        ingestor.save_rejected(rejected, str(output_dir / "rejected_leads.csv"))
    
    if not leads:
        print("❌ Geçerli kayıt yok. Pipeline durdu.")
        return
    
    # -------------------------------------------------------------------
    # AŞAMA 2: Clean
    # -------------------------------------------------------------------
    print(f"\n🧹 AŞAMA 2: Temizleme")
    cleaner = LeadCleaner()
    cleaned = cleaner.clean(leads)
    cleaner.save(cleaned, str(output_dir / "leads_clean.csv"))
    
    if skip_enrich and skip_generate:
        print(f"\n✅ Pipeline tamamlandı (--skip-enrich --skip-generate).")
        return
    
    # -------------------------------------------------------------------
    # AŞAMA 3: Enrich
    # -------------------------------------------------------------------
    if not skip_enrich:
        print(f"\n🤖 AŞAMA 3: AI Zenginleştirme")
        enricher = LeadEnricher()
        enriched = enricher.enrich(cleaned)
        enricher.save(enriched, str(output_dir / "leads_enriched.csv"))
    else:
        enriched = cleaned
        print(f"\n⏭️  AŞAMA 3: Atladı (--skip-enrich)")
    
    # -------------------------------------------------------------------
    # AŞAMA 3.5: Email Enrichment Merge
    # -------------------------------------------------------------------
    email_file = output_dir / "leads_email_enriched.csv"
    if email_file.exists():
        print(f"\n📧 AŞAMA 3.5: Email enrichment merge")
        enriched = merge_email_enrichment(enriched, str(email_file))
    else:
        print(f"\n📧 AŞAMA 3.5: Email enrichment atlandı (leads_email_enriched.csv yok)")
        print(f"   python scripts/email_enrich.py")
    
    # -------------------------------------------------------------------
    # AŞAMA 4: Generate
    # -------------------------------------------------------------------
    if not skip_generate:
        print(f"\n✍️  AŞAMA 4: Outreach Mesajları")
        generator = OutreachGenerator()
        final = generator.generate(enriched)
        generator.save_data(final, str(output_dir / "leads_final.xlsx"))
        generator.save_messages_md(final, str(output_dir / "messages"))
    else:
        final = enriched
        print(f"\n⏭️  AŞAMA 4: Atladı (--skip-generate)")
    
    # -------------------------------------------------------------------
    # ÖZET
    # -------------------------------------------------------------------
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("  ✅ PIPELINE TAMAMLANDI")
    print("=" * 60)
    print(f"  Süre: {elapsed:.1f}s")
    print(f"  Input: {input_file.name}")
    print(f"  Ham kayıt: {ingestor.stats['loaded']}")
    print(f"  Reddedilen: {ingestor.stats['rejected']}")
    print(f"  Duplicate: {ingestor.stats['duplicates']}")
    print(f"  Temiz: {len(cleaned)}")
    if not skip_enrich:
        print(f"  Zenginleştirilmiş: {len(enriched)}")
    if not skip_generate:
        print(f"  Mesaj üretilmiş: {len(final)}")
    print(f"\n  Çıktılar → {output_dir}/")
    print(f"    leads_clean.csv")
    if not skip_enrich:
        print(f"    leads_enriched.csv")
    if not skip_generate:
        print(f"    leads_final.xlsx")
        print(f"    messages/")
    if rejected:
        print(f"    rejected_leads.csv")
    print("=" * 60)
    
    # -------------------------------------------------------------------
    # ÖRNEK
    # -------------------------------------------------------------------
    if final and not skip_generate:
        print("\n📱 ÖRNEK MESAJ:")
        generator.preview(final[0])
    
    # Verification önerisi
    print(f"\n💡 Doğrulamak için: python scripts/verify_outputs.py")


def main():
    parser = argparse.ArgumentParser(
        description="Growth Automation Pipeline — Input-Driven Lead Processor"
    )
    parser.add_argument("--input", "-i", help="Input dosyası (CSV veya JSON)")
    parser.add_argument("--output-dir", "-o", default="data", 
                        help="Çıktı klasörü (varsayılan: data/)")
    parser.add_argument("--skip-enrich", action="store_true",
                        help="AI zenginleştirmeyi atla")
    parser.add_argument("--skip-generate", action="store_true",
                        help="Mesaj üretimini atla")
    args = parser.parse_args()
    
    input_file = find_input_file(args.input)
    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    run_pipeline(
        input_file=input_file,
        output_dir=output_dir,
        skip_enrich=args.skip_enrich,
        skip_generate=args.skip_generate,
    )


if __name__ == "__main__":
    main()
