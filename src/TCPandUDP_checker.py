import socket
import time
import errno

# =============================================================================
# GENİŞLETİLMİŞ HATA KODU SÖZLÜĞÜ (Socket Error Code Dictionary)
# =============================================================================
# İşletim sistemi seviyesindeki soket hata kodlarını Türkçe teşhis mesajlarına çevirir.
# Windows (WSA*) ve Linux (errno) kodları birleştirilmiştir.
#
# Her bir anahtar bir hata kodu, değeri ise (kategori, açıklama) çiftidir.
# Kategori kısa bir etiket, açıklama ise sistem yöneticisine yönelik detaylı bilgidir.
# =============================================================================
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

    Returns:
        dict: {"hata_kodu": int, "kategori": str, "aciklama": str}
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


def check_port(ip_address, port, protocol="TCP", timeout=1):
    """
    Verilen IP adresi ve port'a belirtilen protokolle bağlantı dener.

    Args:
        ip_address (str): Hedef IP adresi veya hostname
        port (int): Hedef port numarası
        protocol (str): "TCP" veya "UDP" (varsayılan="TCP")
        timeout (int): Bağlantı zaman aşımı süresi (saniye)

    Returns:
        tuple: (port_acik_mi, gecikme_ms, durum_mesaji, hata_detayi)
            - port_acik_mi (bool): Port açık mı?
            - gecikme_ms (float|None): Yanıt süresi (ms) veya None
            - durum_mesaji (str): İnsan okunabilir durum mesajı
            - hata_detayi (dict|None): Yapılandırılmış hata bilgisi veya None
    """
    start_time = time.time()

    try:
        if protocol.upper() == "TCP":
            # AF_INET = IPv4 ailesi, SOCK_STREAM = TCP protokolü
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip_address, port))
            sock.close()

            # Hata Teşhis Algoritması (Socket Level Diagnostics)
            # Amaç: Sistemin sadece 'çalışıp çalışmadığını' değil, 'neden çalışmadığını'
            # işletim sistemi seviyesinde teşhis etmek.
            if result == 0:
                latency_ms = (time.time() - start_time) * 1000
                return True, round(latency_ms, 2), "AÇIK", None
            else:
                detay = _hata_detayi_olustur(result)
                return False, None, f"{detay['kategori']}", detay

        elif protocol.upper() == "UDP":
            # SOCK_DGRAM = UDP protokolü
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # UDP Probing ve Zaman Aşımı Yönetimi
            # Amaç: UDP'nin bağlantısız (unreliable) doğasını, zaman aşımı yönetimiyle daha güvenilir
            # bir 'yoklama' (probing) mekanizmasına dönüştürmek. Paketi gönderdikten sonra ICMP hatası bekleriz.
            sock.settimeout(2.0)
            try:
                # Sadece boş bir paket gönder ('gönder ve unut' yerine)
                sock.sendto(b'\x00', (ip_address, port))
                # Hata dönüp dönmediğini dinle (ICMP Destination Unreachable vb.)
                sock.recvfrom(1024)
                latency_ms = (time.time() - start_time) * 1000
                return True, round(latency_ms, 2), "AÇIK", None
            except socket.timeout:
                # Timeout olması, UDP'de portun açık veya filtrelenmiş olduğunu gösterir.
                latency_ms = (time.time() - start_time) * 1000
                return True, round(latency_ms, 2), "AÇIK (Filtrelenmiş)", None
            except ConnectionResetError:
                # ICMP Port Unreachable hatası
                detay = _hata_detayi_olustur(10061)
                return False, None, "Servis Kapalı (Port Reddedildi)", detay
            except OSError as e:
                detay = _hata_detayi_olustur(e.errno or 0)
                return False, None, f"UDP Hatası: {detay['kategori']}", detay
            except Exception as e:
                return False, None, f"UDP Hatası: {str(e)}", {"hata_kodu": 0, "kategori": "Beklenmeyen Hata", "aciklama": str(e)}
            finally:
                sock.close()

    except socket.timeout:
        detay = _hata_detayi_olustur(10060)
        return False, None, "Zaman Aşımı", detay
    except socket.gaierror as e:
        # DNS çözümleme hatası (getaddrinfo failed)
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