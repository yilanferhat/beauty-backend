from fastapi import FastAPI, File, UploadFile
import cv2
import mediapipe as mp
import numpy as np
import database 

app = FastAPI(title="BeautyTech AAA+ API", description="Ultra Profesyonel Cilt Analiz Motoru")

# Veritabanını Başlat
try:
    database.tablolari_olustur()
    database.baslangic_verisi_ekle()
except:
    pass

# MediaPipe Ayarları (Yüz Mesh)
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5
)

# --- YASAKLI BÖLGELER (Maskelenecek Alanlar) ---
EXCLUDE_INDICES = [
    33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 144, 145, 153, 52, 65, 55, 
    263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249, 285, 
    70, 63, 105, 66, 107, 55, 193, 
    336, 296, 334, 293, 300, 285, 417, 
    61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78, 
    2, 326, 327, 278, 279, 360, 363, 281, 5, 51, 48, 49, 131, 134, 115, 220
]

def analyze_skin_quality(image, landmarks):
    h, w, c = image.shape
    face_mask = np.zeros((h, w), dtype=np.uint8)
    face_oval = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
    face_pts = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in face_oval], np.int32)
    cv2.fillConvexPoly(face_mask, face_pts, 255)
    
    exclusion_mask = np.zeros((h, w), dtype=np.uint8)
    for idx in EXCLUDE_INDICES:
        lm = landmarks.landmark[idx]
        x, y = int(lm.x * w), int(lm.y * h)
        cv2.circle(exclusion_mask, (x, y), 15, 255, -1) 
        
    final_skin_mask = cv2.bitwise_and(face_mask, cv2.bitwise_not(exclusion_mask))
    
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl,a,b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 17, 4)
    thresh = cv2.bitwise_and(thresh, thresh, mask=final_skin_mask)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    leke_sayisi = 0
    ciddi_leke_sayisi = 0
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 8 < area < 400: 
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0: continue
            circularity = 4 * np.pi * (area / (perimeter * perimeter))
            if circularity > 0.3: 
                leke_sayisi += 1
                if area > 30:
                    ciddi_leke_sayisi += 1
                    
    return leke_sayisi, ciddi_leke_sayisi

@app.post("/analiz_et")
async def analiz_et(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    if not results.multi_face_landmarks:
        return {"status": "failed", "message": "Yuz bulunamadi"}

    landmarks = results.multi_face_landmarks[0]
    
    toplam_leke, ciddi_leke = analyze_skin_quality(frame, landmarks)
    
    kayip_puan = (toplam_leke * 0.5) + (ciddi_leke * 2)
    genel_skor = max(10, int(100 - kayip_puan))
    
    kirisiklik_skoru = max(0, 100 - int(toplam_leke / 3)) 
    
    ana_sorun = "Mükemmel Cilt"
    if genel_skor < 90:
        if ciddi_leke > 5:
            ana_sorun = "Akne/Sivilce"
        elif toplam_leke > 30:
            ana_sorun = "Geniş Gözenek/Leke"
        else:
            ana_sorun = "Yorgun Görünüm"

    onerilen_urun = database.en_uygun_urunu_bul(toplam_leke)
    database.analiz_kaydet(toplam_leke, genel_skor, onerilen_urun['urun_adi'])

    return {
        "status": "success",
        "genel_skor": genel_skor,
        "detaylar": {
            "leke_skoru": max(0, 100 - int(kayip_puan)),
            "leke_sayisi": toplam_leke,
            "ciddi_leke": ciddi_leke,
            "kirisiklik_skoru": kirisiklik_skoru,
            "ana_sorun": ana_sorun
        },
        "reçete": {
            "sorun": ana_sorun,
            "onerilen_urun": onerilen_urun['urun_adi'],
            "marka": onerilen_urun['marka'],
            "link": onerilen_urun['link']
        }
    }
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)