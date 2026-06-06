"""
LinkedIn Scraper
================

Profil yöneticisi + anti-detect katmanını kullanarak LinkedIn
profillerinden veri çeker.

Çalışma mantığı:
  1. Profil yöneticisinden sıradaki browser profilini al
  2. O profilin user_data_dir'i ile tarayıcı başlat
     → Eğer daha önce login olduysan çerezler hazır, tekrar login gerekmez
  3. Anti-detect katmanını uygula
  4. Profili ziyaret et, veriyi çek
  5. Profil yöneticisine "1 profil çektim" kaydını düş

İlk kullanım:
  Tarayıcı açılır, LinkedIn'e manuel login olursun.
  Sonraki çalıştırmalarda oturum hazırdır.
"""

import asyncio
import csv
import json
import random
from pathlib import Path
from typing import Optional
from datetime import datetime

# Bizim modüllerimiz
from scraper.profile_manager import ProfileManager, BrowserProfile, Fingerprint
from scraper.anti_detect import HumanBehavior


class LinkedinScraper:
    """
    LinkedIn profil scraping motoru.
    
    Kullanım:
        pm = ProfileManager()
        pm.setup_profiles()
        
        scraper = LinkedinScraper(pm)
        await scraper.login_once()                    # İlk sefer: elle login ol
        leads = await scraper.scrape_profiles(urls)   # Verileri çek
    """
    
    def __init__(self, profile_manager: ProfileManager, headless: bool = False):
        self.pm = profile_manager
        self.headless = headless
        self.human = HumanBehavior()
        
        # Eğer headless çalışıyorsak bazı stealth'ler çalışmayabilir
        if headless:
            print("⚠️  Headless mod: LinkedIn tespit edebilir. Test için headful önerilir.")
    
    async def _launch_browser_for_profile(self, bp: BrowserProfile):
        """
        Bir browser profili için yeni tarayıcı başlat.
        
        launch_persistent_context: 
          - user_data_dir = çerezlerin, oturumun saklandığı klasör
          - Her profil için AYRI bir tarayıcı süreci başlatır
          - Tıpkı AdsPower'ın her profil için ayrı tarayıcı açması gibi
        """
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        
        fp = bp.fingerprint
        
        # Anti-otomasyon flag'lerini kaldir
        args = [
            "--disable-blink-features=AutomationControlled",  # navigator.webdriver gizler
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
        
        # Persistent context = tarayıcı + context tek seferde
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(bp.user_data_dir),
            headless=False,  # LinkedIn için headful şart (headless %90 ban)
            viewport=fp.viewport,
            user_agent=fp.user_agent,
            timezone_id=fp.timezone,
            locale=fp.locale,
            args=args,
            # Ek güvenlik: otomasyon flag'lerini kaldır
            ignore_default_args=["--enable-automation"],
        )
        
        # Anti-detect script'leri enjekte et
        from scraper.anti_detect import apply_stealth
        await apply_stealth(context)
        
        return playwright, context
    
    async def login_once(self):
        """
        İlk çalıştırmada: tarayıcıyı aç, LinkedIn'e manuel login ol.
        
        Bu sadece bir kere yapılır. Sonrasında user_data_dir'deki
        çerezler sayesinde otomatik login olunur.
        """
        bp = self.pm.get_next_profile()
        playwright, context = await self._launch_browser_for_profile(bp)
        
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")
        
        print(f"\n{'='*60}")
        print(f"  Browser profili: {bp.fingerprint.name}")
        print(f"  LinkedIn login sayfası açıldı.")
        print(f"  Lütfen manuel olarak login ol.")
        print(f"  Login olduktan sonra tarayıcıyı kapatma,")
        print(f"  bu terminale gelip ENTER'a bas.")
        print(f"{'='*60}\n")
        
        input("Login olduktan sonra ENTER'a bas...")
        
        # Oturumu kontrol et
        await page.goto("https://www.linkedin.com/feed/")
        title = await page.title()
        
        if "LinkedIn" in title and "login" not in title.lower():
            print(f"✅ Login başarılı! Profil '{bp.fingerprint.name}' hazır.")
        else:
            print(f"⚠️  Login doğrulanamadı. Sayfa başlığı: {title}")
        
        await context.close()
        await playwright.stop()
    
    async def scrape_profile(self, profile_url: str) -> dict:
        """
        Tek bir LinkedIn profilini ziyaret et ve verileri çıkar.
        
        Döndürdüğü dict:
            {
                "full_name": "Ahmet Yılmaz",
                "title": "İK Direktörü",
                "company": "XYZ A.Ş.",
                "linkedin_url": "https://...",
                "location": "İstanbul, Türkiye",
                "about": "",
                "scraped_at": "2025-06-05 14:30:00"
            }
        """
        # Sıradaki browser profilini al
        bp = self.pm.get_next_profile()
        playwright, context = await self._launch_browser_for_profile(bp)
        
        try:
            page = await context.new_page()
            
            # Profil sayfasına git
            print(f"  [{bp.fingerprint.name}] Ziyaret: {profile_url}")
            await page.goto(profile_url, wait_until="domcontentloaded")
            
            # İnsan gibi bekle + scroll yap
            await self.human.simulate_reading(page, min_sec=2.0, max_sec=5.0)
            
            # Verileri çıkar
            data = await self._extract_profile_data(page, profile_url)
            
            # Kaydı işle
            self.pm.record_scrape(bp)
            
            print(f"  ✅ {data.get('full_name', '?')} — {data.get('title', '?')}")
            return data
            
        finally:
            await context.close()
            await playwright.stop()
    
    async def _extract_profile_data(self, page, profile_url: str) -> dict:
        """Sayfa DOM'undan profil verilerini kazı."""
        
        # LinkedIn'in CSS sınıfları sık değişir, bu yüzden
        # birden fazla seçici deneriz (fallback'li)
        
        data = {
            "full_name": "",
            "title": "",
            "company": "",
            "linkedin_url": profile_url,
            "location": "",
            "about": "",
            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        try:
            # İsim — profil sayfasının en üstündeki h1
            name_el = await page.query_selector("h1")
            if name_el:
                data["full_name"] = (await name_el.inner_text()).strip()
            
            # Headline / Ünvan
            headline_el = await page.query_selector("div.text-body-medium")
            if headline_el:
                data["title"] = (await headline_el.inner_text()).strip()
            
            # Mevcut şirket
            # LinkedIn'de mevcut pozisyon genelde experience bölümünde ilk sıradadır
            company_els = await page.query_selector_all(
                "span[aria-hidden='true']"
            )
            # Deneyim bölümünden şirket adını bulmaya çalış
            for el in company_els:
                text = (await el.inner_text()).strip()
                if text and len(text) > 1 and "·" not in text:
                    # İlk anlamlı metin genelde şirket adıdır
                    if not data["company"] and text != data["full_name"]:
                        data["company"] = text
                        break
            
            # Konum
            location_el = await page.query_selector(
                "span.text-body-small.inline.t-black--light"
            )
            if location_el:
                data["location"] = (await location_el.inner_text()).strip()
            
            # About bölümü
            about_el = await page.query_selector("section.summary div.display-flex")
            if about_el:
                data["about"] = (await about_el.inner_text()).strip()[:500]
            
        except Exception as e:
            print(f"  ⚠️  Veri çıkarma hatası: {e}")
        
        return data
    
    async def scrape_profiles(self, profile_urls: list[str]) -> list[dict]:
        """
        Birden fazla profili sırayla çek.
        
        Profil yöneticisi otomatik rotasyon yapar.
        Her profile insan gibi davranır.
        """
        results = []
        total = len(profile_urls)
        
        print(f"\n{'='*60}")
        print(f"  Toplam {total} profil çekilecek")
        print(f"  Profil rotasyonu: her browser profili max {self.pm.max_per_profile} çeker")
        print(f"{'='*60}\n")
        
        for i, url in enumerate(profile_urls, 1):
            print(f"[{i}/{total}]", end=" ")
            
            # Hata olursa devam et, tüm pipeline'ı kırma
            try:
                data = await self.scrape_profile(url)
                results.append(data)
            except Exception as e:
                print(f"  ❌ Hata: {e}")
                results.append({
                    "linkedin_url": url,
                    "error": str(e),
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
            
            # Profiller arası bekleme (rate-limit koruması)
            if i < total:
                delay = random.uniform(5, 15)  # 5-15 saniye arası
                print(f"  ⏳ {delay:.0f}s bekleniyor...")
                await asyncio.sleep(delay)
        
        # Sonuçları göster
        success = sum(1 for r in results if "error" not in r)
        print(f"\n{'='*60}")
        print(f"  Tamamlandı: {success}/{total} başarılı")
        print(self.pm.status())
        print(f"{'='*60}")
        
        return results
    
    def save_results(self, results: list[dict], filepath: str = None):
        """Sonuçları CSV olarak kaydet."""
        if filepath is None:
            project_root = Path(__file__).parent.parent
            filepath = project_root / "data" / "leads_raw.csv"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if not results:
            print("Kaydedilecek veri yok.")
            return
        
        fieldnames = results[0].keys()
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"✅ {len(results)} kayıt → {filepath}")


# ---------------------------------------------------------------------------
# Hızlı test
# ---------------------------------------------------------------------------
async def main():
    pm = ProfileManager()
    pm.setup_profiles()
    
    scraper = LinkedinScraper(pm)
    
    # İlk çalıştırma: login ol
    print("İlk adım: LinkedIn'e login olman gerekiyor.")
    await scraper.login_once()


if __name__ == "__main__":
    asyncio.run(main())
