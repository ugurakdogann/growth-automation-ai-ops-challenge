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
- Email tahmini kanıt URL'si ve güven skoru bilgisiyle ayrı kolonda tutuldu.
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
- Tahmini email için kanıt URL'si: 181
- Gerçek email kolonuna tahmini email sızması: 0
- Reddedilen kayıt: 0

## Email Metodolojisi

Herkese açık kişisel HR email'i bulunmadığı için gerçek `email` alanı boş
bırakıldı.

Her şirket için resmi/herkese açık domain kanıt URL'si kaydedildi. Tahmini
emailler `first.last@domain` formatıyla üretildi ve yalnızca `estimated_email`
alanında tutuldu.

Her tahmini email için şu alanlar eklendi:

- `email_status`
- `email_confidence`
- `email_evidence_url`
- `email_pattern`
- `email_pattern_source_note`

Bu sayede tahmini email'ler doğrulanmış gerçek email gibi gösterilmedi.

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

## Challenge ile Uyum

Challenge mükemmel bir production ürünü değil, küçük ama çalışan ve mantıklı bir
sistem istiyordu. Bu repo şu akışı uçtan uca gösterir:

1. Lead toplama
2. Temizleme
3. Zenginleştirme
4. Lead puanlama
5. Kanıta dayalı email tahmini
6. Kişiselleştirilmiş outreach üretimi
7. Final çıktı doğrulama

Canlı ortama taşımak için sonraki adımlar CRM entegrasyonu, onaylı veri
kaynakları, `needs_review` lead'leri için insan kontrolü, yanıt sınıflandırma
ve gelen kutusu otomasyonu olabilir.
