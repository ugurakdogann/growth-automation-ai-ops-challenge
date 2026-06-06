"""
Email Evidence Collector
========================
Kanıt toplama script'i. email_enrich.py tarafından import edilir.
Her şirket için web araştırması ile toplanan kanıtları içerir.
"""

# ===========================================================================
# COMPANY EVIDENCE — Web araştırması ile toplanan kanıtlar
# ===========================================================================
# evidence_type:
#   "found_public_lead_email" → lead'in kendi email'i bulundu (email kolonuna yazılır)
#   "employee_email_sample"   → aynı şirketten çalışan email örneği var (estimated, conf 85)
#   "company_domain_evidence" → şirket doküman/sayfalarında domain kullanım kanıtı (estimated, conf 70)
#   "none"                    → hiç kanıt yok (low_confidence_guess, conf 50)

COMPANY_EVIDENCE = {
    # =========================================================================
    # EMPLOYEE EMAIL SAMPLE (confidence 85)
    # Aynı şirketten en az 1 public çalışan email örneği bulundu
    # =========================================================================
    "Turkcell": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://tedarik.turkcell.com.tr/Shared%20Documents/BeSupplier/TURKCELL%20%C4%B0NSAN%20HAKLARI%20POL%C4%B0T%C4%B0KASI.pdf",
        "pattern": "first.last",
        "sample_emails": ["insanhaklari@turkcell.com.tr"],
        "source_note": "Company PDF confirms @turkcell.com.tr domain; first.last is an inferred pattern",
    },

    # =========================================================================
    # COMPANY DOMAIN EVIDENCE (confidence 70)
    # Şirket kariyer/iletişim/doküman sayfalarında domain kullanımı kanıtlandı
    # =========================================================================
    "Trendyol": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.trendyol.com/iletisim",
        "pattern": "first.last",
        "source_note": "Company contact page uses @trendyol.com domain",
    },
    "Getir": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://getir.com/tr/kariyer/",
        "pattern": "first.last",
        "source_note": "Company career page — corporate domain confirmed",
    },
    "Hepsiburada": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.hepsiburada.com/iletisim",
        "pattern": "first.last",
        "source_note": "Company contact page — corporate domain confirmed",
    },
    "Akbank": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.akbank.com/tr-tr/iletisim",
        "pattern": "first.last",
        "source_note": "Bank contact page — corporate domain confirmed",
    },
    "Garanti BBVA": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.garantibbva.com.tr/iletisim",
        "pattern": "first.last",
        "source_note": "Bank contact page — corporate domain confirmed",
    },
    "İş Bankası": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.isbank.com.tr/iletisim",
        "pattern": "first.last",
        "source_note": "Bank contact page — corporate domain confirmed",
    },
    "THY": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://investor.thy.com/tr/contact",
        "pattern": "first.last",
        "source_note": "Investor relations contact page — @thy.com domain confirmed",
    },
    "Pegasus": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.flypgs.com/kurumsal/iletisim",
        "pattern": "first.last",
        "source_note": "Corporate contact page — domain confirmed",
    },
    "Arçelik": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.arcelik.com/iletisim",
        "pattern": "first.last",
        "source_note": "Company contact page — corporate domain confirmed",
    },
    "Koç Holding": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.koc.com.tr/iletisim",
        "pattern": "first.last",
        "source_note": "Holding contact page — corporate domain confirmed",
    },
    "Sabancı Holding": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.sabanci.com/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Holding contact page — corporate domain confirmed",
    },
    "Borusan Holding": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.borusan.com/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Holding contact page — corporate domain confirmed",
    },
    "Yıldız Holding": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.yildizholding.com.tr/iletisim",
        "pattern": "first.last",
        "source_note": "Holding contact page — corporate domain confirmed",
    },
    "Zorlu Holding": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.zorlu.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Holding contact page — corporate domain confirmed",
    },
    "Anadolu Grubu": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.anadolugrubu.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Holding contact page — corporate domain confirmed",
    },
    "Doğuş Grubu": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.dogusgrubu.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Holding contact page — corporate domain confirmed",
    },
    "Eczacıbaşı": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.eczacibasi.com.tr/iletisim",
        "pattern": "first.last",
        "source_note": "Holding contact page — corporate domain confirmed",
    },
    "LC Waikiki": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.lcwaikiki.com/tr-TR/TR/iletisim",
        "pattern": "first.last",
        "source_note": "Retail contact page — corporate domain confirmed",
    },
    "Defacto": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.defacto.com.tr/iletisim",
        "pattern": "first.last",
        "source_note": "Retail contact page — corporate domain confirmed",
    },
    "Migros": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.migros.com.tr/iletisim",
        "pattern": "first.last",
        "source_note": "Retail contact page — corporate domain confirmed",
    },
    "BİM": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.bim.com.tr/iletisim.aspx",
        "pattern": "first.last",
        "source_note": "Retail contact page — corporate domain confirmed",
    },
    "Boyner": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.boyner.com.tr/iletisim",
        "pattern": "first.last",
        "source_note": "Retail contact page — corporate domain confirmed",
    },
    "Tofaş": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.tofas.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Automotive contact page — corporate domain confirmed",
    },
    "Ford Otosan": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.fordotosan.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Automotive contact page — corporate domain confirmed",
    },
    "Şişecam": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.sisecam.com/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Corporate contact page — domain confirmed",
    },
    "Enerjisa": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.enerjisa.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Energy company contact page — domain confirmed",
    },
    "Siemens Turkey": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.siemens.com.tr/tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Multinational — siemens.com.tr domain confirmed",
    },
    "Nestlé Turkey": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.nestle.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Multinational — nestle.com.tr domain confirmed",
    },
    "P&G Turkey": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.pg.com/tr_TR/contact",
        "pattern": "first.last",
        "source_note": "Multinational — pg.com domain confirmed",
    },
    "Vodafone Turkey": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.vodafone.com.tr/iletisim",
        "pattern": "first.last",
        "source_note": "Telecom contact page — corporate domain confirmed",
    },
    "Türk Telekom": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.turktelekom.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Telecom contact page — corporate domain confirmed",
    },
    "Eti": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.eti.com.tr/iletisim",
        "pattern": "first.last",
        "source_note": "Food company contact page — corporate domain confirmed",
    },
    "Ülker": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.ulker.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Food company contact page — corporate domain confirmed",
    },
    "CCI": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.cci.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Beverage company contact page — corporate domain confirmed",
    },
    "Kariyer.net": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.kariyer.net/iletisim",
        "pattern": "first.last",
        "source_note": "HR tech company — kariyer.net domain confirmed",
    },
    "MediaMarkt Turkey": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.mediamarkt.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Retail contact page — corporate domain confirmed",
    },
    "Allianz Turkey": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.allianz.com.tr/tr_TR/sizin-icin/iletisim.html",
        "pattern": "first.last",
        "source_note": "Insurance contact page — corporate domain confirmed",
    },
    "TAV": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.tav.aero/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Airport operator contact page — corporate domain confirmed",
    },
    "Socar Turkey": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.socar.com.tr/tr/iletisim",
        "pattern": "first.last",
        "source_note": "Energy company contact page — corporate domain confirmed",
    },

    # =========================================================================
    # LOW CONFIDENCE (confidence 50) — NO EVIDENCE FOUND
    # Bu şirketler için sadece yaygın first.last pattern tahmini
    # =========================================================================
    "Insider": {
        "evidence_type": "none",
        "evidence_url": "",
        "pattern": "first.last",
        "source_note": "No evidence found — default first.last pattern",
    },
    "Papara": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.papara.com/contact?hl=tr_TR",
        "pattern": "first.last",
        "sample_emails": ["destek@papara.com"],
        "source_note": "Official contact page confirms @papara.com domain; first.last is an inferred pattern",
    },
    "Peak Games": {
        "evidence_type": "none",
        "evidence_url": "",
        "pattern": "first.last",
        "source_note": "No evidence found — default first.last pattern",
    },
    "Dream Games": {
        "evidence_type": "none",
        "evidence_url": "",
        "pattern": "first.last",
        "source_note": "No evidence found — default first.last pattern",
    },
    "Masomo": {
        "evidence_type": "none",
        "evidence_url": "",
        "pattern": "first.last",
        "source_note": "No evidence found — default first.last pattern",
    },
    "Spyke Games": {
        "evidence_type": "none",
        "evidence_url": "",
        "pattern": "first.last",
        "source_note": "No evidence found — default first.last pattern",
    },
    "Vestel": {
        "evidence_type": "none",
        "evidence_url": "",
        "pattern": "first.last",
        "source_note": "No evidence found — default first.last pattern",
    },
    "Yemeksepeti": {
        "evidence_type": "none",
        "evidence_url": "",
        "pattern": "first.last",
        "source_note": "No evidence found — default first.last pattern",
    },
    "iyzico": {
        "evidence_type": "none",
        "evidence_url": "",
        "pattern": "first.last",
        "source_note": "No evidence found — default first.last pattern",
    },
    "Paraşüt": {
        "evidence_type": "none",
        "evidence_url": "",
        "pattern": "first.last",
        "source_note": "No evidence found — default first.last pattern",
    },
    "Şok Marketler": {
        "evidence_type": "none",
        "evidence_url": "",
        "pattern": "first.last",
        "source_note": "No evidence found — default first.last pattern",
    },
    "Unilever Turkey": {
        "evidence_type": "none",
        "evidence_url": "",
        "pattern": "first.last",
        "source_note": "No evidence found — default first.last pattern",
    },
    "Kale": {
        "evidence_type": "company_domain_evidence",
        "evidence_url": "https://www.kale.com.tr/tr-en/ethics-hotline",
        "pattern": "first.last",
        "sample_emails": ["etikhat@kale.com.tr"],
        "source_note": "Official ethics hotline confirms @kale.com.tr domain; first.last is an inferred pattern",
    },
}
