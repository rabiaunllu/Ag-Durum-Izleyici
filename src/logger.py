import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# logs klasörünü ve json dosyasını proje dizininde tutuyoruz
LOG_DOSYASI = os.path.abspath(os.path.join(BASE_DIR, "..", "logs", "monitor_log.json"))
MAKSIMUM_KAYIT = 500


def kayit_ekle(veri):
    tarih_saat = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    # Arayüzdeki log akışı için dinamik mesaj oluşturma
    if veri["durum"] in ["ACIK", "AÇIK"]:
        mesaj = f"{veri['hedef_ip']} sunucusu erişilebilir."
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
        "mesaj": mesaj
    }

    # JSON dosyasına yazma işlemleri
    mevcut_veriler = _dosyayi_oku()

    # En yeni kaydı en başa ekliyoruz (Arayüzde en üstte görünsün diye)
    mevcut_veriler.insert(0, yeni_kayit)

    # Dosya şişmesin diye sınırı koruyoruz
    if len(mevcut_veriler) > MAKSIMUM_KAYIT:
        mevcut_veriler = mevcut_veriler[:MAKSIMUM_KAYIT]

    _dosyaya_yaz(mevcut_veriler)


def _dosyayi_oku():
    if not os.path.exists(LOG_DOSYASI):
        return []
    try:
        with open(LOG_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
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
    mevcut_veriler = _dosyayi_oku()
    return mevcut_veriler[:getirilecek_sayi]


def maksimum_kayit_ayarla(sayi):
    """Maksimum kayıt sayısını günceller."""
    global MAKSIMUM_KAYIT
    MAKSIMUM_KAYIT = sayi