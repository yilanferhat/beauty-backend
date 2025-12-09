import sqlite3

# --- CİLT TİPİNE ÖZEL KATALOG ---
URUN_KATALOGU = {
    # KURU CİLT (Yoğun Nemlendirici - CeraVe)
    "kuru": {
        "urun_adi": "CeraVe Nemlendirici Krem (Kuru Ciltler)",
        "marka": "CeraVe",
        "link": "https://www.trendyol.com/sr?q=cerave%20nemlendirici%20krem",
        "fiyat_araligi": "Uygun"
    },
    # YAĞLI CİLT (Parlama Karşıtı - La Roche)
    "yagli": {
        "urun_adi": "La Roche-Posay Effaclar Jel (Yağlı Ciltler)",
        "marka": "La Roche-Posay",
        "link": "https://www.trendyol.com/sr?q=la%20roche%20posay%20effaclar%20jel",
        "fiyat_araligi": "Orta"
    },
    # LEKE SORUNU
    "leke": {
        "urun_adi": "Nivea Luminous 630 Leke Karşıtı",
        "marka": "Nivea",
        "link": "https://www.trendyol.com/sr?q=nivea%20luminous",
        "fiyat_araligi": "Orta"
    },
    # KIRIŞIKLIK
    "kirisik": {
        "urun_adi": "L'Oreal Paris Revitalift Laser X3",
        "marka": "L'Oreal Paris",
        "link": "https://www.trendyol.com/sr?q=loreal%20revitalift%20laser",
        "fiyat_araligi": "Orta"
    },
    # NORMAL / STANDART
    "normal": {
        "urun_adi": "Nivea Aqua Sensation",
        "marka": "Nivea",
        "link": "https://www.trendyol.com/sr?q=nivea%20aqua%20sensation",
        "fiyat_araligi": "Uygun"
    }
}

def tablolari_olustur():
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
    except:
        pass

def en_uygun_urunu_bul(leke_sayisi, kirisiklik_indeksi, cilt_tipi="normal"):
    """
    Önce Cilt Tipine bakar, sonra sorunlara bakar.
    """
    # 1. Cilt Tipi Analizi (Kuruysa direkt nemlendirici ver)
    if cilt_tipi == "Kuru Cilt":
        return URUN_KATALOGU["kuru"]
    
    if cilt_tipi == "Yağlı Cilt":
        # Yağlı ama aynı zamanda çok lekeli ise leke kremi ver
        if leke_sayisi > 20:
             return URUN_KATALOGU["leke"]
        return URUN_KATALOGU["yagli"]

    # 2. Sorun Bazlı Analiz (Normal/Karma Ciltler için)
    if kirisiklik_indeksi > 100:
        return URUN_KATALOGU["kirisik"]
    
    if leke_sayisi > 15:
        return URUN_KATALOGU["leke"]
    
    return URUN_KATALOGU["normal"]