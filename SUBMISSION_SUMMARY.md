# Teslim Özeti

## Proje

Konuşarak Öğren Growth Automation & AI Ops Intern Challenge için hazırlanmış
çalışan bir prototip.

Bu repo; HR odaklı lead toplama, lead temizleme, zenginleştirme, lead puanlama,
kanıta dayalı email tahmini ve kişiselleştirilmiş outreach mesaj üretimi için
uçtan uca çalışan bir iş akışı içerir.

## Neler Yapıldı?

- CSV/JSON veriyle çalışabilen girdi odaklı lead pipeline kuruldu.
- SerpAPI/Google Search üzerinden herkese açık LinkedIn profil sonuçlarından lead toplama betiği yazıldı.
- 42 Türkiye şirketinden 181 HR ilişkili lead hazırlandı.
- Duplicate temizleme ve veri normalizasyonu yapıldı.
- Şirket sektörü, şirket büyüklüğü, HR rolü, pain point, English need ve outreach angle üretildi.
- Lead puanı hesaplama sistemi eklendi.
- Email tahmini güven skoru bilgisiyle ayrı kolonda tutuldu.
- Her lead için LinkedIn DM ve cold email üretildi.
- Final çıktıları doğrulayan kontrol betiği eklendi.

## Veri Toplama

Ana veri seti, Google'da indexlenmiş LinkedIn profil sonuçlarının SerpAPI ile
aranmasıyla toplandı. Toplama betiği şu formatta sorgular üretir:

```text
site:linkedin.com/in/ "İK" "Turkcell"
```

Veri toplama betiği:

```bash
python scripts/collect_leads.py --api-key YOUR_SERPAPI_KEY --max 4
```

Güvenlik nedeniyle repo içinde gerçek SerpAPI / Google Search API key'i yoktur.
Kullanıcı kendi key'ini `--api-key` parametresiyle verebilir veya `SERPAPI_KEY`
ortam değişkeni olarak tanımlayabilir.

## Final Çıktılar

- Final lead dosyası: `data/leads_final.xlsx`
- Firma bazlı mesaj dosyaları: `data/messages/`
- Email kanıt raporu: `data/email_enrichment_report.md`

Doğrulanmış final sayılar:

- Toplam lead: 181
- Gerçek herkese açık kişisel email: 0
- Tahmini email: 181
- Final Excel'de teknik email kanıt/pattern kolonları kaldırıldı
- Gerçek email kolonuna tahmini email sızması: 0
- Reddedilen kayıt: 0

## Email Metodolojisi

Herkese açık kişisel HR email'i bulunmadığı için gerçek `email` alanı boş
bırakıldı.

Her şirket için resmi/herkese açık domain kanıt URL'si teknik enrichment
dosyasında kaydedildi. Tahmini emailler `first.last@domain` formatıyla üretildi
ve yalnızca `estimated_email` alanında tutuldu.

Teknik email enrichment dosyasında her tahmini email için şu alanlar eklendi:

- `email_status`
- `email_confidence`
- `email_evidence_url`
- `email_pattern`
- `email_pattern_source_note`

Final Excel dosyasında ise sade görünüm için yalnızca tahmini email, email
durumu ve güven skoru gösterildi. Kanıt URL, pattern, kaynak notu, arama
sorguları ve bulunan URL gibi teknik alanlar final Excel'e yazılmadı. Bu sayede
tahmini email'ler doğrulanmış gerçek email gibi gösterilmedi.

## Nasıl Çalıştırılır?

Hazır veriyle pipeline çalıştırmak için:

```bash
pip install -r requirements.txt
python main.py
python scripts/email_enrich.py
python main.py
python scripts/verify_outputs.py
```

Sıfırdan yeni lead toplamak için:

```bash
python scripts/collect_leads.py --api-key YOUR_SERPAPI_KEY --max 4
python main.py
python scripts/email_enrich.py
python main.py
python scripts/verify_outputs.py
```

Ortam değişkeni ile kullanım:

```powershell
$env:SERPAPI_KEY="YOUR_SERPAPI_KEY"
python scripts/collect_leads.py --max 4
```
