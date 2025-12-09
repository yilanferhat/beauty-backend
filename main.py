from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import cv2
import mediapipe as mp
import numpy as np
import database 
import traceback 

# ==========================================
# 1. UYGULAMA AYARLARI (ELON MUSK LEVEL 🚀)
# ==========================================

app = FastAPI(title="BeautyTech Ultra AI", description="Next-Gen Skin Analysis Kernel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB Başlatma
try:
    database.tablolari_olustur()
    database.baslangic_verisi_ekle()
except Exception as e:
    print(f"DB Log: {e}")

# MediaPipe (Yüz Haritalama - 468 Nokta)
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5
)

# ==========================================
# 2. GÖRÜNTÜ İŞLEME MODÜLLERİ
# ==========================================

def preprocess_image(image):
    """Görüntüyü laboratuvar standardına getirir."""
    try:
        denoised = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        processed = cv2.merge((cl,a,b))
        return cv2.cvtColor(processed, cv2.COLOR_LAB2BGR)
    except:
        return image 

def create_face_mask(h, w, landmarks):
    """Sadece cilt dokusunu izole eder."""
    mask = np.zeros((h, w), dtype=np.uint8)
    face_oval = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
    points = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in face_oval], np.int32)
    cv2.fillConvexPoly(mask, points, 255)
    return mask

# --- MODÜL 1: KIRIŞIKLIK (Hassasiyet Ayarlı) ---
def detect_wrinkles_tophat(gray_image, mask):
    try:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        tophat = cv2.morphologyEx(gray_image, cv2.MORPH_TOPHAT, kernel)
        tophat = cv2.bitwise_and(tophat, tophat, mask=mask)
        # Eşik değeri 35'te tutuyoruz (Gençleri yaşlı sanmasın diye)
        _, thresh = cv2.threshold(tophat, 35, 255, cv2.THRESH_BINARY)
        wrinkle_pixels = cv2.countNonZero(thresh)
        face_area = cv2.countNonZero(mask)
        if face_area == 0: return 0
        ratio = (wrinkle_pixels / face_area) * 1000 
        return ratio
    except:
        return 0 

# --- MODÜL 2: LEKE VE AKNE ---
def detect_spots_adaptive(gray_image, mask):
    try:
        blur = cv2.GaussianBlur(gray_image, (17, 17), 0)
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 3)
        thresh = cv2.bitwise_and(thresh, thresh, mask=mask)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        spot_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 15 < area < 400: spot_count += 1
        return spot_count
    except:
        return 0

# --- MODÜL 3: CİLT TİPİ (T-Bölgesi Parlaklığı) ---
def detect_skin_type_advanced(image, landmarks):
    try:
        h, w, c = image.shape
        t_zone_indices = [10, 338, 297, 332, 284, 251, 389, 356, 168, 6, 197, 195, 5, 4]
        mask = np.zeros((h, w), dtype=np.uint8)
        points = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in t_zone_indices], np.int32)
        hull = cv2.convexHull(points)
        cv2.fillConvexPoly(mask, hull, 255)
        
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:,:,2] 
        t_zone_brightness = cv2.mean(v_channel, mask=mask)[0]
        
        # Daha bilimsel kategoriler
        if t_zone_brightness > 160: return "Yağlı/Parlak"
        elif t_zone_brightness < 100: return "Kuru/Mat"
        else: return "Karma/Dengeli"
    except:
        return "Karma/Dengeli"

# --- MODÜL 4: GÖZ ALTI MORLUKLARI (YENİ 🌟) ---
def detect_dark_circles(image, landmarks):
    try:
        h, w, c = image.shape
        # Sol ve Sağ göz altı bölgesi
        left_eye_indices = [349, 348, 347, 346, 345, 340, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        
        mask = np.zeros((h, w), dtype=np.uint8)
        points = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in left_eye_indices], np.int32)
        hull = cv2.convexHull(points)
        cv2.fillConvexPoly(mask, hull, 255)
        
        # LAB renk uzayında L (Lightness) kanalına bak
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel = lab[:,:,0]
        
        eye_brightness = cv2.mean(l_channel, mask=mask)[0]
        
        # Yanak parlaklığıyla kıyasla (Referans noktası)
        cheek_brightness = eye_brightness + 20 # Varsayılan referans
        
        diff = cheek_brightness - eye_brightness
        
        if diff > 40: return True # Göz altı çok koyu
        return False
    except:
        return False

# --- MODÜL 5: KIZARIKLIK / HASSASİYET (YENİ 🌟) ---
def detect_redness(image, landmarks):
    try:
        h, w, c = image.shape
        # Yanak bölgesi
        cheek_indices = [116, 117, 118, 100, 126, 209, 198, 50, 101, 203, 205, 36, 123, 137]
        
        mask = np.zeros((h, w), dtype=np.uint8)
        points = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in cheek_indices], np.int32)
        hull = cv2.convexHull(points)
        cv2.fillConvexPoly(mask, hull, 255)
        
        # LAB renk uzayında A kanalı (Yeşil-Kırmızı ekseni)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        a_channel = lab[:,:,1]
        
        redness_score = cv2.mean(a_channel, mask=mask)[0]
        
        if redness_score > 150: return True # Cilt kızarık
        return False
    except:
        return False

# ==========================================
# 3. KARAR MOTORU (MASTERMIND)
# ==========================================

@app.post("/analiz_et")
async def analiz_et(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None: return {"status": "error", "genel_skor": 0}

        h, w, c = frame.shape
        processed_frame = preprocess_image(frame)
        rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return {"status": "success", "genel_skor": 0, "detaylar": {"ana_sorun": "Yüz Bulunamadı"}, "reçete": {"onerilen_urun": "-"}}
        
        landmarks = results.multi_face_landmarks[0]
        face_mask = create_face_mask(h, w, landmarks)
        gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
        
        # --- ANALİZLERİ ÇALIŞTIR ---
        wrinkle_index = detect_wrinkles_tophat(gray, face_mask)
        spot_count = detect_spots_adaptive(gray, face_mask)
        cilt_tipi_raw = detect_skin_type_advanced(processed_frame, landmarks)
        has_dark_circles = detect_dark_circles(processed_frame, landmarks)
        has_redness = detect_redness(processed_frame, landmarks)
        
        # --- PUANLAMA MANTIĞI ---
        # Gençleri korumak için kırışıklık eşiğini çok yüksek tutuyoruz
        if wrinkle_index < 12: kirisiklik_puani = 100 # HATA PAYI DÜŞÜRÜLDÜ
        else: kirisiklik_puani = max(10, 100 - (wrinkle_index * 1.0))
        
        leke_puani = max(10, 100 - (spot_count * 0.8))
        
        genel_skor = int((kirisiklik_puani * 0.45) + (leke_puani * 0.45) + 10)
        
        # Bonus Puanlar (Cilt iyiyse ödüllendir)
        if not has_dark_circles: genel_skor += 2
        if not has_redness: genel_skor += 2
        if genel_skor > 100: genel_skor = 100
        
        # --- TEŞHİS KOYMA (KARAR AĞACI) ---
        # Burası Elon Musk seviyesi: Sadece sayıya bakmaz, duruma bakar.
        
        ana_sorun = "Cilt Dengesi İyi" # Varsayılan pozitif
        
        # 1. Öncelik: CİDDİ SORUNLAR
        if genel_skor < 85:
            if spot_count > 25: 
                ana_sorun = "Akne/Leke Eğilimi"
            elif kirisiklik_puani < 50: # Sadece puan çok düşükse yaşlanma de
                ana_sorun = "Elastikiyet Kaybı (Yaşlanma)"
            elif has_redness:
                ana_sorun = "Hassas/Kızarık Cilt"
            elif has_dark_circles:
                ana_sorun = "Göz Çevresi Yorgunluğu"
        
        # 2. Öncelik: ORTA SEVİYE SORUNLAR (Gençler buraya düşer)
        elif genel_skor < 94:
            if cilt_tipi_raw == "Kuru/Mat":
                ana_sorun = "Nem İhtiyacı (Kuruluk)"
            elif cilt_tipi_raw == "Yağlı/Parlak":
                ana_sorun = "Gözenek/Yağlanma Problemi"
            elif has_dark_circles:
                ana_sorun = "Yorgun Görünüm"
            else:
                ana_sorun = "Cilt Tonu Eşitsizliği"
        
        # 3. Öncelik: MÜKEMMEL CİLTLER
        else:
            if cilt_tipi_raw == "Yağlı/Parlak":
                ana_sorun = "Doğal Işıltı (Parlak)"
            else:
                ana_sorun = "Mükemmel Cilt Dengesi"

        # --- DB UYUMLULUĞU ---
        # Veritabanı hala eski anahtar kelimeleri (kuru, yagli, leke, kirisik, normal) bekliyor.
        # Bu yüzden teşhisi veritabanı diline çeviriyoruz (Mapping).
        
        db_category = "normal"
        if "Kuru" in ana_sorun or "Nem" in ana_sorun: db_category = "Kuru Cilt"
        elif "Yağ" in ana_sorun or "Gözenek" in ana_sorun: db_category = "Yağlı Cilt"
        elif "Akne" in ana_sorun or "Leke" in ana_sorun or "Ton" in ana_sorun: db_category = "Karma/Normal" # Leke için özel kategori yoksa normalden ver
        elif "Yaşlanma" in ana_sorun or "Elastikiyet" in ana_sorun: db_category = "Karma/Normal" # Kırışıklık parametresiyle zaten bulunacak
        
        # Veritabanından ürün çek
        try:
            # Parametreleri gönderiyoruz
            onerilen_urun = database.en_uygun_urunu_bul(spot_count, wrinkle_index, db_category)
            database.analiz_kaydet(spot_count, genel_skor, onerilen_urun['urun_adi'])
        except:
            onerilen_urun = {"urun_adi": "Günlük Bakım Kremi", "marka": "Simple", "link": ""}

        return {
            "status": "success",
            "genel_skor": genel_skor,
            "detaylar": {
                "leke_skoru": int(leke_puani),
                "leke_sayisi": spot_count,
                "kirisiklik_skoru": int(kirisiklik_puani),
                "kirisiklik_indeksi": round(wrinkle_index, 2),
                "ana_sorun": ana_sorun # ÖRN: "Nem İhtiyacı"
            },
            "reçete": {
                "sorun": ana_sorun,
                "onerilen_urun": onerilen_urun['urun_adi'],
                "marka": onerilen_urun['marka'],
                "link": onerilen_urun['link']
            }
        }

    except Exception as e:
        print(f"HATA: {traceback.format_exc()}")
        return {"status": "error", "genel_skor": 0, "detaylar": {"ana_sorun": "Hata"}, "reçete": {"onerilen_urun": "-", "link": ""}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)