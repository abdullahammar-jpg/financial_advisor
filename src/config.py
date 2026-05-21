from pathlib import Path
import csv

_ROOT = Path(__file__).parents[1]
_PROC = _ROOT / "data" / "processed"

cpi_processed_path = _PROC / "cpi_clean.csv"
if cpi_processed_path.is_file():
    HISTORICAL_CPI_INDONESIA: dict[int, float] = {}
    with open(cpi_processed_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                year = int(row["year"].strip())
                val  = row.get("inflasi_pct", "").strip()
                if val:
                    HISTORICAL_CPI_INDONESIA[year] = float(val)
            except (ValueError, KeyError):
                continue
else:
    print(f"WARNING config.py: {cpi_processed_path} tidak ditemukan. Jalankan: python scripts/wrangle_all.py")
    HISTORICAL_CPI_INDONESIA = {}

_mult_path = _PROC / "cpi_sektor_multiplier.csv"
_mult_empiris = {"general": 1.00, "food": 1.269, "healthcare": 0.895, "education": 0.987}  
if _mult_path.is_file():
    with open(_mult_path, newline="", encoding="utf-8") as _f:
        for _row in csv.DictReader(_f):
            _s = _row.get("sektor", "").strip().lower()
            _v = _row.get("multiplier_median", "").strip()
            if _v:
                if _s == "makanan":    _mult_empiris["food"]       = float(_v)
                elif _s == "kesehatan": _mult_empiris["healthcare"] = float(_v)
                elif _s == "pendidikan": _mult_empiris["education"] = float(_v)

SECTORAL_INFLATION_MULTIPLIERS = {
    "general":    1.00,
    "healthcare": _mult_empiris["healthcare"],  
    "education":  _mult_empiris["education"],   
    "food":       _mult_empiris["food"],         
}

INFLATION_OU_PARAMS = {
    "theta": 3.50,   
    "kappa": 0.35,   
    "sigma": 1.45,   
    "floor": 0.50,   
    "ceiling": 15.0, 
} 

INVESTMENT_INSTRUMENTS = {
    "deposito": {
        "name": "Deposito Bank",
        "real_return_mean": 2.50,
        "real_return_std":  0.50,
        "nominal_return_mean": 5.00,
        "nominal_return_std":  1.00,
        "risk_level": 1,
        "tax_rate": 0.20,
        "min_investment": 1_000_000,
        "description": "Deposito bank dijamin LPS s.d. Rp 2 Miliar",
    }, 
    "ori_sbn": { 
        "name": "ORI / SBN (Obligasi Pemerintah)",
        "real_return_mean": 3.42,
        "real_return_std":  0.38,
        "nominal_return_mean": 6.92,
        "nominal_return_std":  0.38,
        "risk_level": 2,
        "tax_rate": 0.10,
        "min_investment": 1_000_000, 
        "description": "Obligasi Negara Ritel dijamin pemerintah Indonesia",
    },
    "rd_pasar_uang": { 
        "name": "Reksa Dana Pasar Uang",
        "real_return_mean": 2.50,
        "real_return_std":  0.40,
        "nominal_return_mean": 6.00,
        "nominal_return_std":  0.80,
        "risk_level": 2,
        "tax_rate": 0.00,
        "min_investment": 10_000, 
        "description": "Reksa Dana berbasis instrumen pasar uang likuiditas harian",
    },
    "rd_pendapatan_tetap": { 
        "name": "Reksa Dana Pendapatan Tetap",
        "real_return_mean": 4.00,
        "real_return_std":  1.50,
        "nominal_return_mean": 7.50,
        "nominal_return_std":  2.50,
        "risk_level": 3,
        "tax_rate": 0.00,
        "min_investment": 10_000,
        "description": "Reksa Dana Pendapatan Tetap berbasis obligasi korporasi dan pemerintah",
    },
    "rd_campuran": { 
        "name": "Reksa Dana Campuran",
        "real_return_mean": 5.50,
        "real_return_std":  4.00,
        "nominal_return_mean": 9.00,
        "nominal_return_std":  6.00,
        "risk_level": 4,
        "tax_rate": 0.00,
        "min_investment": 10_000,
        "description": "Reksa Dana Campuran antara saham dan obligasi untuk balanced growth, lebih berisiko",
    },
    "rd_saham_idx": {
        "name": "Reksa Dana Saham / IDX Composite",
        "proxy_ticker": "^JKSE",
        
        "real_return_mean": 3.60,
        "real_return_std":  13.10,
        "nominal_return_mean": 6.90,
        "nominal_return_std":  13.10,
        "risk_level": 5,
        "tax_rate": 0.00,
        "min_investment": 10_000,
        "description": "Berbasis IDX Composite (IHSG) via Reksa Dana indeks | Kalibrasi: IHSG 2010-2025",
    },
}

EMPIRICAL_CALIBRATION = {
    "ihsg_nominal_mean_yoy":  6.90,
    "ihsg_std_yoy":          13.10,
    "ob10y_avg_yield":        7.15,
    "ob3y_avg_yield":         6.34,  
    "cpi_avg_excl_anomali":   3.30,  
    "data_updated": "2026-05",
}

RISK_PROFILES = {
    "conservative": { 
        "label": "Konservatif",
        "description": "Prioritas preservasi modal, toleransi risiko rendah",
        "allocation": {
            "deposito": 0.30, "ori_sbn": 0.40, "rd_pasar_uang": 0.20,
            "rd_pendapatan_tetap": 0.10, "rd_campuran": 0.00, "rd_saham_idx": 0.00,
        },
    },
    "moderate": { 
        "label": "Moderat",
        "description": "Keseimbangan antara pertumbuhan dan stabilitas",
        "allocation": {
            "deposito": 0.10, "ori_sbn": 0.25, "rd_pasar_uang": 0.10,
            "rd_pendapatan_tetap": 0.15, "rd_campuran": 0.25, "rd_saham_idx": 0.15,
        },
    },
    "aggressive": { 
        "label": "Agresif",
        "description": "Prioritas pertumbuhan jangka panjang, toleransi risiko tinggi",
        "allocation": {
            "deposito": 0.05, "ori_sbn": 0.10, "rd_pasar_uang": 0.05,
            "rd_pendapatan_tetap": 0.10, "rd_campuran": 0.25, "rd_saham_idx": 0.45,
        },
    },
    "very_aggressive": { 
        "label": "Sangat Agresif",
        "description": "Maksimalkan pertumbuhan, siap menghadapi volatilitas tinggi",
        "allocation": {
            "deposito": 0.00, "ori_sbn": 0.05, "rd_pasar_uang": 0.00,
            "rd_pendapatan_tetap": 0.05, "rd_campuran": 0.15, "rd_saham_idx": 0.75,
        },
    },
}

PROFILE_ORDER = ["very_aggressive", "aggressive", "moderate", "conservative"]

MONTE_CARLO = {
    "n_simulations": 10_000, 
    "random_seed": 42, 
    "time_step_months": 1,
}

SAFE_WITHDRAWAL_RATES = {
    "conservative":    0.030, 
    "moderate":        0.035,
    "aggressive":      0.040,
    "very_aggressive": 0.045,
}

ACTUARIAL = {
    "planning_confidence_level": 0.90,  
    "mortality_improvement_rate": 0.005,
    
    "mortality_table_path": str(_PROC / "mortality_clean.csv"),
    "ae_ratio_path":        str(_PROC / "ae_ratio_clean.csv"),
}

CONTRIBUTION = {
    "salary_growth_rate":   0.05,   
    "annual_bonus_months":  1.0,    
    "bonus_savings_rate":   0.50,   
}

_sal_growth_path = _PROC / "salary_growth.csv"
SECTOR_SALARY_GROWTH: dict = {}
if _sal_growth_path.is_file():
    with open(_sal_growth_path, newline="", encoding="utf-8") as _f:
        for _row in csv.DictReader(_f):
            _sektor = _row.get("sektor", "").strip()
            _normal = _row.get("growth_normal", "").strip()
            _covid  = _row.get("growth_with_covid", "").strip()
            if _sektor and _normal:
                SECTOR_SALARY_GROWTH[_sektor] = {
                    "normal":              float(_normal),
                    "with_pandemic_risk":  float(_covid) if _covid else float(_normal),
                }
else:
    print(f"WARNING config.py: {_sal_growth_path} tidak ditemukan. Jalankan: python scripts/wrangle_all.py")
    
    SECTOR_SALARY_GROWTH = {
        "Rata-rata": {"normal": 0.0363, "with_pandemic_risk": 0.0471},
    }

LIFESTYLE = {
    "replacement_ratio": 0.70,  
    "healthcare_cost_ratio": {
        "age_55_65":  0.10,
        "age_65_75":  0.18,
        "age_75_plus": 0.28,
    },
}
