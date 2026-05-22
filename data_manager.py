import streamlit as st
import pandas as pd
import numpy as np
import re
from pydantic import BaseModel, ValidationError
from typing import Optional
from config import CSV_URL, logger

# Пример валидации структуры (можно расширять)
class DashboardRow(BaseModel):
    Направление: str
    Метрика: str

@st.cache_data(ttl=300)
def load_data():
    logger.info("Запуск загрузки данных из Google Sheets")
    try:
        df = pd.read_csv(CSV_URL)
        logger.info(f"Данные успешно загружены. Строк: {len(df)}")
    except Exception as e:
        logger.error(f"Критическая ошибка при чтении CSV: {e}")
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
            
    # 2. DYNAMIC COLUMN MAPPING
    col_mapping = {}
    keywords = {
        'Направление': ['направление', 'департамент', 'отдел'],
        'Направление 2': ['направление 2', 'поднаправление', 'проект'],
        'Метрика': ['метрика', 'показатель', 'название'],
        'Комментарий': ['комментарий', 'коммент', 'примечание'],
        'Ответственный': ['ответственный', 'фио', 'куратор']
    }
    
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
        for col in df.columns:
            if any(term in col.lower() for term in search_terms) and col not in used_cols:
                col_mapping[col] = key
                used_cols.add(col)
                found = True
                break
        
        if not found:
            idx = priority_indices.get(key, 999)
            if idx < len(df.columns):
                col_name = df.columns[idx]
                col_mapping[col_name] = key
                used_cols.add(col_name)

    df = df.rename(columns=col_mapping)
    
    if 'Направление' not in df.columns:
        df.rename(columns={df.columns[1]: 'Направление'}, inplace=True)
    
    df = df.dropna(subset=['Направление'])
    df = df[df['Направление'].astype(str).str.len() > 1]
    
    # 3. ROBUST NUMERIC CONVERSION
    def clean_numeric(x):
        if pd.isna(x): return 0.0
        s = str(x).replace('\xa0', '').replace(' ', '').replace(',', '.')
        s = re.sub(r'[^-0-9.]', '', s)
        try:
            return float(s) if s else 0.0
        except:
            return 0.0

    for col in period_cols:
        df[col] = df[col].apply(clean_numeric)
        
    logger.info("Обработка данных завершена")
    return df, period_cols

def get_kpi_metrics(df, period_cols, period_name, metric_name):
    idx = period_cols.index(period_name)
    
    # Try exact match first, then contains
    metric_df = df[df['Метрика'] == metric_name]
    if metric_df.empty:
        metric_df = df[df['Метрика'].str.contains(metric_name, case=False, na=False)]
    
    if metric_df.empty:
        return 0, 0, 0

    # Находим два последних ненулевых значения, начиная с выбранного периода и назад
    vals = []
    for i in range(idx, -1, -1):
        v = metric_df[period_cols[i]].sum()
        if v != 0:
            vals.append(v)
            if len(vals) == 2:
                break
    
    curr_val = vals[0] if len(vals) > 0 else 0
    prev_val = vals[1] if len(vals) > 1 else 0
    
    delta = curr_val - prev_val
    delta_pct = (delta / prev_val * 100) if prev_val != 0 else 0
    
    return curr_val, delta, delta_pct

def generate_forecast(df, period_cols, metric_name, periods_ahead=3):
    """Простой линейный прогноз на основе исторических данных."""
    metric_df = df[df['Метрика'].str.contains(metric_name, case=False, na=False)]
    if metric_df.empty or len(period_cols) < 2:
        return []
    
    y = metric_df[period_cols].sum().values
    x = np.arange(len(y))
    
    # Линейный тренд
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    
    future_x = np.arange(len(y), len(y) + periods_ahead)
    future_y = p(future_x)
    
    # Прогноз не может быть отрицательным для наших метрик
    future_y = np.maximum(future_y, 0)
    
    return future_y.tolist()
