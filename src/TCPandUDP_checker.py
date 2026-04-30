import socket
import time
import errno

def check_port(ip_address, port, protocol="TCP", timeout=1):
    """
    Verilen IP adresi ve port'a belirtilen protokolle bağlantı dener.

    Args:
        protocol (str): "TCP" veya "UDP" (varsayılan="TCP")
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
            # Amaç: Sistemin sadece 'çalışıp çalışmadığını' değil, 'neden çalışmadığını' işletim sistemi seviyesinde teşhis etmek.
            if result == 0:
                latency_ms = (time.time() - start_time) * 1000
                return True, round(latency_ms, 2), "AÇIK"
            elif result == errno.ECONNREFUSED or result == 10061: # Windows WSAECONNREFUSED
                return False, None, "Servis Kapalı (Port Reddedildi)"
            elif result == errno.ETIMEDOUT or result == 10060: # Windows WSAETIMEDOUT
                return False, None, "Zaman Aşımı"
            else:
                return False, None, f"Hata Kodu: {result}"

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
                return True, round(latency_ms, 2), "AÇIK"
            except socket.timeout:
                # Timeout olması, UDP'de portun açık veya filtrelenmiş olduğunu gösterir.
                latency_ms = (time.time() - start_time) * 1000
                return True, round(latency_ms, 2), "AÇIK"
            except ConnectionResetError:
                # ICMP Port Unreachable hatası
                return False, None, "Servis Kapalı (Port Reddedildi)"
            except Exception as e:
                return False, None, f"UDP Hatası: {str(e)}"
            finally:
                sock.close()

    except (socket.timeout, socket.error) as e:
        return False, None, f"Soket Hatası: {str(e)}"
    
    return False, None, "Bilinmeyen Durum"


# MODÜL TESTİ GÜNCELLEMESİ
if __name__ == "__main__":
    # Test senaryolarına UDP örneği ekleyelim
    test_cases = [
        ("8.8.8.8", 53, "UDP", "Google DNS (UDP)"),  # DNS protokolü için en doğrusu
        ("google.com", 443, "TCP", "Google HTTPS (TCP)"),
    ]

    for ip, port, proto, desc in test_cases:
        is_open, latency, msg = check_port(ip, port, protocol=proto)
        print(f"{desc} -> {msg} ({latency if latency else '---'} ms)")