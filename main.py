from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import cv2
import mediapipe as mp
import numpy as np
import database 
import traceback # Hata takibi için

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

# MediaPipe Ayarları
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5
)

# --- YARDIMCI FONKSİYONLAR ---

def preprocess_image(image):
    """Gürültü temizleme ve renk dengeleme"""
    try:
        denoised = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        processed = cv2.merge((cl,a,b))
        return cv2.cvtColor(processed, cv2.COLOR_LAB2BGR)
    except:
        return image # Hata olursa orjinalini döndür

def create_face_mask(h, w, landmarks):
    mask = np.zeros((h, w), dtype=np.uint8)
    # Basit yüz ovali (Basitleştirilmiş indexler)
    face_oval = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
    points = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in face_oval], np.int32)
    cv2.fillConvexPoly(mask, points, 255)
    return mask

def detect_wrinkles_tophat(gray_image, mask):
    try:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        tophat = cv2.morphologyEx(gray_image, cv2.MORPH_TOPHAT, kernel)
        tophat = cv2.bitwise_and(tophat, tophat, mask=mask)
        _, thresh = cv2.threshold(tophat, 15, 255, cv2.THRESH_BINARY)
        wrinkle_pixels = cv2.countNonZero(thresh)
        face_area = cv2.countNonZero(mask)
        if face_area == 0: return 0
        ratio = (wrinkle_pixels / face_area) * 1000 
        return ratio
    except:
        return 0 # Hata olursa 0 döndür

def detect_spots_adaptive(gray_image, mask):
    try:
        blur = cv2.GaussianBlur(gray_image, (17, 17), 0)
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 3)
        thresh = cv2.bitwise_and(thresh, thresh, mask=mask)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        spot_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 15 < area < 400: 
                spot_count += 1
        return spot_count
    except:
        return 0

@app.post("/analiz_et")
async def analiz_et(file: UploadFile = File(...)):
    # --- GÜVENLİK BLOĞU BAŞLANGICI ---
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Resim okunamadıysa
        if frame is None:
            return {"status": "failed", "message": "Resim dosyasi bozuk veya okunamadi"}

        h, w, c = frame.shape

        # 1. İşleme
        processed_frame = preprocess_image(frame)
        
        # 2. Yüz Taraması
        rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            # Yüz bulunamadıysa 500 verme, düzgün cevap dön
            return {
                "status": "success", # Uygulama çökmesin diye success dönüyoruz ama puan 0
                "genel_skor": 0,
                "detaylar": {
                    "leke_skoru": 0, "leke_sayisi": 0, "ciddi_leke": 0,
                    "kirisiklik_skoru": 0, "kirisiklik_indeksi": 0,
                    "ana_sorun": "Yüz Algılanamadı"
                },
                "reçete": {"onerilen_urun": "Tekrar Deneyin", "marka": "-", "link": ""}
            }
        
        landmarks = results.multi_face_landmarks[0]
        face_mask = create_face_mask(h, w, landmarks)
        gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
        
        # 3. Analizler
        wrinkle_index = detect_wrinkles_tophat(gray, face_mask)
        spot_count = detect_spots_adaptive(gray, face_mask)
        
        # 4. Puanlama
        if wrinkle_index < 5: kirisiklik_puani = 100
        else: kirisiklik_puani = max(10, 100 - (wrinkle_index * 1.5))
            
        leke_puani = max(10, 100 - (spot_count * 0.8))
        
        genel_skor = int((kirisiklik_puani * 0.5) + (leke_puani * 0.5))
        
        ana_sorun = "Mükemmel Cilt"
        if genel_skor < 92:
            if kirisiklik_puani < leke_puani: ana_sorun = "Kırışıklık/Yaşlanma"
            elif spot_count > 20: ana_sorun = "Cilt Lekeleri"
            else: ana_sorun = "Yorgun Görünüm"

        # 5. Veritabanı (Hata korumalı)
        try:
            onerilen_urun = database.en_uygun_urunu_bul(spot_count)
            # Eğer veritabanı boş dönerse elle doldur
            if not onerilen_urun:
                onerilen_urun = {"urun_adi": "Nemlendirici", "marka": "Genel", "link": ""}
                
            database.analiz_kaydet(spot_count, genel_skor, onerilen_urun['urun_adi'])
        except Exception as db_err:
            print(f"DB Hatası: {db_err}")
            onerilen_urun = {"urun_adi": "Genel Bakım Kremi", "marka": "Medikal", "link": ""}

        return {
            "status": "success",
            "genel_skor": genel_skor,
            "detaylar": {
                "leke_skoru": int(leke_puani),
                "leke_sayisi": spot_count,
                "ciddi_leke": 0,
                "kirisiklik_skoru": int(kirisiklik_puani),
                "kirisiklik_indeksi": round(wrinkle_index, 2),
                "ana_sorun": ana_sorun
            },
            "reçete": {
                "sorun": ana_sorun,
                "onerilen_urun": onerilen_urun['urun_adi'],
                "marka": onerilen_urun['marka'],
                "link": onerilen_urun['link']
            }
        }

    except Exception as e:
        # --- HAVA YASTIĞI ---
        # Ne olursa olsun 500 dönme! Hatayı ekrana bas.
        print(f"KRİTİK HATA: {traceback.format_exc()}")
        return {
            "status": "error",
            "genel_skor": 0,
            "message": str(e),
            "detaylar": {"ana_sorun": "Sunucu Hatası"},
            "reçete": {"onerilen_urun": "Sistem Hatası", "marka": "Lütfen tekrar deneyin"}
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)