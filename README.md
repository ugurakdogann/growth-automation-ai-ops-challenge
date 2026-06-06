# Growth Automation & AI Ops Intern Challenge

Konuşarak Öğren için hazırlanmış girdi odaklı growth automation prototipi.

Amaç: Türkiye'deki İK profesyonellerinden oluşan bir lead listesi üretmek,
bu lead'leri temizlemek, zenginleştirmek, puanlamak ve kişiselleştirilmiş
LinkedIn DM / cold email mesajları hazırlamak.

## Son Durum

- Toplam lead: 181
- Şirket sayısı: 42
- Final dosya: `data/leads_final.xlsx`
- Mesaj dosyaları: `data/messages/`
- Gerçek herkese açık kişisel email: 0
- Tahmini email: 181, ayrı kolonda ve güven skoru ile
- Needs review: 6 lead

## Çalıştırma

```bash
pip install -r requirements.txt

# Hazır veriyle çalıştırma
python main.py
python scripts/email_enrich.py
python main.py
python scripts/verify_outputs.py
```

Yeni veri toplamak için:

```bash
python scripts/collect_leads.py --api-key YOUR_SERPAPI_KEY --max 4
python main.py
python scripts/email_enrich.py
python main.py
python scripts/verify_outputs.py
```

API key ortam değişkeni ile de verilebilir:

```powershell
$env:SERPAPI_KEY="YOUR_SERPAPI_KEY"
python scripts/collect_leads.py --max 4
```

Güvenlik nedeniyle repo içinde gerçek SerpAPI / Google Search API key'i yoktur.
Mevcut `data/input_leads.json` hazır örnek veri olarak gelir. Sıfırdan veri
toplamak isteyen kişi kendi API key'ini kullanmalıdır.

Not: `scripts/email_enrich.py`, `leads_enriched.csv` üzerinden çalıştığı için
önce `python main.py` ile lead zenginleştirme çıktısı üretilir. Sonra email
alanları final dosyaya merge edilsin diye `python main.py` tekrar çalıştırılır.

## Veri Toplama Metodu

Bu prototipte lead listesi, Google Search sonuçlarını kullanan SerpAPI üzerinden
indexlenmiş LinkedIn profil sonuçlarından üretilmiştir.

Örnek sorgu:

```text
site:linkedin.com/in/ "İK" "Şirket Adı"
```

Toplanan temel alanlar:

- `full_name`
- `title`
- `company`
- `linkedin_url`
- `source`

Bu yaklaşım challenge için küçük ama çalışan bir prototip sunar. Canlı ortamda
Apollo, CRM export, izinli Sales Navigator iş akışı veya şirket web sitelerinden
manuel/yarı otomatik lead toplama tercih edilebilir.

## İş Akışı

```text
input_leads.json
  -> veri alma
  -> temizleme
  -> lead zenginleştirme
  -> email zenginleştirme
  -> mesaj üretimi
  -> doğrulama
```

Ana dosyalar:

- `main.py`: pipeline orkestrasyonu
- `pipeline/ingestion.py`: CSV/JSON input okuma, kolon normalizasyonu
- `pipeline/cleaner.py`: duplicate ve veri temizliği
- `pipeline/enricher.py`: sektör, şirket büyüklüğü, pain point, English need, lead score
- `pipeline/generator.py`: LinkedIn DM ve cold email üretimi
- `scripts/collect_leads.py`: SerpAPI ile herkese açık arama sonuçlarından lead toplama
- `scripts/email_enrich.py`: kanıt temelli email tahmini
- `scripts/email_evidence.py`: şirket domain kanıt veritabanı
- `scripts/verify_outputs.py`: çıktı doğrulama

## Script Rehberi

### `main.py`

Pipeline'ın ana giriş noktasıdır. Önce input dosyasını bulur, sonra sırasıyla
veri alma, temizleme, zenginleştirme ve mesaj üretimi adımlarını çalıştırır.

Input önceliği:

1. `--input` ile verilen dosya
2. `data/input_leads.csv`
3. `data/input_leads.json`

Ürettiği temel çıktılar:

- `data/leads_clean.csv`
- `data/leads_enriched.csv`
- `data/leads_final.xlsx`
- `data/messages/`

Eğer `data/leads_email_enriched.csv` varsa, email enrichment sonucu final Excel
dosyasına ayrıca merge edilir. Bu yüzden email enrichment çalıştırıldıktan sonra
`main.py` ikinci kez çalıştırılır.

### `scripts/collect_leads.py`

Yeni lead toplamak için kullanılan script'tir. SerpAPI üzerinden Google Search
sonuçlarını çağırır ve Google'da indexlenmiş herkese açık LinkedIn profil
sonuçlarını toplar.

Kullandığı sorgu mantığı:

```text
site:linkedin.com/in/ "İK" "Şirket Adı"
```

Script her sonuçtan isim, unvan, şirket, LinkedIn URL ve kaynak bilgisini
çıkarmaya çalışır. Sonuçlar pipeline'ın okuyabileceği input formatına yazılır.
Repo içinde gerçek API key yoktur; kullanıcı kendi SerpAPI key'ini `--api-key`
parametresiyle veya `SERPAPI_KEY` ortam değişkeniyle verir.

### `pipeline/ingestion.py`

CSV veya JSON lead dosyasını okur. Farklı kolon adlarını standart alanlara
normalize eder. Örneğin `name`, `full_name`, `company_name`, `linkedin` gibi
alanları pipeline'ın beklediği ortak şemaya çevirir.

Standart alanlar:

- `full_name`
- `title`
- `company`
- `linkedin_url`
- `email`
- `source`

Eksik veya tanınmayan kolonlar pipeline'ı kırmadan boş değerle devam eder.

### `pipeline/cleaner.py`

Ham lead listesini temizler. Aynı LinkedIn URL'ye veya aynı kişi/şirket
kombinasyonuna sahip tekrarları azaltır. Boşluk, eksik alan ve format
tutarsızlıklarını sadeleştirir.

Amaç final dosyada aynı kişinin tekrar tekrar görünmesini engellemek ve
enrichment adımına daha temiz veri göndermektir.

### `pipeline/enricher.py`

Lead'lere growth/outreach için gerekli bağlamı ekler. Bu adım canlı web
araştırması yapmaz; şirket veritabanı, unvan anahtar kelimeleri ve kural tabanlı
mantık kullanır.

Eklediği başlıca alanlar:

- `sector`: şirketin sektörü
- `company_size`: şirket büyüklüğü
- `company_focus`: şirket odağı
- `hr_role`: unvana göre HR rol kategorisi
- `pain_point`: role ve sektöre göre olası problem alanı
- `english_need`: İngilizce eğitim ihtiyacı skoru
- `outreach_angle`: mesajda kullanılacak yaklaşım
- `needs_review`: şüpheli lead'lerde insan kontrolü bayrağı
- `lead_score`: lead öncelik puanı

Türkçe karakter normalizasyonu içerir. Bu sayede `İK`, `İşe Alım`, `İnsan
Kaynakları`, `Yetenek Kazanımı` gibi başlıklar daha doğru sınıflandırılır.

### `scripts/email_enrich.py`

Email tahmini için kullanılır. `data/leads_enriched.csv` dosyasını okur,
şirket-domain kanıtlarına bakar ve tahmini email alanlarını üretir.

Önemli prensip: Tahmini email hiçbir zaman gerçek `email` alanına yazılmaz.
Gerçek kişisel email bulunmadıysa `email` boş kalır; tahmin ayrı alanlarda
tutulur.

Teknik email enrichment dosyasında ürettiği alanlar:

- `estimated_email`
- `email_status`
- `email_confidence`
- `email_evidence_url`
- `email_pattern`
- `email_pattern_source_note`

Final Excel dosyasında ise sade görünüm için yalnızca tahmini email, email
durumu ve güven skoru gösterilir. Kanıt URL, pattern, kaynak notu, arama
sorguları ve bulunan URL gibi teknik alanlar final Excel'e yazılmaz.

### `scripts/email_evidence.py`

Email enrichment için kullanılan şirket-domain kanıt veritabanıdır. Her şirket
için resmi domain, kanıt URL'si ve kaynak notu tutulur. Böylece tahmini email'in
hangi kanıta dayanarak üretildiği teknik CSV ve rapor dosyasında şeffaf şekilde
görülebilir.

### `pipeline/generator.py`

Zenginleştirilmiş lead verisini kullanarak outreach çıktısı üretir. Her lead
için kısa LinkedIn DM ve cold email metni oluşturur. Mesajlarda şirket, rol,
pain point, English need ve outreach angle alanları kullanılır.

Final Excel dosyasını ve firma bazlı Markdown mesaj dosyalarını üretir.

### `scripts/verify_outputs.py`

Teslimden önce final dosyaları kontrol etmek için kullanılır. Excel dosyasının
varlığını, satır sayısını, email alanlarını, tahmini email'in gerçek email
kolonuna sızıp sızmadığını ve teknik email kolonlarının final Excel'den
kaldırıldığını kontrol eder.

Bu script'in amacı reviewer'a sadece çıktı değil, çıktının temel kalite
kontrollerinden geçtiğini de göstermektir.

## Lead Zenginleştirme

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

Son doğrulamada HR rol dağılımı:

- HR Generalist: 89
- CHRO / Director / Head: 27
- HRBP / İş Ortağı: 22
- HR Operations: 19
- L&D / Eğitim: 9
- Talent Acquisition: 9
- Belirsiz: 6

## Email Zenginleştirme

Herkese açık kişisel HR email'i bulunmadığı için `E-posta` kolonu boş
bırakılmıştır. Tahmini emailler `Tahmini E-posta` kolonunda tutulur.

Email status mantığı:

| Status | Açıklama | Güven Skoru |
| --- | --- | --- |
| `found_public` | Lead'in kendi herkese açık email'i bulundu | 95 |
| `estimated_from_employee_pattern` | Aynı şirketten herkese açık çalışan email örneğiyle pattern çıkarıldı | 85 |
| `estimated_from_company_domain` | Resmi şirket domain kanıtı var, email pattern tahmin edildi | 70 |
| `low_confidence_guess` | Kanıt yok, düşük güvenli tahmin | 50 |

Mevcut final sonuç:

- `found_public`: 0
- `estimated_from_employee_pattern`: 0
- `estimated_from_company_domain`: 181
- `low_confidence_guess`: 0
- Final Excel'de teknik email kanıt/pattern kolonları kaldırıldı

Önemli: Tahmini email hiçbir zaman gerçek email kolonuna yazılmaz.

## Outreach Mesajları

Her lead için iki çıktı üretilir:

- LinkedIn DM: kısa, profesyonel B2B mesaj
- Cold email: konu satırı ve daha detaylı değer önerisi

Mesajlar şirket, rol, pain point, English need ve outreach angle alanlarını
kullanır. Firma bazlı Markdown çıktıları `data/messages/` altındadır.

## Doğrulama

```bash
python scripts/verify_outputs.py
```

Son doğrulama:

- `leads_final.xlsx`: mevcut
- Excel satır: 181
- Excel `E-posta` dolu: 0
- Excel `Tahmini E-posta` dolu: 181
- Excel teknik email kolonları sadeleştirildi
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
