import cv2
import mediapipe as mp
import numpy as np
import time

# --- AYARLAR ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True, # İris tespiti için kritik
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# --- WARPING MOTORU ---
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

# --- LENS RENKLERİ ---
LENS_RENKLERI = [
    ((0, 0, 0), "Dogal"),       
    ((255, 255, 0), "Mavi"),    
    ((0, 255, 0), "Yesil"),     
    ((0, 200, 255), "Ela"),     
    ((255, 0, 255), "Menekse"), 
    ((50, 50, 50), "Gri")       
]
lens_index = 0
fox_intensity = 0.0
MAX_FOX = 0.7
cap = cv2.VideoCapture(0)

# --- YENİ İRİS ÇİZME FONKSİYONU (Daha Hassas Merkezleme) ---
def draw_iris_precise(frame, landmarks, iris_center_idx, iris_edge_idx, color, h, w):
    # İris Merkez Noktası
    center_pt = landmarks[iris_center_idx]
    cx, cy = int(center_pt.x * w), int(center_pt.y * h)
    center = (cx, cy)

    # İris Kenar Noktası (Yarıçap hesabı için)
    edge_pt = landmarks[iris_edge_idx]
    ex, ey = int(edge_pt.x * w), int(edge_pt.y * h)
    
    # Yarıçapı hesapla (Merkez ile kenar arasındaki mesafe)
    radius = int(np.sqrt((cx - ex)**2 + (cy - ey)**2))

    # Maske
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, center, radius, 255, -1)

    # Renk Katmanı
    colored_layer = np.zeros((h, w, c), dtype=np.uint8)
    colored_layer[:] = color

    # Karıştırma (Alpha Blending - Biraz daha şeffaf yaptım: 0.30)
    alpha = 0.30
    blended = cv2.addWeighted(frame, 1, colored_layer, alpha, 0)
    
    eye_colored = cv2.bitwise_and(blended, blended, mask=mask)
    eye_natural = cv2.bitwise_and(frame, frame, mask=cv2.bitwise_not(mask))
    return cv2.add(eye_natural, eye_colored)

print("--- GOZ ESTETIGI V3 (DUZELTILMIS) ---")
print("[F]: Fox Artir | [G]: Fox Azalt | [C]: Lens Degistir | [S]: Kaydet")

while True:
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    output_frame = frame.copy()
    
    secili_renk, renk_ismi = LENS_RENKLERI[lens_index]

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            lm = face_landmarks.landmark

            # 1. FOX EYE (Aynı kalıyor)
            if fox_intensity > 0.01:
                source_points = []
                dest_points = []
                left_eye_outer = np.array([lm[263].x * w, lm[263].y * h], dtype=np.float32)
                left_brow_tail = np.array([lm[334].x * w, lm[334].y * h], dtype=np.float32)
                right_eye_outer = np.array([lm[33].x * w, lm[33].y * h], dtype=np.float32)
                right_brow_tail = np.array([lm[105].x * w, lm[105].y * h], dtype=np.float32)
                force = 40.0 * fox_intensity
                source_points.append(left_eye_outer); dest_points.append(left_eye_outer + np.array([force*0.5, -force])) 
                source_points.append(left_brow_tail); dest_points.append(left_brow_tail + np.array([0, -force*1.2])) 
                source_points.append(right_eye_outer); dest_points.append(right_eye_outer + np.array([-force*0.5, -force])) 
                source_points.append(right_brow_tail); dest_points.append(right_brow_tail + np.array([0, -force*1.2]))
                output_frame = warp_image(frame, source_points, dest_points, sigma=h/25)
            
            # 2. RENKLİ LENSLER (Yeni ve Hassas Yöntem)
            if renk_ismi != "Dogal":
                # Sol Göz: Merkez(468), Kenar(469)
                output_frame = draw_iris_precise(output_frame, lm, 468, 469, secili_renk, h, w)
                # Sağ Göz: Merkez(473), Kenar(474)
                output_frame = draw_iris_precise(output_frame, lm, 473, 474, secili_renk, h, w)

    # --- UI ---
    cv2.rectangle(output_frame, (0, h-100), (w, h), (20, 20, 20), -1)
    cv2.putText(output_frame, f"FOX EYE: %{int(fox_intensity*100)}", (20, h-60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(output_frame, f"LENS: {renk_ismi}", (20, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, secili_renk, 2)
    cv2.putText(output_frame, "[F]: Fox Artir | [G]: Fox Azalt", (w-350, h-60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(output_frame, "[C]: Lens Degistir | [S]: Kaydet", (w-350, h-30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    cv2.imshow('BeautyTech - Goz Estetigi V3', output_frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    elif key == ord('s'):
        cv2.imwrite(f"Goz_Estetigi_V3_{int(time.time())}.jpg", output_frame)
        cv2.rectangle(output_frame, (0, 0), (w, h), (255, 255, 255), 50)
        cv2.imshow('BeautyTech - Goz Estetigi V3', output_frame)
        cv2.waitKey(100)
    elif key == ord('f'): fox_intensity = min(MAX_FOX, fox_intensity + 0.05)
    elif key == ord('g'): fox_intensity = max(0.0, fox_intensity - 0.05)
    elif key == ord('c'): lens_index = (lens_index + 1) % len(LENS_RENKLERI)

cap.release()
cv2.destroyAllWindows()