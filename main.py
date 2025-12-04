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

# MediaPipe Ayarları
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5
)

# --- YASAKLI BÖLGELER ---
EXCLUDE_INDICES = [
    33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 144, 145, 153, 52, 65, 55, 
    263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249, 285, 
    70, 63, 105, 66, 107, 55, 193, 
    336, 296, 334, 293, 300, 285, 417, 
    61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78, 
    2, 326, 327, 278, 279, 360, 363, 281, 5, 51, 48, 49, 131, 134, 115, 220
]

def analyze_skin_features(image, landmarks):
    """Hem Leke Hem Kırışıklık İçin Ortak ve Akıllı Analiz"""
    h, w, c = image.shape
    
    # 1. Maskeleme (Yüzü al, gözleri/ağzı çıkar)
    face_mask = np.zeros((h, w), dtype=np.uint8)
    face_oval = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
    face_pts = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in face_oval], np.int32)
    cv2.fillConvexPoly(face_mask, face_pts, 255)
    
    exclusion_mask = np.zeros((h, w), dtype=np.uint8)
    for idx in EXCLUDE_INDICES:
        lm = landmarks.landmark[idx]
        x, y = int(lm.x * w), int(lm.y * h)
        cv2.circle(exclusion_mask, (x, y), 12, 255, -1) 
        
    final_skin_mask = cv2.bitwise_and(face_mask, cv2.bitwise_not(exclusion_mask))
    
    # 2. Ön İşleme (Işık Dengeleme)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    enhanced = cv2.merge((cl,a,b))
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    # 3. Leke Analizi (Yuvarlak Nesneler)
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    blur_leke = cv2.bilateralFilter(gray, 15, 75, 75)
    thresh_leke = cv2.adaptiveThreshold(blur_leke, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 19, 5)
    thresh_leke = cv2.bitwise_and(thresh_leke, thresh_leke, mask=final_skin_mask)
    
    contours_leke, _ = cv2.findContours(thresh_leke, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    leke_sayisi = 0
    ciddi_leke = 0
    
    for cnt in contours_leke:
        area = cv2.contourArea(cnt)
        if 15 < area < 300: # Hassasiyet ayarı: Çok küçükleri at
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0: continue
            circularity = 4 * np.pi * (area / (perimeter * perimeter))
            if circularity > 0.4: # Yuvarlaksa lekedir
                leke_sayisi += 1
                if area > 40: ciddi_leke += 1

    # 4. Kırışıklık Analizi (Çizgisel Nesneler)
    # Kırışıklık için daha farklı bir filtreleme
    # Sobel veya Canny kullanacağız ama Morphological Open ile noktaları yok edeceğiz
    
    edges = cv2.Canny(blur_leke, 30, 100) # Kenarları bul
    edges = cv2.bitwise_and(edges, edges, mask=final_skin_mask)
    
    # MORFOLOJİK TEMİZLİK (Sırrı burada)
    # Sadece uzun çizgileri tut, noktaları sil
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    # Opening: Erozyon + Genişleme (Küçük noktaları yok eder)
    cleaned_edges = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel) 
    
    contours_kirisik, _ = cv2.findContours(cleaned_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    kirisiklik_sayisi = 0
    
    for cnt in contours_kirisik:
        # Sadece uzunluk kontrolü
        length = cv2.arcLength(cnt, True) # True: kapalı, False: açık. Kırışık açıktır ama contour kapalı döner.
        
        # Eğer çizgi 30 pikselden kısaysa görmezden gel (Tüy veya gözenektir)
        if length > 30: 
            kirisiklik_sayisi += 1
            
    return leke_sayisi, ciddi_leke, kirisiklik_sayisi

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
    
    # Detaylı Analiz
    leke, ciddi, kirisik = analyze_skin_features(frame, landmarks)
    
    # Skorlama (Daha adil bir sistem)
    # Her kırışıklık 3 puan götürür
    kirisiklik_puani = max(0, 100 - (kirisik * 3))
    
    # Leke Puanı
    leke_puani = max(0, 100 - ((leke * 0.5) + (ciddi * 2)))
    
    # Genel Skor Ortalaması
    genel_skor = int((leke_puani + kirisiklik_puani) / 2)
    
    # Sorun Tespiti
    ana_sorun = "Mükemmel Cilt"
    if genel_skor < 92:
        if kirisiklik_puani < leke_puani:
            ana_sorun = "İnce Kırışıklıklar"
        elif ciddi > 5:
            ana_sorun = "Akne/Sivilce"
        elif leke > 20:
            ana_sorun = "Geniş Gözenek"
        else:
            ana_sorun = "Yorgun Görünüm"

    onerilen_urun = database.en_uygun_urunu_bul(leke)
    database.analiz_kaydet(leke, genel_skor, onerilen_urun['urun_adi'])

    return {
        "status": "success",
        "genel_skor": genel_skor,
        "detaylar": {
            "leke_skoru": int(leke_puani),
            "leke_sayisi": leke,
            "ciddi_leke": ciddi,
            "kirisiklik_skoru": int(kirisiklik_puani),
            "kirisiklik_sayisi": kirisik, # Bunu da görmek için ekledik
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