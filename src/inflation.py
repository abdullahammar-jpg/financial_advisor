import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
from src.config import HISTORICAL_CPI_INDONESIA, INFLATION_OU_PARAMS, SECTORAL_INFLATION_MULTIPLIERS

#! ─── Konstanta filter bersama ──────────────────────────────────────────────
_CUTOFF      = pd.Timestamp("2025-12-31")   # data 2026 belum lengkap setahun
_COVID_START = pd.Timestamp("2020-02-01")   # shock pandemi mulai
_COVID_END   = pd.Timestamp("2021-07-31")   # PPKM berakhir


def _filter_general_cpi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter untuk CPI UMUM (cpi_monthly.csv).
    Tahun 2015 TIDAK perlu di-exclude secara eksplisit karena inflation_yoy_pct
    di 2015 sudah NaN (tidak ada data 2014 sebagai pembanding) → terbuang oleh dropna.
    Yang di-exclude: cutoff Des 2025 + COVID window.
    """
    mask = (
        (df["year_month"] <= _CUTOFF) &
        ~((df["year_month"] >= _COVID_START) & (df["year_month"] <= _COVID_END))
    )
    return df[mask].copy()


def _filter_sectoral_cpi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter untuk CPI SEKTORAL (cpi_sektor_monthly.csv).
    Tahun 2015 HARUS di-exclude secara eksplisit karena YoY sektoral 2015
    di-backfill dengan satu angka konstanta (misal makanan: 6.595% × 12 bulan).
    Jika masuk regresi OU → 12 pasang identik → beta = 1 → kappa = 0 (tidak ada
    mean reversion). Sama: cutoff Des 2025 + COVID window.
    """
    mask = (
        (df["year_month"] <= _CUTOFF) &
        (df["year_month"].dt.year != 2015) &
        ~((df["year_month"] >= _COVID_START) & (df["year_month"] <= _COVID_END))
    )
    return df[mask].copy()


#! Muat YoY bulanan CPI UMUM dari cpi_monthly.csv
def _load_monthly_cpi_yoy() -> Optional[np.ndarray]:
    """
    Sumber: cpi_monthly.csv — CPI agregat nasional (semua kelompok).
    Filter: dropna (buang 2015 NaN otomatis) + cutoff Des 2025 + exclude COVID.
    Hasil: ~96 obs bersih (Jan 2016 – Des 2025, tanpa COVID window).
    """
    fp = Path(__file__).parents[1] / "data" / "processed" / "cpi_monthly.csv"
    if not fp.exists():
        return None
    try:
        df = pd.read_csv(fp)
        df["year_month"] = pd.to_datetime(df["year_month"])
        df = df.dropna(subset=["inflation_yoy_pct"])
        df_clean = _filter_general_cpi(df)

        if len(df_clean) < 10:
            return None

        arr = df_clean["inflation_yoy_pct"].values
        print(f"[inflation.py] CPI umum: {len(arr)} obs "
              f"({df_clean['year_month'].min().strftime('%Y-%m')} – "
              f"{df_clean['year_month'].max().strftime('%Y-%m')}), "
              f"mean={arr.mean():.2f}%, std={arr.std():.2f}%")
        return arr
    except Exception as e:
        print(f"[inflation.py] Gagal load CPI umum: {e}")
        return None


#! Muat YoY bulanan CPI SEKTORAL dari cpi_sektor_monthly.csv
def _load_sectoral_cpi_yoy(sector: str) -> Optional[np.ndarray]:
    """
    Sumber: cpi_sektor_monthly.csv — CPI per kelompok pengeluaran.
    Sektor: 'makanan'/'food', 'kesehatan'/'healthcare', 'pendidikan'/'education'.
    Filter: IDENTIK dengan _load_monthly_cpi_yoy (exclude 2015, COVID, cutoff Des 2025).
    Hasil: ~96 obs bersih per sektor — sama dengan CPI umum.

    Keunggulan vs multiplier statis:
      - theta berbeda per sektor (makanan ~4-5%, kesehatan ~3-4%, pendidikan ~2-3%)
      - sigma dan kappa mencerminkan volatilitas dan kecepatan mean-reversion masing-masing
    """
    fp = Path(__file__).parents[1] / "data" / "processed" / "cpi_sektor_monthly.csv"
    if not fp.exists():
        return None
    sector_map = {
        "food":       "makanan",
        "healthcare": "kesehatan",
        "education":  "pendidikan",
        "makanan":    "makanan",
        "kesehatan":  "kesehatan",
        "pendidikan": "pendidikan",
    }
    csv_label = sector_map.get(sector)
    if csv_label is None:
        return None
    try:
        df = pd.read_csv(fp)
        df["year_month"] = pd.to_datetime(df["year_month"])
        df_sec = df[df["sektor"] == csv_label].dropna(subset=["inflation_yoy_pct"])
        # 2015 di-exclude eksplisit karena YoY sektoral diisi backfill (bukan perhitungan nyata)
        df_clean = _filter_sectoral_cpi(df_sec)

        if len(df_clean) < 10:
            return None

        arr = df_clean["inflation_yoy_pct"].values
        print(f"[inflation.py] CPI '{csv_label}': {len(arr)} obs "
              f"({df_clean['year_month'].min().strftime('%Y-%m')} – "
              f"{df_clean['year_month'].max().strftime('%Y-%m')}), "
              f"mean={arr.mean():.2f}%, std={arr.std():.2f}%")
        return arr
    except Exception as e:
        print(f"[inflation.py] Gagal load CPI sektoral '{sector}': {e}")
        return None


#! Kalibrasi parameter model Ornstein-Uhlenbeck (OU) berdasarkan regresi linear data historis
def calibrate_ou_params(
    historical_data=None,
    series_array: Optional[np.ndarray] = None,
    source_label: str = "",
) -> dict:
    """
    Kalibrasi OU — urutan prioritas:
      1. series_array (np.ndarray)          → langsung dari loader monthly/sektoral
      2. Auto-load cpi_monthly.csv           → _load_monthly_cpi_yoy()
      3. historical_data (dict {year: pct}) → fallback lama
      4. HISTORICAL_CPI_INDONESIA config     → fallback terakhir
    """
    _fallback = {
        "theta":           INFLATION_OU_PARAMS["theta"],
        "kappa":           INFLATION_OU_PARAMS["kappa"],
        "sigma":           INFLATION_OU_PARAMS["sigma"],
        "calibrated_from": "config_fallback",
        "n_observations":  0,
    }

    # Bangun series berdasarkan input
    if series_array is not None and len(series_array) >= 5:
        series = np.asarray(series_array, dtype=float)
        series = series[~np.isnan(series)]
        src    = source_label or "array_input"

    elif historical_data is None:
        arr = _load_monthly_cpi_yoy()
        if arr is not None and len(arr) >= 5:
            series = arr
            src    = source_label or "cpi_monthly.csv (YoY bulanan)"
        else:
            data   = HISTORICAL_CPI_INDONESIA
            years  = sorted(data.keys())[-15:]
            series = np.array([data[y] for y in years if not np.isnan(data[y])])
            src    = "config HISTORICAL_CPI_INDONESIA"

    else:
        data   = historical_data
        years  = sorted(data.keys())[-15:]
        series = np.array([data[y] for y in years if not np.isnan(data[y])])
        src    = source_label or "custom dict"

    if len(series) < 4:
        _fallback["calibrated_from"] = f"config_fallback (hanya {len(series)} obs valid)"
        _fallback["n_observations"]  = len(series)
        return _fallback

    # Regresi OLS: X_t = α + β·X_{t-1}
    try:
        x = series[:-1]
        y = series[1:]
        n = len(x)

        beta  = (n*np.sum(x*y) - np.sum(x)*np.sum(y)) / (n*np.sum(x**2) - np.sum(x)**2)
        alpha = (np.sum(y) - beta*np.sum(x)) / n

        if beta <= 0 or beta >= 1:
            raise ValueError(f"beta={beta:.4f} diluar range (0,1)")

        kappa = -np.log(beta)
        theta = alpha / (1 - beta)
        resid = y - (alpha + beta*x)
        sigma = np.std(resid, ddof=1) * np.sqrt(2*kappa / (1 - np.exp(-2*kappa)))

        if not (0 < theta < 20) or not (0 < kappa < 5) or not (0 < sigma < 10):
            raise ValueError(f"Diluar range wajar: θ={theta:.2f}, κ={kappa:.2f}, σ={sigma:.2f}")

        return {
            "theta":           round(float(theta), 4),
            "kappa":           round(float(kappa), 4),
            "sigma":           round(float(sigma), 4),
            "calibrated_from": f"{src} (n={n})",
            "n_observations":  n,
        }
    except Exception as e:
        print(f"[WARNING] Kalibrasi OU gagal: {e}. Menggunakan nilai dari config.")
        _fallback["calibrated_from"] = f"config_fallback ({e})"
        return _fallback

#! Simulasi jalur inflasi acak — Ornstein-Uhlenbeck, kalibrasi per sektor dari data historis
def simulate_inflation_paths(
    n_years: int,
    n_simulations: int = 10_000,
    initial_inflation: Optional[float] = None,
    params: Optional[dict] = None,
    random_seed: int = 42,
    sector: str = "general",
) -> np.ndarray:
    """
    Hasilkan matriks (n_simulations × n_years) jalur inflasi stokastik (OU).

    Untuk sektor 'healthcare', 'food', 'education' — kalibrasi dari cpi_sektor_monthly.csv:
      → theta, kappa, sigma mencerminkan dinamika inflasi sektor tersebut secara independen
      → TIDAK lagi hanya multiplier statis × inflasi umum
    Untuk 'general' / tidak dikenal → kalibrasi dari cpi_monthly.csv (inflasi agregat).
    """
    if params is None:
        sector_csv_map = {
            "healthcare": "kesehatan",
            "food":       "makanan",
            "education":  "pendidikan",
        }
        csv_sector = sector_csv_map.get(sector)
        if csv_sector is not None:
            arr = _load_sectoral_cpi_yoy(csv_sector)
            if arr is not None:
                params = calibrate_ou_params(
                    series_array=arr,
                    source_label=f"cpi_sektor '{csv_sector}'",
                )
        if params is None:
            params = calibrate_ou_params()  # umum / fallback

    theta   = params.get("theta",   INFLATION_OU_PARAMS["theta"])
    kappa   = params.get("kappa",   INFLATION_OU_PARAMS["kappa"])
    sigma   = params.get("sigma",   INFLATION_OU_PARAMS["sigma"])
    floor   = INFLATION_OU_PARAMS["floor"]
    ceiling = INFLATION_OU_PARAMS["ceiling"]

    if initial_inflation is None:
        last_year = max(HISTORICAL_CPI_INDONESIA.keys())
        initial_inflation = HISTORICAL_CPI_INDONESIA[last_year]

    rng   = np.random.default_rng(random_seed)
    dt    = 1.0
    paths = np.zeros((n_simulations, n_years))
    pi_t  = np.full(n_simulations, float(initial_inflation))

    for t in range(n_years):
        dW   = rng.standard_normal(n_simulations) * np.sqrt(dt)
        pi_t = pi_t + kappa * (theta - pi_t) * dt + sigma * dW
        pi_t = np.clip(pi_t, floor, ceiling)
        paths[:, t] = pi_t

    return paths

#! Menghasilkan ringkasan ringkas proyeksi inflasi masa depan
def get_inflation_summary(n_years: int = 30, sector: str = "general") -> dict:
    paths = simulate_inflation_paths(n_years=n_years, n_simulations=10_000, sector=sector)
    avg_per_sim   = paths.mean(axis=1)  

    return {
        "sector": sector,
        "n_years": n_years,
        "historical_mean_pct": round(np.mean(list(HISTORICAL_CPI_INDONESIA.values())), 2),
        "projected_mean_pct":  round(float(avg_per_sim.mean()), 2),
        "projected_p10_pct":   round(float(np.percentile(avg_per_sim, 10)), 2),
        "projected_p50_pct":   round(float(np.percentile(avg_per_sim, 50)), 2),
        "projected_p90_pct":   round(float(np.percentile(avg_per_sim, 90)), 2),
        "calibrated_params":   calibrate_ou_params(),
    }

#! Mengambil deret data inflasi historis terformat pandas dataframe
def get_historical_series() -> pd.DataFrame:
    df = pd.DataFrame(
        list(HISTORICAL_CPI_INDONESIA.items()),
        columns=["year", "cpi_pct"]
    ).sort_values("year").reset_index(drop=True)
    df["cpi_decimal"] = df["cpi_pct"] / 100
    return df
