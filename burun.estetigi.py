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

# Başlangıç Değerleri
warp_intensity = 0.0
MAX_INTENSITY = 0.6 

# --- WARPING MOTORU (Geliştirilmiş V2) ---
def warp_image(image, source_points, dest_points, sigma=30):
    h, w = image.shape[:2]
    grid_y, grid_x = np.mgrid[0:h, 0:w].astype(np.float32)
    map_x = grid_x.copy()
    map_y = grid_y.copy()

    for src, dst in zip(source_points, dest_points):
        shift_x = dst[0] - src[0]
        shift_y = dst[1] - src[1]
        dist_squared = (grid_x - src[0])**2 + (grid_y - src[1])**2
        weight = np.exp(-dist_squared / (2 * sigma**2))
        map_x += shift_x * weight
        map_y += shift_y * weight

    return cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

cap = cv2.VideoCapture(0)

print("--- BURUN ESTETIGI SON SURUM ---")
print("[Y]: Yukselt (Artir) | [A]: Azalt (Dusur)")
print("[S]: Sakla (Save) | [Q]: Cikis")

while True:
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    output_frame = frame.copy()

    if results.multi_face_landmarks and warp_intensity > 0.01:
        for face_landmarks in results.multi_face_landmarks:
            lm = face_landmarks.landmark
            
            # Koordinatlar
            nose_tip = np.array([lm[1].x * w, lm[1].y * h], dtype=np.float32)
            left_alar = np.array([lm[279].x * w, lm[279].y * h], dtype=np.float32)
            right_alar = np.array([lm[49].x * w, lm[49].y * h], dtype=np.float32)

            source_points = []
            dest_points = []

            # 1. Daraltma
            narrow_force = 35.0 * warp_intensity 
            source_points.append(left_alar)
            dest_points.append(left_alar + np.array([narrow_force, 0])) 
            source_points.append(right_alar)
            dest_points.append(right_alar + np.array([-narrow_force, 0]))

            # 2. Kaldırma
            lift_force = 25.0 * warp_intensity
            source_points.append(nose_tip)
            dest_points.append(nose_tip + np.array([0, -lift_force]))

            # Etki alanını optimize ettim
            output_frame = warp_image(frame, source_points, dest_points, sigma=h/20)

    # --- UI ---
    cv2.rectangle(output_frame, (0, h-80), (w, h), (30, 30, 30), -1)
    
    # Progress Bar
    bar_width = 300
    filled_width = int(bar_width * (warp_intensity / MAX_INTENSITY))
    # Renk Yeşilden Kırmızıya
    color_g = int(255 * (1 - warp_intensity/MAX_INTENSITY))
    color_r = int(255 * (warp_intensity/MAX_INTENSITY))
    
    cv2.rectangle(output_frame, (20, h-50), (20 + bar_width, h-20), (50, 50, 50), -1)
    cv2.rectangle(output_frame, (20, h-50), (20 + filled_width, h-20), (0, color_g, color_r), -1)

    label = f"Estetik: %{int((warp_intensity/MAX_INTENSITY)*100)}"
    cv2.putText(output_frame, label, (340, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    # Bilgilendirme Yazısı
    cv2.putText(output_frame, "[Y]: Yukselt | [A]: Azalt | [S]: Kaydet", (w-500, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow('BeautyTech - Burun Estetigi Final', output_frame)

    # --- TUŞ KONTROLLERİ ---
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'): # Çıkış
        break
    elif key == ord('s'): # Save / Sakla (Eski haline döndü)
        dosya_adi = f"Burun_Estetigi_{int(time.time())}.jpg"
        cv2.imwrite(dosya_adi, output_frame)
        # Görsel Feedback (Ekran Beyazlar)
        cv2.rectangle(output_frame, (0, 0), (w, h), (255, 255, 255), 50)
        cv2.imshow('BeautyTech - Burun Estetigi Final', output_frame)
        print(f"Kaydedildi: {dosya_adi}")
        cv2.waitKey(100)
    elif key == ord('y'): # Yükselt
        warp_intensity = min(MAX_INTENSITY, warp_intensity + 0.05)
    elif key == ord('a'): # Azalt
        warp_intensity = max(0.0, warp_intensity - 0.05)

cap.release()
cv2.destroyAllWindows()