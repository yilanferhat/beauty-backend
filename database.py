import sqlite3
import datetime

DB_NAME = "beauty_tech.db"

def baglanti_al():
    return sqlite3.connect(DB_NAME)

def tablolari_olustur():
    conn = baglanti_al()
    cursor = conn.cursor()
    
    # Analiz Sonuçları Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analizler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            leke_sayisi INTEGER,
            cilt_skoru INTEGER,
            onerilen_urun TEXT
        )
    ''')
    
    # Ürünler Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urunler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hedef_problem TEXT,
            urun_adi TEXT,
            marka TEXT,
            min_leke INTEGER,
            max_leke INTEGER,
            link TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def baslangic_verisi_ekle():
    conn = baglanti_al()
    cursor = conn.cursor()
    
    # Önce tablo boş mu kontrol et
    cursor.execute("SELECT count(*) FROM urunler")
    count = cursor.fetchone()[0]
    
    if count == 0:
        urunler = [
            ("Mükemmel", "Günlük Nemlendirici", "Cerave", 0, 5, "https://ornek.com/nemlendirici"),
            ("Hafif Leke", "C Vitamini Serumu", "La Roche Posay", 6, 20, "https://ornek.com/c-vitamini"),
            ("Orta Leke", "Niacinamide %10", "The Ordinary", 21, 50, "https://ornek.com/niacinamide"),
            ("Ciddi Leke", "AHA/BHA Peeling", "The Ordinary", 51, 100, "https://ornek.com/peeling"),
            ("Akne/Sivilce", "Salisilik Asit Temizleyici", "Cosmed", 101, 500, "https://ornek.com/akne"),
            ("Kırışıklık", "Retinol %0.5", "Loreal", 501, 1000, "https://ornek.com/retinol"),
            ("Yorgun Görünüm", "Kafein Göz Serumu", "Revolution", 1001, 5000, "https://ornek.com/goz-serumu")
        ]
        
        cursor.executemany('''
            INSERT INTO urunler (hedef_problem, urun_adi, marka, min_leke, max_leke, link)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', urunler)
        
        conn.commit()
    
    conn.close()

def analiz_kaydet(leke_sayisi, cilt_skoru, onerilen_urun):
    conn = baglanti_al()
    cursor = conn.cursor()
    tarih = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO analizler (tarih, leke_sayisi, cilt_skoru, onerilen_urun)
        VALUES (?, ?, ?, ?)
    ''', (tarih, leke_sayisi, cilt_skoru, onerilen_urun))
    
    conn.commit()
    conn.close()

def en_uygun_urunu_bul(leke_sayisi):
    conn = baglanti_al()
    cursor = conn.cursor()
    
    # Leke sayısına göre aralık sorgusu
    cursor.execute('''
        SELECT hedef_problem, urun_adi, marka, link 
        FROM urunler 
        WHERE ? BETWEEN min_leke AND max_leke
    ''', (leke_sayisi,))
    
    sonuc = cursor.fetchone()
    conn.close()
    
    if sonuc:
        return {
            "hedef_problem": sonuc[0],
            "urun_adi": sonuc[1],
            "marka": sonuc[2],
            "link": sonuc[3]
        }
    else:
        # Aralık dışındaysa varsayılan bir ürün döndür
        return {
            "hedef_problem": "Genel Bakım",
            "urun_adi": "Onarıcı Bakım Kremi",
            "marka": "Bioderma",
            "link": "https://ornek.com/genel"
        }