import sqlite3
import random # Rastgele seçim için gerekli

# --- DEVASA ÜRÜN HAVUZU ---
# Her kategoride birden fazla ürün var.
# Sistem her seferinde bunlardan birini RASTGELE seçecek.

URUN_HAVUZU = {
    # ---------------------------------------------------------
    # 1. KURU CİLT (Nemlendirici Odaklı)
    # ---------------------------------------------------------
    "kuru": [
        {"marka": "CeraVe", "urun_adi": "Kuru Ciltler İçin Nemlendirici Krem", "link": "https://www.trendyol.com/sr?q=cerave%20nemlendirici%20krem"},
        {"marka": "La Roche-Posay", "urun_adi": "Lipikar Baume AP+M", "link": "https://www.trendyol.com/sr?q=la%20roche%20lipikar%20baume"},
        {"marka": "Bioderma", "urun_adi": "Atoderm Intensive Balm", "link": "https://www.trendyol.com/sr?q=bioderma%20atoderm%20intensive"},
        {"marka": "Nivea", "urun_adi": "Besleyici Vücut Sütü", "link": "https://www.trendyol.com/sr?q=nivea%20besleyici%20vucut%20sutu"},
        {"marka": "Bepanthol", "urun_adi": "Derma Onarıcı Bakım Kremi", "link": "https://www.trendyol.com/sr?q=bepanthol%20derma"},
        {"marka": "Neutrogena", "urun_adi": "Hydro Boost Jel Krem (Kuru)", "link": "https://www.trendyol.com/sr?q=neutrogena%20hydro%20boost%20jel%20krem"},
        {"marka": "The Purest Solutions", "urun_adi": "Intensive Hydration Serum", "link": "https://www.trendyol.com/sr?q=the%20purest%20solutions%20hydration"},
    ],

    # ---------------------------------------------------------
    # 2. YAĞLI CİLT (Parlama ve Gözenek Karşıtı)
    # ---------------------------------------------------------
    "yagli": [
        {"marka": "La Roche-Posay", "urun_adi": "Effaclar Jel Temizleyici", "link": "https://www.trendyol.com/sr?q=la%20roche%20effaclar%20jel"},
        {"marka": "Bioderma", "urun_adi": "Sebium Foaming Gel", "link": "https://www.trendyol.com/sr?q=bioderma%20sebium%20jel"},
        {"marka": "CeraVe", "urun_adi": "Köpüren Temizleyici (Yağlı Cilt)", "link": "https://www.trendyol.com/sr?q=cerave%20kopuren%20temizleyici"},
        {"marka": "Garnier", "urun_adi": "Saf & Temiz 3'ü 1 Arada", "link": "https://www.trendyol.com/sr?q=garnier%20saf%20ve%20temiz"},
        {"marka": "The Ordinary", "urun_adi": "Niacinamide 10% + Zinc 1%", "link": "https://www.trendyol.com/sr?q=the%20ordinary%20niacinamide"},
        {"marka": "Sebamed", "urun_adi": "Clear Face Kompakt", "link": "https://www.trendyol.com/sr?q=sebamed%20clear%20face"},
        {"marka": "Vichy", "urun_adi": "Normaderm Phytosolution", "link": "https://www.trendyol.com/sr?q=vichy%20normaderm"},
    ],

    # ---------------------------------------------------------
    # 3. LEKE / AKNE İZİ (Aydınlatıcılar)
    # ---------------------------------------------------------
    "leke": [
        {"marka": "Nivea", "urun_adi": "Luminous 630 Leke Karşıtı Serum", "link": "https://www.trendyol.com/sr?q=nivea%20luminous%20630"},
        {"marka": "La Roche-Posay", "urun_adi": "Pure Niacinamide 10 Serum", "link": "https://www.trendyol.com/sr?q=la%20roche%20posay%20niacinamide"},
        {"marka": "The Purest Solutions", "urun_adi": "Arbutin %2 Leke Serumu", "link": "https://www.trendyol.com/sr?q=the%20purest%20arbutin"},
        {"marka": "L'Oreal Paris", "urun_adi": "Revitalift C Vitamini Serumu", "link": "https://www.trendyol.com/sr?q=loreal%20c%20vitamini"},
        {"marka": "SkinCeuticals", "urun_adi": "Discoloration Defense", "link": "https://www.trendyol.com/sr?q=skinceuticals%20discoloration"},
        {"marka": "Garnier", "urun_adi": "C Vitamini Parlaklık Serumu", "link": "https://www.trendyol.com/sr?q=garnier%20c%20vitamini"},
        {"marka": "Caudalie", "urun_adi": "Vinoperfect Leke Serumu", "link": "https://www.trendyol.com/sr?q=caudalie%20vinoperfect"},
    ],

    # ---------------------------------------------------------
    # 4. KIRIŞIKLIK / YAŞLANMA KARŞITI (Anti-Aging)
    # ---------------------------------------------------------
    "kirisik": [
        {"marka": "L'Oreal Paris", "urun_adi": "Revitalift Laser X3 Bakım", "link": "https://www.trendyol.com/sr?q=loreal%20revitalift%20laser"},
        {"marka": "Estée Lauder", "urun_adi": "Advanced Night Repair Serum", "link": "https://www.trendyol.com/sr?q=estee%20lauder%20advanced%20night"},
        {"marka": "The Ordinary", "urun_adi": "Retinol 0.5% in Squalane", "link": "https://www.trendyol.com/sr?q=the%20ordinary%20retinol"},
        {"marka": "La Roche-Posay", "urun_adi": "Redermic Retinol Krem", "link": "https://www.trendyol.com/sr?q=la%20roche%20retinol"},
        {"marka": "Vichy", "urun_adi": "Liftactiv Collagen Specialist", "link": "https://www.trendyol.com/sr?q=vichy%20liftactiv"},
        {"marka": "Kiehl's", "urun_adi": "Midnight Recovery Concentrate", "link": "https://www.trendyol.com/sr?q=kiehls%20midnight"},
        {"marka": "Sebamed", "urun_adi": "Q10 Yaşlanma Karşıtı Krem", "link": "https://www.trendyol.com/sr?q=sebamed%20q10"},
    ],

    # ---------------------------------------------------------
    # 5. NORMAL / KARMA / GENEL BAKIM
    # ---------------------------------------------------------
    "normal": [
        {"marka": "Nivea", "urun_adi": "Aqua Sensation Jel Krem", "link": "https://www.trendyol.com/sr?q=nivea%20aqua%20sensation"},
        {"marka": "Simple", "urun_adi": "Su Bazlı Nemlendirici", "link": "https://www.trendyol.com/sr?q=simple%20su%20bazli"},
        {"marka": "L'Oreal Paris", "urun_adi": "Nem Terapisi Aloe Vera Suyu", "link": "https://www.trendyol.com/sr?q=loreal%20nem%20terapisi"},
        {"marka": "Garnier", "urun_adi": "Hyaluronik Aloe Jel", "link": "https://www.trendyol.com/sr?q=garnier%20hyaluronik%20aloe"},
        {"marka": "Kiehl's", "urun_adi": "Ultra Facial Cream", "link": "https://www.trendyol.com/sr?q=kiehls%20ultra%20facial"},
    ]
}

def tablolari_olustur():
    """Veritabanı tablosunu oluşturur"""
    conn = sqlite3.connect('beauty.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analizler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            leke_sayisi INTEGER,
            genel_skor INTEGER,
            onerilen_urun TEXT
        )
    ''')
    conn.commit()
    conn.close()

def baslangic_verisi_ekle():
    pass 

def analiz_kaydet(leke_sayisi, genel_skor, onerilen_urun):
    try:
        conn = sqlite3.connect('beauty.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO analizler (leke_sayisi, genel_skor, onerilen_urun) VALUES (?, ?, ?)',
                       (leke_sayisi, genel_skor, onerilen_urun))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Kayıt Hatası: {e}")

def en_uygun_urunu_bul(leke_sayisi, kirisiklik_indeksi, cilt_tipi="normal"):
    """
    Kategoriye göre ürün listesini bulur ve içinden RASTGELE birini seçer.
    """
    secilen_kategori = "normal"
    
    # 1. Önce Cilt Tipi (Kuru/Yağlı)
    if cilt_tipi == "Kuru Cilt":
        secilen_kategori = "kuru"
    elif cilt_tipi == "Yağlı Cilt":
        # Yağlı ama çok lekeli ise leke kategorisine kay
        if leke_sayisi > 20:
             secilen_kategori = "leke"
        else:
             secilen_kategori = "yagli"
    
    # 2. Eğer cilt tipi 'Karma/Normal' ise Soruna Bak
    else:
        # Ciddi kırışıklık varsa
        if kirisiklik_indeksi > 60: # Eşik değerler main.py ile uyumlu
            secilen_kategori = "kirisik"
        # Ciddi leke varsa
        elif leke_sayisi > 15:
            secilen_kategori = "leke"
        else:
            secilen_kategori = "normal"
            
    # LİSTEDEN RASTGELE SEÇİM YAP (SİHİRLİ DOKUNUŞ BURADA)
    # random.choice() fonksiyonu liste içinden kura çeker gibi birini alır.
    try:
        urun_listesi = URUN_HAVUZU.get(secilen_kategori, URUN_HAVUZU["normal"])
        secilen_urun = random.choice(urun_listesi)
        return secilen_urun
    except:
        # Herhangi bir hata olursa varsayılan dön
        return {"marka": "Nivea", "urun_adi": "Aqua Sensation", "link": "https://www.trendyol.com/sr?q=nivea"}