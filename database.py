import sqlite3

# --- GÜNCELLENMİŞ AKILLI KATALOG (ARAMA LİNKLERİ) ---
# Linklerin hepsi Trendyol Arama Sonuçlarına gider.
# Böylece "Ürün tükendi" hatası asla alınmaz.

URUN_KATALOGU = {
    "akne_yogun": {
        "urun_adi": "La Roche-Posay Effaclar Duo(+)",
        "marka": "La Roche-Posay",
        # Link: "La Roche Posay Effaclar Duo" araması
        "link": "https://www.trendyol.com/sr?q=la%20roche%20posay%20effaclar%20duo", 
        "fiyat_araligi": "Orta"
    },
    "akne_hafif": {
        "urun_adi": "CeraVe Blemish Control Gel",
        "marka": "CeraVe",
        # Link: "CeraVe Blemish Control" araması
        "link": "https://www.trendyol.com/sr?q=cerave%20blemish%20control%20gel",
        "fiyat_araligi": "Uygun"
    },
    "kirisiklik_derin": {
        "urun_adi": "Estée Lauder Advanced Night Repair",
        "marka": "Estée Lauder",
        # Link: "Estee Lauder Advanced Night Repair" araması
        "link": "https://www.trendyol.com/sr?q=estee%20lauder%20advanced%20night%20repair",
        "fiyat_araligi": "Premium"
    },
    "kirisiklik_ince": {
        "urun_adi": "The Ordinary Retinol 0.5%",
        "marka": "The Ordinary",
        # Link: "The Ordinary Retinol" araması
        "link": "https://www.trendyol.com/sr?q=the%20ordinary%20retinol",
        "fiyat_araligi": "Uygun"
    },
    "leke": {
        "urun_adi": "SkinCeuticals Discoloration Defense",
        "marka": "SkinCeuticals",
        # Link: "SkinCeuticals Discoloration" araması
        "link": "https://www.trendyol.com/sr?q=skinceuticals%20discoloration",
        "fiyat_araligi": "Premium"
    },
    "normal": {
        "urun_adi": "Kiehl's Ultra Facial Cream",
        "marka": "Kiehl's",
        # Link: "Kiehls Ultra Facial Cream" araması
        "link": "https://www.trendyol.com/sr?q=kiehls%20ultra%20facial%20cream",
        "fiyat_araligi": "Orta"
    }
}

def tablolari_olustur():
    """Veritabanı tablosunu oluşturur (Eğer yoksa)"""
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

def en_uygun_urunu_bul(leke_sayisi, kirisiklik_indeksi=0):
    """
    Analiz sonuçlarına göre katalogdan EN DOĞRU ürünü seçer.
    """
    # 1. Kırışıklık Durumu
    if kirisiklik_indeksi > 80:
        return URUN_KATALOGU["kirisiklik_derin"]
    elif kirisiklik_indeksi > 30:
        return URUN_KATALOGU["kirisiklik_ince"]
    
    # 2. Leke Durumu
    if leke_sayisi > 30:
        return URUN_KATALOGU["akne_yogun"]
    elif leke_sayisi > 10:
        return URUN_KATALOGU["akne_hafif"]
    elif leke_sayisi > 0:
        return URUN_KATALOGU["leke"]
    
    # 3. Sorunsuz Cilt
    return URUN_KATALOGU["normal"]