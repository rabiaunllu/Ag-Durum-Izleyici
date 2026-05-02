#hedefe ping atıp gecikmeyi ve paket kaybını hesaplar.

import time
# ping3 kütüphanesini içeri al
try:
    import ping3
    PING3_VAR_MI = True
except ImportError:
    PING3_VAR_MI = False

# Renkli konsol çıktıları için colorama
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    RENK_VAR_MI = True
except ImportError:
    RENK_VAR_MI = False
#belirtilen ip adresine ping atar
def ping_gonder(hedef_ip, paket_sayisi=1, zaman_asimi=1):
    #ping3 kurulu değilse subprocess ile yedek yönteme geç yani arka pşanda cmd açıp ping atmak 
    #subprocessinin bazı dezavantajalrı var RAPORDA açıklanacak neden direkt kütüphane kullandığımz
    if not PING3_VAR_MI:
        return _alternatif_ping_kullan(hedef_ip, paket_sayisi, zaman_asimi)

    basarili_sayisi = 0
    gecikme_toplami = 0.0

    for _ in range(paket_sayisi):
        try:
            #süreyi saniye -> milisaniye
            sonuc = ping3.ping(hedef_ip, timeout=zaman_asimi)

            if sonuc is not None and sonuc is not False:
                gecikme_ms = round(sonuc * 1000, 2)
                gecikme_toplami += gecikme_ms
                basarili_sayisi += 1
        except Exception: # Ağ hatası,yetki hatası vb. durumlarda bu paketi kayıp say
            pass # Hata olursa paketi kayıp say

        if paket_sayisi > 1: # Birden fazla ping varsa aralarında kısa beklelemek için paketleri droplamamak için
            time.sleep(0.2) #ddos sanmasın sanrsa paketlerde kayıp meydana gelir bu sebeple bekleme süresi eklememiz gerekti

    # Ortalamaları hesapla
    if basarili_sayisi > 0:
        ort_gecikme = round(gecikme_toplami / basarili_sayisi, 2)
        paket_kaybi = round(((paket_sayisi - basarili_sayisi) / paket_sayisi) * 100, 1)
        return ort_gecikme, paket_kaybi
    else:
        return None, 100.0 # Ulaşılamadı
    
#ping3 kütüphanesi çalışmazsa devreye girecek fonksiyonalr
def _alternatif_ping_kullan(hedef_ip, paket_sayisi=1, zaman_asimi=1):
    import subprocess
    import platform
    import re

    sistem = platform.system().lower()
    if sistem == "windows":
        komut = ["ping", "-n", str(paket_sayisi), "-w", str(zaman_asimi * 1000), hedef_ip]
    else:
        komut = ["ping", "-c", str(paket_sayisi), "-W", str(zaman_asimi), hedef_ip]

    try:
        cikti = subprocess.run(komut, capture_output=True, text=True, timeout=zaman_asimi + 3)
        if cikti.returncode == 0:
            if sistem == "windows":
                eslesme = re.search(r"(?:Ortalama|Average)\s*=\s*(\d+)\s*ms", cikti.stdout, re.IGNORECASE)
            else:
                eslesme = re.search(r"min/avg/max.*=\s*[\d.]+/([\d.]+)/", cikti.stdout)

            gecikme = float(eslesme.group(1)) if eslesme else 0.0
            kayip_eslesme = re.search(r"(\d+)%\s*(?:packet\s*)?loss", cikti.stdout, re.IGNORECASE)
            kayip = float(kayip_eslesme.group(1)) if kayip_eslesme else 0.0

            return gecikme, kayip
        else:
            return None, 100.0
    except Exception:
        return None, 100.0
#bağlantı durumunu çıktıda okunabilir kılmak için renklendirme
def renkli_durum_yazdir(mesaj, durum):
    if not RENK_VAR_MI:
        print(mesaj)
        return

    if durum == "AÇIK":
        print(Fore.GREEN + mesaj)
    elif durum == "YAVAS":
        print(Fore.YELLOW + mesaj)
    elif durum == "KAPALI":
        print(Fore.RED + mesaj)
    else:
        print(mesaj)


# TEST BÖLÜMÜ: Modülü doğrudan çalıştırınca test eder 
def modulu_test_et():
    print("  Ping Modülü Test Ediliyor...")

    test_hedefler = [
        ("8.8.8.8",   "Google DNS      — Ulaşılabilir olmalı"),
        ("1.1.1.1",   "Cloudflare DNS  — Ulaşılabilir olmalı"),
        ("192.0.2.1", "TEST-NET IP     — Ulaşılamaz olmalı"),
    ]

    for ip, aciklama in test_hedefler:
        print(f"\n  Test: {aciklama}")
        gecikme, kayip = ping_gonder(ip, paket_sayisi=2, zaman_asimi=2)

        if gecikme is not None:
            renkli_durum_yazdir(f"  Sonuç -> Gecikme: {gecikme} ms | Paket Kaybı: %{kayip}", "AÇIK")
        else:
            renkli_durum_yazdir(f"  Sonuç -> Ulaşılamadı! Paket Kaybı: %{kayip}", "KAPALI")

    print("  Test tamamlandı.")

if __name__ == "__main__":
    modulu_test_et()