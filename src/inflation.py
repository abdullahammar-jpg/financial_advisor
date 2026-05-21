import numpy as np
import pandas as pd
from typing import Optional
from src.config import HISTORICAL_CPI_INDONESIA, INFLATION_OU_PARAMS, SECTORAL_INFLATION_MULTIPLIERS

def calibrate_ou_params(historical_data: Optional[dict] = None) -> dict:
    data = historical_data or HISTORICAL_CPI_INDONESIA

    if len(data) < 5:
        
        return {
            "theta": INFLATION_OU_PARAMS["theta"],
            "kappa": INFLATION_OU_PARAMS["kappa"],
            "sigma": INFLATION_OU_PARAMS["sigma"],
            "calibrated_from": "config_fallback (data < 5 obs)",
            "n_observations": len(data),
        }

    recent_years = sorted(data.keys())[-15:]
    series = np.array([data[y] for y in recent_years if not np.isnan(data[y])])

    if len(series) < 4:
        return {
            "theta": INFLATION_OU_PARAMS["theta"],
            "kappa": INFLATION_OU_PARAMS["kappa"],
            "sigma": INFLATION_OU_PARAMS["sigma"],
            "calibrated_from": "config_fallback (valid obs < 4)",
            "n_observations": len(series),
        }

    try:
        
        x = series[:-1]
        y = series[1:]
        n = len(x)

        beta  = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
        alpha = (np.sum(y) - beta * np.sum(x)) / n

        if beta <= 0 or beta >= 1:
            raise ValueError(f"beta={beta:.4f} diluar range (0,1)")

        kappa = -np.log(beta)
        theta = alpha / (1 - beta)
        resid = y - (alpha + beta * x)
        sigma = np.std(resid, ddof=1) * np.sqrt(2 * kappa / (1 - np.exp(-2 * kappa)))

        if not (0 < theta < 20) or not (0 < kappa < 5) or not (0 < sigma < 10):
            raise ValueError(f"Nilai kalibrasi diluar range wajar: theta={theta:.2f}, kappa={kappa:.2f}, sigma={sigma:.2f}")

        return {
            "theta": round(float(theta), 4),
            "kappa": round(float(kappa), 4),
            "sigma": round(float(sigma), 4),
            "calibrated_from": f"{recent_years[0]}-{recent_years[-1]}",
            "n_observations": n,
        }
    except Exception as e:
        print(f"[WARNING] Kalibrasi OU gagal: {e}. Menggunakan nilai dari config.")
        return {
            "theta": INFLATION_OU_PARAMS["theta"],
            "kappa": INFLATION_OU_PARAMS["kappa"],
            "sigma": INFLATION_OU_PARAMS["sigma"],
            "calibrated_from": f"config_fallback ({e})",
            "n_observations": 0,
        }

def simulate_inflation_paths(
    n_years: int,
    n_simulations: int = 10_000,
    initial_inflation: Optional[float] = None,
    params: Optional[dict] = None,
    random_seed: int = 42,
    sector: str = "general",
) -> np.ndarray:
    if params is None:
        params = calibrate_ou_params()

    theta = params.get("theta", INFLATION_OU_PARAMS["theta"])
    kappa = params.get("kappa", INFLATION_OU_PARAMS["kappa"])
    sigma = params.get("sigma", INFLATION_OU_PARAMS["sigma"])
    floor   = INFLATION_OU_PARAMS["floor"]
    ceiling = INFLATION_OU_PARAMS["ceiling"]

    if initial_inflation is None:
        last_year = max(HISTORICAL_CPI_INDONESIA.keys())
        initial_inflation = HISTORICAL_CPI_INDONESIA[last_year]

    multiplier = SECTORAL_INFLATION_MULTIPLIERS.get(sector, 1.0)

    rng = np.random.default_rng(random_seed)
    dt  = 1.0  

    paths = np.zeros((n_simulations, n_years))
    pi_t  = np.full(n_simulations, initial_inflation)

    for t in range(n_years):
        dW    = rng.standard_normal(n_simulations) * np.sqrt(dt)
        pi_t  = pi_t + kappa * (theta - pi_t) * dt + sigma * dW
        pi_t  = np.clip(pi_t, floor, ceiling)
        paths[:, t] = pi_t * multiplier

    return paths

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

def get_historical_series() -> pd.DataFrame:
    df = pd.DataFrame(
        list(HISTORICAL_CPI_INDONESIA.items()),
        columns=["year", "cpi_pct"]
    ).sort_values("year").reset_index(drop=True)
    df["cpi_decimal"] = df["cpi_pct"] / 100
    return df
