import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DOSYASI = os.path.abspath(os.path.join(BASE_DIR, "..", "logs", "monitor_log.json"))


def rapor_olustur():
    """JSON dosyasındaki verileri analiz eder."""
    if not os.path.exists(LOG_DOSYASI):
        print("[!] Veri dosyası bulunamadı.")
        return

    with open(LOG_DOSYASI, "r", encoding="utf-8") as f:
        kayitlar = json.load(f)

    if not kayitlar:
        print("[!] Henüz analiz edilecek veri yok.")
        return

    # Benzersiz cihaz isimlerini bul
    cihazlar = set(k["hedef_adi"] for k in kayitlar)

    print("\n" + "=" * 50)
    print("      AĞ ANALİZ RAPORU (JSON TABANLI)      ")
    print("=" * 50)
    print(f"{'Cihaz Adı':<15} | {'Erişilebilirlik':<15} | {'Ort. Gecikme':<12}")
    print("-" * 50)

    for cihaz in cihazlar:
        cihaz_kayitlari = [k for k in kayitlar if k["hedef_adi"] == cihaz]
        toplam = len(cihaz_kayitlari)
        aciklar = [k for k in cihaz_kayitlari if k["durum"] == "ACIK"]

        # Gecikme sürelerini topla (None olmayanları)
        gecikmeler = [k["gecikme_ms"] for k in aciklar if k["gecikme_ms"] is not None]

        uptime = (len(aciklar) / toplam) * 100
        ort_gecikme = sum(gecikmeler) / len(gecikmeler) if gecikmeler else 0

        gecikme_metni = f"{ort_gecikme:.2f} ms" if ort_gecikme > 0 else "---"
        print(f"{cihaz:<15} | %{uptime:<14.2f} | {gecikme_metni:<12}")

    print("=" * 50)


if __name__ == "__main__":
    rapor_olustur()