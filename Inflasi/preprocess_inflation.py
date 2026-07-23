import pandas as pd
import numpy as np
import os

def preprocess_and_engineer_features(file_path, output_dir):
    print("=== Memulai Preprocessing & Feature Engineering ===")
    
    # 1. Load Data
    # Melewati 4 baris pertama karena merupakan header formatting Excel
    df = pd.read_excel(file_path, skiprows=4)
    df = df.iloc[:, [1, 2]].dropna().reset_index(drop=True)
    df.columns = ['Periode', 'Inflasi']
    
    # 2. Pembersihan & Parsing Tanggal
    month_mapping = {
        'Januari': 'January', 'Februari': 'February', 'Maret': 'March', 'April': 'April',
        'Mei': 'May', 'Juni': 'June', 'Juli': 'July', 'Agustus': 'August',
        'September': 'September', 'Oktober': 'October', 'November': 'November', 'Desember': 'December'
    }
    
    def parse_periode(val):
        if not isinstance(val, str):
            return pd.NaT
        parts = val.strip().split()
        if len(parts) != 2:
            return pd.NaT
        month_id, year_str = parts
        month_en = month_mapping.get(month_id)
        if not month_en:
            return pd.NaT
        try:
            return pd.to_datetime(f"{month_en} {year_str}")
        except:
            return pd.NaT
            
    df['Tanggal'] = df['Periode'].apply(parse_periode)
    
    # 3. Pembersihan & Parsing Nilai Inflasi (YoY)
    def clean_inflasi(val):
        if pd.isnull(val):
            return np.nan
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            val = val.replace('%', '').strip()
            try:
                return float(val)
            except:
                return np.nan
        return np.nan
        
    df['Inflasi_YoY'] = df['Inflasi'].apply(clean_inflasi)
    
    # Drop data yang tidak valid setelah parsing (jika ada)
    df = df.dropna(subset=['Tanggal', 'Inflasi_YoY']).reset_index(drop=True)
    
    # Urutkan secara kronologis (dari masa lalu ke masa kini)
    df = df.sort_values('Tanggal').reset_index(drop=True)
    
    # 4. Feature Engineering
    # A. Ekstraksi Waktu (Datetime Features)
    df['Year'] = df['Tanggal'].dt.year
    df['Month'] = df['Tanggal'].dt.month
    df['Quarter'] = df['Tanggal'].dt.quarter
    
    # B. Fitur Lag (Nilai Inflasi pada bulan-bulan sebelumnya)
    # Sangat berguna untuk model regresi (XGBoost, Random Forest, Linear Regression, LSTM)
    for lag in [1, 2, 3, 6, 12]:
        df[f'Inflasi_Lag_{lag}'] = df['Inflasi_YoY'].shift(lag)
        
    # C. Fitur Statistik Bergulir (Rolling Statistics)
    # Menggambarkan tren jangka pendek (3 bulan), jangka menengah (6 bulan), dan jangka panjang (12 bulan)
    for window in [3, 6, 12]:
        df[f'Inflasi_RollMean_{window}'] = df['Inflasi_YoY'].shift(1).rolling(window=window).mean()
        df[f'Inflasi_RollStd_{window}'] = df['Inflasi_YoY'].shift(1).rolling(window=window).std()
        
    # D. Fitur Selisih (Differences / Momentum)
    # Berguna untuk mendeteksi percepatan/perlambatan inflasi (kecepatan perubahan)
    df['Inflasi_Diff_1'] = df['Inflasi_YoY'].shift(1) - df['Inflasi_YoY'].shift(2) # Perubahan bulan lalu dibanding 2 bulan lalu
    df['Inflasi_Diff_12'] = df['Inflasi_YoY'].shift(1) - df['Inflasi_YoY'].shift(13) # Perubahan tahunan untuk bulan lalu
    
    # Urutkan kolom agar rapi
    cols_order = [
        'Tanggal', 'Periode', 'Inflasi_YoY', 
        'Year', 'Month', 'Quarter',
        'Inflasi_Lag_1', 'Inflasi_Lag_2', 'Inflasi_Lag_3', 'Inflasi_Lag_6', 'Inflasi_Lag_12',
        'Inflasi_RollMean_3', 'Inflasi_RollMean_6', 'Inflasi_RollMean_12',
        'Inflasi_RollStd_3', 'Inflasi_RollStd_6', 'Inflasi_RollStd_12',
        'Inflasi_Diff_1', 'Inflasi_Diff_12'
    ]
    df = df[cols_order]
    
    # 5. Simpan Hasil
    csv_output = os.path.join(output_dir, 'data_inflasi_processed.csv')
    xlsx_output = os.path.join(output_dir, 'data_inflasi_processed.xlsx')
    
    df.to_csv(csv_output, index=False)
    df.to_excel(xlsx_output, index=False)
    
    print(f"\nProses selesai!")
    print(f"- Data CSV disimpan ke: {csv_output}")
    print(f"- Data Excel disimpan ke: {xlsx_output}")
    print(f"- Total baris diproses: {len(df)}")
    print(f"- Jumlah kolom baru yang dihasilkan: {len(df.columns)}")
    print("\nFitur-fitur yang tersedia untuk pemodelan:")
    for col in df.columns:
        print(f"  * {col}")

if __name__ == "__main__":
    src_file = r"d:\Mine\Coding Camp 2026\Final\Inflasi\Data Inflasi.xlsx"
    dest_dir = r"d:\Mine\Coding Camp 2026\Final\Inflasi"
    preprocess_and_engineer_features(src_file, dest_dir)
