import sqlite3
import datetime

# Veritabanı Dosya Adı
DB_NAME = "beauty_tech.db"

def baglanti_kur():
    """Veritabanına bağlanır ve bağlantı nesnesini döndürür."""
    conn = sqlite3.connect(DB_NAME)
    return conn

def tablolari_olustur():
    """Gerekli tablolar yoksa oluşturur."""
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    # 1. ÜRÜNLER TABLOSU
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT NOT NULL,
        marka TEXT,
        problem_turu TEXT,
        esik_deger INTEGER,
        link TEXT,
        fiyat REAL
    )
    ''')

    # 2. ANALİZ GEÇMİŞİ TABLOSU
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        leke_sayisi INTEGER,
        cilt_skoru INTEGER,
        onerilen_urun_id INTEGER,
        FOREIGN KEY(onerilen_urun_id) REFERENCES products(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Veritabani tablolari hazir/kontrol edildi.")

def baslangic_verisi_ekle():
    """Tablo boşsa varsayılan başlangıç ürünlerini ekler."""
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    cursor.execute("SELECT count(*) FROM products")
    sayi = cursor.fetchone()[0]
    
    if sayi == 0:
        print("⚠️ Tablo boş, varsayılan ürünler ekleniyor...")
        urunler = [
            ("Salisilik Asit Tonik", "COSRX", "Problemli", 40, "trendyol.com/salisilik", 450.0),
            ("C Vitamini Serumu", "The Ordinary", "Yorgun", 15, "hepsiburada.com/cvitamin", 320.0),
            ("Hafif Nemlendirici", "Cerave", "Mükemmel", 0, "amazon.com/nemlendirici", 280.0)
        ]
        cursor.executemany("INSERT INTO products (ad, marka, problem_turu, esik_deger, link, fiyat) VALUES (?,?,?,?,?,?)", urunler)
        conn.commit()
        print("✅ Varsayılan ürünler eklendi.")
    
    conn.close()

def analiz_kaydet(leke, skor, urun_adi):
    """Yapılan her analizi kaydeder."""
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    # Önce önerilen ürünün ID'sini bulalım
    cursor.execute("SELECT id FROM products WHERE ad = ?", (urun_adi,))
    sonuc = cursor.fetchone()
    urun_id = sonuc[0] if sonuc else None
    
    tarih = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("INSERT INTO analysis_history (tarih, leke_sayisi, cilt_skoru, onerilen_urun_id) VALUES (?, ?, ?, ?)", 
                   (tarih, leke, skor, urun_id))
    conn.commit()
    conn.close()

def en_uygun_urunu_bul(leke_sayisi):
    """SQL'den eşik değerine göre ürün çeker."""
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM products WHERE esik_deger <= ? ORDER BY esik_deger DESC LIMIT 1", (leke_sayisi,))
    urun = cursor.fetchone()
    conn.close()
    
    if urun:
        # (id, ad, marka, problem, esik, link, fiyat)
        return {
            "urun_adi": urun[1],
            "marka": urun[2],
            "hedef_problem": urun[3],
            "link": urun[5]
        }
    else:
        return {"urun_adi": "Bilinmiyor", "marka": "-", "hedef_problem": "Belirsiz", "link": "#"}

# --- YENİ EKLENEN ADMIN FONKSİYONLARI ---

def tum_urunleri_getir():
    """Admin paneli için tüm ürünleri listeler."""
    conn = baglanti_kur()
    conn.row_factory = sqlite3.Row # Veriyi sözlük gibi çekmemizi sağlar
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    
    sonuc = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sonuc

def analiz_gecmisini_getir():
    """Admin paneli için analiz geçmişini çeker."""
    conn = baglanti_kur()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    sorgu = '''
    SELECT h.tarih, h.leke_sayisi, h.cilt_skoru, p.ad as onerilen_urun 
    FROM analysis_history h
    LEFT JOIN products p ON h.onerilen_urun_id = p.id
    ORDER BY h.tarih DESC
    '''
    cursor.execute(sorgu)
    
    sonuc = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sonuc

def urun_ekle_sql(ad, marka, problem, esik, link, fiyat):
    """Admin panelinden yeni ürün ekler."""
    conn = baglanti_kur()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (ad, marka, problem_turu, esik_deger, link, fiyat) VALUES (?,?,?,?,?,?)", 
                   (ad, marka, problem, esik, link, fiyat))
    conn.commit()
    conn.close()

# --- BAŞLANGIÇ KURULUMU ---
if __name__ == "__main__":
    tablolari_olustur()
=======
import sqlite3
import datetime

# Veritabanı Dosya Adı
DB_NAME = "beauty_tech.db"

def baglanti_kur():
    """Veritabanına bağlanır ve bağlantı nesnesini döndürür."""
    conn = sqlite3.connect(DB_NAME)
    return conn

def tablolari_olustur():
    """Gerekli tablolar yoksa oluşturur."""
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    # 1. ÜRÜNLER TABLOSU
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT NOT NULL,
        marka TEXT,
        problem_turu TEXT,
        esik_deger INTEGER,
        link TEXT,
        fiyat REAL
    )
    ''')

    # 2. ANALİZ GEÇMİŞİ TABLOSU
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        leke_sayisi INTEGER,
        cilt_skoru INTEGER,
        onerilen_urun_id INTEGER,
        FOREIGN KEY(onerilen_urun_id) REFERENCES products(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Veritabani tablolari hazir/kontrol edildi.")

def baslangic_verisi_ekle():
    """Tablo boşsa varsayılan başlangıç ürünlerini ekler."""
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    cursor.execute("SELECT count(*) FROM products")
    sayi = cursor.fetchone()[0]
    
    if sayi == 0:
        print("⚠️ Tablo boş, varsayılan ürünler ekleniyor...")
        urunler = [
            ("Salisilik Asit Tonik", "COSRX", "Problemli", 40, "trendyol.com/salisilik", 450.0),
            ("C Vitamini Serumu", "The Ordinary", "Yorgun", 15, "hepsiburada.com/cvitamin", 320.0),
            ("Hafif Nemlendirici", "Cerave", "Mükemmel", 0, "amazon.com/nemlendirici", 280.0)
        ]
        cursor.executemany("INSERT INTO products (ad, marka, problem_turu, esik_deger, link, fiyat) VALUES (?,?,?,?,?,?)", urunler)
        conn.commit()
        print("✅ Varsayılan ürünler eklendi.")
    
    conn.close()

def analiz_kaydet(leke, skor, urun_adi):
    """Yapılan her analizi kaydeder."""
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    # Önce önerilen ürünün ID'sini bulalım
    cursor.execute("SELECT id FROM products WHERE ad = ?", (urun_adi,))
    sonuc = cursor.fetchone()
    urun_id = sonuc[0] if sonuc else None
    
    tarih = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("INSERT INTO analysis_history (tarih, leke_sayisi, cilt_skoru, onerilen_urun_id) VALUES (?, ?, ?, ?)", 
                   (tarih, leke, skor, urun_id))
    conn.commit()
    conn.close()

def en_uygun_urunu_bul(leke_sayisi):
    """SQL'den eşik değerine göre ürün çeker."""
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM products WHERE esik_deger <= ? ORDER BY esik_deger DESC LIMIT 1", (leke_sayisi,))
    urun = cursor.fetchone()
    conn.close()
    
    if urun:
        # (id, ad, marka, problem, esik, link, fiyat)
        return {
            "urun_adi": urun[1],
            "marka": urun[2],
            "hedef_problem": urun[3],
            "link": urun[5]
        }
    else:
        return {"urun_adi": "Bilinmiyor", "marka": "-", "hedef_problem": "Belirsiz", "link": "#"}

# --- YENİ EKLENEN ADMIN FONKSİYONLARI ---

def tum_urunleri_getir():
    """Admin paneli için tüm ürünleri listeler."""
    conn = baglanti_kur()
    conn.row_factory = sqlite3.Row # Veriyi sözlük gibi çekmemizi sağlar
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    
    sonuc = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sonuc

def analiz_gecmisini_getir():
    """Admin paneli için analiz geçmişini çeker."""
    conn = baglanti_kur()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    sorgu = '''
    SELECT h.tarih, h.leke_sayisi, h.cilt_skoru, p.ad as onerilen_urun 
    FROM analysis_history h
    LEFT JOIN products p ON h.onerilen_urun_id = p.id
    ORDER BY h.tarih DESC
    '''
    cursor.execute(sorgu)
    
    sonuc = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sonuc

def urun_ekle_sql(ad, marka, problem, esik, link, fiyat):
    """Admin panelinden yeni ürün ekler."""
    conn = baglanti_kur()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (ad, marka, problem_turu, esik_deger, link, fiyat) VALUES (?,?,?,?,?,?)", 
                   (ad, marka, problem, esik, link, fiyat))
    conn.commit()
    conn.close()

# --- BAŞLANGIÇ KURULUMU ---
if __name__ == "__main__":
    tablolari_olustur()
>>>>>>> ea47e5eb7c0f678437af64e22143a2d741433320
    baslangic_verisi_ekle()