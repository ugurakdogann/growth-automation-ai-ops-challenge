# Growth Automation & AI Ops Intern Challenge

Konuşarak Öğren için hazırlanmış input-driven growth automation prototipi.

Amaç: Türkiye'deki İK profesyonellerini hedefleyen bir lead listesi üretmek,
lead'leri zenginleştirmek, skorlamak ve kişiselleştirilmiş LinkedIn DM / cold
email mesajları hazırlamak.

## Son Durum

- Toplam lead: 181
- Şirket sayısı: 42
- Final dosya: `data/leads_final.xlsx`
- Mesaj dosyaları: `data/messages/`
- Gerçek public kişisel email: 0
- Tahmini email: 181, ayrı kolonda ve evidence URL ile
- Needs review: 6 lead

## Çalıştırma

```bash
pip install -r requirements.txt

# Veri zaten hazırsa bu adımdan başlanır.
python main.py
python scripts/email_enrich.py
python main.py
python scripts/verify_outputs.py
```

Yeni veri toplamak için:

```bash
python scripts/collect_leads.py --api-key SERPAPI_KEY --max 4
python main.py
python scripts/email_enrich.py
python main.py
python scripts/verify_outputs.py
```

Not: `scripts/email_enrich.py`, `leads_enriched.csv` üzerinden çalıştığı için
önce `python main.py` ile lead enrichment çıktısı üretilir. Sonra email alanları
merge edilsin diye `python main.py` tekrar çalıştırılır.

## Veri Toplama Metodu

Bu prototipte lead listesi Google/SerpAPI üzerinde indexlenmiş LinkedIn profil
sonuçlarından üretilmiştir:

```text
site:linkedin.com/in/ "İK" "Şirket Adı"
```

Toplanan temel alanlar:

- `full_name`
- `title`
- `company`
- `linkedin_url`
- `source`

Bu yaklaşım challenge için küçük ama çalışan bir prototip sunar. Production
ortamında Apollo, CRM export, izinli Sales Navigator workflow'u veya şirket
web sitelerinden manuel/yarı otomatik lead toplama tercih edilebilir.

## Pipeline

```text
input_leads.json
  -> ingestion
  -> cleaner
  -> lead enrichment
  -> email enrichment
  -> message generation
  -> verification
```

Ana dosyalar:

- `main.py`: pipeline orkestrasyonu
- `pipeline/ingestion.py`: CSV/JSON input okuma, kolon normalizasyonu
- `pipeline/cleaner.py`: duplicate ve veri temizliği
- `pipeline/enricher.py`: sektör, şirket büyüklüğü, pain point, English need, lead score
- `pipeline/generator.py`: LinkedIn DM ve cold email üretimi
- `scripts/collect_leads.py`: SerpAPI ile public search sonuçlarından lead toplama
- `scripts/email_enrich.py`: kanıt temelli email tahmini
- `scripts/email_evidence.py`: şirket domain evidence veritabanı
- `scripts/verify_outputs.py`: çıktı doğrulama

## Lead Enrichment

Her lead için eklenen alanlar:

- `sector`
- `company_size`
- `company_focus`
- `hr_role`
- `pain_point`
- `english_need`
- `outreach_angle`
- `needs_review`
- `lead_score`

Son doğrulamada HR role dağılımı:

- HR Generalist: 89
- CHRO / Director / Head: 27
- HRBP / İş Ortağı: 22
- HR Operations: 19
- L&D / Eğitim: 9
- Talent Acquisition: 9
- Belirsiz: 6

## Email Enrichment

Public kişisel HR email'i bulunmadığı için `E-posta` kolonu boş bırakılmıştır.
Tahmini emailler `Tahmini E-posta` kolonunda tutulur.

Email status mantığı:

| Status | Açıklama | Confidence |
| --- | --- | --- |
| `found_public` | Lead'in kendi public email'i bulundu | 95 |
| `estimated_from_employee_pattern` | Aynı şirketten public çalışan email örneğiyle pattern çıkarıldı | 85 |
| `estimated_from_company_domain` | Resmi şirket domain kanıtı var, email pattern tahmin edildi | 70 |
| `low_confidence_guess` | Kanıt yok, düşük güvenli tahmin | 50 |

Mevcut final sonuç:

- `found_public`: 0
- `estimated_from_employee_pattern`: 0
- `estimated_from_company_domain`: 181
- `low_confidence_guess`: 0
- `Email Kanit URL`: 181/181 dolu

Önemli: Tahmini email hiçbir zaman gerçek email kolonuna yazılmaz.

## Outreach Mesajları

Her lead için iki çıktı üretilir:

- LinkedIn DM: kısa, profesyonel B2B mesaj
- Cold email: konu satırı ve daha detaylı değer önerisi

Mesajlar şirket, rol, pain point, English need ve outreach angle alanlarını kullanır.
Firma bazlı Markdown çıktıları `data/messages/` altındadır.

## Verification

```bash
python scripts/verify_outputs.py
```

Son doğrulama:

- `leads_final.xlsx`: mevcut
- Excel satır: 181
- Excel `E-posta` dolu: 0
- Excel `Tahmini E-posta` dolu: 181
- Excel `Email Kanit URL` dolu: 181
- Email leak: yok
- Rejected: 0

## Teslim Dosyaları

- `SUBMISSION_SUMMARY.md`
- `README.md`
- `requirements.txt`
- `main.py`
- `pipeline/`
- `scripts/`
- `data/input_leads.json`
- `data/leads_clean.csv`
- `data/leads_enriched.csv`
- `data/leads_email_enriched.csv`
- `data/leads_final.xlsx`
- `data/email_enrichment_report.md`
- `data/messages/`
