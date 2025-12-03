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

# --- KESİN ÇALIŞAN NOKTA LİSTELERİ ---
# Bu listeler noktaların sırasını takip eder, böylece poligon bozulmaz.

# Üst Dudak (Dış Çerçeve + İç Çerçeve Birleşimi)
UPPER_LIP = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191, 78]

# Alt Dudak (Dış Çerçeve + İç Çerçeve Birleşimi)
LOWER_LIP = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78]

# --- RENK PALETİ ---
RUJ_RENKLERI = {
    'r': (0, 0, 255),     # Kırmızı
    'p': (180, 105, 255), # Pembe
    'm': (255, 0, 255),   # Mor
    'n': (145, 155, 190), # Nude
    'b': (90, 20, 90)     # Bordo
}
aktif_renk = RUJ_RENKLERI['r']
aktif_renk_ismi = "Kirmizi"

cap = cv2.VideoCapture(0)

print("--- SANAL MAKYAJ V3 (GARANTILI) ---")

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
            landmarks = face_landmarks.landmark
            
            # Maske katmanı (Siyah)
            dudak_maskesi = np.zeros((h, w), dtype=np.uint8)
            
            # --- ADIM 1: Üst Dudağı Çiz ---
            points_upper = []
            for idx in UPPER_LIP:
                pt = landmarks[idx]
                points_upper.append([int(pt.x * w), int(pt.y * h)])
            if points_upper:
                cv2.fillPoly(dudak_maskesi, [np.array(points_upper, dtype=np.int32)], 255)

            # --- ADIM 2: Alt Dudağı Çiz ---
            points_lower = []
            for idx in LOWER_LIP:
                pt = landmarks[idx]
                points_lower.append([int(pt.x * w), int(pt.y * h)])
            if points_lower:
                cv2.fillPoly(dudak_maskesi, [np.array(points_lower, dtype=np.int32)], 255)

            # --- ADIM 3: Renklendirme ---
            ruj_katmani = np.zeros((h, w, c), dtype=np.uint8)
            ruj_katmani[:] = aktif_renk
            
            # 0.4 = %40 Ruj, %60 Orijinal Dudak (Doğal görünüm için)
            alpha = 0.4 
            karistirilmis = cv2.addWeighted(frame, 1-alpha, ruj_katmani, alpha, 0)

            # Sadece maskelenen (beyaz boyalı) dudak alanlarını al
            dudak_renkli = cv2.bitwise_and(karistirilmis, karistirilmis, mask=dudak_maskesi)
            dudak_disi = cv2.bitwise_and(frame, frame, mask=cv2.bitwise_not(dudak_maskesi))
            
            output_frame = cv2.add(dudak_disi, dudak_renkli)

    # Arayüz
    cv2.rectangle(output_frame, (20, h-60), (60, h-20), aktif_renk, -1)
    cv2.putText(output_frame, f"Ruj: {aktif_renk_ismi}", (80, h-35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(output_frame, "[R]Kirmizi [P]Pembe [M]Mor [N]Nude [B]Bordo", (w-450, h-50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(output_frame, "'s': Kaydet | 'q': Cikis", (w-450, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    cv2.imshow('BeautyTech AR - Sanal Ruj V3', output_frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    elif key == ord('s'):
        cv2.imwrite(f"Sanal_Ruj_V3_{int(time.time())}.jpg", output_frame)
        cv2.rectangle(output_frame, (0, 0), (w, h), (255, 255, 255), 50)
        cv2.imshow('BeautyTech AR - Sanal Ruj V3', output_frame)
        cv2.waitKey(100)
    elif key == ord('r'): aktif_renk = RUJ_RENKLERI['r']; aktif_renk_ismi = "Kirmizi"
    elif key == ord('p'): aktif_renk = RUJ_RENKLERI['p']; aktif_renk_ismi = "Pembe"
    elif key == ord('m'): aktif_renk = RUJ_RENKLERI['m']; aktif_renk_ismi = "Mor"
    elif key == ord('n'): aktif_renk = RUJ_RENKLERI['n']; aktif_renk_ismi = "Nude"
    elif key == ord('b'): aktif_renk = RUJ_RENKLERI['b']; aktif_renk_ismi = "Bordo"

cap.release()
cv2.destroyAllWindows()