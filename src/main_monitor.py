import time
import threading
from datetime import datetime

# Proje klasöründeki diğer modüllerimizi içeri aktarıyoruz
# G1'den TCP, G2'den Ping ve loglama modülleri sisteme dahil ediliyor.
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

# --- DURUM TAKİBİ (STATE MANAGEMENT) ---
son_durumlar = {}

# e-Bu sayede bir cihazın ping süresini beklerken diğeri de kendi işlemini yapabilecek.
def cihaz_kontrol_et(isim, veri):
    global son_durumlar
    ip = veri["ip"]
    port = veri["port"]
    proto = veri.get("protokol", "TCP") # Eğer belirtilmemişse varsayılan TCP

    # --- YENİLENEN KONTROL MEKANİZMASI (RETRY LOGIC) ---
    su_anki_durum = "KAPALI"
    aktif_gecikme = None
    kayip = 100
    
    control_type = veri.get("control_type", "ICMP + TCP (İkisi de)")

    # Cihazı 3 kez kontrol ediyoruz
    for deneme in range(3):
        gecikme_ping = None
        port_acik_mi = False
        gecikme_port = None
        k = 100
        tcp_mesaj = "KAPALI"

        # Kontrol tipine göre testleri yap
        if "ICMP" in control_type or "İkisi de" in control_type:
            gecikme_ping, k = ping_checker.ping_gonder(ip, paket_sayisi=1)
            
        if "TCP" in control_type or "İkisi de" in control_type:
            port_acik_mi, gecikme_port, tcp_mesaj = TCPandUDP_checker.check_port(ip, port, protocol=proto)

        # Eğer herhangi biri yanıt verirse cihaz AÇIK'tır
        if (gecikme_ping is not None) or port_acik_mi:
            su_anki_durum = "AÇIK"
            aktif_gecikme = gecikme_ping if gecikme_ping is not None else gecikme_port
            kayip = k if (gecikme_ping is not None) else 0
            break
        else:
            # Başarısızsa, socket seviyesi teşhis mesajını durum olarak kaydet
            if "TCP" in control_type or "İkisi de" in control_type:
                su_anki_durum = tcp_mesaj
            else:
                su_anki_durum = "KAPALI (ICMP Timeout)"

        # Eğer yanıt alamadıysak ve 3. deneme değilse üstel geri çekilme (exponential backoff) ile bekle
        if deneme < 2:
            # Üstel Geri Çekilme Algoritması (Exponential Backoff)
            # Amaç: Ağdaki yoğunluğu (congestion) önlemek ve hedef sunucuyu gereksiz paket yağmuruna 
            # tutmamak için bekleme süresini katlayarak artırmak (2^1 = 2sn, 2^2 = 4sn).
            bekleme_suresi = 2 ** (deneme + 1)
            time.sleep(bekleme_suresi)
    # --------------------------------------------------

    # 3. ADIM: DURUM DEĞİŞİKLİĞİ VE LOGLAMA
    # Arayüzün (Streamlit) taze veri alabilmesi için her kontrolde log paketini hazırlayıp kaydediyoruz
    log_paketi = {
        "hedef_ip": ip,
        "port": port,
        "protokol": proto,
        "hedef_adi": isim,
        "durum": su_anki_durum,
        "gecikme_ms": aktif_gecikme,
        "paket_kaybi": kayip
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
    # Program Ctrl+C ile kapatıldığında düzgün bir şekilde çıkış yapması için
    print("\n[!] İzleme sistemi kullanıcı tarafından durduruldu.")

# yaptigim degisiklikler:
""""
1. Çalışma Mimarisi (Senkron vs. Asenkron)
İlk Kod (Sıralı/Senkron): Cihazları bir kuyruğa girmiş gibi tek tek kontrol ediyordu. Örneğin, Google DNS'in yanıt vermesini beklerken Marmara Üniversitesi'nin kontrolü başlayamıyordu. Bir cihaz takılırsa tüm sistem duraksıyordu.
Son Kod (Paralel/Eşzamanlı): threading kütüphanesi sayesinde tüm cihazlar aynı anda "yola çıkar". Her cihaz kendi iş parçacığında (thread) bağımsız kontrol edildiği için birinin yavaşlığı diğerini etkilemez.
2. Zaman Verimliliği 
İlk Kod: Toplam işlem süresi, listedeki tüm cihazların kontrol sürelerinin toplamına eşitti. 10 cihazın her biri 2 saniye sürse, bir döngü 20 saniye sürüyordu.
Son Kod: Toplam işlem süresi, listedeki en yavaş tek bir cihazın süresine eşittir. 10 cihaz olsa bile işlem yaklaşık 2 saniyede biter. 
3. Kod Organizasyonu ve Modülerlik
#İlk Kod: Tüm mantık (veri çekme, karar verme, loglama) devasa bir while döngüsünün içine hapsedilmişti. Bu, kodun okunmasını ve hata ayıklanmasını (debugging) zorlaştırıyordu.
#Son Kod: İzleme mantığını cihaz_kontrol_et adında bağımsız bir fonksiyona taşıdık. Bu modüler yapı sayesinde ileride sadece bu fonksiyonu değiştirerek yeni özellikler eklemek çok daha kolaylaştı.
"""