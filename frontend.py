import streamlit as st
import requests
from PIL import Image
import io
import database # SQL Veritabanı modülümüzü çağırıyoruz
import pandas as pd # Tablo ve grafikler için

# --- AYARLAR ---
API_URL = "http://127.0.0.1:8000/analiz_et"
st.set_page_config(page_title="BeautyTech AI", page_icon="💄", layout="wide")

# --- YAN MENÜ ---
st.sidebar.title("BeautyTech Menü")
secim = st.sidebar.radio("Git:", ["👤 Kullanici Modu", "📊 Patron Ekrani (Admin)"])

# ==========================================
# MOD 1: KULLANICI ARAYÜZÜ
# ==========================================
if secim == "👤 Kullanici Modu":
    st.header("Yapay Zeka Cilt Analizi 📸")
    
    # Kamera veya Dosya Seçimi
    kaynak = st.radio("Fotograf Kaynagi:", ["Dosya Yukle", "Kamera Ac"], horizontal=True)
    
    img_file = None
    if kaynak == "Dosya Yukle":
        img_file = st.file_uploader("Fotograf Sec...", type=["jpg", "png"])
    else:
        img_file = st.camera_input("Selfie Cek")

    if img_file is not None:
        # Görseli göster (Sadece dosya yüklemedeyse, kamera zaten gösteriyor)
        if kaynak == "Dosya Yukle":
            image = Image.open(img_file)
            st.image(image, width=300)
        else:
            image = Image.open(img_file)

        if st.button("🔍 Analiz Et", type="primary"):
            with st.spinner('AI cildinizi tarıyor...'):
                try:
                    # API'ye Gönderim Hazırlığı
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='JPEG') # Hepsini JPEG'e çevir
                    img_bytes = img_byte_arr.getvalue()

                    files = {'file': ('image.jpg', img_bytes, 'image/jpeg')}
                    response = requests.post(API_URL, files=files)

                    if response.status_code == 200:
                        data = response.json()
                        
                        # Sonuçları Göster
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Cilt Skoru", f"{data['cilt_skoru']}/100", f"{data['cilt_skoru']-100}")
                        col2.metric("Leke Sayisi", f"{data['leke_sayisi']} adet")
                        col3.metric("Tespit", data['reçete']['sorun'])
                        
                        st.success(f"Oneri: {data['reçete']['onerilen_urun']} ({data['reçete']['marka']})")
                        st.link_button("🛒 Satin Al", data['reçete']['link'])
                        
                    else:
                        st.error("Analiz yapilamadi. Yuz net gorunmuyor olabilir.")
                except Exception as e:
                    st.error(f"Baglanti Hatasi: {e}")

# ==========================================
# MOD 2: PATRON EKRANI (DASHBOARD)
# ==========================================
elif secim == "📊 Patron Ekrani (Admin)":
    st.title("Yonetim Paneli 🛠️")
    
    sifre = st.sidebar.text_input("Admin Sifresi", type="password")
    
    if sifre == "admin123":
        tab1, tab2 = st.tabs(["📈 Analiz Gecmisi", "➕ Urun Yonetimi"])
        
        # --- SEKME 1: ANALİZ RAPORLARI ---
        with tab1:
            st.subheader("Sistem Performans Raporu")
            
            # Veritabanından geçmişi çek
            gecmis_data = database.analiz_gecmisini_getir()
            
            if gecmis_data:
                df = pd.DataFrame(gecmis_data)
                
                # Özet Kartlar
                c1, c2, c3 = st.columns(3)
                c1.metric("Toplam Analiz", len(df))
                c2.metric("Ortalama Cilt Skoru", int(df['cilt_skoru'].mean()))
                c3.metric("En Son Analiz", df['tarih'].iloc[0])
                
                # Tabloyu Göster
                st.dataframe(df, use_container_width=True)
                
                # Grafik: Zamanla Cilt Skoru Değişimi
                st.subheader("Zaman icinde Analiz Skorlari")
                st.line_chart(df.set_index('tarih')['cilt_skoru'])
            else:
                st.info("Henuz hic analiz yapilmadi.")

        # --- SEKME 2: ÜRÜN EKLEME ---
        with tab2:
            st.subheader("Yeni Urun Ekle")
            with st.form("sql_urun_form"):
                ad = st.text_input("Urun Adi")
                marka = st.text_input("Marka")
                problem = st.selectbox("Hedef Problem", ["Problemli", "Yorgun", "Mükemmel", "Kuru"])
                esik = st.slider("Leke Esik Degeri", 0, 100, 30)
                fiyat = st.number_input("Fiyat (TL)", 0, 5000, 100)
                link = st.text_input("Satis Linki")
                
                if st.form_submit_button("Veritabanina Kaydet"):
                    database.urun_ekle_sql(ad, marka, problem, esik, link, fiyat)
                    st.success("✅ Urun SQL Veritabanina Eklendi!")
                    st.experimental_rerun()
                    
            st.divider()
            st.subheader("Mevcut Urunler")
            urunler = database.tum_urunleri_getir()
            st.table(urunler)
            
    else:
        st.warning("Giris yapmak icin sifreyi giriniz.")