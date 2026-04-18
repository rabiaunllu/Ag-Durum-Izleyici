import socket
import time


def check_tcp_port(ip_address, port, timeout=1):
    """
    Verilen IP adresi ve port'a TCP bağlantısı dener.

    Args:
        ip_address (str): Hedef IP adresi veya hostname
        port (int): Hedef port numarası
        timeout (float): Bağlantı zaman aşımı süresi (saniye, varsayılan=1)

    Returns:
        tuple: (is_open: bool, latency_ms: float or None)
               - is_open: Bağlantı başarılıysa True, değilse False
               - latency_ms: Bağlantı süresi milisaniye cinsinden (başarısızsa None)
    """

    # Bağlantı denemesinin başlangıç zamanını kaydet (latency hesabı için)
    start_time = time.time()

    try:
        # AF_INET = IPv4 ailesi, SOCK_STREAM = TCP protokolü
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Belirtilen süre içinde bağlantı kurulamazsa zaman aşımı hatası fırlatılır
        sock.settimeout(timeout)

        # Hedefe bağlanmayı dene; 0 dönerse bağlantı başarılı, aksi hâlde hata kodu döner
        result = sock.connect_ex((ip_address, port))

        # Bağlantı denemesi bitti, bitiş zamanını kaydet
        end_time = time.time()

        # Soketi kapat, kaynakları serbest bırak
        sock.close()

        if result == 0:
            # Bağlantı başarılı → port açık
            # Geçen süreyi saniyeden milisaniyeye çevir ve 2 ondalık basamağa yuvarla
            latency_ms = (end_time - start_time) * 1000
            return True, round(latency_ms, 2)
        else:
            # connect_ex sıfır dışı bir hata kodu döndürdü → port kapalı
            return False, None

    except socket.timeout:
        # Bağlantı, timeout süresi dolmadan tamamlanamadı
        return False, None

    except socket.error as e:
        # Ağ erişim hatası, geçersiz adres vb. soket düzeyindeki diğer hatalar
        print(f"Soket hatası: {e}")
        return False, None


# ──────────────────────────────────────────
# MODÜL TESTİ
# ──────────────────────────────────────────
if __name__ == "__main__":

    # Test senaryoları: (ip/hostname, port, açıklama)
    # 1) Gerçek ve açık olması beklenen port
    # 2) Gerçek IP fakat kapalı port
    # 3) Erişilemeyen (yönlendirilemeyen) IP adresi
    # 4) Hostname ile HTTPS bağlantısı
    test_cases = [
        ("8.8.8.8",    53,   "Google DNS     - Açık port"),
        ("8.8.8.8",    9999, "Google DNS     - Kapalı port"),
        ("192.0.2.1",  80,   "Erişilemeyen IP (TEST-NET)"),
        ("google.com", 443,  "Google HTTPS   - Açık port"),
    ]

    print("=" * 60)
    print("TCP PORT CHECKER - TEST SONUÇLARI")
    print("=" * 60)

    for ip, port, description in test_cases:
        print(f"\nSenaryo : {description}")
        print(f"Hedef   : {ip}:{port}")

        # Fonksiyonu çağır; timeout=2 saniye olarak ayarlandı
        is_open, latency = check_tcp_port(ip, port, timeout=2)

        if is_open:
            # Port açıksa bağlantı süresini göster
            print(f"Durum   : ✅ AÇIK")
            print(f"Gecikme : {latency} ms")
        else:
            # Port kapalı veya host erişilemez
            print(f"Durum   : ❌ KAPALI / ERİŞİLEMEZ")
            print(f"Gecikme : Ölçülemedi")

    print("\n" + "=" * 60)
