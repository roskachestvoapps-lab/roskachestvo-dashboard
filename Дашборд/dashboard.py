import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# --- CONFIGURATION ---
SHEET_ID = "1sKa9u7YIgHvLCC8pEZus7OFVLuATvV2eZ9kn8csOtww"
GID = "0"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

ROSKACHESTVO_RED = "#E30613"

st.set_page_config(
    page_title="Панель управления Роскачество",
    page_icon="📊",
    layout="wide",
)

# --- STYLING ---
st.markdown(f"""
    <style>
    .main {{
        background-color: #f8f9fa;
    }}
    .stMetric {{
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid {ROSKACHESTVO_RED};
    }}
    h1, h2, h3 {{
        color: #333;
    }}
    .ros-header {{
        background-color: {ROSKACHESTVO_RED};
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 25px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- DATA LOADING ---
@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
    except Exception as e:
        st.error(f"Критическая ошибка при чтении CSV: {e}")
        return None, []
    
    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]
    
    # 1. FIND PERIOD COLUMNS
    period_cols = []
    for col in df.columns:
        try:
            pd.to_datetime(col, format='%d.%m.%Y')
            period_cols.append(col)
        except:
            continue
            
    # 2. DYNAMIC COLUMN MAPPING (Search by keywords)
    col_mapping = {}
    keywords = {
        'Направление': ['направление', 'департамент', 'отдел'],
        'Направление 2': ['направление 2', 'поднаправление', 'проект'],
        'Метрика': ['метрика', 'показатель', 'название'],
        'Комментарий': ['комментарий', 'коммент', 'примечание'],
        'Ответственный': ['ответственный', 'фио', 'куратор']
    }
    
    # Priority indices as fallback
    priority_indices = {
        'Направление': 1,
        'Направление 2': 2,
        'Метрика': 3,
        'Комментарий': 4,
        'Ответственный': 5
    }

    used_cols = set()
    for key, search_terms in keywords.items():
        found = False
        # Try finding by keyword
        for col in df.columns:
            if any(term in col.lower() for term in search_terms) and col not in used_cols:
                col_mapping[col] = key
                used_cols.add(col)
                found = True
                break
        
        # Fallback to index if not found and index exists
        if not found:
            idx = priority_indices[key]
            if idx < len(df.columns):
                col_name = df.columns[idx]
                col_mapping[col_name] = key
                used_cols.add(col_name)

    df = df.rename(columns=col_mapping)
    
    # Ensure required columns exist
    if 'Направление' not in df.columns:
        # Emergency mapping if everything failed
        df.rename(columns={df.columns[1]: 'Направление'}, inplace=True)
    
    # Drop rows where Направление is null or looks like header/empty
    df = df.dropna(subset=['Направление'])
    df = df[df['Направление'].astype(str).str.len() > 1]
    
    # 3. ROBUST NUMERIC CONVERSION
    def clean_numeric(x):
        if pd.isna(x): return 0.0
        s = str(x).replace('\xa0', '').replace(' ', '').replace(',', '.')
        # Remove any non-numeric characters except . and -
        import re
        s = re.sub(r'[^-0-9.]', '', s)
        try:
            return float(s) if s else 0.0
        except:
            return 0.0

    for col in period_cols:
        df[col] = df[col].apply(clean_numeric)
        
    return df, period_cols

# --- MANUAL REFRESH ---
if st.sidebar.button("🔄 Обновить данные"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Загрузка данных из Google Sheets..."):
    df_raw, period_cols = load_data()

if df_raw is None or df_raw.empty:
    st.error("Не удалось загрузить данные. Проверьте SHEET_ID и доступ к таблице.")
    st.stop()

# --- SMART PERIOD SELECTION ---
today = datetime.now()
default_period_idx = len(period_cols) - 1

# Try to find a match for current month/year
for i, col in enumerate(period_cols):
    dt = pd.to_datetime(col, format='%d.%m.%Y')
    if dt.year == today.year and dt.month == today.month:
        default_period_idx = i
        break
    elif dt > today:
        default_period_idx = max(0, i-1)
        break

# --- SIDEBAR FILTERS ---
st.sidebar.header("Фильтры")

directions = sorted(df_raw['Направление'].unique().tolist())
selected_dir = st.sidebar.selectbox("Направление", ["Все"] + directions)

df_filtered = df_raw.copy()
if selected_dir != "Все":
    df_filtered = df_filtered[df_filtered['Направление'] == selected_dir]

directions2 = sorted(df_filtered['Направление 2'].dropna().unique().tolist())
selected_dir2 = st.sidebar.selectbox("Направление 2", ["Все"] + directions2)

if selected_dir2 != "Все":
    df_filtered = df_filtered[df_filtered['Направление 2'] == selected_dir2]

metrics_list = sorted(df_filtered['Метрика'].dropna().unique().tolist())
selected_metric = st.sidebar.selectbox("Метрика", ["Все"] + metrics_list)

if selected_metric != "Все":
    df_filtered = df_filtered[df_filtered['Метрика'] == selected_metric]

st.sidebar.markdown("---")
st.sidebar.subheader("Выбор периода")

# Use a select_slider for period range - more visual
period_range = st.sidebar.select_slider(
    "Диапазон дат",
    options=period_cols,
    value=(period_cols[max(0, default_period_idx-6)], period_cols[default_period_idx])
)

current_period = period_range[1]
period_from, period_to = period_range

# Ensure period range is valid
idx_from = period_cols.index(period_from)
idx_to = period_cols.index(period_to)
selected_periods = period_cols[idx_from:idx_to+1]

# --- HELPER FUNCTIONS ---
def get_kpi_metrics(df, period_name, metric_name):
    idx = period_cols.index(period_name)
    prev_period = period_cols[idx-1] if idx > 0 else None
    
    # Try exact match first, then contains
    metric_df = df[df['Метрика'] == metric_name]
    if metric_df.empty:
        metric_df = df[df['Метрика'].str.contains(metric_name, case=False, na=False)]
    
    curr_val = metric_df[period_name].sum()
    prev_val = metric_df[prev_period].sum() if prev_period else 0
    
    delta = curr_val - prev_val
    delta_pct = (delta / prev_val * 100) if prev_val != 0 else 0
    
    return curr_val, delta, delta_pct

def render_kpi(label, value, delta, delta_pct):
    delta_color = "green" if delta >= 0 else "red"
    st.markdown(f"""
        <div style="background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid {ROSKACHESTVO_RED}; min-height: 120px;">
            <div style="color: #666; font-size: 14px; margin-bottom: 8px; font-weight: 500;">{label}</div>
            <div style="font-size: 28px; font-weight: bold; color: #333;">{value:,.0f}</div>
            <div style="color: {delta_color}; font-size: 14px; margin-top: 8px;">
                {delta:+,.0f} ({delta_pct:+.1f}%)
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
    <div class="ros-header">
        <div style="display: flex; align-items: center;">
            <div style="font-size: 24px; font-weight: bold;">РОСКАЧЕСТВО</div>
            <div style="margin-left: 20px; font-size: 18px; border-left: 1px solid white; padding-left: 20px;">
                Аналитическая панель управления
            </div>
        </div>
        <div style="font-size: 14px; text-align: right;">
            <div>Отчетный период: {current_period}</div>
            <div style="opacity: 0.8; font-size: 12px;">Обновлено: {datetime.now().strftime('%d.%m.%Y')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- KPI CARDS ---
st.subheader("Основные показатели")
cols = st.columns(5)

kpi_names = [
    ("Бюджет", "Сумма Бюджет"),
    ("Сумма договоров", "Сумма договоров"),
    ("Кол-во договоров", "Кол-во договоров"),
    ("Кол-во заявок", "Кол-во заявок"),
    ("Кол-во сертификатов", "Кол-во сертификатов")
]

for i, (label, search_term) in enumerate(kpi_names):
    val, d, d_p = get_kpi_metrics(df_filtered if selected_dir != "Все" else df_raw, current_period, search_term)
    with cols[i]:
        render_kpi(label, val, d, d_p)

# --- MAIN CHARTS ---
st.markdown("<br>", unsafe_allow_html=True)

if selected_dir == "Все":
    # OVERVIEW MODE
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Динамика бюджета по всем направлениям")
        budget_df = df_raw[df_raw['Метрика'].str.contains("Сумма Бюджет", case=False, na=False)]
        if not budget_df.empty:
            plot_data = budget_df[selected_periods].sum().reset_index()
            plot_data.columns = ['Период', 'Значение']
            fig = px.area(plot_data, x='Период', y='Значение', markers=True)
            fig.update_traces(line_color=ROSKACHESTVO_RED, fillcolor='rgba(227, 6, 19, 0.1)')
            fig.update_layout(xaxis_title=None, yaxis_title="Бюджет", margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
    with c2:
        st.subheader("Доля направлений в бюджете")
        pie_data = budget_df.groupby('Направление')[current_period].sum().reset_index()
        fig_pie = px.pie(pie_data, values=current_period, names='Направление', hole=0.5)
        fig_pie.update_layout(showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)
else:
    # DIRECTION DRILL-DOWN MODE
    st.subheader(f"Аналитика по направлению: {selected_dir}")
    
    c1, c2, c3 = st.columns(3)
    
    # 1. Budget Trend for this Direction
    with c1:
        st.write("**Динамика бюджета**")
        d_budget = df_filtered[df_filtered['Метрика'].str.contains("Сумма Бюджет", case=False, na=False)]
        if not d_budget.empty:
            plot_d = d_budget[selected_periods].sum().reset_index()
            plot_d.columns = ['Период', 'Значение']
            fig_d = px.line(plot_d, x='Период', y='Значение', markers=True)
            fig_d.update_traces(line_color=ROSKACHESTVO_RED)
            fig_d.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig_d, use_container_width=True)
            
    # 2. Conversion/Ratio: Contracts vs Applications
    with c2:
        st.write("**Договоры vs Заявки**")
        d_conv = df_filtered[df_filtered['Метрика'].isin(["Кол-во заявок", "Кол-во договоров"])]
        if not d_conv.empty:
            conv_data = d_conv.groupby('Метрика')[selected_periods].sum().T.reset_index()
            # Убедимся, что обе колонки присутствуют для корректной работы графика
            for m in ["Кол-во заявок", "Кол-во договоров"]:
                if m not in conv_data.columns:
                    conv_data[m] = 0
            
            fig_conv = px.bar(conv_data, x='index', y=["Кол-во заявок", "Кол-во договоров"], barmode='group')
            fig_conv.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0), legend_title=None)
            st.plotly_chart(fig_conv, use_container_width=True)
            
    # 3. Sub-direction breakdown
    with c3:
        st.write("**Бюджет по поднаправлениям**")
        sub_data = d_budget.groupby('Направление 2')[current_period].sum().reset_index()
        fig_sub = px.bar(sub_data, y='Направление 2', x=current_period, orientation='h')
        fig_sub.update_traces(marker_color=ROSKACHESTVO_RED)
        fig_sub.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_sub, use_container_width=True)

# --- AGGREGATED TABLE ---
st.markdown("---")
st.subheader("Сводная таблица")

table_metrics = ["Сумма Бюджет", "Сумма договоров", "Кол-во договоров", "Кол-во заявок"]
table_rows = []

idx_curr = period_cols.index(current_period)
prev_period = period_cols[idx_curr-1] if idx_curr > 0 else None

for (nav, nav2), group in df_filtered.groupby(['Направление', 'Направление 2']):
    row = {'Направление': nav, 'Направление 2': nav2}
    for m in table_metrics:
        m_data = group[group['Метрика'].str.contains(m, case=False, na=False)]
        curr_val = m_data[current_period].sum()
        prev_val = m_data[prev_period].sum() if prev_period else 0
        
        row[f'{m}'] = curr_val
        delta = curr_val - prev_val
        row[f'{m} Δ%'] = (delta / prev_val * 100) if prev_val != 0 else 0
        
    table_rows.append(row)

if table_rows:
    df_table = pd.DataFrame(table_rows)
    
    def color_delta(val):
        color = 'red' if val < 0 else 'green'
        return f'color: {color}'

    st.dataframe(
        df_table.style.format({f'{m} Δ%': '{:+.1f}%' for m in table_metrics} | {m: '{:,.0f}' for m in table_metrics})
        .map(color_delta, subset=[f'{m} Δ%' for m in table_metrics]),
        width="stretch"
    )
else:
    st.info("Нет данных для таблицы с выбранными фильтрами.")

# --- FOOTER ---
st.markdown("""
<div style="text-align: center; color: #888; margin-top: 50px; font-size: 12px;">
    © 2026 Роскачество | Информационная панель на базе Python & Streamlit
</div>
""", unsafe_allow_html=True)
