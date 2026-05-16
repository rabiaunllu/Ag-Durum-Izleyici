import socket
import time
import errno
import http.client


# Her bir anahtar bir hata kodu, değeri ise (kategori, açıklama) çiftidir.
HATA_KODLARI = {
    0:     ("Başarılı", "Bağlantı sağlandı."),
    10035: ("Güvenlik Duvarı Engeli", "Bağlantı güvenlik duvarı tarafından engellendi."),
    10038: ("Geçersiz İşlem", "Sistemde geçersiz bir işlem yapılmaya çalışıldı."),
    10049: ("Hatalı IP Adresi", "Girilen IP adresi geçersiz."),
    10051: ("Ağ Bağlantısı Yok", "İnternet veya ağ bağlantınız kesilmiş olabilir."),
    10053: ("Bağlantı İptal Edildi", "Güvenlik yazılımı bağlantıyı kesmiş olabilir."),
    10054: ("Bağlantı Koptu", "Karşı sunucu bağlantıyı zorla kapattı."),
    10056: ("Zaten Bağlı", "Cihaz zaten sisteme bağlı."),
    10057: ("Bağlantı Yok", "Sisteme bağlı değil."),
    10060: ("Zaman Aşımı", "Cihazdan çok uzun süre yanıt alınamadı. Cihaz kapalı olabilir."),
    10061: ("Erişim Reddedildi", "Cihaz açık ancak ilgili servis veya port kapalı."),
    10064: ("Cihaz Çöktü", "Cihaz aniden bağlantıyı kesti veya yeniden başlıyor."),
    10065: ("Cihaza Ulaşılamıyor", "Hedef cihaza giden bir yol bulunamadı."),

    errno.ECONNREFUSED: ("Erişim Reddedildi", "Bağlantı karşı tarafça reddedildi."),
    errno.ETIMEDOUT:    ("Zaman Aşımı", "Cihazdan zamanında yanıt alınamadı."),
    errno.ENETUNREACH:  ("Ağ Bağlantısı Yok", "Ağa erişilemiyor."),
    errno.EHOSTUNREACH: ("Cihaza Ulaşılamıyor", "Hedef cihaza erişilemiyor."),
    errno.ECONNRESET:   ("Bağlantı Koptu", "Karşı sunucu bağlantıyı zorla kapattı."),
    errno.ECONNABORTED: ("Bağlantı İptal Edildi", "Bağlantı iptal edildi."),
}


def _hata_detayi_olustur(hata_kodu):
    """
    Hata kodunu yapılandırılmış bir sözlüğe çevirir.
    Bilinmeyen kodlar için genel bir mesaj üretir.
    """
    if hata_kodu in HATA_KODLARI:
        kategori, aciklama = HATA_KODLARI[hata_kodu]
    else:
        kategori = f"Bilinmeyen Hata"
        aciklama = f"İşletim sistemi hata kodu {hata_kodu} döndürdü. Bu kod tanınmıyor."

    return {
        "hata_kodu": hata_kodu,
        "kategori": kategori,
        "aciklama": aciklama
    }


def check_http(ip_address, port, timeout=5):
    start_time = time.time() #zaman baslatma
    try:
        if port == 443: #https ise SSL sertifikasını doğrulamadan geçiyor
            import ssl
            context = ssl._create_unverified_context()
            conn = http.client.HTTPSConnection(ip_address, timeout=timeout, context=context)
        else: #port 80 ise
            conn = http.client.HTTPConnection(ip_address, port, timeout=timeout)
        #güvenlik duvarlarının bizi bot sanıp engellememesi için maske 
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        conn.request("GET", "/", headers=headers)
        response = conn.getresponse() #sunucudan geelen cevabı tut
        latency_ms = (time.time() - start_time) * 1000
        
        if response.status < 500: #gelen cevap yani sayfadaki kod no bakar
            return True, round(latency_ms, 2), f"HTTP {response.status}", None
        else:
            detay = {"hata_kodu": response.status, "kategori": "HTTP Sunucu Hatası", "aciklama": f"Sunucu HTTP {response.status} hatası döndürdü."}
            return False, None, f"HTTP {response.status} veya Hata", detay
        
    except Exception as e:
        detay = {"hata_kodu": 0, "kategori": "HTTP Bağlantı Hatası", "aciklama": str(e)}
        return False, None, "HTTP veya Hata", detay
    finally:
        try:
            conn.close() #kapatmazsak ram dolup sistem çöker unutma
        except:
            pass



def check_port(ip_address, port, protocol="TCP", timeout=1): #timeout 21 sn den büyük olsaydı 10060 gibi hatları alırdık

    start_time = time.time()
#TCP SENERYOSU
    try:
        if protocol.upper() == "TCP":
            # AF_INET = IPv4 ailesi, SOCK_STREAM = TCP protokolü
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip_address, port)) #connect de bağlanamazsa exception fırlatır program patlar.
            sock.close()# İşimiz bitince suncu iel bağlantıyı kapattık (RAM dolmasın diye)
            #connect_ex kullandık ki bağlanamadığında hata kodu dönsün
            # Sadece açık mı? demiyoruz, neden kapalı diye işletim sistemine soruyoruz.
            if result == 0:#hata yoksa
                latency_ms = (time.time() - start_time) * 1000
                return True, round(latency_ms, 2), "AÇIK", None
            else:
                detay = _hata_detayi_olustur(result)
                return False, None, f"{detay['kategori']}", detay
            
         #UDP SENARYOSU
        elif protocol.upper() == "UDP":
            # SOCK_DGRAM = UDP protokolü
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 

            # Amaç: UDP'nin bağlantısız doğasını, zaman aşımı yönetimiyle daha güvenilir
            # bir yoklama mekanizmasına dönüştürmek. Paketi gönderdikten sonra ICMP hatası bekleriz.
            sock.settimeout(2.0)
            try:#TCP'deki gibi connect yapamayız çünkü UDP bağlantısızdır bu yzden bos veri gönderiyoruz
                sock.sendto(b'\x00', (ip_address, port))
                # Hata dönüp dönmediğini dinle 
                sock.recvfrom(1024)#sento ile fraltılan paketi takip et dinle ıcmp hatası buradan
                latency_ms = (time.time() - start_time) * 1000
                return True, round(latency_ms, 2), "Durum Belirsiz (UDP doğası gereği kesin yanıt dönmez. Port açık veya güvenlik duvarı tarafından filtrelenmiş olabilir.)", None
            except socket.timeout:
                # 2 saniye bekledik ses gelmedi. UDP'de sessizlik genelde 'Port açık ama 
                # sana cevap vermiyo veya Firewalla takıldı demektir.
                latency_ms = (time.time() - start_time) * 1000
                return True, round(latency_ms, 2), "Durum Belirsiz (UDP doğası gereği kesin yanıt dönmez. Port açık veya güvenlik duvarı tarafından filtrelenmiş olabilir.)", None
            except ConnectionResetError:
                # ICMP Port ulaşılamadı hatası
                detay = _hata_detayi_olustur(10061)
                return False, None, "Servis Kapalı (Port Reddedildi)", detay
            except OSError as e:
                detay = _hata_detayi_olustur(e.errno or 0)
                return False, None, f"UDP Hatası: {detay['kategori']}", detay
            except Exception as e:
                return False, None, f"UDP Hatası: {str(e)}", {"hata_kodu": 0, "kategori": "Beklenmeyen Hata", "aciklama": str(e)}
            finally:
                sock.close()
         #Eğer port 80 veya 443 ise otomatik bu fonksiyon çalışsın dedik
        elif protocol.upper() == "HTTP":
            return check_http(ip_address, port, timeout)
    
    #GENEL HATA YAKALAYICILAR
    except socket.timeout:
        detay = _hata_detayi_olustur(10060)
        return False, None, "Zaman Aşımı", detay
    except socket.gaierror as e:
        # DNS çözümleme hatası -ıp yerine site ismi girilirse sistem çökmez 
        detay = {"hata_kodu": -1, "kategori": "DNS Hatası", "aciklama": f"Hostname çözümlenemedi: {ip_address}. DNS sunucusu erişilemez veya hostname geçersiz."}
        return False, None, "DNS Çözümleme Hatası", detay
    except OSError as e:
        detay = _hata_detayi_olustur(e.errno or 0)
        return False, None, f"Soket Hatası: {detay['kategori']}", detay
    except Exception as e:
        detay = {"hata_kodu": 0, "kategori": "Beklenmeyen Hata", "aciklama": str(e)}
        return False, None, f"Soket Hatası: {str(e)}", detay

    return False, None, "Bilinmeyen Durum", None


# MODÜL TESTİ GÜNCELLEMESİ
if __name__ == "__main__":
    print("=" * 60)
    print("  TCP/UDP PORT KONTROL MODÜlÜ — GENİŞLETİLMİŞ TEST")
    print("=" * 60)

    test_cases = [
        ("8.8.8.8", 53, "UDP", "Google DNS (UDP)"),
        ("google.com", 443, "TCP", "Google HTTPS (TCP)"),
        ("192.0.2.1", 80, "TCP", "TEST-NET (Ulaşılamaz)"),
        ("google.com", 12345, "TCP", "Google Kapalı Port"),
    ]

    for ip, port, proto, desc in test_cases:
        print(f"\n  Test: {desc}")
        is_open, latency, msg, detay = check_port(ip, port, protocol=proto, timeout=2)
        print(f"    Sonuç: {msg} ({latency if latency else '---'} ms)")
        if detay:
            print(f"    Hata Kodu : {detay['hata_kodu']}")
            print(f"    Kategori  : {detay['kategori']}")
            print(f"    Açıklama  : {detay['aciklama']}")

    print(f"\n{'=' * 60}")
    print("  Test tamamlandı.")
    print(f"{'=' * 60}")