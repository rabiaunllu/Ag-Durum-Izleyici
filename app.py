import streamlit as st
import pandas as pd
import json
import os
import sys
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# src dizinini python yoluna ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
import logger

# Dosya yolları
TARGETS_FILE = os.path.join(os.path.dirname(__file__), "config", "targets.json")

# Sayfa Yapılandırması
st.set_page_config(page_title="Ağ İzleme Sistemi", layout="wide", initial_sidebar_state="collapsed")

# --- SESSION STATE INITIALIZATION ---
if 'settings_interval' not in st.session_state:
    st.session_state.settings_interval = 5
if 'settings_max_logs' not in st.session_state:
    st.session_state.settings_max_logs = 5000
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'filter_status' not in st.session_state:
    st.session_state.filter_status = "Tümü"
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = []
if 'is_monitoring' not in st.session_state:
    st.session_state.is_monitoring = True
if 'previous_status' not in st.session_state:
    st.session_state.previous_status = {}

# Her döngüde dialog durumunu sıfırla. Dialog açıkken içindeki kod bu değeri True yapacak.
st.session_state.dialog_active = False

# Custom CSS (React/Figma Inspired)
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    .stApp {{
        background: radial-gradient(circle at top left, #1e293b, #0f172a);
        color: #f8fafc;
    }}

    /* Üst İstatistik Kartları */
    .metric-card {{
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid rgba(51, 65, 85, 0.5);
        transition: transform 0.2s;
    }}
    .metric-card:hover {{
        transform: translateY(-2px);
        border-color: rgba(59, 130, 246, 0.5);
    }}
    .metric-title {{
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .metric-value {{
        font-size: 2.2rem;
        font-weight: 700;
        color: #f8fafc;
    }}

    /* İzlenen Hedefler Kartları */
    .target-card {{
        background: rgba(30, 41, 59, 0.5);
        backdrop-filter: blur(8px);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        border: 1px solid rgba(51, 65, 85, 0.5);
        position: relative;
        overflow: hidden;
    }}
    .target-card::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: var(--status-color, #334155);
    }}
    .target-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 15px;
    }}
    .target-name {{
        font-weight: 600;
        font-size: 1.15rem;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .target-ip {{
        color: #94a3b8;
        font-size: 0.85rem;
        margin-top: 2px;
    }}
    .status-row {{
        display: flex;
        justify-content: space-between;
        margin-bottom: 10px;
        font-size: 0.9rem;
        color: #cbd5e1;
    }}
    .status-badge {{
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }}
    .badge-up {{ background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }}
    .badge-down {{ background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }}
    
    .status-info {{ color: #3b82f6; font-weight: 600; }}

    /* Header */
    .main-header {{
        margin-bottom: 35px;
    }}
    .header-title {{
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(to right, #f8fafc, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    .header-subtitle {{
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 5px 0 0 0;
    }}

    /* Search and Filter Container */
    .filter-container {{
        background: rgba(30, 41, 59, 0.4);
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(51, 65, 85, 0.5);
        margin-bottom: 25px;
    }}

    /* Buttons Style Override */
    .stButton>button {{
        border-radius: 8px !important;
        font-weight: 500 !important;
    }}

    /* Performans Analizi Bölümü */
    .perf-container {{
        background: rgba(30, 41, 59, 0.4);
        padding: 25px;
        border-radius: 16px;
        border: 1px solid rgba(51, 65, 85, 0.5);
        margin-top: 40px;
        margin-bottom: 40px;
    }}
    .chart-container {{
        background: rgba(15, 23, 42, 0.5);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid rgba(51, 65, 85, 0.3);
    }}
    .chart-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }}
    .chart-title {{
        font-weight: 600;
        font-size: 1.1rem;
        color: #f8fafc;
    }}
    .chart-avg {{
        font-size: 0.9rem;
        color: #3b82f6;
    }}
    .perf-metric-mini {{
        background: rgba(30, 41, 59, 0.5);
        padding: 12px;
        border-radius: 8px;
        border: 1px solid rgba(51, 65, 85, 0.3);
    }}
    .perf-metric-label {{
        font-size: 0.75rem;
        color: #94a3b8;
        margin-bottom: 4px;
    }}
    .perf-metric-val {{
        font-size: 1rem;
        font-weight: 600;
        color: #f8fafc;
    }}

    /* Kart Butonları */
    .card-btn-container {{
        display: flex;
        gap: 8px;
        margin-top: 15px;
    }}
    
    /* Trash icon positioning */
    .trash-btn {{
        position: absolute;
        top: 10px;
        right: 10px;
        z-index: 100;
    }}
</style>
""", unsafe_allow_html=True)

# --- MODALS (st.dialog) ---

@st.dialog("📚 Ağ ve Hata Kodları Sözlüğü")
def dictionary_dialog():
    st.session_state.dialog_active = True
    st.markdown("""
| Kod | Durum | Açıklama |
| :--- | :--- | :--- |
| **0** | Bağlantı Başarılı | Port açık, servis çalışıyor. |
| **10061** | Port Reddedildi | Sunucu açık ama o portta servis yok. |
| **10060** | Zaman Aşımı | Pakete cevap gelmedi, paket yolda kayboldu. |
| **10035** | Güvenlik Duvarı | Firewall paketi sessizce düşürdü (Stealth Drop). |
| **10065** | Hedefe Ulaşılamıyor | Ağ rotası yok, cihaz tamamen erişilemez. |
| **10064** | Host Çöktü | Cihaz bağlantı sırasında kapandı. |
""")
    if st.button("Kapat", use_container_width=True):
        st.rerun()


@st.dialog("Hedef Ekle")
def add_target_dialog():
    st.session_state.dialog_active = True
    with st.form("add_target_form_dialog"):
        st.write("İzlemek istediğiniz yeni cihaz bilgilerini girin.")
        new_name = st.text_input("Hedef Adı", placeholder="örn: Web Server")
        new_ip = st.text_input("IP Adresi", placeholder="örn: 192.168.1.100")
        new_port = st.number_input("Port Numarası", min_value=1, max_value=65535, value=80)
        
        control_type = st.selectbox("Kontrol Tipi", 
                                    options=["ICMP + TCP (İkisi de)", "Sadece ICMP Ping", "Sadece TCP Port"])
        
        submitted = st.form_submit_button("➕ Listeye Ekle", use_container_width=True)
        if submitted:
            if new_name and new_ip:
                targets = load_targets()
                targets.append({
                    "ip": new_ip, 
                    "port": int(new_port), 
                    "name": new_name,
                    "control_type": control_type
                })
                save_targets(targets)
                st.success(f"{new_name} eklendi!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Lütfen tüm alanları doldurun.")

@st.dialog("Sistem Ayarları")
def settings_dialog():
    st.session_state.dialog_active = True
    st.write("İzleme sistemi parametrelerini yapılandırın.")
    
    new_interval = st.select_slider(
        "Kontrol Aralığı (Saniye)",
        options=[3, 5, 10, 30, 60],
        value=st.session_state.settings_interval
    )
    
    new_max_logs = st.number_input(
        "Maksimum Log Sayısı",
        min_value=10,
        max_value=50000,
        value=st.session_state.settings_max_logs
    )
    
    if st.button("Kaydet", use_container_width=True):
        st.session_state.settings_interval = new_interval
        st.session_state.settings_max_logs = new_max_logs
        logger.maksimum_kayit_ayarla(new_max_logs)
        st.success("Ayarlar uygulandı!")
        time.sleep(1)
        st.rerun()

@st.dialog("Hedefi Kaldır")
def confirm_remove_dialog(ip, port, name):
    st.session_state.dialog_active = True
    st.warning(f"**{name}** ({ip}:{port}) hedefini izleme listesinden kaldırmak istediğinize emin misiniz?")
    st.write("Bu işlem geri alınamaz.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Evet, Kaldır", type="primary", use_container_width=True):
            remove_target(ip, port)
            st.success(f"{name} kaldırıldı.")
            time.sleep(1)
            st.rerun()
    with col2:
        if st.button("İptal", use_container_width=True):
            st.rerun()

@st.dialog("Logları Temizle")
def confirm_clear_logs_dialog():
    st.session_state.dialog_active = True
    st.warning("Tüm sistem loglarını silmek istediğinize emin misiniz?")
    st.write("Bu işlem tüm geçmiş kayıtları kalıcı olarak silecektir.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Evet, Temizle", type="primary", use_container_width=True):
            clear_logs()
            st.success("Loglar temizlendi.")
            time.sleep(1)
            st.rerun()
    with col2:
        if st.button("İptal", use_container_width=True):
            st.rerun()

# --- YARDIMCI FONKSİYONLAR ---

def load_targets():
    if os.path.exists(TARGETS_FILE):
        try:
            with open(TARGETS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_targets(targets):
    os.makedirs(os.path.dirname(TARGETS_FILE), exist_ok=True)
    with open(TARGETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(targets, f, indent=2, ensure_ascii=False)

def remove_target(ip, port):
    targets = load_targets()
    new_targets = [t for t in targets if not (t['ip'] == ip and t['port'] == port)]
    save_targets(new_targets)


def clear_logs():
    with open(logger.LOG_DOSYASI, 'w', encoding='utf-8') as f:
        json.dump([], f)

# Veri Güncelleme (Sadece JSON'dan Oku)
def get_latest_status():
    targets = load_targets()
    # Son 500 kaydı alıp hedeflere göre en günceli buluyoruz
    log_data = logger.son_kayitlari_getir(500)
    latest_logs = {}

    for entry in log_data:
        key = (entry.get('hedef_ip'), entry.get('hedef_adi'))
        if key not in latest_logs:
            latest_logs[key] = entry

    results = []
    for t in targets:
        ip = t.get("ip")
        port = t.get("port")
        name = t.get("name")
        control_type = t.get("control_type", "ICMP + TCP")
        
        device_logs = [log for log in log_data if log.get('hedef_ip') == ip and log.get('hedef_adi') == name]
        total_logs = len(device_logs)
        if total_logs > 0:
            open_logs = sum(1 for log in device_logs if log.get('durum') == "AÇIK")
            uptime_pct = (open_logs / total_logs) * 100
            uptime_str = f"%{uptime_pct:.1f}"
        else:
            uptime_str = "%0.0"

        log = latest_logs.get((ip, name))
        if log:
            durum = log.get("durum", "KAPALI")
            results.append({
                "name": name,
                "ip": ip,
                "port": port,
                "control_type": control_type,
                "uptime": uptime_str,
                "servis_durumu": "Başarılı" if durum == "AÇIK" else "Başarısız",
                "latency": f"{log.get('gecikme_ms')}ms" if log.get('gecikme_ms') is not None else "N/A",
                "last_check": log.get("tarih_saat").split(" ")[1] if log.get("tarih_saat") else "N/A",
                "status": "AÇIK" if durum == "AÇIK" else "KAPALI"
            })
        else:
            results.append({
                "name": name,
                "ip": ip,
                "port": port,
                "control_type": control_type,
                "uptime": uptime_str,
                "servis_durumu": "Bilinmiyor",
                "latency": "N/A",
                "last_check": "N/A",
                "status": "BILINMIYOR"
            })
    return results

st.session_state.scan_results = get_latest_status()
results = st.session_state.scan_results

# --- ALERTS / ERKEN UYARI ---
current_status = {}
for r in results:
    key = f"{r['ip']}:{r['port']}"
    current_status[key] = r['status']
    if key in st.session_state.previous_status:
        if st.session_state.previous_status[key] == "AÇIK" and r['status'] == "KAPALI":
            st.toast(f"⚠️ {r['name']} ({r['ip']}) bağlantısı koptu!", icon="🚨")
st.session_state.previous_status = current_status

# --- HEADER & ACTIONS ---
header_col1, header_col2 = st.columns([6, 4])
with header_col1:
    st.markdown('''
        <div class="main-header">
            <h1 class="header-title"> Ağ İzleme Sistemi</h1>
            <p class="header-subtitle">Gerçek Zamanlı Ağ ve Servis Durumu</p>
        </div>
    ''', unsafe_allow_html=True)

with header_col2:
    act_col1, act_col2, act_col3, act_col4 = st.columns(4)
    with act_col1:
        if st.button("ℹ️ Hata Kodları", use_container_width=True):
            dictionary_dialog()
    with act_col2:
        if st.button("⚙️ Ayarlar", use_container_width=True):
            settings_dialog()
    with act_col3:
        if st.button("➕ Hedef Ekle", use_container_width=True):
            add_target_dialog()
    with act_col4:
        monitor_color = "#10b981" if st.session_state.is_monitoring else "#ef4444"
        monitor_text = "📡 İzleme Aktif" if st.session_state.is_monitoring else "🚫 İzleme Durdu"
        if st.button(monitor_text, use_container_width=True):
            st.session_state.is_monitoring = not st.session_state.is_monitoring
            st.rerun()

# --- FILTER & SEARCH ---
st.markdown('<div class="filter-container">', unsafe_allow_html=True)
f_col1, f_col2 = st.columns([7, 3])
with f_col1:
    search_query = st.text_input("🔍 Ara", placeholder="IP adresi veya hedef adı ile ara...", label_visibility="collapsed", key="search_input_field")
    st.session_state.search_query = search_query
with f_col2:
    filter_status = st.segmented_control(
        "Filtrele",
        options=["Tümü", "Çevrimdışı", "Açık Portlar"],
        default="Tümü",
        label_visibility="collapsed"
    )
    st.session_state.filter_status = filter_status
st.markdown('</div>', unsafe_allow_html=True)

# Filtreleme Uygula
filtered_results = results
if st.session_state.search_query:
    q = st.session_state.search_query.lower()
    filtered_results = [r for r in filtered_results if q in r['name'].lower() or q in r['ip']]

if st.session_state.filter_status == "Çevrimdışı":
    filtered_results = [r for r in filtered_results if r['status'] == "KAPALI"]
elif st.session_state.filter_status == "Açık Portlar":
    filtered_results = [r for r in filtered_results if r['status'] == 'AÇIK' and 'TCP' in r['control_type']]

# --- STATS OVERVIEW ---
online_count = sum(1 for r in results if r['status'] == 'AÇIK')
offline_count = len(results) - online_count
open_ports_count = sum(1 for r in results if r['status'] == 'AÇIK' and 'TCP' in r['control_type'])

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Toplam Hedef</div><div class="metric-value">{len(results)}</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card" style="border-left: 4px solid #10b981;"><div class="metric-title">Çevrimiçi</div><div class="metric-value" style="color: #10b981;">{online_count}</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card" style="border-left: 4px solid #ef4444;"><div class="metric-title">Çevrimdışı</div><div class="metric-value" style="color: #ef4444;">{offline_count}</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card" style="border-left: 4px solid #8b5cf6;"><div class="metric-title">Açık Portlar</div><div class="metric-value" style="color: #8b5cf6;">{open_ports_count}</div></div>', unsafe_allow_html=True)

# --- TARGETS GRID ---
st.markdown(f"### İzlenen Hedefler ({len(filtered_results)} / {len(results)})")
if not filtered_results:
    st.info("Eşleşen hedef bulunamadı.")
else:
    cols = st.columns(3)
    all_logs = logger.son_kayitlari_getir(500)
    for i, r in enumerate(filtered_results):
        c = cols[i % 3]
        card_color = "#ef4444" if r['status'] == "KAPALI" else "#10b981"
        servis_badge = "badge-up" if r['status'] == "AÇIK" else "badge-down"
        
        with c:
            # Kart Başlığı ve Silme Butonu
            card_header_col1, card_header_col2 = st.columns([8, 2])
            with card_header_col1:
                st.markdown(f'<div style="font-weight: 600; font-size: 1.15rem; color: #f8fafc;">🖥️ {r["name"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="color: #94a3b8; font-size: 0.85rem;">{r["ip"]}:{r["port"]}</div>', unsafe_allow_html=True)
            with card_header_col2:
                if st.button("🗑️", key=f"rm_{r['ip']}_{r['port']}", help="Cihazı Kaldır"):
                    confirm_remove_dialog(r['ip'], r['port'], r['name'])

            # Durum Satırları
            st.markdown(f'''
            <div class="target-card" style="--status-color: {card_color}; margin-top: 10px;">
                <div class="status-row">
                    <span>Kontrol Tipi</span>
                    <span>{r['control_type']}</span>
                </div>
                <div class="status-row">
                    <span>Uptime (Erişilebilirlik)</span>
                    <span class="status-info">{r['uptime']}</span>
                </div>
                <div class="status-row" style="margin-top: 10px;">
                    <span>Sonuç</span>
                    <span class="status-badge {servis_badge}">{r['servis_durumu']}</span>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Aksiyon Butonları
            btn_col1, btn_col2 = st.columns(2)
            preview_key = f"preview_{r['ip']}_{r['port']}"
            if preview_key not in st.session_state:
                st.session_state[preview_key] = False
                
            with btn_col1:
                preview_label = "📈 Gizle" if st.session_state[preview_key] else "📈 Önizleme"
                if st.button(preview_label, key=f"btn_pre_{r['ip']}_{r['port']}", use_container_width=True):
                    st.session_state[preview_key] = not st.session_state[preview_key]
                    st.rerun()
            
            with btn_col2:
                if st.button("📊 Detaylı", key=f"btn_det_{r['ip']}_{r['port']}", use_container_width=True):
                    # Detaylı bölüme odaklanmak için session state'i güncelle
                    st.session_state.perf_target_select = f"{r['name']} ({r['ip']}:{r['port']})"
                    st.rerun()

            # Önizleme Grafikleri
            if st.session_state[preview_key]:
                st.markdown("---")
                # Bu cihazın son verilerini çek
                t_logs = [l for l in all_logs if l.get('hedef_ip') == r['ip'] and l.get('hedef_adi') == r['name']][:20]
                t_logs.reverse()
                if t_logs:
                    df_t = pd.DataFrame(t_logs)
                    st.markdown(f'<p style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 2px;">Ping Trend (ms)</p>', unsafe_allow_html=True)
                    st.line_chart(df_t[['gecikme_ms']], height=100, use_container_width=True)
                    st.markdown(f'<p style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 2px;">Paket Kaybı (%)</p>', unsafe_allow_html=True)
                    st.area_chart(df_t[['paket_kaybi']], height=80, use_container_width=True, color="#ef4444")
                else:
                    st.caption("Veri bulunamadı.")

# --- PERFORMANCE ANALYSIS SECTION ---
st.markdown('<div class="perf-container">', unsafe_allow_html=True)
perf_title_col, perf_select_col = st.columns([7, 3])

with perf_title_col:
    st.markdown('### 📉 Performans Geçmişi')

if not results:
    st.info("İzlenen hedef bulunmuyor.")
    st.markdown('</div>', unsafe_allow_html=True)
else:
    with perf_select_col:
        target_names = [f"{r['name']} ({r['ip']}:{r['port']})" for r in results]
        selected_target_str = st.selectbox("Analiz Edilecek Hedef", options=target_names, label_visibility="collapsed", key="perf_target_select")
        selected_idx = target_names.index(selected_target_str)
        selected_target = results[selected_idx]

    # Geçmiş verileri çek
    all_logs = logger.son_kayitlari_getir(1000)
    # Seçili hedefe göre filtrele
    target_logs = [l for l in all_logs if l.get('hedef_ip') == selected_target['ip'] and l.get('hedef_adi') == selected_target['name']]
    target_logs.reverse() # Grafik için eskiden yeniye

    if not target_logs:
        st.info("Bu hedef için yeterli veri bulunmuyor.")
    else:
        # Veriyi hazırla
        df_perf = pd.DataFrame(target_logs)
        df_perf['tarih_saat'] = pd.to_datetime(df_perf['tarih_saat'], format="%d-%m-%Y %H:%M:%S")
        
        avg_latency = df_perf['gecikme_ms'].mean()
        avg_loss = df_perf['paket_kaybi'].mean()

        p_col1, p_col2 = st.columns(2)
        
        with p_col1:
            st.markdown(f'''
            <div class="chart-header">
                <span class="chart-title">Ping Süresi (Latency)</span>
                <span class="chart-avg">Ort: {avg_latency:.1f}ms</span>
            </div>
            ''', unsafe_allow_html=True)
            # Latency Chart
            chart_data_lat = df_perf.set_index('tarih_saat')[['gecikme_ms']]
            st.line_chart(chart_data_lat, color="#3b82f6")
            st.markdown('<p style="color: #64748b; font-size: 0.8rem; margin-top: -10px;">Düşük gecikme daha iyidir</p>', unsafe_allow_html=True)

        with p_col2:
            st.markdown(f'''
            <div class="chart-header">
                <span class="chart-title">Paket Kaybı (Packet Loss)</span>
                <span class="chart-avg" style="color: #ef4444;">Ort: {avg_loss:.1f}%</span>
            </div>
            ''', unsafe_allow_html=True)
            # Loss Chart
            chart_data_loss = df_perf.set_index('tarih_saat')[['paket_kaybi']]
            st.area_chart(chart_data_loss, color="#ef4444")
            st.markdown('<p style="color: #64748b; font-size: 0.8rem; margin-top: -10px;">%0 kaybı ideal durumdur</p>', unsafe_allow_html=True)

        # Mini Metrics below charts
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.markdown(f'''
            <div class="perf-metric-mini">
                <div class="perf-metric-label">Mevcut Durum</div>
                <div class="perf-metric-val" style="color: {"#10b981" if selected_target['status'] == "AÇIK" else "#ef4444"};">{selected_target['status']}</div>
            </div>
            ''', unsafe_allow_html=True)
        with m_col2:
            st.markdown(f'''
            <div class="perf-metric-mini">
                <div class="perf-metric-label">Port Durumu</div>
                <div class="perf-metric-val">Port {selected_target['port']} - {selected_target['servis_durumu']}</div>
            </div>
            ''', unsafe_allow_html=True)
        with m_col3:
            st.markdown(f'''
            <div class="perf-metric-mini">
                <div class="perf-metric-label">Son Yanıt Süresi</div>
                <div class="perf-metric-val">{selected_target['latency']}</div>
            </div>
            ''', unsafe_allow_html=True)
        with m_col4:
            # Son paket kaybını loglardan al
            latest_loss = target_logs[-1].get('paket_kaybi', 0)
            st.markdown(f'''
            <div class="perf-metric-mini">
                <div class="perf-metric-label">Mevcut Paket Kaybı</div>
                <div class="perf-metric-val" style="color: {"#10b981" if latest_loss == 0 else "#ef4444"};">{latest_loss}%</div>
            </div>
            ''', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# --- LOGS SECTION ---
st.markdown("---")
l_col1, l_col2 = st.columns([8, 2])
with l_col1:
    st.markdown("### Sistem Logları")
with l_col2:
    log_data = logger.son_kayitlari_getir(st.session_state.settings_max_logs)
    log_df = pd.DataFrame(log_data)
    
    csv_col, clear_col = st.columns(2)
    with csv_col:
        csv = log_df.to_csv(index=False, sep=';').encode('utf-8-sig') if not log_df.empty else b""
        st.download_button("📥 CSV", data=csv, file_name="monitor_logs.csv", mime="text/csv", use_container_width=True)
    with clear_col:
        if st.button("🗑️ Temizle", use_container_width=True, key="clear_logs_btn"):
            confirm_clear_logs_dialog()

if not log_df.empty:
    display_df = log_df.rename(columns={
        "tarih_saat": "Tarih & Saat",
        "hedef_ip": "IP Adresi",
        "port": "Port",
        "hedef_adi": "Hedef Adı",
        "durum": "Durum",
        "gecikme_ms": "Gecikme (ms)",
        "paket_kaybi": "Paket Kaybı (%)"
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("Henüz log kaydı bulunmuyor.")

# --- OTO YENİLEME (En Sonda Çağrılır) ---
if st.session_state.is_monitoring and not st.session_state.dialog_active:
    st_autorefresh(interval=st.session_state.settings_interval * 1000, key="data_refresh")
