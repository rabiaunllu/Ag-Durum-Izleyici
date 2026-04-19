import time
from datetime import datetime

# Proje klasöründeki diğer modüllerimizi içeri aktarıyoruz
# G1'den TCP, G2'den Ping ve loglama modülleri sisteme dahil ediliyor.
import logger
import ping_checker
import tcp_checker

# --- SİSTEM YAPILANDIRMASI ---
# İzlenecek cihazları bir sözlük yapısında tutuyorum. 
# Böylece yeni bir cihaz eklemek veya çıkarmak çok kolay oluyor.
HEDEFLER = {
    "Google DNS": {"ip": "8.8.8.8", "port": 53},
    "Marmara Uni": {"ip": "193.140.160.11", "port": 80},
    "Cloudflare": {"ip": "1.1.1.1", "port": 443},
    "Test Sunucusu": {"ip": "192.0.2.1", "port": 80} # Bilerek ulaşılamaz IP eklendi
}

# --- DURUM TAKİBİ (STATE MANAGEMENT) ---
# Burası benim görevimin en kritik noktası: Cihazların son durumunu hafızada tutuyorum.
# Sadece durum değiştiğinde (örneğin AÇIK'tan KAPALI'ya geçince) işlem yapacağız.
son_durumlar = {isim: "BILINMIYOR" for isim in HEDEFLER}

print("-" * 60)
print("   AĞ DURUM İZLEME PANELİ - ANA KONTROL MERKEZİ (G3)   ")
print("-" * 60)

try:
    # Programın kesintisiz çalışması için sonsuz döngü kuruyorum
    while True:
        for isim, veri in HEDEFLER.items():
            ip = veri["ip"]
            port = veri["port"]

            # 1. ADIM: DİĞER MODÜLLERDEN VERİ ÇEKME
            # Arkadaşlarımdan gelen fonksiyonları kullanarak verileri topluyorum.
            gecikme_ping, kayip = ping_checker.ping_gonder(ip, paket_sayisi=2)
            port_acik_mi, gecikme_tcp = tcp_checker.check_tcp_port(ip, port)

            # 2. ADIM: KARAR MEKANİZMASI (DECISION LOGIC)
            # Eğer ping atılabiliyorsa VEYA port yanıt veriyorsa sistem 'ACIK' kabul edilir.
            if gecikme_ping is not None or port_acik_mi:
                su_anki_durum = "ACIK"
            else:
                su_anki_durum = "KAPALI"
            
            # Gecikme değerini raporlamak için hangi modülden veri geldiyse onu seçiyorum.
            aktif_gecikme = gecikme_ping if gecikme_ping is not None else gecikme_tcp

            # 3. ADIM: DURUM DEĞİŞİKLİĞİ KONTROLÜ
            # Gereksiz log kalabalığı yapmamak için sadece durum değiştiğinde çıktı üretiyorum.
            if su_anki_durum != son_durumlar[isim]:
                zaman = datetime.now().strftime("%H:%M:%S")
                mesaj = f"[{zaman}] {isim} Durumu: {son_durumlar[isim]} -> {su_anki_durum}"
                
                # Konsolda dikkat çekmesi için renkli çıktı modülünü kullanıyorum
                ping_checker.renkli_durum_yazdir(mesaj, su_anki_durum)

                # 4. ADIM: LOG KAYDI (PERSISTENCE)
                # Durum değişimini JSON formatında kalıcı olarak kaydediyorum.
                # logger modülüne veriyi bir sözlük (dictionary) paketi halinde gönderiyorum.
                log_paketi = {
                    "hedef_ip": ip,
                    "port": port,
                    "hedef_adi": isim,
                    "durum": su_anki_durum,
                    "gecikme_ms": aktif_gecikme,
                    "paket_kaybi": kayip
                }
                logger.kayit_ekle(log_paketi)

                # Durum güncellendi, bir sonraki kontrolde buna göre kıyas yapılacak
                son_durumlar[isim] = su_anki_durum
            
            else:
                # Durum değişmediyse sadece terminalde işlem aktığını takip ediyorum
                print(f"Kontrol edildi: {isim} -> Stabil ({su_anki_durum})")

        print("-" * 40)
        # Ağdaki yükü ve log dosyasının büyümesini kontrol altında tutmak için 10 sn bekleme
        time.sleep(10)

except KeyboardInterrupt:
    # Program Ctrl+C ile kapatıldığında düzgün bir şekilde çıkış yapması için
    print("\n[!] İzleme sistemi kullanıcı tarafından durduruldu.")