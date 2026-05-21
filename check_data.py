import pandas as pd
import re

url = 'https://docs.google.com/spreadsheets/d/1QTklm0AohB04VDul1ScIOiTPNYjmKeVp9GxeQsKVs1s/export?format=csv&gid=0'
df = pd.read_csv(url)
df.columns = [str(c).strip() for c in df.columns]

def clean(x):
    if pd.isna(x): return 0.0
    s = str(x).replace('\xa0', '').replace(' ', '').replace(',', '.')
    s = re.sub(r'[^-0-9.]', '', s)
    try:
        return float(s) if s else 0.0
    except:
        return 0.0

period_cols = []
for col in df.columns:
    try:
        pd.to_datetime(col, format='%d.%m.%Y')
        period_cols.append(col)
    except:
        continue

for col in period_cols:
    df[col] = df[col].apply(clean)

target_metric = 'Кол-во выданных сертификатов'
res = df[df.iloc[:, 3] == target_metric]
print(f"Results for '{target_metric}' on 04.05.2026:")
print(res[['Направление', 'Метрика', '04.05.2026']])
