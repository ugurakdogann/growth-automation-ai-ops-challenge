"""Anti-detect testleri — sonuç bekleyen versiyon"""
import asyncio
import sys
sys.path.insert(0, ".")

from scraper.anti_detect import apply_stealth, HumanBehavior

async def test_stealth():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # Test 1: bot.sannysoft.com — KAPSAMLI
        print("=" * 50)
        print("TEST 1: bot.sannysoft.com")
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            timezone_id="Europe/Istanbul",
            locale="tr-TR",
        )
        await apply_stealth(context)
        page = await context.new_page()
        await page.goto("https://bot.sannysoft.com/", wait_until="networkidle")
        await HumanBehavior.random_delay(2, 3)  # Testin tamamlanmasini bekle
        await page.screenshot(path="bot_test_result_v2.png")
        print("  → bot_test_result_v2.png")
        await context.close()
        
        # Test 2: pixelscan.net — sonucu bekle
        print("\nTEST 2: pixelscan.net")
        context2 = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            timezone_id="Europe/Istanbul",
            locale="tr-TR",
        )
        await apply_stealth(context2)
        page2 = await context2.new_page()
        await page2.goto("https://pixelscan.net/", wait_until="networkidle")
        # Pixelscan otomatik scan yapar, sonuclari bekle
        await HumanBehavior.random_delay(5, 8)
        await page2.screenshot(path="pixelscan_result_v2.png")
        print("  → pixelscan_result_v2.png")
        await context2.close()
        
        # Test 3: fingerprint.com demo
        print("\nTEST 3: fingerprint.com")
        context3 = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            timezone_id="Europe/Istanbul",
            locale="tr-TR",
        )
        await apply_stealth(context3)
        page3 = await context3.new_page()
        await page3.goto("https://fingerprint.com/products/bot-detection/", wait_until="networkidle")
        await HumanBehavior.random_delay(5, 8)
        await page3.screenshot(path="fp_test_result_v2.png")
        print("  → fp_test_result_v2.png")
        await context3.close()
        
        await browser.close()
        
        print("\n✅ Tum testler tamamlandi.")
        print("Dosyalar: bot_test_result_v2.png, pixelscan_result_v2.png, fp_test_result_v2.png")

asyncio.run(test_stealth())
