import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

import config
import data_manager
import ui_components

# --- INITIALIZATION ---
config.set_page_config()
ui_components.apply_custom_css()

# Session state for direction selection (to support interactive charts)
if 'selected_dir' not in st.session_state:
    st.session_state.selected_dir = "Все"

# --- DATA LOADING ---
if st.sidebar.button("🔄 Обновить данные"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Загрузка данных..."):
    df_raw, period_cols = data_manager.load_data()

if df_raw is None or df_raw.empty:
    st.error("Ошибка загрузки данных. Проверьте логи.")
    st.stop()

# Add Funding Type to raw data
df_raw['Тип'] = df_raw['Направление'].map(config.DIRECTION_TYPES).fillna("Не указано")

# --- PERIOD SELECTION ---
today = datetime.now()
# Поиск индекса периода, максимально близкого к сегодня "в меньшую сторону"
default_period_idx = 0
closest_past_dt = None

for i, col in enumerate(period_cols):
    try:
        dt = pd.to_datetime(col, format='%d.%m.%Y')
        # Ищем дату, которая меньше или равна сегодня, но при этом самая поздняя из таких
        if dt <= today:
            if closest_past_dt is None or dt > closest_past_dt:
                closest_past_dt = dt
                default_period_idx = i
    except:
        continue

# --- SIDEBAR FILTERS ---
st.sidebar.header("Фильтры")

# Filter: Направление
directions = sorted(df_raw['Направление'].unique().tolist())
# Sync with session state
selected_dir = st.sidebar.selectbox(
    "Направление", 
    ["Все"] + directions, 
    index=(["Все"] + directions).index(st.session_state.selected_dir) if st.session_state.selected_dir in (["Все"] + directions) else 0,
    key="selectbox_dir"
)
st.session_state.selected_dir = selected_dir

df_filtered = df_raw.copy()
if selected_dir != "Все":
    df_filtered = df_filtered[df_filtered['Направление'] == selected_dir]

st.sidebar.markdown("---")
period_range = st.sidebar.select_slider(
    "Диапазон дат",
    options=period_cols,
    value=(period_cols[0], period_cols[default_period_idx])
)

current_period = period_range[1]
idx_from = period_cols.index(period_range[0])
idx_to = period_cols.index(period_range[1])
selected_periods = period_cols[idx_from:idx_to+1]

# --- DATA PROCESSING FOR CHARTS (CARRY-OVER) ---
def apply_carry_over(df, cols):
    df_copy = df.copy()
    for index, row in df_copy.iterrows():
        last_val = 0
        for col in cols:
            if row[col] == 0:
                df_copy.at[index, col] = last_val
            else:
                last_val = row[col]
    return df_copy

df_raw_filled = apply_carry_over(df_raw, period_cols)
df_filtered_filled = apply_carry_over(df_filtered, period_cols)

# --- HEADER & KPI ---
ui_components.render_header(current_period)

if selected_dir == "Все":
    st.subheader("Основные показатели")
    cols = st.columns(4)
    kpis = [
        ("Бюджет (Сумма)", "Сумма Бюджет", "Общая сумма выделенного бюджета за период"),
        ("Внебюджет (Сумма)", "Сумма Внебюджет", "Общая сумма внебюджетных поступлений"),
        ("Знак качества", "Кол-во выданных сертификатов", "Количество выданных сертификатов знака качества"),
        ("Кол-во договоров", "Кол-во договоров", "Количество подписанных документов")
    ]

    for i, (label, search_term, tooltip) in enumerate(kpis):
        val, d, d_p = data_manager.get_kpi_metrics(df_raw, period_cols, current_period, search_term)
        with cols[i]:
            ui_components.render_kpi_card(label, val, d, d_p, tooltip)

    # --- CHARTS (HOME PAGE) ---
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Row 1: Budget Dynamics (Full Width)
    st.subheader("Динамика бюджета")
    budget_df = df_raw_filled[df_raw_filled['Метрика'].str.contains("Сумма Бюджет", case=False, na=False)]
    if not budget_df.empty:
        plot_data = budget_df[selected_periods].sum().reset_index()
        plot_data.columns = ['Период', 'Значение']
        fig = px.area(plot_data, x='Период', y='Значение', markers=True)
        fig.update_traces(line_color=config.ROSKACHESTVO_RED, fillcolor='rgba(227, 6, 19, 0.1)')
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=400)
        st.plotly_chart(fig, width="stretch")

    # Row 2: Extra-Budget Dynamics & Pie (Interactive)
    st.markdown("---")
    c3, c4 = st.columns([2, 1])
    with c3:
        st.subheader("Динамика внебюджета")
        extra_df = df_raw_filled[df_raw_filled['Метрика'].str.contains("Сумма Внебюджет", case=False, na=False)]
        if not extra_df.empty:
            plot_extra = extra_df[selected_periods].sum().reset_index()
            plot_extra.columns = ['Период', 'Значение']
            fig_extra = px.line(plot_extra, x='Период', y='Значение', markers=True)
            fig_extra.update_traces(line_color="#FF8A00", line_width=3)
            fig_extra.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=350)
            st.plotly_chart(fig_extra, width="stretch")
            
    with c4:
        st.subheader("Доля внебюджета")
        if not extra_df.empty:
            pie_extra = extra_df.groupby('Направление')[current_period].sum().reset_index()
            pie_extra = pie_extra[pie_extra[current_period] > 0]
            if not pie_extra.empty:
                fig_pie_extra = px.pie(pie_extra, values=current_period, names='Направление', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie_extra.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=350, showlegend=False)
                
                # Interactive selection
                selected_points = st.plotly_chart(fig_pie_extra, width="stretch", on_select="rerun", selection_mode="points")
                
                if selected_points and selected_points.get("selection", {}).get("points"):
                    point = selected_points["selection"]["points"][0]
                    label = point.get("label")
                    if label:
                        st.session_state.selected_dir = label
                        st.rerun()
        else:
            st.info("Нет данных по внебюджету за выбранный период.")

else:
    # --- DIRECTION VIEW ---
    st.markdown(f"### Аналитика: {selected_dir}")
    ui_components.render_funding_type(selected_dir, config.DIRECTION_TYPES)
    
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Исполнение бюджета (План / Факт)")
        # Plan = Сумма Бюджет, Fact = Сумма договоров
        plan_df = df_filtered_filled[df_filtered_filled['Метрика'].str.contains("Сумма Бюджет", case=False, na=False)]
        fact_df = df_filtered_filled[df_filtered_filled['Метрика'].str.contains("Сумма договоров", case=False, na=False)]
        
        if not plan_df.empty or not fact_df.empty:
            plot_pf = pd.DataFrame(index=selected_periods)
            plot_pf['План'] = plan_df[selected_periods].sum().values if not plan_df.empty else 0
            plot_pf['Факт'] = fact_df[selected_periods].sum().values if not fact_df.empty else 0
            
            fig_pf = go.Figure()
            fig_pf.add_trace(go.Bar(x=selected_periods, y=plot_pf['План'], name='План (Бюджет)', marker_color='#D3D3D3'))
            fig_pf.add_trace(go.Bar(x=selected_periods, y=plot_pf['Факт'], name='Факт (Договоры)', marker_color=config.ROSKACHESTVO_RED))
            fig_pf.update_layout(barmode='group', margin=dict(l=0, r=0, t=30, b=0), height=400, legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_pf, width="stretch")
            
    with c2:
        st.subheader("Прогноз")
        forecast_vals = data_manager.generate_forecast(df_raw, selected_periods, "Сумма Бюджет", periods_ahead=2)
        if forecast_vals:
            # Simple forecast display
            f_df = pd.DataFrame({
                "Период": [f"Прогноз {i+1}" for i in range(len(forecast_vals))],
                "Значение": forecast_vals
            })
            fig_f = px.bar(f_df, x="Период", y="Значение")
            fig_f.update_traces(marker_color="orange")
            fig_f.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=400)
            st.plotly_chart(fig_f, width="stretch")

    # --- DYNAMIC METRIC CHARTS (DIRECTION VIEW) ---
    st.markdown("---")
    st.subheader(f"Динамика показателей: {selected_dir}")
    
    # Get all unique metrics for this direction except the ones already shown in Budget/Forecast
    other_metrics = df_filtered['Метрика'].unique().tolist()
    # Remove duplicates or similar metrics to keep it clean
    display_metrics = [m for m in other_metrics if not any(x in m.lower() for x in ["сумма бюджет", "прогноз"])]
    
    if display_metrics:
        # Arrange in 2 columns
        m_cols = st.columns(2)
        for i, metric in enumerate(display_metrics):
            with m_cols[i % 2]:
                m_data = df_filtered[df_filtered['Метрика'] == metric]
                if not m_data.empty:
                    plot_m = m_data[selected_periods].sum().reset_index()
                    plot_m.columns = ['Период', 'Значение']
                    
                    fig_m = px.line(plot_m, x='Период', y='Значение', markers=True, title=metric)
                    fig_m.update_traces(line_color=config.ROSKACHESTVO_RED, line_width=2)
                    fig_m.update_layout(
                        margin=dict(l=0, r=0, t=40, b=0), 
                        height=250, 
                        xaxis_title=None, 
                        yaxis_title=None,
                        title_font_size=14
                    )
                    st.plotly_chart(fig_m, width="stretch")
    else:
        st.info("Нет дополнительных метрик для отображения.")

# --- TABLE & EXPORT ---
st.markdown("---")
table_title = f"Детальные данные: {selected_dir}" if selected_dir != "Все" else "Сводная таблица по всем направлениям"
st.subheader(table_title)

if selected_dir != "Все":
    # Mirror Google Sheets: Metrics as rows, Periods as columns
    # We use selected_periods (the range from the slider)
    display_df = df_filtered[['Метрика'] + selected_periods].copy()
    
    # Group by Metric to aggregate if there are multiple rows for the same metric (shouldn't be, but safe)
    display_df = display_df.groupby('Метрика').sum().reset_index()
    
    # Format: numbers with separators
    st.dataframe(display_df.style.format({col: '{:,.0f}' for col in selected_periods}), width="stretch")
    
    # Export
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        display_df.to_excel(writer, index=False, sheet_name='Отчет')
    
    st.download_button(
        label="📥 Скачать детальный отчет (Excel)",
        data=buffer.getvalue(),
        file_name=f"detail_report_{selected_dir}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    # For "All", show the full raw table like in Google Sheets
    st.subheader("База данных")
    
    # Selecting columns to display: Direction, Metric, and all Period columns
    # We filter columns that match the date format
    full_display_df = df_raw.copy()
    
    # Sort columns to have metadata first, then dates
    metadata_cols = ['Направление', 'Направление 2', 'Метрика', 'Тип', 'Ответственный']
    existing_metadata = [c for c in metadata_cols if c in full_display_df.columns]
    display_cols = existing_metadata + period_cols
    
    st.dataframe(
        full_display_df[display_cols].style.format({col: '{:,.0f}' for col in period_cols}), 
        width="stretch"
    )
    
    # Export for the full database
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        full_display_df[display_cols].to_excel(writer, index=False, sheet_name='Полная база')
    
    st.download_button(
        label="📥 Скачать полную базу (Excel)",
        data=buffer.getvalue(),
        file_name=f"full_database_{current_period}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

ui_components.footer()
