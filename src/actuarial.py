import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Literal
from src.config import ACTUARIAL

class MortalityTable:

    def __init__(self, table_path: Optional[str] = None):
        self.table_path = Path(table_path or ACTUARIAL["mortality_table_path"])
        self._qx_male: dict = {}
        self._qx_female: dict = {}
        self._lx_male: dict = {}
        self._lx_female: dict = {}
        self._max_age: int = 111  
        self._source: str = ""
        self._ae_male: dict = {}    # A/E ratio per usia (male)
        self._ae_female: dict = {}  # A/E ratio per usia (female)
        self._load_ae_ratio()       # muat A/E sebelum _load()
        self._load()

    #! Muat A/E ratio dari ae_ratio_clean.csv untuk mortality improvement factor
    def _load_ae_ratio(self):
        """
        A/E (Actual-to-Expected) ratio dari BPJS 2018-2022.
        Nilai > 1: mortalitas aktual lebih tinggi dari tabel standar (mis. COVID).
        Nilai < 1: mortalitas aktual lebih rendah (mis. underreporting).
        Digunakan untuk menyesuaikan qx agar lebih mencerminkan pengalaman Indonesia.
        """
        fp = Path(__file__).parents[1] / "data" / "processed" / "ae_ratio_clean.csv"
        if not fp.exists():
            return  # fallback: tidak ada adjustment
        try:
            df = pd.read_csv(fp)
            if "age" not in df.columns:
                return
            if "ae_avg_male" in df.columns:
                self._ae_male = dict(zip(df["age"].astype(int), df["ae_avg_male"].fillna(1.0)))
            if "ae_avg_female" in df.columns:
                self._ae_female = dict(zip(df["age"].astype(int), df["ae_avg_female"].fillna(1.0)))
            print(f"[actuarial.py] A/E ratio dimuat: {len(self._ae_male)} usia dari ae_ratio_clean.csv")
        except Exception as e:
            print(f"[actuarial.py] Gagal load ae_ratio_clean.csv: {e}")

    def _apply_ae(self, qx_dict: dict, gender: str) -> dict:
        """Terapkan A/E adjustment ke qx per usia."""
        ae = self._ae_male if gender == "male" else self._ae_female
        if not ae:
            return qx_dict  # tidak ada data A/E
        return {
            age: min(float(qx) * float(ae.get(age, 1.0)), 1.0)
            for age, qx in qx_dict.items()
        }

    #! Fungsi pembuka pemuatan tabel mortalitas
    def _load(self):
        if self.table_path.exists():
            self._load_from_csv()
        else:
            print(
                f"[WARNING] Tabel mortalitas BPJS tidak ditemukan di '{self.table_path}'.\n"
                "          Menggunakan synthetic Gompertz-Makeham (Indonesia-calibrated).\n"
                "          Ganti dengan data BPJS asli untuk akurasi lebih tinggi."
            )
            self._load_gompertz_synthetic()

    #! Pemuatan data qx (peluang mati) dari dataset processed mortality_clean.csv
    def _load_from_csv(self):
        df = pd.read_csv(self.table_path)
        required_cols = {"age", "qx_male", "qx_female"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Kolom berikut tidak ada di CSV mortalitas: {missing}")

        self._max_age = int(df["age"].max())

        # Mengisi data usia yang bolong menggunakan interpolasi cubic spline
        full_ages = pd.DataFrame({"age": range(0, self._max_age + 1)})
        df = full_ages.merge(df[["age", "qx_male", "qx_female"]], on="age", how="left")
        df = df.interpolate(method="cubic")
        df["qx_male"]   = df["qx_male"].clip(0.0001, 1.0)
        df["qx_female"] = df["qx_female"].clip(0.0001, 1.0)
        
        # Batasi peluang mati di usia maksimal adalah pasti (1.0)
        df.loc[df["age"] == self._max_age, ["qx_male", "qx_female"]] = 1.0

        self._qx_male   = dict(zip(df["age"], df["qx_male"]))
        self._qx_female = dict(zip(df["age"], df["qx_female"]))
        # Terapkan A/E adjustment dari pengalaman BPJS 2018-2022
        self._qx_male   = self._apply_ae(self._qx_male,   "male")
        self._qx_female = self._apply_ae(self._qx_female, "female")
        self._compute_lx()
        self._source = f"TMPI 2023 (BPJS/PAI/ITB): {self.table_path.name}"
        if self._ae_male:
            self._source += " + A/E adjustment (ae_ratio_clean.csv 2018-2022)"

    #! Pemuatan model kematian sintetis Gompertz-Makeham jika file data absen
    def _load_gompertz_synthetic(self):
        params = {
            "male":   {"A": 0.0007, "B": 0.000060, "c": 1.0915},
            "female": {"A": 0.0004, "B": 0.000035, "c": 1.0920},
        }
        for gender, p in params.items():
            qx_dict = {}
            for age in range(0, 101):
                if age == 100:
                    qx_dict[age] = 1.0
                else:
                    # Persamaan Gompertz-Makeham
                    mu = p["A"] + p["B"] * (p["c"] ** age)
                    qx = min(1 - np.exp(-mu), 1.0)
                    
                    # Kalibrasi manual khusus usia balita/anak-anak
                    if age == 0:
                        qx = max(qx, 0.024)
                    elif age < 5:
                        qx = max(qx, 0.003 - age * 0.0005)
                    qx_dict[age] = max(qx, 0.0001)
            if gender == "male":
                self._qx_male = qx_dict
            else:
                self._qx_female = qx_dict

        self._compute_lx()
        self._source = "Synthetic Gompertz-Makeham (Indonesia-calibrated, fallback)"
        if self._ae_male:
            self._source += " + A/E adjustment (ae_ratio_clean.csv 2018-2022)"

    #! Kalkulasi lx (jumlah orang yang bertahan hidup dari kohort 100.000 jiwa)
    def _compute_lx(self):
        radix = 100_000
        for gender in ["male", "female"]:
            qx = self._qx_male if gender == "male" else self._qx_female
            lx = {}
            lx[0] = radix
            for age in range(0, self._max_age):
                lx[age + 1] = lx[age] * (1 - qx.get(age, 1.0))
            lx[self._max_age] = 0
            if gender == "male":
                self._lx_male = lx
            else:
                self._lx_female = lx

    #! Mengambil nilai qx untuk usia dan gender tertentu
    def get_qx(self, age: int, gender: Literal["male", "female"]) -> float:
        qx = self._qx_male if gender == "male" else self._qx_female
        return qx.get(int(age), 1.0)

    #! Menghitung probabilitas bertahan hidup dari current_age s.d. target_age
    def survival_probability(
        self,
        current_age: int,
        target_age: int,
        gender: Literal["male", "female"],
    ) -> float:
        if target_age <= current_age:
            return 1.0
        lx = self._lx_male if gender == "male" else self._lx_female
        l_current = lx.get(int(current_age), 1)
        l_target  = lx.get(int(target_age), 0)
        if l_current == 0:
            return 0.0
        return l_target / l_current

    #! Menghitung rata-rata sisa harapan hidup di usia tertentu
    def expected_remaining_life(
        self, age: int, gender: Literal["male", "female"]
    ) -> float:
        lx = self._lx_male if gender == "male" else self._lx_female
        l_x = lx.get(int(age), 0)
        if l_x == 0:
            return 0.0
        ex = sum(lx.get(t, 0) for t in range(int(age) + 1, self._max_age + 1)) / l_x
        return round(ex, 2)

    #! Menghitung persentil kematian / survival age untuk merencanakan ketahanan dana
    def get_longevity_percentile(
        self,
        current_age: int,
        gender: Literal["male", "female"],
        percentile: float = 0.90,
    ) -> int:
        for target_age in range(int(current_age) + 1, self._max_age + 1):
            sp = self.survival_probability(current_age, target_age, gender)
            if sp <= (1 - percentile):
                return target_age
        return self._max_age

    #! Menghasilkan ringkasan laporan aktuaria lengkap (harapan hidup, longevity risk)
    def get_planning_summary(
        self, current_age: int, retirement_age: int, gender: Literal["male", "female"]
    ) -> dict:
        expected_death = current_age + self.expected_remaining_life(current_age, gender)
        p50_survival   = self.get_longevity_percentile(current_age, gender, 0.50)
        p75_survival   = self.get_longevity_percentile(current_age, gender, 0.75)
        p90_survival   = self.get_longevity_percentile(current_age, gender, 0.90)

        planning_age   = p90_survival  
        horizon_post_retirement = max(planning_age - retirement_age, 0)

        return {
            "source":                    self._source,
            "current_age":               current_age,
            "gender":                    gender,
            "expected_death_age":        round(expected_death, 1),
            "p50_survival_age":          p50_survival,
            "p75_survival_age":          p75_survival,
            "p90_survival_age":          p90_survival,
            "planning_age_recommended":  planning_age,
            "years_to_retirement":       retirement_age - current_age,
            "planning_horizon_post_retirement": horizon_post_retirement,
            "survival_prob_at_retirement": round(
                self.survival_probability(current_age, retirement_age, gender), 4
            ),
            "longevity_risk_flag": expected_death < (retirement_age + 15),
            "warning": (
                "Harapan hidup mendekati target pensiun. Pertimbangkan pensiun lebih awal "
                "atau perlindungan asuransi jiwa tambahan."
                if expected_death < (retirement_age + 15) else None
            ),
        }

_mortality_table: Optional[MortalityTable] = None

#! Singletone getter untuk tabel mortalitas
def get_mortality_table() -> MortalityTable:
    global _mortality_table
    if _mortality_table is None:
        _mortality_table = MortalityTable()
    return _mortality_table
