import streamlit as st
import logging

# --- LOGGING CONFIG ---
logging.basicConfig(
    filename='dashboard.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- GOOGLE SHEETS CONFIG (SECURE VERSION) ---
# Try to get credentials from Streamlit Secrets (for Cloud)
# Fallback to hardcoded values for local development if secrets are not set
try:
    SHEET_ID = st.secrets["gsheets"]["sheet_id"]
    GID = st.secrets["gsheets"]["gid"]
except Exception:
    # Fallback for local run
    SHEET_ID = "1QTklm0AohB04VDul1ScIOiTPNYjmKeVp9GxeQsKVs1s"
    GID = "0"

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# --- VISUAL CONFIG ---
ROSKACHESTVO_RED = "#E30613"
LOGO_PATH = "logo.jpg"

# --- MAPPING ---
DIRECTION_TYPES = {
    "Платформа ДПО": "Внебюджет",
    "Исследования": "Бюджет",
    "Винный гид": "Внебюджет",
    "Веганство": "Внебюджет",
    "Сделано в регионах": "Внебюджет",
    "Академия": "Внебюджет",
    "ХАССП": "Внебюджет",
    "Туризм": "Внебюджет",
    "Функциональное питание": "Внебюджет",
    "Цифровая трансформация": "Бюджет",
    "Халяль": "Внебюджет",
    "Органика": "Внебюджет",
    "Пресс-служба": "Бюджет",
    "Соцмедиа": "Бюджет",
    "СМИ1": "Внебюджет",
    "СМИ2": "Внебюджет",
    "СММ": "Бюджет",
    "ЗК": "Бюджет",
    "HR": "Бюджет",
    "Финансовый": "Бюджет",
    "Производители и КНО": "Бюджет",
    "Суды": "Бюджет",
    "ДВПР": "Бюджет",
    "ППК": "Внебюджет",
    "Аудиты сетей": "Внебюджет",
    "РЭО": "Внебюджет",
    "МСИ": "Внебюджет",
    "Дни российских вин": "Внебюджет",
    "Российское пиво": "Внебюджет",
    "Зелень": "Внебюджет",
    "Зеленая недвижимость и косметика": "Внебюджет",
    "Бюджет": "Бюджет",
    "TS": "Внебюджет",
    "Орган по сертификации": "Внебюджет"
}

def set_page_config():
    st.set_page_config(
        page_title="Панель управления Роскачество",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
