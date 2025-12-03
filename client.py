import requests
import os

# --- AYARLAR ---
API_URL = "http://127.0.0.1:8000/analiz_et"

# Test edilecek fotoğrafın adı (Klasöründeki gerçek bir fotoğraf ismini buraya yaz)
# Örn: "Cilt_Raporu_1764445471.jpg" veya çektiğin herhangi bir fotonun adı
FOTO_DOSYA_ADI = "Cilt_Raporu_1764601789.jpg" 

# Dosyanın tam yolunu bul
script_dizini = os.path.dirname(os.path.abspath(__file__))
foto_yolu = os.path.join(script_dizini, FOTO_DOSYA_ADI)

print(f"Baglanti kuruluyor... Hedef: {API_URL}")
print(f"Gonderilen Dosya: {FOTO_DOSYA_ADI}")

if not os.path.exists(foto_yolu):
    print("HATA: Belirttigin fotograf dosyasi bulunamadi!")
    print("Lutfen kodun icindeki 'FOTO_DOSYA_ADI' kismina klasordeki gercek bir jpg ismini yaz.")
    exit()

try:
    # Dosyayı aç ve POST isteği ile gönder
    with open(foto_yolu, 'rb') as f:
        files = {'file': (FOTO_DOSYA_ADI, f, 'image/jpeg')}
        response = requests.post(API_URL, files=files)

    # Sonucu Kontrol Et
    if response.status_code == 200:
        print("\n--- SUNUCUDAN GELEN CEVAP (BASARILI) ---")
        data = response.json()
        
        print(f"Cilt Skoru: {data.get('cilt_skoru')}/100")
        print(f"Leke Sayisi: {data.get('leke_sayisi')}")
        
        recete = data.get('reçete', {})
        print(f"\n--- RECETE ---")
        print(f"Sorun: {recete.get('sorun')}")
        print(f"Oneri: {recete.get('onerilen_urun')}")
        print(f"Marka: {recete.get('marka')}")
        print(f"Link:  {recete.get('link')}")
        
    else:
        print(f"\n--- HATA OLUSTU ---")
        print(f"Kod: {response.status_code}")
        print(f"Mesaj: {response.text}")

except Exception as e:
    print(f"\nBAGLANTI HATASI: Sunucu kapali olabilir mi?")
    print(f"Hata detayi: {e}")