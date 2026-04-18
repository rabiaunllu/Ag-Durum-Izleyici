#ağ durumunu jsona kaydetme işlemleri (erişebilme-gecikme-paket kaybı- tcp http 80 port istekelre yantı veriyor mu)
import json
import os
from datetime import datetime

LOG_DOSYASI = os.path.join(os.path.dirname(__file__), "..", "logs", "monitor_log.json")
MAKSIMUM_KAYIT = 1000 # dosya şişmesin diye eski kayıtları silme sınırı

#gelen yeni veriyi (ağ durumu) jsona ekleme
def kayit_ekle(veri):
    log_klasoru = os.path.dirname(LOG_DOSYASI)
    os.makedirs(log_klasoru, exist_ok=True)

    # veri kaydedilme formatı
    yeni_kayit = {
        "tarih_saat": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "hedef_ip"  : veri.get("hedef_ip", ""),
        "port"      : veri.get("port", 0),
        "hedef_adi" : veri.get("hedef_adi", ""),
        "durum"     : veri.get("durum", "BILINMIYOR"),#açık kapalı veya bozulmuş olabilir
        "gecikme_ms": veri.get("gecikme_ms", None),
        "paket_kaybi": veri.get("paket_kaybi", None)
    }

    #dosyayı okuma ve veriyi ekleme
    mevcut_veriler = _dosyayi_oku()
    mevcut_veriler.append(yeni_kayit)

    #1000 aştıysak eski verileri sil ve en son halini yaz
    if len(mevcut_veriler) > MAKSIMUM_KAYIT:
        mevcut_veriler = mevcut_veriler[-MAKSIMUM_KAYIT:]
    _dosyaya_yaz(mevcut_veriler)

#arayüz tasarımı için kullanılcak fonksiyonlar
#kaydedilen son 50 veriyi getir
def son_kayitlari_getir(getirilecek_sayi=50):
    kayitlar = _dosyayi_oku()
    return kayitlar[-getirilecek_sayi:] if len(kayitlar) >= getirilecek_sayi else kayitlar

#Sadece istenilen ip adresine ait 100 kaydı döndürür.
def hedefe_gore_filtrele(aranan_ip, aranan_port, getirilecek_sayi=100):
    kayitlar = _dosyayi_oku()
    filtrelenmis = [
        k for k in kayitlar 
        if k.get("hedef_ip") == aranan_ip and k.get("port") == aranan_port #ip ve port beraber bakıyoruz çünkü doğru yere ulaşalım:)
    ]
    return filtrelenmis[-getirilecek_sayi:]

#json dosyasını oku ve liste olarak döndür
def _dosyayi_oku():
    if not os.path.exists(LOG_DOSYASI):
        return []
    
    try:
        with open(LOG_DOSYASI, "r", encoding="utf-8") as dosya:
            okunan = json.load(dosya)
            return okunan if isinstance(okunan, list) else []
    except (json.JSONDecodeError, IOError):
        return [] # JSON bozulmuşsa sistemi çökertmemek için boş liste dön

#jsona verileri json formatında yazmak için
def _dosyaya_yaz(veri_listesi):
    """Listeyi JSON formatında okunabilir şekilde dosyaya işler"""
    try:
        with open(LOG_DOSYASI, "w", encoding="utf-8") as dosya:
            json.dump(veri_listesi, dosya, indent=2, ensure_ascii=False)
    except IOError as hata:
        print(f" [HATA] Log dosyasına yazılamadı: {hata}")

# TEST BÖLÜMÜ: Modülü doğrudan çalıştırınca test eder

def modulu_test_et():
    print("  Logger Modülü Test Ediliyor...")

    test_verisi = {
        "hedef_ip"  : "8.8.8.8",
        "port"      : 80,
        "hedef_adi" : "Google DNS (Test)",
        "durum"     : "ACIK",
        "gecikme_ms": 12.5,
        "paket_kaybi": 0.0
    }

    print("\n  1. Örnek test verisi dosyaya yazılıyor...")
    kayit_ekle(test_verisi)
    print("     Yazma işlemi başarılı.")

    print("\n  2. Dosyadaki son kayıtlar okunuyor...")
    son_kayitlar = son_kayitlari_getir(5)
    for kayit in son_kayitlar:
        print(f"     [{kayit['tarih_saat']}] {kayit['hedef_adi']} → {kayit['durum']}")

    print("\n" + "=" * 55)
    print(f"  Log dosyasının konumu: {os.path.abspath(LOG_DOSYASI)}")
    print("  Test tamamlandı.")

if __name__ == "__main__":
    modulu_test_et()
        