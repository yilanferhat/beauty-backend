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
    refine_landmarks=True, # Göz bebeklerini bile bulur
    min_detection_confidence=0.5
)

# --- YASAKLI BÖLGELER (Maskelenecek Alanlar) ---
# Kaşlar, Gözler, Dudaklar, Burun Delikleri -> Bunları leke sanmasın!
EXCLUDE_INDICES = [
    # Gözler ve Kaşlar
    33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 144, 145, 153, 52, 65, 55, # Sol Göz
    263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249, 285, # Sağ Göz
    70, 63, 105, 66, 107, 55, 193, # Sol Kaş
    336, 296, 334, 293, 300, 285, 417, # Sağ Kaş
    # Dudaklar
    61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78, # Dudak Çevresi
    # Burun Delikleri (Gölgeleri sivilce sanmasın)
    2, 326, 327, 278, 279, 360, 363, 281, 5, 51, 48, 49, 131, 134, 115, 220
]

def create_mask_from_landmarks(image, landmarks, indices, invert=False):
    """Belirli bölgeleri maskelemek için yardımcı fonksiyon"""
    h, w, c = image.shape
    mask = np.zeros((h, w), dtype=np.uint8)
    points = []
    
    for idx in indices:
        lm = landmarks.landmark[idx]
        x, y = int(lm.x * w), int(lm.y * h)
        points.append([x, y])
        
    if points:
        points = np.array(points, dtype=np.int32)
        hull = cv2.convexHull(points)
        cv2.fillConvexPoly(mask, hull, 255)
        
    if invert:
        mask = cv2.bitwise_not(mask)
        
    return mask

def analyze_skin_quality(image, landmarks):
    """AAA+ Kalite Leke ve Doku Analizi"""
    h, w, c = image.shape
    
    # 1. Yüz Maskesi Oluştur (Sadece cilde odaklan)
    face_mask = np.zeros((h, w), dtype=np.uint8)
    face_oval = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
    face_pts = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in face_oval], np.int32)
    cv2.fillConvexPoly(face_mask, face_pts, 255)
    
    # 2. Yasaklı Bölgeleri Çıkar (Göz, Dudak, Kaş sil)
    # Bu adım çok kritiktir. 1300 lekenin 1000 tanesi buralardan geliyordu.
    exclusion_mask = np.zeros((h, w), dtype=np.uint8)
    # Basit bir döngü yerine toplu convex hull mantığı (Daha hızlı olması için basitleştirilmiş gruplar kullanılabilir ama şimdilik nokta bazlı karartma yapalım)
    # Hızlı çözüm: MediaPipe'dan gelen noktaların etrafına küçük daireler çizerek maskele
    for idx in EXCLUDE_INDICES:
        lm = landmarks.landmark[idx]
        x, y = int(lm.x * w), int(lm.y * h)
        cv2.circle(exclusion_mask, (x, y), 15, 255, -1) # 15px yarıçapında maske
        
    # Yüz maskesinden yasaklı bölgeleri çıkar
    final_skin_mask = cv2.bitwise_and(face_mask, cv2.bitwise_not(exclusion_mask))
    
    # 3. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # Işığı düzelt. Cilt tonunu eşitle.
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl,a,b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    
    # 4. Leke Tespiti (Gelişmiş)
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    # Ciltteki ani renk değişimlerini bul (Sadece koyuluk değil, doku değişimi)
    # Threshold değerini (15) biraz daha düşürdük çünkü artık maskeleme var, korkmadan hassas olabiliriz.
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 17, 4)
    
    # Maskeyi uygula (Sadece cilt üzerinde ara)
    thresh = cv2.bitwise_and(thresh, thresh, mask=final_skin_mask)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    leke_sayisi = 0
    ciddi_leke_sayisi = 0
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        # Minik gözenekler (2-8 px) -> Yok say
        # Küçük sivilceler (8-30 px) -> Hafif Leke
        # Büyük sivilceler (>30 px) -> Ciddi Leke
        
        if 8 < area < 400: # Üst limit arttı, çünkü artık gözleri karıştırmıyoruz
            # Şekil Analizi (Yuvarlaklık Kontrolü)
            # Lekeler genelde yuvarlaktır, kırışıklıklar çizgidir.
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0: continue
            circularity = 4 * np.pi * (area / (perimeter * perimeter))
            
            if circularity > 0.3: # Çok ince çizgileri (kıl/kırışık) leke sayma
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
    
    # Profesyonel Analiz Başlasın
    toplam_leke, ciddi_leke = analyze_skin_quality(frame, landmarks)
    
    # Skorlama Algoritması (AAA+ Mantığı)
    # Leke sayısı 0 ise 100 puan.
    # Her leke puan düşürür ama logaritmik olarak (ilk lekeler çok düşürür, sonrakiler az)
    # Basit formül: 
    kayip_puan = (toplam_leke * 0.5) + (ciddi_leke * 2)
    genel_skor = max(10, int(100 - kayip_puan))
    
    # Kırışıklık için basit analiz (şimdilik standart)
    # İleride buraya da özel maskeleme ekleyebiliriz
    kirisiklik_skoru = max(0, 100 - int(toplam_leke / 3)) # Geçici mantık
    
    # Sorun Tespiti
    ana_sorun = "Mükemmel Cilt"
    if genel_skor < 90:
        if ciddi_leke > 5:
            ana_sorun = "Akne/Sivilce"
        elif toplam_leke > 30:
            ana_sorun = "Geniş Gözenek/Leke"
        else:
            ana_sorun = "Yorgun Görünüm"

    # Veritabanı
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