from fastapi import FastAPI, File, UploadFile
import cv2
import mediapipe as mp
import numpy as np
import database 

app = FastAPI(title="BeautyTech Master API", description="Medical Grade Skin Analysis")

# Veritabanı Başlatma
try:
    database.tablolari_olustur()
    database.baslangic_verisi_ekle()
except:
    pass

# MediaPipe Ayarları (High Confidence)
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.7 # Emin olmadan yüzü kabul etme
)

# --- YASAKLI BÖLGELER (Göz, Kaş, Ağız) ---
EXCLUDE_INDICES = [
    33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 144, 145, 153, 52, 65, 55, 
    263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249, 285, 
    70, 63, 105, 66, 107, 55, 193, 
    336, 296, 334, 293, 300, 285, 417, 
    61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78, 
    2, 326, 327, 278, 279, 360, 363, 281, 5, 51, 48, 49, 131, 134, 115, 220
]

def preprocess_image(image):
    """
    MASTER LEVEL: Işık ve Renk Dengeleme
    Farklı telefon kameralarını standart hale getirir.
    """
    # 1. Gürültü Temizleme (Noise Reduction) - Pürüzsüz cildi bozuk sanmasın diye
    # Bu işlem biraz ağırdır ama sonucu mükemmelleştirir.
    denoised = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
    
    # 2. LAB Renk Uzayında Kontrast (CLAHE)
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    processed = cv2.merge((cl,a,b))
    return cv2.cvtColor(processed, cv2.COLOR_LAB2BGR)

def create_face_mask(h, w, landmarks):
    """Yüzün sadece deri olan kısımlarını maskeler"""
    mask = np.zeros((h, w), dtype=np.uint8)
    
    # Yüz Ovali
    face_oval = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
    points = np.array([[int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)] for i in face_oval], np.int32)
    cv2.fillConvexPoly(mask, points, 255)
    
    # Yasaklı Bölgeleri Çıkar (Siyah Boya)
    for idx in EXCLUDE_INDICES:
        lm = landmarks.landmark[idx]
        x, y = int(lm.x * w), int(lm.y * h)
        cv2.circle(mask, (x, y), 15, 0, -1) # 0 = Siyah
        
    return mask

def detect_wrinkles_tophat(gray_image, mask):
    """
    MASTER LEVEL: Top-Hat Dönüşümü ile Kırışıklık Analizi
    Bu algoritma ışık gölgelerini değil, DERİN ÇİZGİLERİ bulur.
    """
    # 1. Top-Hat Dönüşümü (Sadece vadileri/kırışıklıkları beyaz yapar)
    # Kernel boyutu kırışıklık genişliğine göre ayarlanır (9x9 idealdir)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    tophat = cv2.morphologyEx(gray_image, cv2.MORPH_TOPHAT, kernel)
    
    # 2. Maske Uygula (Sadece yüz içine bak)
    tophat = cv2.bitwise_and(tophat, tophat, mask=mask)
    
    # 3. Eşikleme (Threshold) - Çok hafif izleri at, derinleri tut
    # Pürüzsüz ciltte burası tamamen siyah döner -> 0 Kırışıklık
    _, thresh = cv2.threshold(tophat, 15, 255, cv2.THRESH_BINARY)
    
    # 4. Gürültü Temizliği (Noktaları at, çizgileri tut)
    kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_clean)
    
    # 5. Piksel Sayımı (Kırışıklık Yoğunluğu)
    wrinkle_pixels = cv2.countNonZero(thresh)
    
    # Toplam yüz alanına oranı
    face_area = cv2.countNonZero(mask)
    if face_area == 0: return 0
    
    ratio = (wrinkle_pixels / face_area) * 1000 # Okunabilir sayıya çevir
    return ratio

def detect_spots_adaptive(gray_image, mask):
    """Leke Analizi: Adaptif Eşikleme"""
    # Leke tespiti için bulanıklaştırma (gözenekleri yoksay)
    blur = cv2.GaussianBlur(gray_image, (17, 17), 0)
    
    # Adaptif Threshold
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 3)
    
    # Maske
    thresh = cv2.bitwise_and(thresh, thresh, mask=mask)
    
    # Kontur Analizi (Sadece yuvarlak ve belli boyuttakileri al)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    spot_count = 0
    ciddi_leke = 0
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 15 < area < 400: # Çok küçük ve çok büyükleri at
            spot_count += 1
            if area > 50: ciddi_leke += 1
            
    return spot_count, ciddi_leke

@app.post("/analiz_et")
async def analiz_et(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    h, w, c = frame.shape

    # 1. Profesyonel Ön İşleme
    processed_frame = preprocess_image(frame)
    
    # 2. Yüz Taraması
    rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    if not results.multi_face_landmarks:
        return {"status": "failed", "message": "Yuz bulunamadi"}
    
    landmarks = results.multi_face_landmarks[0]
    
    # 3. Yüz Maskesi Çıkar (Ortak Kullanım)
    face_mask = create_face_mask(h, w, landmarks)
    gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
    
    # 4. Master Level Analizler
    wrinkle_index = detect_wrinkles_tophat(gray, face_mask) # 0 ile 200 arası değer döner
    spot_count, serious_spots = detect_spots_adaptive(gray, face_mask)
    
    # 5. Akıllı Skorlama (Sigmoid Mantığına Yakın)
    
    # Kırışıklık Skoru:
    # 0-5 arası index -> 100 Puan (Pürüzsüz)
    # 50 üzeri index -> Hızla düşer
    if wrinkle_index < 5:
        kirisiklik_puani = 100
    else:
        kirisiklik_puani = max(10, 100 - (wrinkle_index * 1.5))
        
    # Leke Skoru:
    # 0-10 leke -> 95-100 Puan
    # Ciddi lekeler çok puan kırar
    leke_puani = max(10, 100 - (spot_count * 0.5 + serious_spots * 1.5))
    
    # Genel Skor
    genel_skor = int((kirisiklik_puani * 0.5) + (leke_puani * 0.5))
    
    # Sorun Tespiti
    ana_sorun = "Mükemmel Cilt"
    if genel_skor < 92:
        if kirisiklik_puani < leke_puani:
            ana_sorun = "Kırışıklık/Yaşlanma"
        elif serious_spots > 5:
            ana_sorun = "Akne/Sivilce"
        elif spot_count > 30:
            ana_sorun = "Cilt Lekeleri"
        else:
            ana_sorun = "Yorgun Görünüm"

    # Veritabanı
    onerilen_urun = database.en_uygun_urunu_bul(spot_count)
    database.analiz_kaydet(spot_count, genel_skor, onerilen_urun['urun_adi'])

    return {
        "status": "success",
        "genel_skor": genel_skor,
        "detaylar": {
            "leke_skoru": int(leke_puani),
            "leke_sayisi": spot_count,
            "ciddi_leke": serious_spots,
            "kirisiklik_skoru": int(kirisiklik_puani),
            "kirisiklik_indeksi": round(wrinkle_index, 2), # Teknik veri (Geliştirici için)
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