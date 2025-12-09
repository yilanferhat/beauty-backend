from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import cv2
import mediapipe as mp
import numpy as np
import database 
import traceback # Hata takibi ve loglama için

# --- UYGULAMA AYARLARI ---
app = FastAPI(title="BeautyTech Master API", description="Medical Grade Skin Analysis")

# CORS (Güvenlik İzni - Her yerden erişime aç)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Veritabanı Başlatma (Hata verirse yoksay, sunucuyu çökertme)
try:
    database.tablolari_olustur()
    database.baslangic_verisi_ekle()
except Exception as e:
    print(f"Veritabanı hatası (Önemsiz): {e}")

# MediaPipe Ayarları (Yüz Tarama Motoru)
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5
)

# ==========================================
# 1. BÖLÜM: GÖRÜNTÜ İŞLEME MOTORU (ESKİ KODLAR)
# ==========================================

def preprocess_image(image):
    """
    Görüntüyü temizler, parlamaları azaltır ve analize hazırlar.
    Bu senin eski kodundaki mantığın aynısıdır.
    """
    try:
        # Gürültü temizleme (Bilateral Filter)
        denoised = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
        
        # Renk dengeleme (CLAHE)
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        processed = cv2.merge((cl,a,b))
        
        return cv2.cvtColor(processed, cv2.COLOR_LAB2BGR)
    except:
        return image # Hata olursa orjinalini döndür

def create_face_mask(h, w, landmarks):
    """
    Yüzün dış hatlarını çıkarır, sadece yüzü analiz etmemizi sağlar.
    Saçları ve arka planı yok sayar.
    """
    mask = np.zeros((h, w), dtype=np.uint8)
    # Yüz ovali indexleri (MediaPipe standardı)
    face_oval = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
    points = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in face_oval], np.int32)
    cv2.fillConvexPoly(mask, points, 255)
    return mask

def detect_wrinkles_tophat(gray_image, mask):
    """
    Kırışıklık tespiti yapan özel algoritma.
    Top-Hat dönüşümü ile ince çizgileri yakalar.
    """
    try:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        tophat = cv2.morphologyEx(gray_image, cv2.MORPH_TOPHAT, kernel)
        tophat = cv2.bitwise_and(tophat, tophat, mask=mask)
        
        _, thresh = cv2.threshold(tophat, 15, 255, cv2.THRESH_BINARY)
        wrinkle_pixels = cv2.countNonZero(thresh)
        face_area = cv2.countNonZero(mask)
        
        if face_area == 0: return 0
        
        # Oran hesaplama
        ratio = (wrinkle_pixels / face_area) * 1000 
        return ratio
    except:
        return 0 

def detect_spots_adaptive(gray_image, mask):
    """
    Leke tespiti yapan algoritma.
    Adaptive Thresholding ile sivilce ve lekeleri sayar.
    """
    try:
        blur = cv2.GaussianBlur(gray_image, (17, 17), 0)
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 3)
        thresh = cv2.bitwise_and(thresh, thresh, mask=mask)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        spot_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Çok küçük (gürültü) ve çok büyük (gölge) alanları ele
            if 15 < area < 400: 
                spot_count += 1
        return spot_count
    except:
        return 0

# ==========================================
# 2. BÖLÜM: YENİ EKLENEN ÖZELLİK (CİLT TİPİ)
# ==========================================

def detect_skin_type(image, landmarks):
    """
    T Bölgesindeki (Alın ve Burun) parlaklığı analiz eder.
    Yağlı Cilt (Parlak) vs Kuru Cilt (Mat) ayrımı yapar.
    Bu özellik eşinin doğru sonucu alması için eklendi.
    """
    try:
        h, w, c = image.shape
        
        # T Bölgesi Noktaları (MediaPipe Indexleri)
        # Alın (Forehead) ve Burun (Nose) bölgeleri
        t_zone_indices = [10, 338, 297, 332, 284, 251, 389, 356, 168, 6, 197, 195, 5, 4]
        
        # Maske oluştur
        mask = np.zeros((h, w), dtype=np.uint8)
        points = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in t_zone_indices], np.int32)
        
        # T Bölgesini doldur
        hull = cv2.convexHull(points)
        cv2.fillConvexPoly(mask, hull, 255)
        
        # Görüntüyü HSV formatına çevir (Parlaklık analizi için en iyisi)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:,:,2] # Value (Parlaklık) kanalı
        
        # Sadece T bölgesindeki parlaklık ortalamasını al
        t_zone_brightness = cv2.mean(v_channel, mask=mask)[0]
        
        print(f"DEBUG: T-Zone Parlaklık Değeri: {t_zone_brightness}")
        
        # Eşik Değerleri (Hassas Ayar)
        if t_zone_brightness > 155: 
            return "Yağlı Cilt"
        elif t_zone_brightness < 110: 
            return "Kuru Cilt"
        else:
            return "Karma/Normal"
    except Exception as e:
        print(f"Cilt tipi hatası: {e}")
        return "Normal"

# ==========================================
# 3. BÖLÜM: ANA ANALİZ SERVİSİ (BİRLEŞTİRME)
# ==========================================

@app.post("/analiz_et")
async def analiz_et(file: UploadFile = File(...)):
    # --- GÜVENLİK BLOĞU (Hava Yastığı) ---
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Resim okunamadıysa
        if frame is None:
            return {"status": "failed", "message": "Resim dosyasi bozuk veya okunamadi"}

        h, w, c = frame.shape

        # A. Ön İşleme (Eski Kod)
        processed_frame = preprocess_image(frame)
        
        # B. Yüz Taraması (MediaPipe)
        rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            # Yüz bulunamadıysa çökme, düzgün cevap dön
            return {
                "status": "success",
                "genel_skor": 0,
                "detaylar": {
                    "leke_skoru": 0, "leke_sayisi": 0,
                    "kirisiklik_skoru": 0, "kirisiklik_indeksi": 0,
                    "ana_sorun": "Yüz Algılanamadı"
                },
                "reçete": {"onerilen_urun": "Tekrar Deneyin", "marka": "-", "link": ""}
            }
        
        landmarks = results.multi_face_landmarks[0]
        face_mask = create_face_mask(h, w, landmarks)
        gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
        
        # C. Detaylı Analizler (HEPSİ ÇALIŞIYOR)
        wrinkle_index = detect_wrinkles_tophat(gray, face_mask) # Kırışıklık
        spot_count = detect_spots_adaptive(gray, face_mask)     # Leke
        cilt_tipi = detect_skin_type(processed_frame, landmarks) # YENİ: Cilt Tipi
        
        # D. Puanlama Mantığı (Senin istediğin formüller)
        # Kırışıklık puanı
        if wrinkle_index < 5: kirisiklik_puani = 100
        else: kirisiklik_puani = max(10, 100 - (wrinkle_index * 1.5))
            
        # Leke puanı
        leke_puani = max(10, 100 - (spot_count * 0.8))
        
        # Genel Skor (Ortalama + Bonus)
        genel_skor = int((kirisiklik_puani * 0.45) + (leke_puani * 0.45) + 10)
        if genel_skor > 100: genel_skor = 100
        
        # E. Ana Sorun Belirleme
        # Varsayılan sorun artık CİLT TİPİ (Örn: "Kuru Cilt")
        ana_sorun = cilt_tipi 
        
        # Ancak bariz bir leke/kırışıklık varsa onu yaz
        if genel_skor < 85:
            if spot_count > 20: ana_sorun = "Leke/Akne"
            elif kirisiklik_puani < 60: ana_sorun = "Kırışıklık"

        # F. Ürün Önerisi (Veritabanından Çekme)
        # BURASI ÖNEMLİ: Artık 3 bilgi gönderiyoruz!
        try:
            onerilen_urun = database.en_uygun_urunu_bul(spot_count, wrinkle_index, cilt_tipi)
            
            # Veritabanına kaydet
            database.analiz_kaydet(spot_count, genel_skor, onerilen_urun['urun_adi'])
        except Exception as db_err:
            print(f"DB Hatası: {db_err}")
            # Hata olursa güvenli bir ürün öner
            onerilen_urun = {"urun_adi": "Genel Bakım Kremi", "marka": "Nivea", "link": ""}

        # G. Sonuç Döndürme (Flutter'a giden veri)
        return {
            "status": "success",
            "genel_skor": genel_skor,
            "detaylar": {
                "leke_skoru": int(leke_puani),
                "leke_sayisi": spot_count,
                "kirisiklik_skoru": int(kirisiklik_puani),
                "kirisiklik_indeksi": round(wrinkle_index, 2),
                "ana_sorun": ana_sorun # Burası artık "Kuru Cilt" dönebilir
            },
            "reçete": {
                "sorun": ana_sorun,
                "onerilen_urun": onerilen_urun['urun_adi'],
                "marka": onerilen_urun['marka'],
                "link": onerilen_urun['link']
            }
        }

    except Exception as e:
        # Hata yakalama (App çökmesin diye)
        print(f"KRİTİK HATA: {traceback.format_exc()}")
        return {
            "status": "error",
            "genel_skor": 0,
            "message": str(e),
            "detaylar": {"ana_sorun": "Sunucu Hatası"},
            "reçete": {"onerilen_urun": "Sistem Hatası", "marka": "Lütfen tekrar deneyin", "link": ""}
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)