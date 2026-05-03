"""
Aktif Bildirim Modülü (Alerter)
================================
Cihaz durumu değiştiğinde (AÇIK -> KAPALI) sistem yöneticisine
Gmail SMTP üzerinden otomatik e-posta uyarısı gönderir.

Özellikler:
- Cooldown mekanizması: Aynı cihaz için belirlenen sürede (varsayılan 5 dk) en fazla 1 bildirim
- Hata toleransı: Bildirim gönderilemezse sistemi çökertmez, sadece konsola loglar
- HTML formatlı e-posta: Hata detayı, cihaz bilgisi ve zaman damgası içerir
"""

import smtplib
import json
import os
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DOSYASI = os.path.join(BASE_DIR, "config", "alert_config.json")


class AlertManager:
    """
    E-posta Bildirim Yöneticisi.

    Ağ izleme sistemi bir cihazın koptuğunu tespit ettiğinde,
    bu sınıf aracılığıyla sistem yöneticisine e-posta bildirimi gönderilir.
    Cooldown mekanizması sayesinde aynı cihaz için tekrar tekrar bildirim gönderilmesi engellenir.
    """

    def __init__(self, config_path=None):
        self.config_path = config_path or CONFIG_DOSYASI
        self.config = self._config_yukle()

        # Cooldown Takip Sözlüğü
        # Amaç: Her cihaz için son bildirim zamanını tutarak spam'i önlemek.
        # Yapı: {"cihaz_adı": son_bildirim_timestamp}
        self.son_bildirim_zamanlari = {}

        # Gönderilmiş bildirim geçmişi (Dashboard'da göstermek için)
        self.bildirim_gecmisi = []

    def _config_yukle(self):
        """Config dosyasını okur. Dosya yoksa veya hatalıysa varsayılan döner."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"  [ALERTER HATA] Config dosyası okunamadı: {e}")
        return {"email": {"aktif": False}, "cooldown_dakika": 5}

    def config_guncelle(self, yeni_config):
        """Config dosyasını günceller (Dashboard'dan ayar değiştirildiğinde)."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(yeni_config, f, indent=2, ensure_ascii=False)
            self.config = yeni_config
            print("  [ALERTER] Config güncellendi.")
            return True
        except Exception as e:
            print(f"  [ALERTER HATA] Config yazılamadı: {e}")
            return False

    def _cooldown_kontrol(self, hedef_adi):
        """
        Cooldown Mekanizması (Spam Önleme Algoritması)
        ================================================
        Amaç: Bir cihaz sürekli düşüp kalkıyorsa (flapping), her seferinde
        bildirim göndermek yerine belirli bir süre beklemek.

        Mantık: Son bildirimden bu yana geçen süre < cooldown süresi ise
        bildirimi göndermez.
        """
        simdi = time.time()
        cooldown_saniye = self.config.get("cooldown_dakika", 5) * 60

        if hedef_adi in self.son_bildirim_zamanlari:
            gecen_sure = simdi - self.son_bildirim_zamanlari[hedef_adi]
            if gecen_sure < cooldown_saniye:
                kalan = int(cooldown_saniye - gecen_sure)
                print(f"  [ALERTER] Cooldown aktif: {hedef_adi} için {kalan}sn kaldı. Bildirim engellendi.")
                return False

        return True

    def email_gonder(self, konu, icerik_html):
        """
        Gmail SMTP ile E-posta Gönderimi
        ==================================
        SMTP (Simple Mail Transfer Protocol) kullanarak Gmail sunucuları
        üzerinden e-posta gönderir.

        Bağlantı Akışı:
        1. SMTP sunucusuna bağlan (smtp.gmail.com:587)
        2. STARTTLS ile şifreli bağlantıya yükselt (TLS Handshake)
        3. Kullanıcı adı ve uygulama şifresiyle kimlik doğrula
        4. E-postayı gönder
        5. Bağlantıyı kapat

        Not: Gmail'de normal şifre değil, 'Uygulama Şifresi' gereklidir.
        Google Hesap > Güvenlik > 2 Adımlı Doğrulama > Uygulama Şifreleri
        """
        email_config = self.config.get("email", {})

        if not email_config.get("aktif", False):
            print("  [ALERTER] E-posta bildirimi devre dışı.")
            return False

        # Gerekli alanların dolu olup olmadığını kontrol et
        gerekli_alanlar = ["gonderen_email", "gonderen_sifre", "alici_email"]
        for alan in gerekli_alanlar:
            if not email_config.get(alan):
                print(f"  [ALERTER HATA] E-posta ayarı eksik: {alan}")
                return False

        try:
            # MIME (Multipurpose Internet Mail Extensions) mesajı oluştur
            # HTML formatında zengin içerikli e-posta göndermemizi sağlar
            mesaj = MIMEMultipart("alternative")
            mesaj["From"] = email_config["gonderen_email"]
            mesaj["To"] = email_config["alici_email"]
            mesaj["Subject"] = konu

            # HTML gövde
            html_kisim = MIMEText(icerik_html, "html", "utf-8")
            mesaj.attach(html_kisim)

            # SMTP Bağlantısı (TLS ile güvenli)
            sunucu = smtplib.SMTP(
                email_config.get("smtp_sunucu", "smtp.gmail.com"),
                email_config.get("smtp_port", 587)
            )
            sunucu.ehlo()       # Sunucuya kendimizi tanıtıyoruz (ESMTP protokolü)
            sunucu.starttls()   # Bağlantıyı TLS ile şifreliyoruz
            sunucu.ehlo()       # TLS sonrası tekrar tanıtım

            # Kimlik doğrulama
            sunucu.login(email_config["gonderen_email"], email_config["gonderen_sifre"])

            # E-postayı gönder
            sunucu.sendmail(
                email_config["gonderen_email"],
                email_config["alici_email"],
                mesaj.as_string()
            )
            sunucu.quit()

            print(f"  [ALERTER OK] E-posta gonderildi -> {email_config['alici_email']}")
            return True

        except smtplib.SMTPAuthenticationError:
            print("  [ALERTER HATA] Gmail kimlik doğrulama hatası! Uygulama şifresini kontrol edin.")
            return False
        except smtplib.SMTPConnectError:
            print("  [ALERTER HATA] SMTP sunucusuna bağlanılamadı! İnternet bağlantısını kontrol edin.")
            return False
        except smtplib.SMTPRecipientsRefused:
            print("  [ALERTER HATA] Alıcı e-posta adresi reddedildi!")
            return False
        except Exception as e:
            print(f"  [ALERTER HATA] E-posta gönderim hatası: {e}")
            return False

    def _html_sablonu_olustur(self, hedef_adi, ip, port, eski_durum, yeni_durum, hata_detayi):
        """
        HTML E-posta Şablonu Oluşturucu
        =================================
        Profesyonel görünümlü, koyu temalı bir HTML e-posta şablonu oluşturur.
        """
        zaman = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        # Hata detayını formatlama
        hata_html = ""
        if hata_detayi:
            hata_html = f"""
            <tr>
                <td style="padding: 10px; color: #94a3b8; border-bottom: 1px solid #334155;">Hata Sebebi</td>
                <td style="padding: 10px; color: #ef4444; font-weight: 600; border-bottom: 1px solid #334155;">
                    {hata_detayi.get('kategori', 'Bilinmiyor')}
                </td>
            </tr>
            <tr>
                <td style="padding: 10px; color: #94a3b8; border-bottom: 1px solid #334155;">Detaylı Açıklama</td>
                <td style="padding: 10px; color: #cbd5e1; border-bottom: 1px solid #334155;">
                    {hata_detayi.get('aciklama', 'Detay yok')}
                </td>
            </tr>
            <tr>
                <td style="padding: 10px; color: #94a3b8;">Hata Kodu</td>
                <td style="padding: 10px; color: #f59e0b; font-family: monospace;">
                    {hata_detayi.get('hata_kodu', 'N/A')}
                </td>
            </tr>"""

        return f"""
        <html>
        <body style="background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Arial, sans-serif; padding: 30px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; overflow: hidden; border: 1px solid #334155;">

                <!-- Başlık Bandı -->
                <div style="background: linear-gradient(135deg, #dc2626, #991b1b); padding: 20px 30px;">
                    <h1 style="margin: 0; font-size: 1.4rem; color: white;">🚨 Ağ Uyarısı — Cihaz Koptu!</h1>
                </div>

                <!-- İçerik -->
                <div style="padding: 25px 30px;">
                    <p style="color: #94a3b8; margin-bottom: 20px;">
                        İzleme sistemi bir cihazın erişilemez olduğunu tespit etti:
                    </p>

                    <table style="width: 100%; border-collapse: collapse; background-color: #0f172a; border-radius: 8px; overflow: hidden;">
                        <tr>
                            <td style="padding: 10px; color: #94a3b8; border-bottom: 1px solid #334155;">Cihaz Adı</td>
                            <td style="padding: 10px; color: #f8fafc; font-weight: 600; border-bottom: 1px solid #334155;">{hedef_adi}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; color: #94a3b8; border-bottom: 1px solid #334155;">IP Adresi</td>
                            <td style="padding: 10px; color: #3b82f6; font-family: monospace; border-bottom: 1px solid #334155;">{ip}:{port}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; color: #94a3b8; border-bottom: 1px solid #334155;">Önceki Durum</td>
                            <td style="padding: 10px; color: #10b981; border-bottom: 1px solid #334155;">✅ {eski_durum}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; color: #94a3b8; border-bottom: 1px solid #334155;">Yeni Durum</td>
                            <td style="padding: 10px; color: #ef4444; font-weight: 600; border-bottom: 1px solid #334155;">❌ {yeni_durum}</td>
                        </tr>
                        {hata_html}
                        <tr>
                            <td style="padding: 10px; color: #94a3b8;">Tespit Zamanı</td>
                            <td style="padding: 10px; color: #f8fafc;">{zaman}</td>
                        </tr>
                    </table>

                    <p style="color: #64748b; font-size: 0.85rem; margin-top: 20px; text-align: center;">
                        Bu e-posta Ağ Durum İzleme Sistemi tarafından otomatik olarak gönderilmiştir.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def bildirim_gonder(self, hedef_adi, ip, port, eski_durum, yeni_durum, hata_detayi=None):
        """
        Ana Bildirim Gönderme Fonksiyonu
        ==================================
        Bu fonksiyon main_monitor.py tarafından çağrılır.
        Cooldown kontrolü yapar, e-postayı hazırlar ve gönderir.

        Args:
            hedef_adi (str): Cihazın adı (ör: "Web Server")
            ip (str): Cihazın IP adresi
            port (int): Kontrol edilen port
            eski_durum (str): Önceki durum (genellikle "AÇIK")
            yeni_durum (str): Yeni durum (ör: "KAPALI", "Zaman Aşımı")
            hata_detayi (dict): Detaylı hata bilgisi (ör: {"hata_kodu": 10061, "kategori": "...", "aciklama": "..."})
        """
        # 1. Config'i yeniden yükle (Dashboard'dan değiştirilmiş olabilir)
        self.config = self._config_yukle()

        # 2. E-posta aktif mi kontrol et
        if not self.config.get("email", {}).get("aktif", False):
            return

        # 3. Cooldown kontrolü
        if not self._cooldown_kontrol(hedef_adi):
            return

        # 4. E-posta içeriğini hazırla
        konu = f"🚨 AĞ UYARISI: {hedef_adi} ({ip}) — {yeni_durum}"
        html_icerik = self._html_sablonu_olustur(
            hedef_adi, ip, port, eski_durum, yeni_durum, hata_detayi
        )

        # 5. Gönder
        basarili = self.email_gonder(konu, html_icerik)

        # 6. Cooldown zamanını güncelle
        if basarili:
            self.son_bildirim_zamanlari[hedef_adi] = time.time()

            # Bildirim geçmişine ekle
            self.bildirim_gecmisi.insert(0, {
                "zaman": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "hedef": hedef_adi,
                "ip": ip,
                "durum": yeni_durum,
                "basarili": True
            })
            # Geçmişi 50 kayıtla sınırla
            self.bildirim_gecmisi = self.bildirim_gecmisi[:50]


# --- MODÜL TESTİ ---
if __name__ == "__main__":
    print("=" * 50)
    print("  ALERTER MODÜL TESTİ")
    print("=" * 50)

    manager = AlertManager()
    config = manager.config

    print(f"\n  Config yüklendi:")
    print(f"    E-posta aktif: {config.get('email', {}).get('aktif', False)}")
    print(f"    Cooldown: {config.get('cooldown_dakika', 5)} dakika")

    # Test bildirimi gönder
    print("\n  Test bildirimi gönderiliyor...")
    manager.bildirim_gonder(
        hedef_adi="Test Sunucu",
        ip="192.168.1.100",
        port=80,
        eski_durum="AÇIK",
        yeni_durum="KAPALI (Zaman Aşımı)",
        hata_detayi={
            "hata_kodu": 10060,
            "kategori": "Zaman Aşımı",
            "aciklama": "Belirtilen süre içinde yanıt alınamadı"
        }
    )
    print("\n  Test tamamlandı.")
