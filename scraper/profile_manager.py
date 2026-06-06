"""
Profil Yöneticisi — Mini AdsPower Mantığı
==========================================

Ne işe yarar?
  LinkedIn scraping yaparken tek bir tarayıcıyla 100 profili
  arka arkaya gezersen LinkedIn "bu bot" der ve ban atar.

Çözüm:
  Her seferinde farklı bir tarayıcı kimliği (fingerprint) kullan.
  LinkedIn her birini "farklı bir insan" sanır.

Nasıl çalışır?
  Her "profil" = ayrı bir Chrome kullanıcı klasörü (user_data_dir)
  + farklı ekran boyutu, user agent, timezone.

  Profil 1: Windows 10 / Chrome / 1920x1080 / İstanbul
  Profil 2: macOS / Chrome / 1440x900 / İstanbul
  Profil 3: Windows 11 / Chrome / 2560x1440 / İstanbul

  Rotasyon: sırayla kullan, her biri max 20 profil çeksin.

Gerçek dünyada (10K+):
  Profil sayısı 20-50'ye çıkar, her birine farklı proxy eklenir,
  AdsPower/GoLogin gibi profesyonel anti-detect tarayıcılar kullanılır.
"""

import os
import json
import random
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Her bir browser profilinin "parmak izi" (fingerprint) ayarları
# ---------------------------------------------------------------------------
@dataclass
class Fingerprint:
    """Bir tarayıcının dış dünyaya nasıl görüneceğini tanımlar."""
    name: str
    viewport: dict              # {"width": 1920, "height": 1080}
    user_agent: str             # Tarayıcı + işletim sistemi bilgisi
    timezone: str               # "Europe/Istanbul"
    locale: str                 # "tr-TR"
    
    # Kullanım takibi
    profiles_scraped: int = 0   # Bu profille kaç LinkedIn profili çekildi?
    max_per_session: int = 20    # Bu profille max kaç profil çekilebilir?


@dataclass
class BrowserProfile:
    """Bir browser profili = fingerprint + kendi çerez/oturum klasörü."""
    fingerprint: Fingerprint
    user_data_dir: Path         # Chrome'un çerezlerini sakladığı klasör
    last_used: Optional[float] = None


# ---------------------------------------------------------------------------
# Ön tanımlı fingerprint'ler
# Her biri farklı bir gerçek bilgisayarı taklit eder.
# ---------------------------------------------------------------------------
DEFAULT_FINGERPRINTS = [
    Fingerprint(
        name="windows_tr",
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        timezone="Europe/Istanbul",
        locale="tr-TR",
    ),
    Fingerprint(
        name="macos_tr",
        viewport={"width": 1440, "height": 900},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        timezone="Europe/Istanbul",
        locale="tr-TR",
    ),
    Fingerprint(
        name="windows_highres",
        viewport={"width": 2560, "height": 1440},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        timezone="Europe/Istanbul",
        locale="tr-TR",
    ),
]


# ---------------------------------------------------------------------------
# Ana sınıf: ProfileManager
# ---------------------------------------------------------------------------
class ProfileManager:
    """
    Mini AdsPower: Browser profillerini yönetir, rotasyon yapar.
    
    Kullanım:
        pm = ProfileManager()
        pm.setup_profiles()                        # Profilleri oluştur
        profile = pm.get_next_profile()            # Sıradaki profili al
        pm.record_scrape(profile, count=1)         # Kaç profil çekildiğini kaydet
    """
    
    def __init__(self, profiles_dir: str = None, max_per_profile: int = 20):
        """
        profiles_dir: Profil klasörlerinin tutulacağı ana dizin.
                      Yoksa proje kökündeki 'profiles/' kullanılır.
        max_per_profile: Bir browser profiliyle en fazla kaç LinkedIn 
                         profili çekilebilir? (rate-limit koruması)
        """
        if profiles_dir is None:
            # Proje kökünü bul: bu dosya scraper/ içinde, bir üst dizin proje kökü
            project_root = Path(__file__).parent.parent
            profiles_dir = project_root / "profiles"
        
        self.profiles_dir = Path(profiles_dir)
        self.max_per_profile = max_per_profile
        self._profiles: list[BrowserProfile] = []
        self._current_index: int = 0
        
        # Her fingerprint'in max değerini güncelle
        for fp in DEFAULT_FINGERPRINTS:
            fp.max_per_session = max_per_profile
    
    def setup_profiles(self) -> list[BrowserProfile]:
        """
        Her fingerprint için bir browser profil klasörü oluştur.
        
        İlk çalıştırmada boş klasörler oluşur.
        Sonraki çalıştırmalarda aynı klasörler kullanılır →
        çerezler ve oturum bilgisi korunur (tıpkı AdsPower gibi).
        """
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._profiles = []
        
        for fp in DEFAULT_FINGERPRINTS:
            # Her profile kendi klasörü: profiles/windows_tr/
            profile_dir = self.profiles_dir / fp.name
            profile_dir.mkdir(exist_ok=True)
            
            browser_profile = BrowserProfile(
                fingerprint=fp,
                user_data_dir=profile_dir,
            )
            self._profiles.append(browser_profile)
        
        return self._profiles
    
    def get_next_profile(self) -> BrowserProfile:
        """
        Sıradaki uygun profili döndür. Rotasyon mantığı:
        
        1. Mevcut profile bak, limit doldu mu?
        2. Dolduysa sonrakine geç.
        3. Hepsi dolduysa resetle (yeni tur).
        """
        if not self._profiles:
            raise RuntimeError("Önce setup_profiles() çağır!")
        
        # Tüm profilleri dene
        for _ in range(len(self._profiles)):
            profile = self._profiles[self._current_index]
            
            if profile.fingerprint.profiles_scraped < profile.fingerprint.max_per_session:
                # Bu profil daha scrape yapabilir
                self._current_index = (self._current_index + 1) % len(self._profiles)
                return profile
            
            # Limit dolmuş, sonrakine geç
            self._current_index = (self._current_index + 1) % len(self._profiles)
        
        # Tüm profiller limiti doldurdu → resetle, yeni tur başlat
        for p in self._profiles:
            p.fingerprint.profiles_scraped = 0
        
        return self._profiles[0]
    
    def record_scrape(self, profile: BrowserProfile, count: int = 1):
        """Bu profille kaç LinkedIn profili çekildiğini kaydet."""
        profile.fingerprint.profiles_scraped += count
    
    def status(self) -> str:
        """Hangi profil ne durumda? Konsola yazdırmak için."""
        lines = ["Profil Durumu:", "-" * 50]
        for p in self._profiles:
            fp = p.fingerprint
            remaining = fp.max_per_session - fp.profiles_scraped
            bar = "█" * fp.profiles_scraped + "░" * remaining
            lines.append(
                f"  {fp.name:20s}  [{bar}]  "
                f"{fp.profiles_scraped}/{fp.max_per_session}  "
                f"(kalan: {remaining})"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Test: Bu dosyayı direkt çalıştırırsan profil yöneticisini test eder.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pm = ProfileManager()
    pm.setup_profiles()
    
    print("Profil yöneticisi hazır!\n")
    print(pm.status())
    
    print("\n--- Rotasyon testi ---")
    for i in range(5):
        p = pm.get_next_profile()
        pm.record_scrape(p)
        print(f"  İstek #{i+1} → {p.fingerprint.name}")
    
    print("\n" + pm.status())
