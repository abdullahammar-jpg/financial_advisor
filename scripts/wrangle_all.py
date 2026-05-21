import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import linregress

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).resolve().parent   
ROOT       = SCRIPT_DIR.parent                 
RAW        = ROOT / "data" / "raw"
PROC       = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

def parse_num(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if s in ("-", "", "nan", "#N/A"):
        return np.nan
    
    s = re.sub(r"[^\d.,-]", "", s)
    if not s:
        return np.nan

    has_comma = "," in s
    has_dot   = "." in s

    if has_comma and has_dot:
        
        last_comma = s.rfind(",")
        last_dot   = s.rfind(".")
        if last_comma > last_dot:
            
            s = s.replace(".", "").replace(",", ".")
        else:
            
            s = s.replace(",", "")
    elif has_comma and not has_dot:
        
        s = s.replace(",", ".")
    
    elif has_dot and not has_comma:
        parts = s.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            
            s = s.replace(".", "")
        
    try:
        return float(s)
    except ValueError:
        return np.nan

def pct_to_float(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if s.endswith("%"):
        try:
            return float(s[:-1]) / 100
        except ValueError:
            return np.nan
    return parse_num(val)

def find_indonesia_row(filepath, col_idx=0):
    df = pd.read_csv(filepath, header=0, dtype=str, encoding="utf-8-sig")
    col = df.columns[col_idx]
    mask = df[col].str.strip().str.upper() == "INDONESIA"
    if not mask.any():
        mask = df[col].str.strip().str.upper().str.contains("INDONESIA", na=False)
    if not mask.any():
        raise ValueError(f"Baris INDONESIA tidak ditemukan: {filepath.name}")
    return df[mask].iloc[0]

def monthly_series_from_bps(series):
    records = []
    for col, val in series.items():
        col = str(col).strip()
        if re.match(r"^\d{2}/\d{4}$", col):
            mm, yyyy = col.split("/")
            records.append({"year_month": f"{yyyy}-{mm}", "index_value": parse_num(val)})
    if not records:
        return pd.DataFrame(columns=["year_month", "index_value"])
    df = pd.DataFrame(records)
    df["year_month"] = pd.to_datetime(df["year_month"], format="%Y-%m")
    return df.sort_values("year_month").reset_index(drop=True)

def parse_dot_decimal(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if s in ("-", "", "nan", "#N/A"):
        return np.nan
    s = re.sub(r"[^\d.-]", "", s)
    try:
        return float(s)
    except ValueError:
        return np.nan

def impute_linear(series: pd.Series) -> pd.Series:
    return series.interpolate("linear").ffill().bfill()

def sep():
    print("-" * 55)

print("=" * 55)
print("1. CPI Umum (chain-link 2012->2018->2022)")
print("=" * 55)

CPI_DIR = RAW / "CPI"

def load_cpi_umum(pattern):
    matches = [f for f in CPI_DIR.glob("*.csv")
               if pattern.lower() in f.name.lower()]
    if not matches:
        raise FileNotFoundError(f"File CPI tidak ditemukan (pattern: {pattern})")
    return monthly_series_from_bps(find_indonesia_row(matches[0]))

df_15_19 = load_cpi_umum("2015-2019")  
df_20_23 = load_cpi_umum("2020-2023")  
df_24_26 = load_cpi_umum("2024-2026")  

df_24_26 = df_24_26[df_24_26["year_month"] <= "2025-12-01"]

df_15_19["base_year"] = "2012=100"
df_20_23["base_year"] = "2018=100"
df_24_26["base_year"] = "2022=100"

def get_val(df, ym_str):
    mask = df["year_month"].dt.strftime("%Y-%m") == ym_str
    vals = df.loc[mask, "index_value"].values
    return vals[0] if len(vals) and not np.isnan(vals[0]) else None

v_dec19_base12 = get_val(df_15_19, "2019-12")  
v_jan20_base18 = get_val(df_20_23, "2020-01")  

scale_2 = (v_dec19_base12 / v_jan20_base18) if (v_dec19_base12 and v_jan20_base18) else 1.0

v_23_base18 = get_val(df_20_23, "2023-12")  
v_23_scaled = v_23_base18 * scale_2 if v_23_base18 else None  
v_24_base22 = get_val(df_24_26, "2024-01")  

scale_3 = (v_23_scaled / v_24_base22) if (v_23_scaled and v_24_base22) else 1.0

print(f"  Chain-link scale_2 (2018->2012): {scale_2:.4f}")
print(f"  Chain-link scale_3 (2022->2012): {scale_3:.4f}")

df_a = df_15_19.copy(); df_a["index_chain"] = df_a["index_value"]  
df_b = df_20_23.copy(); df_b["index_chain"] = df_b["index_value"] * scale_2
df_c = df_24_26.copy(); df_c["index_chain"] = df_c["index_value"] * scale_3

df_a_trim = df_a[df_a["year_month"] < "2020-01-01"]
df_b_trim = df_b[(df_b["year_month"] >= "2020-01-01") & (df_b["year_month"] < "2024-01-01")]
df_c_trim = df_c[df_c["year_month"] >= "2024-01-01"]

cpi_all = (
    pd.concat([
        df_a_trim[["year_month", "index_chain", "base_year"]],
        df_b_trim[["year_month", "index_chain", "base_year"]],
        df_c_trim[["year_month", "index_chain", "base_year"]],
    ])
    .sort_values("year_month")
    .reset_index(drop=True)
)

cpi_all["index_chain"]       = impute_linear(cpi_all["index_chain"])
cpi_all["inflation_mom_pct"] = cpi_all["index_chain"].pct_change(1) * 100
cpi_all["inflation_yoy_pct"] = cpi_all["index_chain"].pct_change(12) * 100

cpi_all["year_month_str"] = cpi_all["year_month"].dt.strftime("%Y-%m")

out_monthly = PROC / "cpi_monthly.csv"
cpi_all.rename(columns={"index_chain":"cpi_index_rebased","year_month_str":"year_month"})       [["year_month","cpi_index_rebased","inflation_mom_pct","inflation_yoy_pct","base_year"]]       .to_csv(out_monthly, index=False)
print(f"  OK cpi_monthly.csv    -- {len(cpi_all)} baris")

v_dec19 = cpi_all.loc[cpi_all["year_month_str"]=="2019-12", "index_chain"].values
v_jan20 = cpi_all.loc[cpi_all["year_month_str"]=="2020-01", "index_chain"].values
if len(v_dec19) and len(v_jan20):
    mom_transition = (v_jan20[0] / v_dec19[0] - 1) * 100
    print(f"  Validasi transisi Des19->Jan20: {mom_transition:+.2f}% MoM (harus kecil)")

cpi_dec = cpi_all[cpi_all["year_month"].dt.month == 12].copy()
cpi_dec["year"]       = cpi_dec["year_month"].dt.year
cpi_dec["inflasi_pct"] = cpi_dec["inflation_yoy_pct"].round(2)
cpi_dec["base_year"]   = cpi_dec["base_year"]
cpi_dec[["year","inflasi_pct","base_year"]].to_csv(PROC/"cpi_clean.csv", index=False)
print(f"  OK cpi_clean.csv      -- {len(cpi_dec)} tahun")

print("\n2. CPI Sektoral (Makanan, Kesehatan, Pendidikan)")
sep()

SEKTOR_DIRS = {
    "makanan":    RAW / "CPI Sektor" / "Sektor 01 Makanan",
    "kesehatan":  RAW / "CPI Sektor" / "Sektor 05 Kesehatan",
    "pendidikan": RAW / "CPI Sektor" / "Sektor 09 Pendidikan",
}

cpi_umum_ref = (
    cpi_all[["year_month","inflation_yoy_pct"]]
    .assign(ym=cpi_all["year_month"].dt.strftime("%Y-%m"))
    .rename(columns={"inflation_yoy_pct":"umum_yoy"})
    [["ym","umum_yoy"]]
)

sektor_all, multipliers = [], []

for sektor, folder in SEKTOR_DIRS.items():
    if not folder.exists():
        print(f"  SKIP {sektor}: folder tidak ada")
        continue

    pieces = []
    for f in sorted(folder.glob("*.csv")):
        try:
            row = find_indonesia_row(f)
            df  = monthly_series_from_bps(row)
            if not df.empty:
                pieces.append(df)
        except Exception as e:
            print(f"  WARN {sektor}/{f.name}: {e}")

    if not pieces:
        print(f"  SKIP {sektor}: tidak ada data")
        continue

    df_s = (
        pd.concat(pieces)
        .drop_duplicates("year_month")
        .sort_values("year_month")
        .reset_index(drop=True)
    )

    n_miss = df_s["index_value"].isna().sum()
    if n_miss:
        df_s["index_value"] = impute_linear(df_s["index_value"])
        print(f"  FIX {sektor}: {n_miss} nilai kosong diimputasi")

    df_s["inflation_mom_pct"] = impute_linear(df_s["index_value"].pct_change(1) * 100)
    df_s["inflation_yoy_pct"] = impute_linear(df_s["index_value"].pct_change(12) * 100)
    df_s["sektor"]            = sektor
    df_s["ym"]                = df_s["year_month"].dt.strftime("%Y-%m")
    df_s["year_month"]        = df_s["ym"]

    sektor_all.append(df_s[["sektor","year_month","index_value","inflation_mom_pct","inflation_yoy_pct"]])

    m = df_s[["ym","inflation_yoy_pct"]].merge(cpi_umum_ref, on="ym", how="inner")
    m = m.dropna(subset=["inflation_yoy_pct","umum_yoy"])
    COVID_ANOMALY_MONTHS = {"2020-03","2020-04","2020-05","2020-06","2021-01","2021-02","2022-09","2022-10","2022-11"}
    m = m[~m["ym"].isin(COVID_ANOMALY_MONTHS)]
    m = m[(m["umum_yoy"].abs() > 0.1)]
    ratio = (m["inflation_yoy_pct"] / m["umum_yoy"]).replace([np.inf,-np.inf], np.nan).dropna()
    med_mult = round(ratio.median(), 3) if len(ratio) >= 3 else None
    multipliers.append({"sektor": sektor, "multiplier_median": med_mult, "n_obs": len(ratio)})
    print(f"  OK {sektor}: {len(df_s)} baris | multiplier = {med_mult}x")

if sektor_all:
    pd.concat(sektor_all, ignore_index=True).to_csv(PROC/"cpi_sektor_monthly.csv", index=False)
    print(f"  OK cpi_sektor_monthly.csv")

pd.DataFrame(multipliers).to_csv(PROC/"cpi_sektor_multiplier.csv", index=False)
print(f"  OK cpi_sektor_multiplier.csv")

print("\n3. Mortalitas & A/E Ratio (TMPI 2023)")
sep()

MORT_DIR  = RAW / "Tabel Mortalitas Indonesia (TMPI JKN 2023)"
mort_file = MORT_DIR / "Tabel_Mortalitas_Penduduk_Indonesia_2023.csv"

if not mort_file.exists():
    print(f"  ERROR: {mort_file.name} tidak ditemukan!")
    sys.exit(1)

df_mort = pd.read_csv(mort_file, dtype=str, encoding="utf-8-sig")
df_mort = df_mort.dropna(subset=["age"])
df_mort = df_mort[df_mort["age"].str.strip() != ""]

NUM_COLS = ["age","exposure_male","dx_male","expectedlife_male","qx_male","px_male",
            "exposure_female","dx_female","expectedlife_female","qx_female","px_female"]
for c in NUM_COLS:
    if c in df_mort.columns:
        df_mort[c] = df_mort[c].apply(parse_num)

AE_COLS = [c for c in df_mort.columns if "A/E" in c]
for c in AE_COLS:
    df_mort[c] = df_mort[c].apply(pct_to_float)

df_mort["age"] = df_mort["age"].apply(parse_num).astype(int)
df_mort = df_mort.sort_values("age").reset_index(drop=True)

MORT_KEEP = [c for c in NUM_COLS if c in df_mort.columns]
df_mort[MORT_KEEP].to_csv(PROC/"mortality_clean.csv", index=False)
print(f"  OK mortality_clean.csv  -- usia 0-{df_mort['age'].max()}, {len(df_mort)} baris")

if AE_COLS:
    ae_keep = ["age"] + AE_COLS
    df_ae = df_mort[[c for c in ae_keep if c in df_mort.columns]].copy()
    ae_male_cols   = [c for c in AE_COLS if "LK" in c.upper()]
    ae_female_cols = [c for c in AE_COLS if "PR" in c.upper()]
    if ae_male_cols:
        df_ae["ae_avg_male"]   = df_ae[ae_male_cols].mean(axis=1).round(4)
    if ae_female_cols:
        df_ae["ae_avg_female"] = df_ae[ae_female_cols].mean(axis=1).round(4)
    df_ae.to_csv(PROC/"ae_ratio_clean.csv", index=False)
    print(f"  OK ae_ratio_clean.csv   -- {len(AE_COLS)} kolom A/E ({', '.join(AE_COLS[:4])}...)")
else:
    print("  WARN: Tidak ada kolom A/E ditemukan di file mortalitas.")

print("\n4. Gaji Per Sektor (BPS)")
sep()

SALARY_DIR  = RAW / "Rata-rata Upah Gaji per Sektor 2015-2026 (February Data - BPS Rakernas)"
salary_file = SALARY_DIR / "Rata-rata upah gaji per sektor 2015 - 2026 BPS.csv"

if not salary_file.exists():
    print(f"  ERROR: {salary_file.name} tidak ditemukan!")
else:
    df_sal = pd.read_csv(salary_file, dtype=str, encoding="utf-8-sig")
    sektor_col = df_sal.columns[0]
    year_cols  = [c for c in df_sal.columns if re.match(r"^\d{4}$", str(c).strip())]

    for c in year_cols:
        df_sal[c] = df_sal[c].apply(parse_num)

    df_sal.to_csv(PROC/"salary_clean.csv", index=False)
    print(f"  OK salary_clean.csv     -- {len(df_sal)} sektor, {year_cols[0]}-{year_cols[-1]}")

    COVID_YEARS = {2020, 2021}
    growth_rows = []
    for _, row in df_sal.iterrows():
        sektor = str(row[sektor_col]).strip()
        vals   = {int(y): row[y] for y in year_cols if not pd.isna(row[y]) and row[y] > 0}
        if len(vals) < 3:
            continue

        years_sorted   = sorted(vals.keys())
        ymin, ymax     = years_sorted[0], years_sorted[-1]
        n_years        = ymax - ymin

        cagr = (vals[ymax] / vals[ymin]) ** (1 / n_years) - 1 if n_years > 0 else np.nan

        clean_years = [(y, vals[y]) for y in years_sorted if y not in COVID_YEARS]
        if len(clean_years) >= 3:
            xs = np.array([y - clean_years[0][0] for y, _ in clean_years])
            ys = np.log([v for _, v in clean_years])
            slope, *_ = linregress(xs, ys)
            trendline  = np.exp(slope) - 1
        else:
            trendline  = cagr

        growth_rows.append({
            "sektor":            sektor,
            "growth_normal":     round(trendline, 4),
            "growth_with_covid": round(cagr, 4),
            "year_start":        ymin,
            "year_end":          ymax,
        })

    df_growth = pd.DataFrame(growth_rows)
    df_growth.to_csv(PROC/"salary_growth.csv", index=False)
    print(f"  OK salary_growth.csv    -- {len(df_growth)} sektor")
    print()
    for _, r in df_growth.iterrows():
        print(f"    {r['sektor'][:45]:<45} normal={r['growth_normal']:+.2%}  covid={r['growth_with_covid']:+.2%}")

print("\n5. Data Investasi")
sep()

INV_DIR = RAW / "Investasi"

ihsg_files = list((INV_DIR / "Monthly IHSG").glob("*.csv"))
if not ihsg_files:
    print("  ERROR: File IHSG tidak ditemukan!")
else:
    df_ihsg = pd.read_csv(ihsg_files[0], dtype=str)
    df_ihsg["Date"]  = pd.to_datetime(df_ihsg["Date"], format="mixed", dayfirst=False)
    df_ihsg["Close"] = df_ihsg["Close"].apply(parse_dot_decimal)
    df_ihsg = df_ihsg[["Date","Close"]].dropna().sort_values("Date").reset_index(drop=True)
    df_ihsg = df_ihsg[df_ihsg["Date"].dt.year <= 2025]

    df_ihsg["return_mom_pct"] = df_ihsg["Close"].pct_change(1) * 100
    df_ihsg["return_yoy_pct"] = df_ihsg["Close"].pct_change(12) * 100
    df_ihsg["year_month"]     = df_ihsg["Date"].dt.strftime("%Y-%m")

    df_ihsg[["year_month","Close","return_mom_pct","return_yoy_pct"]]        .to_csv(PROC/"ihsg_monthly.csv", index=False)
    print(f"  OK ihsg_monthly.csv     -- {len(df_ihsg)} baris")

    ihsg_ann = df_ihsg[df_ihsg["Date"].dt.month == 12].copy()
    ihsg_ann["year"] = ihsg_ann["Date"].dt.year
    ihsg_ann[["year","return_yoy_pct"]]        .rename(columns={"return_yoy_pct":"ihsg_annual_return_pct"})        .to_csv(PROC/"ihsg_annual.csv", index=False)

    mean_ret = df_ihsg["return_yoy_pct"].dropna().mean()
    std_ret  = df_ihsg["return_yoy_pct"].dropna().std()
    print(f"  OK ihsg_annual.csv      -- mean YoY={mean_ret:.1f}%, std={std_ret:.1f}%")

def load_yield(folder_name, label):
    folder = INV_DIR / folder_name
    files  = list(folder.glob("*.csv")) if folder.exists() else []
    if not files:
        print(f"  WARN: Folder {folder_name} kosong atau tidak ada.")
        return None
    df = pd.read_csv(files[0], dtype=str)
    df["Date"]      = pd.to_datetime(df["Date"], format="mixed")
    df["yield_pct"] = df["Close"].apply(parse_dot_decimal)
    df = df[["Date","yield_pct"]].dropna().sort_values("Date")
    df = df[df["Date"].dt.year <= 2025]
    df["year_month"] = df["Date"].dt.strftime("%Y-%m")
    print(f"  OK {label:<20} -- {len(df)} baris | avg yield={df['yield_pct'].mean():.2f}%")
    return df[["year_month","yield_pct"]]

df_ob10 = load_yield("10 Tahun Obligasi 2015 - 2026", "Obligasi 10Y")
df_ob3  = load_yield("3 Tahun Obligasi 2015-2026",    "Obligasi 3Y")

frames = {}
if df_ob10 is not None:
    frames["ob10y_yield_pct"] = df_ob10.set_index("year_month")["yield_pct"]
if df_ob3 is not None:
    frames["ob3y_yield_pct"]  = df_ob3.set_index("year_month")["yield_pct"]

if frames:
    df_inv = pd.DataFrame(frames).reset_index().rename(columns={"index":"year_month"})
    df_inv = df_inv.sort_values("year_month").reset_index(drop=True)
    
    df_inv.to_csv(PROC/"investment_clean.csv", index=False)
    print(f"  OK investment_clean.csv -- {len(df_inv)} baris")

print("\n" + "=" * 55)
print("SELESAI -- Semua output di data/processed/")
print("=" * 55)

EXPECTED = [
    "cpi_monthly.csv", "cpi_clean.csv",
    "cpi_sektor_monthly.csv", "cpi_sektor_multiplier.csv",
    "mortality_clean.csv", "ae_ratio_clean.csv",
    "salary_clean.csv", "salary_growth.csv",
    "ihsg_monthly.csv", "ihsg_annual.csv", "investment_clean.csv",
]

for fname in EXPECTED:
    p = PROC / fname
    if p.exists():
        kb = p.stat().st_size / 1024
        print(f"  [OK] {fname:<35} {kb:6.1f} KB")
    else:
        print(f"  [!!] {fname:<35} BELUM DIBUAT")
