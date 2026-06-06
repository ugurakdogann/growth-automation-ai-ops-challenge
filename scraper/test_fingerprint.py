"""fingerprint.com testi — daha kapsamlı bot tespiti"""
import asyncio
from scraper.anti_detect import create_stealth_context, HumanBehavior

async def test_fingerprint():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await create_stealth_context(
            browser,
            fingerprint={
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "timezone": "Europe/Istanbul",
                "locale": "tr-TR",
            }
        )
        page = await context.new_page()
        
        print("fingerprint.com test sayfasına gidiliyor...")
        await page.goto("https://fingerprint.com/products/bot-detection/", wait_until="networkidle")
        await HumanBehavior.random_delay(3, 5)
        
        await page.screenshot(path="fp_test_result.png")
        print("Sonuç: fp_test_result.png kaydedildi.")
        
        # Ayrıca pikatchu testi
        print("\npixelscan.net test sayfasına gidiliyor...")
        await page.goto("https://pixelscan.net/", wait_until="networkidle")
        await HumanBehavior.random_delay(3, 5)
        await page.screenshot(path="pixelscan_result.png")
        print("Sonuç: pixelscan_result.png kaydedildi.")
        
        await browser.close()

asyncio.run(test_fingerprint())
