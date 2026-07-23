import pandas as pd
import numpy as np

# 1. Load data
print("Loading Merged_IHK_Februari.csv...")
df = pd.read_csv('Merged_IHK_Februari.csv')

# 2. Melt to long format
long_df = df.melt(
    id_vars='Daerah',
    var_name='Tahun',
    value_name='IHK'
)

# 3. Convert IHK and Tahun types
long_df['IHK'] = pd.to_numeric(
    long_df['IHK'],
    errors='coerce'
)
long_df['Tahun'] = long_df['Tahun'].astype(int)

# 4. Sort by Daerah and Tahun
long_df = long_df.sort_values(
    ['Daerah', 'Tahun']
).reset_index(drop=True)

# 5. Impute IHK NaNs with overall IHK median
median_val = long_df['IHK'].median()
print(f"Overall IHK median for imputation: {median_val}")
long_df['IHK'] = long_df['IHK'].fillna(median_val)

# 6. Winsorization (clipping)
clean_df = long_df.copy()
lower = clean_df['IHK'].quantile(0.10)
upper = clean_df['IHK'].quantile(0.90)
print(f"Winsorization thresholds: lower={lower}, upper={upper}")
clean_df['IHK'] = np.clip(
    clean_df['IHK'],
    lower,
    upper
)

# 7. Trend
clean_df['Trend'] = clean_df['Tahun'] - clean_df['Tahun'].min()

# 8. Lags (Lag1, Lag2, Lag3)
clean_df['Lag1'] = clean_df.groupby('Daerah')['IHK'].shift(1)
clean_df['Lag2'] = clean_df.groupby('Daerah')['IHK'].shift(2)
clean_df['Lag3'] = clean_df.groupby('Daerah')['IHK'].shift(3)

# 9. Diff1 (first difference of winsorized IHK)
clean_df['Diff1'] = clean_df.groupby('Daerah')['IHK'].diff(1)

# 10. Growth_% (percentage change of winsorized IHK * 100)
clean_df['Growth_%'] = clean_df.groupby('Daerah')['IHK'].pct_change() * 100

# 11. Rolling Mean (RollingMean3)
clean_df['RollingMean3'] = (
    clean_df.groupby('Daerah')['IHK']
    .rolling(3)
    .mean()
    .reset_index(0, drop=True)
)

# 12. Rolling STD (RollingSTD3)
clean_df['RollingSTD3'] = (
    clean_df.groupby('Daerah')['IHK']
    .rolling(3)
    .std()
    .reset_index(0, drop=True)
)

# 13. Expanding Mean (ExpandingMean)
clean_df['ExpandingMean'] = (
    clean_df.groupby('Daerah')['IHK']
    .expanding()
    .mean()
    .reset_index(level=0, drop=True)
)

# 14. Save to CSV without dropna!
print("Saving output to dataset_forecasting_final.csv...")
clean_df.to_csv('dataset_forecasting_final.csv', index=False)
print("Finished successfully!")
