import json
import os
from datetime import datetime
import threading
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# logs klasörünü ve json dosyasını proje dizininde tutuyoruz
LOG_DOSYASI = os.path.abspath(os.path.join(BASE_DIR, "logs", "monitor_log.json"))
lock = threading.Lock()

def get_maksimum_kayit():
    config_yolu = os.path.join(BASE_DIR, "config", "alert_config.json")
    try:
        if os.path.exists(config_yolu):
            with open(config_yolu, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("log_ayarlari", {}).get("max_kayit", 10000)
    except Exception:
        pass
    return 10000


def kayit_ekle(veri):
    tarih_saat = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    # Hata detay bilgilerini al (varsa)
    hata_detayi = veri.get("hata_detayi")       # Kısa kategori: "Zaman Aşımı", "Port Reddedildi" vb.
    hata_kodu = veri.get("hata_kodu")            # Sayısal kod: 10061, 10060 vb.
    hata_aciklamasi = veri.get("hata_aciklamasi") # Detaylı Türkçe açıklama

    # Arayüzdeki log akışı için dinamik mesaj oluşturma
    if veri["durum"] == "AÇIK":
        mesaj = f"{veri['hedef_ip']} sunucusu erişilebilir."
    elif hata_detayi:
        # Hata detayı varsa mesaja dahil et (daha bilgilendirici log)
        mesaj = f"{veri['hedef_ip']} sunucusuna ulaşılamıyor! Sebep: {hata_detayi}"
    else:
        mesaj = f"{veri['hedef_ip']} sunucusuna ulaşılamıyor! (Bağlantı koptu)"

    yeni_kayit = {
        "tarih_saat": tarih_saat,
        "hedef_ip": veri.get("hedef_ip"),
        "port": veri.get("port"),
        "hedef_adi": veri.get("hedef_adi"),
        "durum": veri.get("durum"),
        "gecikme_ms": veri.get("gecikme_ms"),
        "paket_kaybi": veri.get("paket_kaybi"),
        "hata_detayi": hata_detayi,
        "hata_kodu": hata_kodu,
        "hata_aciklamasi": hata_aciklamasi,
        "mesaj": mesaj
    }

    # JSON dosyasına yazma işlemleri
    with lock:
        mevcut_veriler = _dosyayi_oku()

        # En yeni kaydı en başa ekliyoruz (Arayüzde en üstte görünsün diye)
        mevcut_veriler.insert(0, yeni_kayit)

        # Dosya şişmesin diye sınırı koruyoruz
        maksimum_kayit = get_maksimum_kayit()
        if len(mevcut_veriler) >= maksimum_kayit:
            # En yeni %70'i ana dosyada bırak (grafikler beslensin), geri kalan en eski %30'u arşivle
            yeni_sinir = max(1, int(maksimum_kayit * 0.70))
            eski_veriler = mevcut_veriler[yeni_sinir:]
            mevcut_veriler = mevcut_veriler[:yeni_sinir]

            # Arşivleme işlemi
            try:
                arsiv_klasoru = os.path.join(os.path.dirname(LOG_DOSYASI), "archives")
                os.makedirs(arsiv_klasoru, exist_ok=True)

                zaman_damgasi = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
                arsiv_dosya_adi = f"archive_bulk_{zaman_damgasi}.json"
                arsiv_yolu = os.path.join(arsiv_klasoru, arsiv_dosya_adi)

                with open(arsiv_yolu, "w", encoding="utf-8") as f:
                    json.dump(eski_veriler, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f" [HATA] Log arşivleme hatası: {e}")

        _dosyaya_yaz(mevcut_veriler)


def _dosyayi_oku():
    if not os.path.exists(LOG_DOSYASI):
        return []
    
    # Dosya o an yazılıyorsa (meşgulse) pes etme, 5 kez milisaniyelik aralarla dene
    for _ in range(5):
        try:
            with open(LOG_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Dosya kilitliyse veya yarım yazılmışsa 0.1 saniye bekle
            time.sleep(0.1)
            continue
            
    return []


def _dosyaya_yaz(veri):
    # Klasör yoksa oluştur
    os.makedirs(os.path.dirname(LOG_DOSYASI), exist_ok=True)
    try:
        with open(LOG_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(veri, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f" [HATA] JSON yazma hatası: {e}")


def son_kayitlari_getir(getirilecek_sayi=50):
    """JSON dosyasındaki son kayıtları döndürür."""
    with lock:
        mevcut_veriler = _dosyayi_oku()
    return mevcut_veriler[:getirilecek_sayi]