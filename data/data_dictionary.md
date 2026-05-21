# Data Dictionary — AI Financial Advisor
**Last Updated:** April 2026 | **Currency:** IDR

---

## Input Variables

| Variabel | Tipe | Contoh | Deskripsi |
|----------|------|--------|-----------|
| `name` | str | "Rizky" | Nama pengguna |
| `age` | int | 25 | Usia saat ini (tahun) |
| `gender` | str | "male" / "female" | Jenis kelamin, mempengaruhi tabel mortalitas |
| `monthly_salary` | float | 8000000 | Gaji bulanan kotor (IDR) |
| `savings_rate` | float | 0.20 | Proporsi gaji yang ditabung/diinvestasikan (0.0–1.0) |
| `retirement_age` | int | 55 | Target usia pensiun |
| `risk_profile` | str | "moderate" | Profil risiko: conservative / moderate / aggressive / very_aggressive |
| `monthly_expense` | float | opsional | Pengeluaran bulanan saat pensiun (jika None, dihitung dari replacement_ratio) |

---

## Actuarial Variables

| Variabel | Sumber | Deskripsi |
|----------|--------|-----------|
| `qx` | Tabel Mortalitas BPJS | Probabilitas meninggal dalam setahun pada usia x |
| `lx` | Dihitung dari qx | Jumlah orang hidup dari 100.000 radix pada usia x |
| `ex` | Dihitung dari lx | Harapan hidup sisa (curtate life expectancy) dari usia x |
| `survival_probability` | Dihitung | P(hidup di usia T \| hidup di usia t), t < T |
| `p90_survival_age` | Dihitung | Usia di mana 10% populasi masih hidup (digunakan sebagai planning horizon) |
| `longevity_risk_flag` | Dihitung | True jika expected death age < retirement_age + 15 |

---

## Inflation Variables

| Variabel | Sumber | Deskripsi |
|----------|--------|-----------|
| `cpi_pct` | BPS Indonesia | Inflasi CPI tahunan dalam persen (%) |
| `theta` (θ) | Dikalibrasi dari BPS | Long-term mean inflasi dalam model OU (target jangka panjang) |
| `kappa` (κ) | Dikalibrasi dari BPS | Kecepatan mean-reversion model OU |
| `sigma` (σ) | Dikalibrasi dari BPS | Volatilitas shock inflasi dalam model OU |
| `inflation_paths` | Simulasi | ndarray (n_simulations × n_years): path inflasi per simulasi (%) |
| `sectoral_multiplier` | Estimasi | Faktor pengganda inflasi per sektor (healthcare: 1.8×, education: 1.5×) |

---

## Investment / Return Variables

| Variabel | Sumber | Deskripsi |
|----------|--------|-----------|
| `nominal_return_mean` | Data historis / estimasi | Expected return nominal tahunan (%) sebelum inflasi |
| `real_return_mean` | Dihitung | Expected return real = nominal - inflasi |
| `nominal_return_std` | Data historis / estimasi | Volatilitas return nominal (standar deviasi, %) |
| `correlation_matrix` | Estimasi pasar Indonesia | Matriks korelasi antar kelas aset |
| `portfolio_variance` | Dihitung (w'Σw) | Varians portfolio = weighted covariance |
| `glide_path_profile` | Logika berbasis usia | Profil efektif setelah glide path adjustment |
| `annual_return_pct` | yfinance (^JKSE) | Return tahunan IDX Composite dari Yahoo Finance |

---

## Output / Projection Variables

| Variabel | Tipe | Deskripsi |
|----------|------|-----------|
| `fund_at_retirement` | float (IDR) | Total dana yang terkumpul saat usia pensiun (NOMINAL) |
| `real_fund_at_retirement` | float (IDR) | Dana pensiun dalam nilai uang hari ini (setelah deflate inflasi) |
| `annual_withdrawal_capacity` | float (IDR) | Penarikan tahunan yang aman = fund × safe_withdrawal_rate |
| `ruin_probability` | float (0–1) | Probabilitas dana habis sebelum usia planning_age |
| `fund_depleted_age` | int / null | Usia median di mana dana habis (dalam skenario ruin) |
| `safe_withdrawal_rate` | float | SWR yang digunakan: 3–4.5% tergantung profil risiko |

---

## A/B Test Variables

| Variabel | Deskripsi |
|----------|-----------|
| `strategy_a_fixed` | Fixed allocation sepanjang waktu (tidak ada glide path) |
| `strategy_b_glide_path` | Alokasi adaptif: geser ke konservatif saat mendekati pensiun |
| `u_statistic` | Statistik Mann-Whitney U (non-parametrik) |
| `p_value` | Tingkat signifikansi (H0 ditolak jika p < 0.05) |
| `statistically_significant` | bool: apakah perbedaan signifikan secara statistik |

---

## Derived / Engineered Features (Notebooks)

| Feature | Formula | Makna |
|---------|---------|-------|
| `real_return` | nominal_return - inflation_rate | Return bersih setelah inflasi |
| `survival_weight` | P(alive at age x) | Bobot probabilitas kelangsungan hidup |
| `inflation_adj_salary` | salary × (1 + avg_inflation)^years | Proyeksi gaji real |
| `required_nest_egg` | annual_expense / SWR | Dana minimum yang dibutuhkan untuk pensiun |
| `savings_rate_gap` | required_monthly - actual_monthly | Kekurangan kontribusi bulanan |
| `health_inflation_burden` | extra cost akibat inflasi kesehatan 1.8× | Risiko biaya kesehatan usia lanjut |
| `cum_inflation_factor` | Π(1 + inf_t) selama akumulasi | Faktor depresiasi daya beli |

---

## Raw Data Files

| File | Lokasi | Sumber | Deskripsi |
|------|--------|--------|-----------|
| `mortality_bpjs.csv` | `data/raw/` | BPJS Ketenagakerjaan | Tabel mortalitas per usia dan jenis kelamin (qx, lx) |
| `cpi_bps_historical.csv` | `data/raw/` | BPS Indonesia | Data inflasi CPI tahunan historis Indonesia |
| `salary_bps_sector_2015_2025.csv` | `data/raw/` | BPS Indonesia | Rata-rata gaji tahunan per sektor lapangan pekerjaan 2015–2025 (IDR). Digunakan untuk menghitung `SECTOR_SALARY_GROWTH` di `config.py`. Kolom: `Sektor`, `2015`–`2025`. |

---

## Notes & Caveats

> **PERINGATAN AKTUARIAL:**
> Semua nilai proyeksi adalah output dari simulasi probabilistik.
> Tidak ada satupun angka yang merepresentasikan "kepastian".
> Selalu sajikan dalam bentuk distribusi (P10/P50/P90), bukan satu angka tunggal.
> Return historis BUKAN jaminan return masa depan.
> Ruin probability adalah estimasi berbasis model, bukan prediksi deterministik.
