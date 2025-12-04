from fastapi import FastAPI, File, UploadFile
import cv2
import mediapipe as mp
import numpy as np
import database 

app = FastAPI(title="BeautyTech Master API", description="Dermatolojik Seviye Cilt Analizi")

# Veritabanı Başlatma
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

def get_roi_region(image, landmarks, indices):
    """Belirli yüz bölgelerini (Alın, Yanak) kesip alır"""
    h, w, c = image.shape
    points = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in indices], np.int32)
    
    # Bölgeyi maskele
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillConvexPoly(mask, points, 255)
    
    # Siyah arka plan üzerine bölgeyi al
    masked_image = cv2.bitwise_and(image, image, mask=mask)
    
    # Dikdörtgen olarak kırp (Gereksiz siyah alanları at)
    x, y, w_rect, h_rect = cv2.boundingRect(points)
    roi = masked_image[y:y+h_rect, x:x+w_rect]
    return roi

def calculate_texture_score(roi):
    """
    MASTER LEVEL TEKNİK: Laplacian Varyansı
    Bu fonksiyon cildin 'Pürüzlülüğünü' matematiksel olarak ölçer.
    Pürüzsüz Cilt = Düşük Varyans (örn: 50-100)
    Kırışık/Bozuk Cilt = Yüksek Varyans (örn: 500-2000)
    """
    if roi.size == 0: return 0
    
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Siyah alanları (maske dışı) analizden çıkar
    # Sadece maskelenmiş (cilt olan) pikselleri al
    pixels = gray[gray > 0]
    
    if len(pixels) == 0: return 0
    
    # 1. Laplacian uygula (Doku detaylarını ortaya çıkarır)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    
    # 2. Sadece cilt üzerindeki varyansı hesapla
    score = laplacian[gray > 0].var()
    return score

def count_spots(roi):
    """Yanaklardaki lekeleri sayar"""
    if roi.size == 0: return 0
    
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    # Leke tespiti için yumuşatma
    blur = cv2.medianBlur(gray, 5)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4)
    
    # Sadece cilt üzerindekileri al
    thresh = cv2.bitwise_and(thresh, thresh, mask=(gray > 0).astype(np.uint8))
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    count = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 10 < area < 200: # Orta boy lekeler
            count += 1
    return count

@app.post("/analiz_et")
async def analiz_et(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    h, w, c = frame.shape

    # Işık Dengeleme (CLAHE) - Her telefonda aynı sonucu versin diye
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    frame_balanced = cv2.cvtColor(cv2.merge((cl,a,b)), cv2.COLOR_LAB2BGR)

    rgb_frame = cv2.cvtColor(frame_balanced, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    if not results.multi_face_landmarks:
        return {"status": "failed", "message": "Yuz bulunamadi"}

    lm = results.multi_face_landmarks[0]
    
    # --- BÖLGESEL ANALİZ ---
    
    # 1. ALIN BÖLGESİ (Kırışıklık için en iyi yer)
    # MediaPipe alın noktaları
    forehead_indices = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
    forehead_roi = get_roi_region(frame_balanced, lm, forehead_indices)
    
    # Alın Dokusu (Kırışıklık Skoru)
    # Yaşlılarda bu değer 1000+, Pürüzsüzde 50-100 çıkar.
    forehead_roughness = calculate_texture_score(forehead_roi)
    
    # 2. YANAK BÖLGESİ (Leke/Akne için en iyi yer)
    left_cheek_indices = [234, 93, 132, 58, 172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361, 323, 454, 356] # Geniş yanak alanı
    cheek_roi = get_roi_region(frame_balanced, lm, left_cheek_indices)
    
    cheek_spots = count_spots(cheek_roi)
    
    # --- SKORLAMA MANTIĞI (MASTER LEVEL) ---
    
    # Kırışıklık Puanı (Ters Orantı)
    # Roughness (Pürüzlülük) arttıkça puan düşer.
    # Normalizasyon: 0-100 arası 100 puan, 1500 üzeri 0 puan.
    kirisiklik_puani = max(0, 100 - (forehead_roughness / 12)) 
    
    # Leke Puanı
    leke_puani = max(0, 100 - (cheek_spots * 2))
    
    # Genel Skor Ağırlıkları
    # Kırışıklık %60, Leke %40 etki etsin (Yaşlanma belirtisi daha kritik)
    genel_skor = int((kirisiklik_puani * 0.6) + (leke_puani * 0.4))
    
    # Sorun Tespiti
    ana_sorun = "Mükemmel Cilt"
    if genel_skor < 90:
        if kirisiklik_puani < leke_puani:
            ana_sorun = "Kırışıklık/Doku Kaybı"
        elif leke_puani < 60:
            ana_sorun = "Akne/Geniş Gözenek"
        else:
            ana_sorun = "Cilt Yorgunluğu"

    # Veritabanı
    onerilen_urun = database.en_uygun_urunu_bul(cheek_spots)
    database.analiz_kaydet(cheek_spots, genel_skor, onerilen_urun['urun_adi'])
    
    # Flutter'a giden veri
    return {
        "status": "success",
        "genel_skor": genel_skor,
        "detaylar": {
            "leke_skoru": int(leke_puani),
            "leke_sayisi": cheek_spots, 
            "ciddi_leke": 0, # Artık doku puanı kullanıyoruz
            "kirisiklik_skoru": int(kirisiklik_puani),
            "kirisiklik_sayisi": int(forehead_roughness), # Ekranda "Doku İndeksi" olarak gösterilebilir
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