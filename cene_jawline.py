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

# Başlangıç Değerleri
warp_intensity = 0.0
MAX_INTENSITY = 0.8 # Çene daha esnek olduğu için limiti biraz artırdım

# --- WARPING MOTORU ---
def warp_image(image, source_points, dest_points, sigma=40):
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

print("--- JAWLINE (CENE HATTI) SIMULATORU ---")
print("[Y]: Keskinlestir (Hollywood) | [A]: Incelte (V-Shape)")
print("[S]: Sakla | [Q]: Cikis")

while True:
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    output_frame = frame.copy()

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            lm = face_landmarks.landmark
            
            # --- JAWLINE NOKTALARI ---
            # Sol Çene Köşesi (Kulağın altı)
            left_jaw = np.array([lm[172].x * w, lm[172].y * h], dtype=np.float32)
            # Sağ Çene Köşesi
            right_jaw = np.array([lm[397].x * w, lm[397].y * h], dtype=np.float32)
            # Çene Ucu (Chin Tip)
            chin_tip = np.array([lm[152].x * w, lm[152].y * h], dtype=np.float32)

            # Görsellik: Çene hattını yeşil çizgiyle gösterelim (Teknolojik his için)
            # Çizim sadece analiz modunda kalsın, warpta bozulmasın diye ekrana en son basacağız.

            # --- WARPING İŞLEMİ ---
            if abs(warp_intensity) > 0.01:
                source_points = []
                dest_points = []

                # Kuvvet Çarpanı
                force = 50.0 * warp_intensity
                
                # 1. Sol Köşe İşlemi
                source_points.append(left_jaw)
                # Köşeyi dışarı ve hafif aşağı çek (Keskinleşme)
                dest_points.append(left_jaw + np.array([force, force*0.2]))

                # 2. Sağ Köşe İşlemi
                source_points.append(right_jaw)
                # Köşeyi dışarı (negatif x) ve hafif aşağı çek
                dest_points.append(right_jaw + np.array([-force, force*0.2]))

                # 3. Çene Ucu İşlemi (Dengelemek için)
                source_points.append(chin_tip)
                # Çeneyi biraz aşağı uzat (Maskülen/Güçlü görüntü için)
                dest_points.append(chin_tip + np.array([0, force*0.3]))

                # Sigma değerini ayarladım (h/15), daha geniş bir alanı etkilesin ki doğal dursun
                output_frame = warp_image(frame, source_points, dest_points, sigma=h/15)

    # --- UI ---
    cv2.rectangle(output_frame, (0, h-80), (w, h), (20, 20, 20), -1)
    
    # Progress Bar (Ortadan başlar)
    # Orta nokta (Sıfır noktası)
    bar_center_x = 170
    bar_width = 150
    
    # Arkaplan barı
    cv2.rectangle(output_frame, (bar_center_x - bar_width, h-50), (bar_center_x + bar_width, h-20), (50, 50, 50), -1)
    cv2.line(output_frame, (bar_center_x, h-55), (bar_center_x, h-15), (255, 255, 255), 2) # Orta çizgi

    # Doluluk Barı
    fill_len = int(bar_width * (warp_intensity / MAX_INTENSITY))
    
    if warp_intensity > 0: # Pozitif (Genişletme/Hollywood)
        cv2.rectangle(output_frame, (bar_center_x, h-50), (bar_center_x + fill_len, h-20), (0, 255, 0), -1)
        durum_yazisi = "MOD: Hollywood Jawline (Genis)"
    else: # Negatif (İncelte/V-Shape)
        cv2.rectangle(output_frame, (bar_center_x + fill_len, h-50), (bar_center_x, h-20), (0, 255, 255), -1)
        durum_yazisi = "MOD: V-Shape (Ince)"
        if warp_intensity == 0: durum_yazisi = "MOD: Dogal"

    cv2.putText(output_frame, durum_yazisi, (350, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(output_frame, "[Y]: Genislet | [A]: Incelte | [S]: Kaydet", (w-550, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow('BeautyTech - Jawline Simulator', output_frame)

    # --- TUŞLAR ---
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    elif key == ord('s'):
        cv2.imwrite(f"Jawline_{int(time.time())}.jpg", output_frame)
        cv2.rectangle(output_frame, (0, 0), (w, h), (255, 255, 255), 50)
        cv2.imshow('BeautyTech - Jawline Simulator', output_frame)
        cv2.waitKey(100)
    elif key == ord('y'):
        warp_intensity = min(MAX_INTENSITY, warp_intensity + 0.05)
    elif key == ord('a'):
        warp_intensity = max(-MAX_INTENSITY, warp_intensity - 0.05)

cap.release()
cv2.destroyAllWindows()