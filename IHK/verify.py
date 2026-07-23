import pandas as pd
import numpy as np
import sys

# Expected values from the original dataset_forecasting_final.csv for BANYUWANGI (2018-2026)
expected_banyuwangi = {
    2018: {"IHK": 126.594, "Trend": 3, "Lag1": 123.74, "Lag2": 121.15, "Lag3": 116.57, "Diff1": 2.853999999999999, "Growth_%": 2.306449005980271, "RollingMean3": 123.82799999999999, "RollingSTD3": 2.7230666536094947, "ExpandingMean": 122.0135},
    2019: {"IHK": 126.594, "Trend": 4, "Lag1": 126.594, "Lag2": 123.74, "Lag3": 121.15, "Diff1": 0.0, "Growth_%": 0.0, "RollingMean3": 125.64266666666667, "RollingSTD3": 1.6477576682672266, "ExpandingMean": 122.92960000000001},
    2020: {"IHK": 106.679, "Trend": 5, "Lag1": 126.594, "Lag2": 126.594, "Lag3": 123.74, "Diff1": -19.914999999999992, "Growth_%": -15.731393272982919, "RollingMean3": 119.95566666666666, "RollingSTD3": 11.497930610911384, "ExpandingMean": 120.22116666666666},
    2021: {"IHK": 106.679, "Trend": 6, "Lag1": 106.679, "Lag2": 126.594, "Lag3": 126.594, "Diff1": 0.0, "Growth_%": 0.0, "RollingMean3": 113.31733333333334, "RollingSTD3": 11.497930610911366, "ExpandingMean": 118.28657142857142},
    2022: {"IHK": 106.679, "Trend": 7, "Lag1": 106.679, "Lag2": 106.679, "Lag3": 126.594, "Diff1": 0.0, "Growth_%": 0.0, "RollingMean3": 106.679, "RollingSTD3": 0.0, "ExpandingMean": 116.835625},
    2023: {"IHK": 112.72, "Trend": 8, "Lag1": 106.679, "Lag2": 106.679, "Lag3": 106.679, "Diff1": 6.040999999999997, "Growth_%": 5.662782740745609, "RollingMean3": 108.69266666666668, "RollingSTD3": 3.487772976174391, "ExpandingMean": 116.37833333333333},
    2024: {"IHK": 115.155, "Trend": 9, "Lag1": 112.72, "Lag2": 106.679, "Lag3": 106.679, "Diff1": 2.4350000000000023, "Growth_%": 2.1602200141944694, "RollingMean3": 111.51799999999999, "RollingSTD3": 4.36397147103406, "ExpandingMean": 116.256},
    2025: {"IHK": 115.155, "Trend": 10, "Lag1": 115.155, "Lag2": 112.72, "Lag3": 106.679, "Diff1": 0.0, "Growth_%": 0.0, "RollingMean3": 114.34333333333335, "RollingSTD3": 1.4058479054765014, "ExpandingMean": 116.15590909090908},
    2026: {"IHK": 115.155, "Trend": 11, "Lag1": 115.155, "Lag2": 115.155, "Lag3": 112.72, "Diff1": 0.0, "Growth_%": 0.0, "RollingMean3": 115.155, "RollingSTD3": 0.0, "ExpandingMean": 116.07249999999999}
}

try:
    print("Loading generated dataset_forecasting_final.csv...")
    df = pd.read_csv('dataset_forecasting_final.csv')
    
    # 1. Check Row Count
    # There are 192 unique districts (daerah) and 12 years (2015-2026)
    expected_rows = 192 * 12
    actual_rows = len(df)
    print(f"Row Count: Expected={expected_rows}, Actual={actual_rows}")
    assert actual_rows == expected_rows, f"Row count mismatch: expected {expected_rows}, got {actual_rows}"
    
    # 2. Check Column Names
    expected_columns = ['Daerah', 'Tahun', 'IHK', 'Trend', 'Lag1', 'Lag2', 'Lag3', 'Diff1', 'Growth_%', 'RollingMean3', 'RollingSTD3', 'ExpandingMean']
    actual_columns = list(df.columns)
    print(f"Columns: {actual_columns}")
    assert actual_columns == expected_columns, f"Columns mismatch: expected {expected_columns}, got {actual_columns}"
    
    # 3. Check Years Range
    years = sorted(df['Tahun'].unique())
    print(f"Years: {years}")
    assert years == list(range(2015, 2027)), f"Years mismatch: expected 2015-2026, got {years}"
    
    # 4. Check BANYUWANGI values for 2018-2026
    banyu = df[df['Daerah'] == 'BANYUWANGI'].set_index('Tahun')
    for yr, expected in expected_banyuwangi.items():
        row = banyu.loc[yr]
        for col, val in expected.items():
            actual_val = row[col]
            if pd.isna(actual_val) and pd.isna(val):
                continue
            assert np.isclose(actual_val, val, rtol=1e-5), f"Mismatch for BANYUWANGI {yr} {col}: expected {val}, got {actual_val}"
    print("Values for BANYUWANGI 2018-2026 match perfectly!")
    
    # 5. Check NaNs for 2015-2017
    # For year 2015: Lag1, Lag2, Lag3, Diff1, Growth_%, RollingMean3, RollingSTD3 must be NaN
    row_2015 = banyu.loc[2015]
    print(f"2015 values for BANYUWANGI: \n{row_2015}")
    assert pd.isna(row_2015['Lag1']), "Lag1 for 2015 should be NaN"
    assert pd.isna(row_2015['Lag2']), "Lag2 for 2015 should be NaN"
    assert pd.isna(row_2015['Lag3']), "Lag3 for 2015 should be NaN"
    assert pd.isna(row_2015['Diff1']), "Diff1 for 2015 should be NaN"
    assert pd.isna(row_2015['Growth_%']), "Growth_% for 2015 should be NaN"
    assert pd.isna(row_2015['RollingMean3']), "RollingMean3 for 2015 should be NaN"
    assert pd.isna(row_2015['RollingSTD3']), "RollingSTD3 for 2015 should be NaN"
    assert not pd.isna(row_2015['ExpandingMean']), "ExpandingMean for 2015 should not be NaN"
    
    # For year 2016: Lag2, Lag3, RollingMean3, RollingSTD3 must be NaN; Lag1, Diff1, Growth_% must not be NaN
    row_2016 = banyu.loc[2016]
    print(f"2016 values for BANYUWANGI: \n{row_2016}")
    assert not pd.isna(row_2016['Lag1']), "Lag1 for 2016 should not be NaN"
    assert pd.isna(row_2016['Lag2']), "Lag2 for 2016 should be NaN"
    assert pd.isna(row_2016['Lag3']), "Lag3 for 2016 should be NaN"
    assert not pd.isna(row_2016['Diff1']), "Diff1 for 2016 should not be NaN"
    assert not pd.isna(row_2016['Growth_%']), "Growth_% for 2016 should not be NaN"
    assert pd.isna(row_2016['RollingMean3']), "RollingMean3 for 2016 should be NaN"
    assert pd.isna(row_2016['RollingSTD3']), "RollingSTD3 for 2016 should be NaN"
    
    # For year 2017: Lag3 must be NaN; others should be valid
    row_2017 = banyu.loc[2017]
    print(f"2017 values for BANYUWANGI: \n{row_2017}")
    assert not pd.isna(row_2017['Lag1']), "Lag1 for 2017 should not be NaN"
    assert not pd.isna(row_2017['Lag2']), "Lag2 for 2017 should not be NaN"
    assert pd.isna(row_2017['Lag3']), "Lag3 for 2017 should be NaN"
    assert not pd.isna(row_2017['Diff1']), "Diff1 for 2017 should not be NaN"
    assert not pd.isna(row_2017['Growth_%']), "Growth_% for 2017 should not be NaN"
    assert not pd.isna(row_2017['RollingMean3']), "RollingMean3 for 2017 should not be NaN"
    assert not pd.isna(row_2017['RollingSTD3']), "RollingSTD3 for 2017 should not be NaN"
    
    print("Verification completed successfully! All checks passed.")
    sys.exit(0)

except Exception as e:
    print(f"Verification FAILED: {e}")
    sys.exit(1)
