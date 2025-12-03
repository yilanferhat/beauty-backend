from fastapi import FastAPI, File, UploadFile
import cv2
import mediapipe as mp
import numpy as np
import database 

# --- BAŞLANGIÇ AYARLARI ---
app = FastAPI(title="BeautyTech API", description="SQL Destekli Cilt Analiz Sunucusu")

print("--- SUNUCU BASLATILIYOR ---")
try:
    database.tablolari_olustur()
    database.baslangic_verisi_ekle()
    print("✅ Veritabani baglantisi basarili.")
except Exception as e:
    print(f"❌ Veritabani hatasi: {e}")

# MediaPipe Ayarları
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)

# Analiz Bölgeleri
FOREHEAD_INDICES = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
LEFT_CHEEK_INDICES = [330, 347, 346, 352, 374, 427, 426, 425, 423, 371, 355, 437, 399, 419, 431, 280, 411, 425]
RIGHT_CHEEK_INDICES = [101, 118, 117, 123, 145, 207, 206, 205, 203, 142, 126, 217, 174, 196, 211, 50, 187, 205]

def create_mask_from_indices(indices, shape, landmarks):
    mask = np.zeros(shape[:2], dtype=np.uint8)
    points = []
    for idx in indices:
        pt = landmarks[idx]
        x = int(pt.x * shape[1])
        y = int(pt.y * shape[0])
        points.append([x, y])
    if points:
        points = np.array(points, dtype=np.int32)
        hull = cv2.convexHull(points)
        cv2.fillConvexPoly(mask, hull, 255)
    return mask

@app.get("/")
def home():
    return {"message": "SQL Veritabani ile calisan BeautyTech sunucusu aktif!"}

@app.post("/analiz_et")
async def analiz_et(file: UploadFile = File(...)):
    print(f"\n📩 YENI ISTEK GELDI! Dosya adi: {file.filename}")
    
    # 1. Dosya Okuma
    print("⏳ Dosya okunuyor...")
    contents = await file.read()
    print(f"✅ Dosya okundu ({len(contents)} bytes).")
    
    # 2. Decode
    print("⏳ Goruntu isleniyor (Decode)...")
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    print("✅ Goruntu decode edildi.")

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # 3. MediaPipe İşlemi
    print("⏳ Yuz taraniyor (MediaPipe)...")
    results = face_mesh.process(rgb_frame)
    
    leke_sayisi = 0
    analiz_sonucu = {"status": "failed", "message": "Yuz bulunamadi"}

    if results.multi_face_landmarks:
        print("✅ Yuz bulundu! Leke analizi basliyor...")
        for face_landmarks in results.multi_face_landmarks:
            h, w, c = frame.shape
            mask_total = np.zeros((h, w), dtype=np.uint8)
            mask_total = cv2.bitwise_or(mask_total, create_mask_from_indices(FOREHEAD_INDICES, frame.shape, face_landmarks.landmark))
            mask_total = cv2.bitwise_or(mask_total, create_mask_from_indices(LEFT_CHEEK_INDICES, frame.shape, face_landmarks.landmark))
            mask_total = cv2.bitwise_or(mask_total, create_mask_from_indices(RIGHT_CHEEK_INDICES, frame.shape, face_landmarks.landmark))

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            thresh = cv2.bitwise_and(thresh, thresh, mask=mask_total)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 2 < area < 30:
                    leke_sayisi += 1
            
            print(f"✅ Analiz bitti. Leke Sayisi: {leke_sayisi}")

            # SQL İşlemleri
            print("⏳ Veritabanindan urun soruluyor...")
            onerilen_urun = database.en_uygun_urunu_bul(leke_sayisi)
            cilt_skoru = max(0, 100 - leke_sayisi)

            print("⏳ Analiz kaydediliyor...")
            database.analiz_kaydet(leke_sayisi, cilt_skoru, onerilen_urun['urun_adi'])
            print("✅ Kayit basarili!")

            analiz_sonucu = {
                "status": "success",
                "cilt_skoru": cilt_skoru,
                "leke_sayisi": leke_sayisi,
                "reçete": {
                    "sorun": onerilen_urun['hedef_problem'],
                    "onerilen_urun": onerilen_urun['urun_adi'],
                    "marka": onerilen_urun['marka'],
                    "link": onerilen_urun['link']
                }
            }
    else:
        print("❌ Fotografta yuz bulunamadi.")
            
    print("🚀 Cevap gonderiliyor...")
    return analiz_sonucu

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)