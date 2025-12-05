import sqlite3

# --- GÜNCELLENMİŞ "SÜRÜMDEN KAZANMA" KATALOĞU ---
# Strateji: Pahalı ürün satılmaz. L'Oreal, Nivea, Garnier gibi
# herkesin bildiği ve sepetine kolayca atacağı ürünleri koyduk.

URUN_KATALOGU = {
    # 1. AKNE / SİVİLCE (Garnier - Uygun Fiyat)
    "akne_yogun": {
        "urun_adi": "Garnier Saf & Temiz 3'ü 1 Arada",
        "marka": "Garnier",
        "link": "https://www.trendyol.com/sr?q=garnier%20saf%20ve%20temiz",
        "fiyat_araligi": "Uygun"
    },
    # 2. HAFİF PÜRÜZLER (Nivea - Orta Fiyat)
    "akne_hafif": {
        "urun_adi": "Nivea Derma Skin Clear",
        "marka": "Nivea",
        "link": "https://www.trendyol.com/sr?q=nivea%20derma%20skin",
        "fiyat_araligi": "Uygun"
    },
    # 3. DERİN KIRIŞIKLIK (L'Oreal Revitalift - Çok Satan)
    "kirisiklik_derin": {
        "urun_adi": "L'Oreal Paris Revitalift Laser X3",
        "marka": "L'Oreal Paris",
        "link": "https://www.trendyol.com/sr?q=loreal%20revitalift%20laser",
        "fiyat_araligi": "Orta"
    },
    # 4. İNCE ÇİZGİLER (L'Oreal Hyaluron - Popüler)
    "kirisiklik_ince": {
        "urun_adi": "L'Oreal Paris Hyaluron Uzmanı",
        "marka": "L'Oreal Paris",
        "link": "https://www.trendyol.com/sr?q=loreal%20hyaluron%20uzman%C4%B1",
        "fiyat_araligi": "Uygun"
    },
    # 5. LEKE (Nivea Luminous - Etkili ve Ulaşılabilir)
    "leke": {
        "urun_adi": "Nivea Luminous 630 Leke Karşıtı",
        "marka": "Nivea",
        "link": "https://www.trendyol.com/sr?q=nivea%20luminous",
        "fiyat_araligi": "Orta"
    },
    # 6. GENEL BAKIM / SORUNSUZ (Nivea Aqua - Herkese Lazım)
    "normal": {
        "urun_adi": "Nivea Aqua Sensation Jel Krem",
        "marka": "Nivea",
        "link": "https://www.trendyol.com/sr?q=nivea%20aqua%20sensation",
        "fiyat_araligi": "Uygun"
    }
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

def en_uygun_urunu_bul(leke_sayisi, kirisiklik_indeksi=0):
    """
    Analiz sonuçlarına göre katalogdan EN DOĞRU ürünü seçer.
    MANTIK GÜNCELLENDİ: Eşikler yükseltildi, artık herkes 'kırışık' çıkmayacak.
    """
    
    # Kırışıklık Eşikleri Yükseltildi (Daha zor tetiklenir)
    # Eskiden 80 idi, şimdi 120. Yani gerçekten kırışık olması lazım.
    if kirisiklik_indeksi > 120:
        return URUN_KATALOGU["kirisiklik_derin"]
    
    # Leke Eşikleri (Önce lekeye bakıyoruz çünkü gençler daha çok leke/sivilce arıyor)
    if leke_sayisi > 25:
        return URUN_KATALOGU["akne_yogun"]
    elif leke_sayisi > 10:
        return URUN_KATALOGU["akne_hafif"]
    
    # İnce Çizgi Kontrolü (Leke yoksa buraya düşer)
    if kirisiklik_indeksi > 40:
        return URUN_KATALOGU["kirisiklik_ince"]
    
    # Hafif Leke Kontrolü
    if leke_sayisi > 3:
        return URUN_KATALOGU["leke"]
    
    # Hiçbir şeye uymuyorsa "Nemlendirici" ver (En güvenli liman)
    return URUN_KATALOGU["normal"]