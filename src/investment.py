from typing import Optional
from pathlib import Path

import numpy as np
import pandas as pd
from src.config import (
    INVESTMENT_INSTRUMENTS,
    RISK_PROFILES,
    PROFILE_ORDER,
    EMPIRICAL_CALIBRATION,
)

_ROOT = Path(__file__).parents[1]
_PROC = _ROOT / "data" / "processed"

def _load_ihsg_empirical() -> dict:
    fp = _PROC / "ihsg_annual.csv"
    if not fp.exists():
        print("[investment.py] ihsg_annual.csv tidak ditemukan, pakai EMPIRICAL_CALIBRATION dari config.")
        return {
            "mean_pct": EMPIRICAL_CALIBRATION["ihsg_nominal_mean_yoy"],
            "std_pct":  EMPIRICAL_CALIBRATION["ihsg_std_yoy"],
            "n_obs":    0,
            "source":   "config_fallback",
        }

    df = pd.read_csv(fp)
    col = [c for c in df.columns if "return" in c.lower() or "yoy" in c.lower()]
    if not col:
        return {
            "mean_pct": EMPIRICAL_CALIBRATION["ihsg_nominal_mean_yoy"],
            "std_pct":  EMPIRICAL_CALIBRATION["ihsg_std_yoy"],
            "n_obs":    0,
            "source":   "config_fallback (col not found)",
        }

    series = df[col[0]].dropna()
    
    if "year" in df.columns:
        mask = ~df["year"].isin([2020])
        series_clean = df.loc[mask, col[0]].dropna()
    else:
        series_clean = series

    mean_val = float(series_clean.mean()) if len(series_clean) > 0 else EMPIRICAL_CALIBRATION["ihsg_nominal_mean_yoy"]
    std_val  = float(series_clean.std())  if len(series_clean) > 1 else EMPIRICAL_CALIBRATION["ihsg_std_yoy"]

    return {
        "mean_pct": round(mean_val, 2),
        "std_pct":  round(std_val, 2),
        "n_obs":    len(series_clean),
        "source":   f"ihsg_annual.csv ({len(series_clean)} obs, excl 2020)",
    }

def _load_bond_empirical() -> dict:
    fp = _PROC / "investment_clean.csv"
    if not fp.exists():
        return {
            "ob10y_mean": EMPIRICAL_CALIBRATION["ob10y_avg_yield"],
            "ob3y_mean":  EMPIRICAL_CALIBRATION["ob3y_avg_yield"],
            "source":     "config_fallback",
        }

    df = pd.read_csv(fp)
    ob10y = df["ob10y_yield_pct"].dropna().mean() if "ob10y_yield_pct" in df.columns else EMPIRICAL_CALIBRATION["ob10y_avg_yield"]
    ob3y  = df["ob3y_yield_pct"].dropna().mean()  if "ob3y_yield_pct"  in df.columns else EMPIRICAL_CALIBRATION["ob3y_avg_yield"]

    if pd.isna(ob3y):
        ob3y = EMPIRICAL_CALIBRATION["ob3y_avg_yield"]

    return {
        "ob10y_mean": round(float(ob10y), 2),
        "ob3y_mean":  round(float(ob3y),  2),
        "source":     "investment_clean.csv",
    }

_IHSG_CALIB  = _load_ihsg_empirical()
_BOND_CALIB  = _load_bond_empirical()
_AVG_INFLASI = EMPIRICAL_CALIBRATION.get("cpi_avg_excl_anomali", 3.30)

INVESTMENT_INSTRUMENTS["rd_saham_idx"]["nominal_return_mean"] = _IHSG_CALIB["mean_pct"]
INVESTMENT_INSTRUMENTS["rd_saham_idx"]["nominal_return_std"]  = _IHSG_CALIB["std_pct"]
INVESTMENT_INSTRUMENTS["rd_saham_idx"]["real_return_mean"]    = round(_IHSG_CALIB["mean_pct"] - _AVG_INFLASI, 2)
INVESTMENT_INSTRUMENTS["rd_saham_idx"]["real_return_std"]     = _IHSG_CALIB["std_pct"]

_ob10y_nom = _BOND_CALIB["ob10y_mean"]
INVESTMENT_INSTRUMENTS["ori_sbn"]["nominal_return_mean"] = _ob10y_nom
INVESTMENT_INSTRUMENTS["ori_sbn"]["real_return_mean"]    = round(_ob10y_nom - _AVG_INFLASI, 2)

print(
    f"[investment.py] Kalibrasi empiris: "
    f"IHSG mean={_IHSG_CALIB['mean_pct']:.1f}% std={_IHSG_CALIB['std_pct']:.1f}% "
    f"({_IHSG_CALIB['source']}) | "
    f"OB10Y={_ob10y_nom:.2f}% | OB3Y={_BOND_CALIB['ob3y_mean']:.2f}%"
)

_INSTRUMENTS_ORDER = [
    "deposito", "ori_sbn", "rd_pasar_uang",
    "rd_pendapatan_tetap", "rd_campuran", "rd_saham_idx",
]

_CORRELATION_MATRIX = np.array([
    
    [1.00,  0.10,  0.95,  0.05, -0.05, -0.10],  
    [0.10,  1.00,  0.15,  0.75,  0.45,  0.20],  
    [0.95,  0.15,  1.00,  0.10,  0.00, -0.05],  
    [0.05,  0.75,  0.10,  1.00,  0.60,  0.35],  
    [-0.05, 0.45,  0.00,  0.60,  1.00,  0.80],  
    [-0.10, 0.20, -0.05,  0.35,  0.80,  1.00],  
])

def get_glide_path_profile(
    base_profile: str, years_to_retirement: int
) -> str:
    idx = PROFILE_ORDER.index(base_profile) if base_profile in PROFILE_ORDER else 1

    if years_to_retirement > 20:
        shift = 0
    elif years_to_retirement > 10:
        shift = 1
    elif years_to_retirement > 5:
        shift = 2
    else:
        shift = 3  

    effective_idx = min(idx + shift, len(PROFILE_ORDER) - 1)
    return PROFILE_ORDER[effective_idx]

def get_portfolio_stats(profile: str, custom_deposit_rate: Optional[float] = None) -> dict:
    alloc = RISK_PROFILES[profile]["allocation"]
    instruments = INVESTMENT_INSTRUMENTS

    w_nominal_mean = 0.0
    w_real_mean    = 0.0
    weights = []
    stds_nominal = []

    for inst_key in _INSTRUMENTS_ORDER:
        w = alloc.get(inst_key, 0.0)
        inst = instruments[inst_key]

        nom_mean  = inst["nominal_return_mean"]
        real_mean = inst["real_return_mean"]

        if inst_key == "deposito" and custom_deposit_rate is not None:
            nom_mean  = custom_deposit_rate
            real_mean = custom_deposit_rate - _AVG_INFLASI

        w_nominal_mean += w * nom_mean
        w_real_mean    += w * real_mean
        weights.append(w)
        stds_nominal.append(inst["nominal_return_std"])

    w = np.array(weights)
    s = np.array(stds_nominal)

    cov_matrix   = np.outer(s, s) * _CORRELATION_MATRIX
    port_variance = float(w @ cov_matrix @ w)
    port_std      = np.sqrt(max(port_variance, 0.0))  

    return {
        "profile":              profile,
        "nominal_return_mean":  round(w_nominal_mean, 4),
        "nominal_return_std":   round(port_std, 4),
        "real_return_mean":     round(w_real_mean, 4),
        "allocation":           alloc,
        "calibration_source":   {
            "ihsg": _IHSG_CALIB["source"],
            "bond": _BOND_CALIB["source"],
        },
    }

def simulate_portfolio_returns(
    profile: str,
    n_years: int,
    n_simulations: int = 10_000,
    random_seed: int = 42,
    inflation_paths: Optional[np.ndarray] = None,
    custom_deposit_rate: Optional[float] = None,
) -> np.ndarray:
    stats = get_portfolio_stats(profile, custom_deposit_rate=custom_deposit_rate)

    mu_pct    = stats["nominal_return_mean"]
    sigma_pct = stats["nominal_return_std"]

    mu_norm    = 1 + mu_pct / 100
    sigma_norm = sigma_pct / (100 + mu_pct)
    mu_log     = np.log(mu_norm) - 0.5 * np.log(1 + sigma_norm**2)
    sigma_log  = np.sqrt(np.log(1 + sigma_norm**2))

    rng = np.random.default_rng(random_seed)
    raw_returns = rng.lognormal(mu_log, sigma_log, size=(n_simulations, n_years)) - 1

    raw_returns = np.clip(raw_returns, -0.80, 2.00)

    if inflation_paths is not None:
        
        inf_dec = np.clip(inflation_paths / 100, -0.10, 0.30)
        
        if inf_dec.shape[1] != n_years:
            if inf_dec.shape[1] > n_years:
                inf_dec = inf_dec[:, :n_years]
            else:
                pad = np.full((n_simulations, n_years - inf_dec.shape[1]), _AVG_INFLASI / 100)
                inf_dec = np.hstack([inf_dec, pad])
        real_returns = (1 + raw_returns) / (1 + inf_dec) - 1
        return real_returns

    real_returns = (1 + raw_returns) / (1 + _AVG_INFLASI / 100) - 1
    return real_returns

def fetch_idx_historical_returns(period: str = "10y") -> pd.DataFrame:
    
    fp = _PROC / "ihsg_annual.csv"
    if fp.exists():
        df = pd.read_csv(fp)
        ret_col = [c for c in df.columns if "return" in c.lower() or "yoy" in c.lower()]
        if ret_col and "year" in df.columns:
            result = df[["year", ret_col[0]]].dropna()
            result.columns = ["year", "annual_return_pct"]
            return result.reset_index(drop=True)

    try:
        import yfinance as yf  
        ticker = yf.Ticker("^JKSE")
        hist   = ticker.history(period=period, interval="1mo")
        if hist.empty:
            raise ValueError("Data IDX kosong dari yfinance")
        hist.index = pd.to_datetime(hist.index)
        monthly_returns = hist["Close"].pct_change().dropna()
        annual_returns  = ((1 + monthly_returns).resample("YE").prod() - 1) * 100
        df = annual_returns.reset_index()
        df.columns = ["date", "annual_return_pct"]
        df["year"] = df["date"].dt.year
        return df[["year", "annual_return_pct"]].dropna()
    except Exception as e:
        print(f"[WARNING] Gagal fetch data IDX dari yfinance: {e}")
        
        fallback = {
            2014: 22.3, 2015: -12.1, 2016: 15.3, 2017: 20.0,
            2018: -2.5, 2019: 1.7,   2020: -5.1, 2021: 10.1,
            2022: 4.1,  2023: 6.2,   2024: 3.5,
        }
        return pd.DataFrame(list(fallback.items()), columns=["year", "annual_return_pct"])

def get_instrument_comparison_table() -> pd.DataFrame:
    rows = []
    for key, inst in INVESTMENT_INSTRUMENTS.items():
        rows.append({
            "Kode":                  key,
            "Instrumen":             inst["name"],
            "Return Nominal (mean)": f"{inst['nominal_return_mean']}%",
            "Volatilitas":           f"{inst['nominal_return_std']}%",
            "Return Real (mean)":    f"{inst['real_return_mean']}%",
            "Risk Level":            inst["risk_level"],
            "Pajak":                 f"{int(inst['tax_rate']*100)}%",
            "Min. Investasi":        f"Rp {inst['min_investment']:,}",
            "Deskripsi":             inst["description"],
        })
    return pd.DataFrame(rows)

def get_calibration_summary() -> dict:
    return {
        "ihsg": _IHSG_CALIB,
        "bond": _BOND_CALIB,
        "avg_inflation_used": _AVG_INFLASI,
        "instruments_updated": {
            "rd_saham_idx": {
                "nominal_return_mean": INVESTMENT_INSTRUMENTS["rd_saham_idx"]["nominal_return_mean"],
                "nominal_return_std":  INVESTMENT_INSTRUMENTS["rd_saham_idx"]["nominal_return_std"],
            },
            "ori_sbn": {
                "nominal_return_mean": INVESTMENT_INSTRUMENTS["ori_sbn"]["nominal_return_mean"],
            },
        },
    }
