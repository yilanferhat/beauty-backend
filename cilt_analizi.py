import cv2
import mediapipe as mp
import numpy as np
import time
import json
import os 

# --- AKILLI DOSYA YOLU BULUCU ---
script_dizini = os.path.dirname(os.path.abspath(__file__))
json_dosya_yolu = os.path.join(script_dizini, 'data.json')

# --- VERİTABANI YÜKLEME ---
try:
    with open(json_dosya_yolu, 'r', encoding='utf-8') as f:
        DB = json.load(f)
    print(f"BASARILI: Veritabanı yüklendi.")
except FileNotFoundError:
    print(f"HATA: data.json dosyası bulunamadı!")
    exit()

# --- AYARLAR ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
# Çizim araçlarını aktif ediyoruz (Görsellik için)
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

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

def urun_onerisi_yap(leke_sayisi, product_db):
    sorted_products = sorted(product_db, key=lambda x: x['esik_deger'], reverse=True)
    for urun in sorted_products:
        if leke_sayisi >= urun['esik_deger']:
            return urun['hedef_problem'], urun['urun_adi'], tuple(urun['renk_kodu_bgr']), urun['marka']
    return "Tanimsiz", "Bilinmeyen Urun", (0, 0, 0), "Hata"

cap = cv2.VideoCapture(0)
print("Kamera baslatiliyor...")

while True:
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    vis_frame = frame.copy()

    # Varsayılan Değerler
    leke_sayisi = 0
    durum_renk = (200, 200, 200)
    marka = "Yuz Araniyor..."
    oneri_metni = "Lutfen kameraya bakin"

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            
            # --- GÖRSELLEŞTİRME: Google Face Mesh Ağını Çiz ---
            mp_drawing.draw_landmarks(
                image=vis_frame,
                landmark_list=face_landmarks,
                connections=mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style())
            
            # Maskeleme ve Leke Tespiti
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
                    (cx, cy), radius = cv2.minEnclosingCircle(cnt)
                    # Lekeleri kırmızı ile işaretle ki ağın üzerinde belli olsun
                    cv2.circle(vis_frame, (int(cx), int(cy)), int(radius), (0, 0, 255), 2)
                    leke_sayisi += 1

            # JSON'dan veri çekme
            durum_metni, oneri_metni, durum_renk, marka = urun_onerisi_yap(leke_sayisi, DB['PRODUCTS'])

    # UI
    h, w, _ = vis_frame.shape
    # Alt paneli biraz daha şeffaf siyah yapalım
    overlay = vis_frame.copy()
    cv2.rectangle(overlay, (0, h-120), (w, h), (0, 0, 0), -1)
    alpha = 0.7 
    vis_frame = cv2.addWeighted(overlay, alpha, vis_frame, 1 - alpha, 0)
    
    cv2.putText(vis_frame, f"Pruz: {leke_sayisi}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
    cv2.putText(vis_frame, f"MARKA: {marka}", (20, h-70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    cv2.putText(vis_frame, f"ONERI: {oneri_metni}", (20, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, durum_renk, 2)

    cv2.imshow('BeautyTech AI Analysis - JSON + Google Mesh', vis_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()