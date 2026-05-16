import time
import threading
from datetime import datetime
import logger
import ping_checker
import TCPandUDP_checker
import os
import json

# Dosya yolları
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGETS_FILE = os.path.join(BASE_DIR, "..", "config", "targets.json")

def load_targets_dynamic():
    if os.path.exists(TARGETS_FILE):
        try:
            with open(TARGETS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Listeyi main_monitor'un beklediği sözlük yapısına çeviriyoruz
                return {f"{t['name']}": t for t in data}
        except Exception as e:
            print(f"Hedef yükleme hatası: {e}")
            return {}
    return {}

# DURUM TAKİBİ
son_durumlar = {}

# temiz ve okunabilir bir yapı
def cihaz_kontrol_et(isim, veri):
    global son_durumlar
    ip = veri["ip"]
    port = veri["port"]
    proto = veri.get("protokol", "TCP") # Eğer belirtilmemişse varsayılan TCP

    #elde veri olması için basta kapalı sonradna güncelleniyor
    su_anki_durum = "KAPALI"
    aktif_gecikme = None
    kayip = 100
    
    control_type = veri.get("control_type", "ICMP + TCP (İkisi de)")

    # Cihazı 3 kez kontrol ediyoruz- Ağdaki anlık bir takılma yüzünden hemen "Cihaz çöktü" alarmı vermesin diye
    for deneme in range(3):
        gecikme_ping = None
        port_acik_mi = False
        gecikme_port = None
        hata_detayi = None
        k = 100
        tcp_mesaj = "KAPALI"

        # Kontrol tipine göre testleri yap
        if "ICMP" in control_type or "İkisi de" in control_type:
            gecikme_ping, k = ping_checker.ping_gonder(ip, paket_sayisi=1)
            
        if "TCP" in control_type or "UDP" in control_type or "İkisi de" in control_type:
            port_acik_mi, gecikme_port, port_mesaj, hata_detayi = TCPandUDP_checker.check_port(ip, port, protocol=proto)

        # Eğer herhangi biri yanıt verirse cihaz AÇIK'tır
        if (gecikme_ping is not None) or port_acik_mi:
            su_anki_durum = "AÇIK"
            aktif_gecikme = gecikme_ping if gecikme_ping is not None else gecikme_port
            kayip = k if (gecikme_ping is not None) else 0
            break
        else:
            # Başarısızsa, socket seviyesi teşhis mesajını durum olarak kaydet
            if "TCP" in control_type or "UDP" in control_type or "İkisi de" in control_type:
                su_anki_durum = port_mesaj
            else:
                su_anki_durum = "KAPALI (ICMP Timeout)"

        # Eğer yanıt alamadıysak ve 3. deneme değilse üstel geri çekilme ile bekle
        if deneme < 2:
            # Üstel Geri Çekilme Algoritması 
            # Amaç: Ağdaki yoğunluğu yani tıkanıklıgı önlemek ve hedef sunucuyu gereksiz paket yağmuruna 
            # tutmamak için bekleme süresini katlayarak artırmak (2^1 = 2sn, 2^2 = 4sn).
            bekleme_suresi = 2 ** (deneme + 1)
            time.sleep(bekleme_suresi)
   
    # Tüm bulguları (IP, hız, hata kodu vb.) bir paket haline getirip logger.py modülüne teslim ediyor
    # Arayüzün güncel veri alabilmesi için her kontrolde log paketini hazırlayıp kaydediyoruz
    #arayüz grafiklerini çizebilsin 
    log_paketi = {
        "hedef_ip": ip,
        "port": port,
        "protokol": proto,
        "hedef_adi": isim,
        "durum": su_anki_durum,
        "gecikme_ms": aktif_gecikme,
        "paket_kaybi": kayip,
        "hata_detayi": hata_detayi.get("kategori") if hata_detayi else None,
        "hata_kodu": hata_detayi.get("hata_kodu") if hata_detayi else None,
        "hata_aciklamasi": hata_detayi.get("aciklama") if hata_detayi else None
    }
    logger.kayit_ekle(log_paketi) # Bu artık hem JSON hem SQLite'a yazar

    if su_anki_durum != son_durumlar[isim]:
        zaman = datetime.now().strftime("%H:%M:%S")
        mesaj = f"[{zaman}] {isim} ({proto}) Durumu: {son_durumlar[isim]} -> {su_anki_durum}"
        ping_checker.renkli_durum_yazdir(mesaj, su_anki_durum)
        son_durumlar[isim] = su_anki_durum
    else:
        # Durum değişmediyse sadece terminalde işlem aktığını takip ediyorum
        print(f"Kontrol edildi: {isim} [{proto}] -> Stabil ({su_anki_durum})")

print("-" * 60)
print("   AĞ DURUM İZLEME PANELİ - ANA KONTROL MERKEZİ   ")
print("-" * 60)

# e-while döngüsünü, her cihazı aynı anda kontrol edecek şekilde güncelleyeceğiz.
try:
    while True:
        HEDEFLER = load_targets_dynamic()
        if not HEDEFLER:
            print("[!] İzlenecek hedef bulunamadı. config/targets.json dosyasını kontrol edin.")
            time.sleep(10)
            continue

        # Yeni hedefleri durumlara ekle
        for isim in HEDEFLER:
            if isim not in son_durumlar:
                son_durumlar[isim] = "BILINMIYOR"

        is_parcaciklari = []
        for isim, veri in HEDEFLER.items():
            t = threading.Thread(target=cihaz_kontrol_et, args=(isim, veri))
            t.start()
            is_parcaciklari.append(t)

        for t in is_parcaciklari:
            t.join()

        print("-" * 40)
        time.sleep(10)

except KeyboardInterrupt:
    print("\n[!] İzleme sistemi kullanıcı tarafından durduruldu.")


""""
1. Çalışma Mimarisi (Senkron vs. Asenkron)
(Sıralı/Senkron): Cihazları bir kuyruğa girmiş gibi tek tek kontrol ediyordu. Örneğin, Google DNS'in yanıt vermesini beklerken Marmara Üniversitesi'nin kontrolü başlayamıyordu. Bir cihaz takılırsa tüm sistem duraksıyordu.
(Paralel/Eşzamanlı): threading kütüphanesi sayesinde tüm cihazlar aynı anda "yola çıkar". Her cihaz kendi iş parçacığında (thread) bağımsız kontrol edildiği için birinin yavaşlığı diğerini etkilemez.
2. Zaman Verimliliği 
Toplam işlem süresi, listedeki en yavaş tek bir cihazın süresine eşittir. 10 cihaz olsa bile işlem yaklaşık 2 saniyede biter. 
3. Kod Organizasyonu ve Modülerlik
 İzleme mantığını cihaz_kontrol_et adında bağımsız bir fonksiyona taşıdık. Bu modüler yapı sayesinde ileride sadece bu fonksiyonu değiştirerek yeni özellikler eklemek kolaylaştı.
"""