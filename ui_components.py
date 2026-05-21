import streamlit as st
from datetime import datetime
from config import ROSKACHESTVO_RED, LOGO_PATH

def apply_custom_css():
    st.markdown(f"""
        <style>
        /* --- General Responsiveness --- */
        [data-testid="stMetricValue"] {{
            font-size: 1.8rem !important;
        }}
        
        /* --- Custom Header --- */
        .ros-header {{
            background-color: {ROSKACHESTVO_RED};
            padding: 10px 20px;
            border-radius: 10px;
            color: white;
            margin-bottom: 25px;
            display: flex;
            flex-direction: row;
            align-items: center;
            justify-content: space-between;
        }}

        .funding-badge {{
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 14px;
            font-weight: bold;
            color: white;
            display: inline-block;
            margin-bottom: 15px;
        }}
        .badge-budget {{ background-color: #2E5BFF; }}
        .badge-extra {{ background-color: #FF8A00; }}

        /* --- KPI Cards Grid-like behavior via CSS --- */
        .kpi-card {{
            background-color: var(--background-color);
            padding: 20px; 
            border-radius: 10px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            border-left: 5px solid {ROSKACHESTVO_RED}; 
            min-height: 100px;
            border: 1px solid var(--secondary-background-color);
            margin-bottom: 10px;
        }}

        /* --- MOBILE ADAPTATION (max-width: 768px) --- */
        @media (max-width: 768px) {{
            .ros-header {{
                flex-direction: column;
                text-align: center;
                gap: 10px;
            }}
            .ros-header div {{
                border-left: none !important;
                margin-left: 0 !important;
                padding-left: 0 !important;
            }}
            .kpi-card {{
                padding: 15px;
                min-height: 80px;
            }}
            h1, h2, h3 {{
                font-size: 1.2rem !important;
            }}
            [data-testid="column"] {{
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }}
        }}

        .tooltip-icon {{
            cursor: help;
            color: #888;
            font-size: 12px;
            margin-left: 5px;
        }}
        </style>
        """, unsafe_allow_html=True)

def render_header(current_period):
    import os
    import base64
    
    logo_html = ""
    if os.path.exists(LOGO_PATH):
        try:
            with open(LOGO_PATH, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
                logo_html = f'<img src="data:image/jpg;base64,{data}" style="height: 50px; margin-right: 20px;">'
        except Exception as e:
            st.error(f"Ошибка загрузки логотипа: {e}")
    else:
        # Debug info for the user if the file is missing in the repository
        st.warning(f"Файл логотипа '{LOGO_PATH}' не найден. Убедитесь, что он загружен на GitHub.")

    st.markdown(f"""
        <div class="ros-header">
            <div style="display: flex; align-items: center; flex-wrap: wrap;">
                {logo_html}
                <div style="font-size: 22px; font-weight: bold; white-space: nowrap; color: white;">РОСКАЧЕСТВО</div>
                <div style="margin-left: 20px; font-size: 16px; border-left: 1px solid white; padding-left: 20px; color: white;" class="header-subtitle">
                    Аналитическая панель
                </div>
            </div>
            <div style="font-size: 13px; text-align: right; color: white;" class="header-info">
                <div>Период: {current_period}</div>
                <div style="opacity: 0.8; font-size: 11px;">{datetime.now().strftime('%d.%m.%Y')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_funding_type(direction_name, mapping):
    f_type = mapping.get(direction_name, "Не указано")
    badge_class = "badge-budget" if f_type == "Бюджет" else "badge-extra"
    st.markdown(f'<div class="funding-badge {badge_class}">{f_type}</div>', unsafe_allow_html=True)

def render_kpi_card(label, value, delta, delta_pct, tooltip=""):
    delta_color = "green" if delta >= 0 else "red"
    tooltip_html = f'<span class="tooltip-icon" title="{tooltip}">ℹ️</span>' if tooltip else ""
    
    st.markdown(f"""
        <div class="kpi-card">
            <div style="color: var(--text-color); font-size: 13px; margin-bottom: 5px; font-weight: 500;">
                {label} {tooltip_html}
            </div>
            <div style="font-size: 24px; font-weight: bold; color: var(--text-color); line-height: 1.2;">
                {value:,.0f}
            </div>
            <div style="color: {delta_color}; font-size: 12px; margin-top: 5px;">
                {delta:+,.0f} ({delta_pct:+.1f}%)
            </div>
        </div>
    """, unsafe_allow_html=True)

def footer():
    st.markdown("""
    <div style="text-align: center; color: #888; margin-top: 30px; font-size: 11px; padding: 20px;">
        2026 Роскачество
    </div>
    """, unsafe_allow_html=True)
