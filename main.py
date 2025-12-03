from fastapi import FastAPI, File, UploadFile
import cv2
import mediapipe as mp
import numpy as np
import database 

app = FastAPI(title="BeautyTech Pro API", description="Profesyonel Cilt Analiz Motoru v2")

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

def crop_face(image, landmarks):
    """Sadece yüzü kesip alır (Arka planı atar)"""
    h, w, c = image.shape
    x_min, y_min = w, h
    x_max, y_max = 0, 0
    
    for lm in landmarks.landmark:
        x, y = int(lm.x * w), int(lm.y * h)
        if x < x_min: x_min = x
        if x > x_max: x_max = x
        if y < y_min: y_min = y
        if y > y_max: y_max = y
        
    # Biraz pay bırakalım (Padding)
    pad = 20
    x_min = max(0, x_min - pad)
    y_min = max(0, y_min - pad)
    x_max = min(w, x_max + pad)
    y_max = min(h, y_max + pad)
    
    return image[y_min:y_max, x_min:x_max]

def analyze_acne(roi_img):
    """Leke ve Sivilce Analizi (Hassasiyet Azaltılmış)"""
    # 1. Gürültü Azaltma (Pürüzsüzleştirme)
    # Bu işlem gözenekleri yok sayar, sadece belirgin lekeleri bırakır
    blur = cv2.bilateralFilter(roi_img, 9, 75, 75)
    
    # 2. Griye Çevir
    gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)
    
    # 3. Adaptif Eşikleme (Sadece koyu noktaları bul)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 15, 3  # Hassasiyet ayarı (değerler büyüdükçe hassasiyet azalır)
    )
    
    # 4. Alan Filtreleme (Çok küçük noktaları sayma)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    gercek_lekeler = 0
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Sadece 5 ile 100 piksel arasındaki lekeleri al (Gözenekler < 5, Saçlar > 100)
        if 5 < area < 100:
            gercek_lekeler += 1
            
    # Skor Hesapla (Ters orantı: Leke arttıkça puan düşer)
    score = max(0, 100 - (gercek_lekeler * 2)) # Her leke 2 puan götürür
    return gercek_lekeler, score

def analyze_wrinkles(roi_img):
    """Kırışıklık Analizi (Canny Edge Detection)"""
    gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
    # Kenar algılama
    edges = cv2.Canny(gray, 100, 200)
    
    # Beyaz piksel sayısı kırışıklık yoğunluğunu verir
    edge_pixels = np.count_nonzero(edges)
    height, width = edges.shape
    total_pixels = height * width
    
    # Yoğunluk oranı
    ratio = edge_pixels / total_pixels
    
    # Basit bir skorlama (Oran arttıkça puan düşer)
    kirisiklik_puani = max(0, int(100 - (ratio * 1000)))
    return kirisiklik_puani

@app.post("/analiz_et")
async def analiz_et(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 1. Yüzü Bul ve Kes
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    if not results.multi_face_landmarks:
        return {"status": "failed", "message": "Yuz bulunamadi"}

    face_landmarks = results.multi_face_landmarks[0]
    cropped_face = crop_face(frame, face_landmarks)
    
    # Eğer yüz çok küçükse (uzaktan çekilmişse) hata vermemesi için kontrol
    if cropped_face.size == 0:
        cropped_face = frame

    # 2. Detaylı Analizler
    leke_sayisi, leke_skoru = analyze_acne(cropped_face)
    kirisiklik_skoru = analyze_wrinkles(cropped_face)
    
    # 3. Genel Cilt Skoru (Ortalama)
    genel_skor = int((leke_skoru + kirisiklik_skoru) / 2)
    
    # 4. Öncelik Sıralaması (Hangi sorun daha büyük?)
    sorunlar = [
        {"tip": "Leke/Akne", "skor": leke_skoru},
        {"tip": "Kırışıklık", "skor": kirisiklik_skoru},
        # Gelecekte buraya "Göz Altı", "Nem" eklenebilir
    ]
    # Skoru en düşük olan sorunu bul
    ana_sorun = min(sorunlar, key=lambda x: x['skor'])
    
    # 5. SQL'den Ürün Getir
    # Veritabanında problem türüne göre arama yap (Mapping)
    db_problem_adi = "Problemli" # Varsayılan
    if ana_sorun["tip"] == "Kırışıklık":
        db_problem_adi = "Yorgun" # Veritabanındaki karşılığı
    elif ana_sorun["tip"] == "Leke/Akne":
        db_problem_adi = "Problemli"
        
    if genel_skor > 85:
        db_problem_adi = "Mükemmel"
        
    # Veritabanından en uygun ürünü çek (Skor değil problem türüne göre)
    # Not: database.py içinde 'en_uygun_urunu_bul' fonksiyonunu birazdan güncelleyeceğiz
    onerilen_urun = database.en_uygun_urunu_bul(leke_sayisi) 

    # Kaydet
    database.analiz_kaydet(leke_sayisi, genel_skor, onerilen_urun['urun_adi'])

    return {
        "status": "success",
        "genel_skor": genel_skor,
        "detaylar": {
            "leke_skoru": leke_skoru,
            "leke_sayisi": leke_sayisi,
            "kirisiklik_skoru": kirisiklik_skoru,
            "ana_sorun": ana_sorun["tip"]
        },
        "reçete": {
            "sorun": db_problem_adi,
            "onerilen_urun": onerilen_urun['urun_adi'],
            "marka": onerilen_urun['marka'],
            "link": onerilen_urun['link']
        }
    }
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)