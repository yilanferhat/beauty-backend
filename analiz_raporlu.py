import cv2
import mediapipe as mp
import numpy as np
import time

# --- AYARLAR ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# Analiz bölgeleri (Alın ve Yanaklar)
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

def urun_onerisi_yap(leke_sayisi):
    if leke_sayisi < 15:
        durum = "MUKEMMEL"
        renk = (0, 255, 0)
        oneri = "Nemlendirici + Gunes Kremi"
    elif leke_sayisi < 40:
        durum = "YORGUN CILT"
        renk = (0, 255, 255)
        oneri = "C Vitamini + Peeling"
    else:
        durum = "PROBLEMLI"
        renk = (0, 0, 255)
        oneri = "Salisilik Asit + Kil Maskesi"
    return durum, oneri, renk

cap = cv2.VideoCapture(0)

print("Kamera acildi. Rapor almak icin 's' tusuna, cikmak icin 'q' tusuna bas.")

while True:
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    vis_frame = frame.copy()

    leke_sayisi = 0
    durum_metni = "Analiz..."
    oneri_metni = ""
    durum_renk = (200, 200, 200)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            h, w, c = frame.shape
            
            # Maske Oluştur
            mask_total = np.zeros((h, w), dtype=np.uint8)
            mask_total = cv2.bitwise_or(mask_total, create_mask_from_indices(FOREHEAD_INDICES, frame.shape, face_landmarks.landmark))
            mask_total = cv2.bitwise_or(mask_total, create_mask_from_indices(LEFT_CHEEK_INDICES, frame.shape, face_landmarks.landmark))
            mask_total = cv2.bitwise_or(mask_total, create_mask_from_indices(RIGHT_CHEEK_INDICES, frame.shape, face_landmarks.landmark))

            # Leke Analizi
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            thresh = cv2.bitwise_and(thresh, thresh, mask=mask_total)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 2 < area < 30:
                    (cx, cy), radius = cv2.minEnclosingCircle(cnt)
                    cv2.circle(vis_frame, (int(cx), int(cy)), int(radius), (0, 0, 255), 1)
                    leke_sayisi += 1
            
            # Yüz Ağını Çiz (Görsellik)
            mp_drawing.draw_landmarks(
                image=vis_frame,
                landmark_list=face_landmarks,
                connections=mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing.DrawingSpec(color=(200,200,200), thickness=1, circle_radius=1))

            durum_metni, oneri_metni, durum_renk = urun_onerisi_yap(leke_sayisi)

    # --- UI ÇİZİMİ ---
    h, w, _ = vis_frame.shape
    # Alt panel (Yarı saydam siyahlık için)
    overlay = vis_frame.copy()
    cv2.rectangle(overlay, (0, h-120), (w, h), (0, 0, 0), -1)
    alpha = 0.6 # Saydamlık oranı
    vis_frame = cv2.addWeighted(overlay, alpha, vis_frame, 1 - alpha, 0)

    # Yazıları ekle
    cv2.putText(vis_frame, f"Pruz: {leke_sayisi}", (20, h-80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, durum_renk, 2)
    cv2.putText(vis_frame, f"DURUM: {durum_metni}", (200, h-80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, durum_renk, 2)
    cv2.putText(vis_frame, f"ONERI: {oneri_metni}", (20, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    # Kullanıcıya bilgi ver
    cv2.putText(vis_frame, "'s': Kaydet | 'q': Cikis", (w-250, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow('BeautyTech Raporlama', vis_frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        # Raporu Kaydet
        timestamp = int(time.time())
        dosya_adi = f"Cilt_Raporu_{timestamp}.jpg"
        cv2.imwrite(dosya_adi, vis_frame)
        print(f"Rapor Kaydedildi: {dosya_adi}")
        # Ekrana 'Kaydedildi' yazısı çıkar (anlık feedback)
        cv2.rectangle(vis_frame, (0, 0), (w, h), (255, 255, 255), 50) # Beyaz flaş efekti
        cv2.imshow('BeautyTech Raporlama', vis_frame)
        cv2.waitKey(200) # 0.2 saniye bekle

cap.release()
cv2.destroyAllWindows()