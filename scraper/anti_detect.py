"""
Anti-Detect Katmanı
===================

Bu modülün tek görevi: Playwright tarayıcısını LinkedIn'in bot
dedektörlerine yakalanmayacak şekilde gizlemek.

İki katmanlı savunma:
  1. Teknik gizleme: navigator.webdriver, WebGL, font fingerprint
  2. Davranışsal gizleme: random bekleme, doğal scroll, insan gibi typing

Nasıl test edilir?
  https://bot.sannysoft.com/ adresine git.
  "You are not a bot" görürsen → başarılı.
  Herhangi bir kırmızı uyarı → bir şey eksik.
"""

import random
import time
import asyncio
from pathlib import Path
from typing import Optional

# Playwright import'ları (kullanım sırasında import edilecek)
# from playwright.async_api import BrowserContext, Page


# ---------------------------------------------------------------------------
# 1. KATMAN: Teknik Gizleme (Fingerprint)
# ---------------------------------------------------------------------------

# Playwright-stealth script'i — tarayıcının her sayfa yüklemesinde
# çalıştıracağı JavaScript kodu. Bunlar bot tespitini zorlaştırır.
STEALTH_SCRIPTS = [
    # navigator.webdriver override — EN KRITIK OLANI
    # Sadece defineProperty yetmez; property zaten true olarak ayarlanmis olabilir.
    # Bu override + --disable-blink-features=AutomationControlled flag'i birlikte kullanilir.
    """
    // Once mevcut property'i sil (configurable ise)
    delete navigator.webdriver;
    // Sonra yeniden tanimla
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });
    // Prototype uzerinden de override et (bazi testler prototype'a bakar)
    if (navigator.__proto__ && navigator.__proto__.webdriver !== undefined) {
        try {
            delete navigator.__proto__.webdriver;
        } catch(e) {}
    }
    """,
    
    # chrome.runtime'ı gizle
    """
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
    """,
    
    # Permissions API'sini normalleştir
    """
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
    );
    """,
    
    # Plugin'leri GERCEK PluginArray olarak taklit et
    # Bos plugin listesi, gercek Chrome'da da olabilir
    """
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const arr = Object.create(PluginArray.prototype);
            arr.item = function(i) { return undefined; };
            arr.namedItem = function(n) { return undefined; };
            arr.refresh = function() {};
            Object.defineProperty(arr, 'length', { value: 0 });
            return arr;
        }
    });
    """,
    
    # Languages taklidi
    """
    Object.defineProperty(navigator, 'languages', {
        get: () => ['tr-TR', 'tr', 'en-US', 'en'],
    });
    """,
    
    # Touch support gizle (headless'te yok)
    """
    Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 });
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
    """,
]


async def apply_stealth(context) -> None:
    """
    Bir browser context'e anti-detect JavaScript'lerini enjekte eder.
    
    context: Playwright BrowserContext (hem persistent hem normal)
    """
    for script in STEALTH_SCRIPTS:
        await context.add_init_script(script)


# ---------------------------------------------------------------------------
# 2. KATMAN: Davranışsal Gizleme (Human Behavior)
# ---------------------------------------------------------------------------

class HumanBehavior:
    """
    Tarayıcı hareketlerini insan gibi yapar.
    
    LinkedIn'in rate-limit algoritması şunlara bakar:
    - İstekler arası süre (sabit mi, değişken mi?)
    - Scroll hızı (sabit mi?)
    - Sayfada kalma süresi (çok kısa mı?)
    - Tıklama pattern'i (hep aynı koordinat mı?)
    
    Bu sınıf hepsini randomize eder.
    """
    
    @staticmethod
    async def random_delay(min_sec: float = 0.5, max_sec: float = 3.0) -> None:
        """İnsan gibi random bekle. Hiçbir insan tam 1 saniye beklemez."""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
    
    @staticmethod
    async def human_scroll(page, direction: str = "down", amount: int = None) -> None:
        """
        İnsan gibi scroll yap.
        
        Gerçek insan:
        - Sabit hızda scroll yapmaz
        - Bazen durup okur
        - Scroll miktarı değişkendir
        """
        if amount is None:
            amount = random.randint(200, 600)
        
        if direction == "down":
            scroll_code = f"window.scrollBy({{ top: {amount}, behavior: 'smooth' }})"
        else:
            scroll_code = f"window.scrollBy({{ top: -{amount}, behavior: 'smooth' }})"
        
        await page.evaluate(scroll_code)
        await HumanBehavior.random_delay(0.3, 1.5)
    
    @staticmethod
    async def human_type(page, selector: str, text: str) -> None:
        """
        İnsan gibi yazı yaz.
        
        Gerçek insan:
        - Her tuşa aynı hızda basmaz
        - Bazen duraksar (düşünür)
        - Harfler arası süre değişkendir
        """
        await page.click(selector)
        await HumanBehavior.random_delay(0.2, 0.5)
        
        for char in text:
            await page.type(selector, char, delay=random.randint(50, 200))
        
        await HumanBehavior.random_delay(0.3, 0.8)
    
    @staticmethod
    async def simulate_reading(page, min_sec: float = 3.0, max_sec: float = 8.0) -> None:
        """
        Sayfayı okuyormuş gibi yap.
        
        LinkedIn'de bir profili hemen kapatıp diğerine geçmek
        en büyük bot sinyalidir. İnsan profili inceler.
        """
        # Önce biraz scroll yap
        await HumanBehavior.human_scroll(page, "down", random.randint(100, 300))
        await HumanBehavior.random_delay(1.0, 2.0)
        
        # "Oku" (bekle)
        await HumanBehavior.random_delay(min_sec, max_sec)
        
        # Biraz daha scroll
        if random.random() > 0.3:  # %70 ihtimalle
            await HumanBehavior.human_scroll(page, "down", random.randint(200, 500))
        
        await HumanBehavior.random_delay(0.5, 1.5)


# ---------------------------------------------------------------------------
# 3. KATMAN: Context Factory
# ---------------------------------------------------------------------------

async def create_stealth_context(browser, fingerprint: dict) -> "BrowserContext":
    """
    Anti-detect özellikleriyle yeni bir browser context oluştur.
    
    browser: Playwright Browser objesi (launch edilmiş)
    fingerprint: ProfileManager'dan gelen Fingerprint bilgisi
    
    Döndürdüğü context:
    - navigator.webdriver = false
    - Belirtilen viewport, user_agent, timezone, locale ayarlanmış
    - Stealth script'ler enjekte edilmiş
    """
    # Context oluştur — fingerprint özelliklerini uygula
    context = await browser.new_context(
        viewport=fingerprint.get("viewport", {"width": 1920, "height": 1080}),
        user_agent=fingerprint.get("user_agent"),
        timezone_id=fingerprint.get("timezone", "Europe/Istanbul"),
        locale=fingerprint.get("locale", "tr-TR"),
        # Gerçek tarayıcı gibi görünmesi için ek ayarlar
        device_scale_factor=1,
        is_mobile=False,
        has_touch=False,
    )
    
    # Stealth script'leri enjekte et
    await apply_stealth(context)
    
    return context


# ---------------------------------------------------------------------------
# Bot testi
# ---------------------------------------------------------------------------

async def test_anti_detect():
    """
    Anti-detect'in çalışıp çalışmadığını test et.
    
    https://bot.sannysoft.com/ adresini açar ve sonuçları gösterir.
    """
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
            ]
        )
        context = await create_stealth_context(
            browser,
            fingerprint={
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "timezone": "Europe/Istanbul",
                "locale": "tr-TR",
            }
        )
        page = await context.new_page()
        
        print("Bot tespit test sayfasına gidiliyor...")
        await page.goto("https://bot.sannysoft.com/", wait_until="networkidle")
        
        # Sayfanın ekran görüntüsünü al
        await page.screenshot(path="bot_test_result.png")
        print("Sonuç: bot_test_result.png olarak kaydedildi.")
        print("Tüm testler yeşil (PASSED) olmalı, kırmızı (FAILED) varsa sorun var.")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_anti_detect())
