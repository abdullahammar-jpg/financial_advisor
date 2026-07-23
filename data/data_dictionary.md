# Data Dictionary — CuanSelor (Financial Advisor)

**Terakhir Diperbarui:** Juni 2026 | **Mata Uang:** IDR (Rupiah)
---

## 1. Variabel Input Pengguna (Input Variables)

Variabel-variabel berikut dikumpulkan dari input pengguna untuk mengonfigurasi profil keuangan dan demografi personal:

| Nama Variabel | Tipe | Contoh | Deskripsi |
| :--- | :---: | :--- | :--- |
| `name` | `str` | `"Rizky"` | Nama lengkap atau panggilan pengguna. |
| `age` | `int` | `25` | Usia saat ini (tahun). Rentang valid: 18 s.d. 60 tahun. |
| `gender` | `str` | `"male"` / `"female"` | Jenis kelamin pengguna. Menentukan tabel mortalitas BPJS yang digunakan. |
| `monthly_salary` | `float` | `8000000.0` | Gaji bulanan kotor saat ini (dalam Rupiah). |
| `savings_rate` | `float` | `0.20` | Proporsi gaji bulanan yang ditabung atau diinvestasikan (rentang: 0.0 s.d. 1.0). |
| `retirement_age` | `int` | `55` | Target usia pensiun pengguna. Harus lebih besar dari `age`. |
| `risk_profile` | `str` | `"moderate"` | Profil risiko investasi: `conservative`, `moderate`, `aggressive`, atau `very_aggressive`. |
| `sector` | `str` | `"Informasi dan Komunikasi"` | Sektor lapangan pekerjaan BPS (mempengaruhi laju kenaikan gaji tahunan). |
| `include_pandemic_risk`| `bool` | `True` | Jika `True`, laju pertumbuhan gaji dihitung pesimis (termasuk anomali drop masa COVID-19). |
| `custom_deposit_rate` | `float` | `5.0` | Nilai bunga kustom deposito bank per tahun (%) (opsional). |
| `custom_planning_age`  | `int` | `85` | Batas akhir proyeksi penarikan dana pensiun (tahun) (opsional). |
| `current_assets` | `float` | `25000000.0` | Nilai aset/tabungan investasi yang sudah dimiliki saat ini (dalam Rupiah). |
| `annual_bonus_months`  | `float` | `1.0` | Jumlah bulan gaji yang diterima sebagai bonus tahunan/THR (misal: 1.0 = 1 bulan gaji). |
| `replacement_ratio` | `float` | `0.70` | Persentase gaji terakhir untuk menunjang gaya hidup pensiun (default: 0.70 atau 70%). |
| `has_health_insurance` | `bool` | `False` | Kepemilikan asuransi kesehatan pasca pensiun. Jika `False`, dana dikenakan biaya medis tambahan di hari tua. |
| `monthly_expense` | `float` | `5000000.0` | Target pengeluaran bulanan riil pasca pensiun (opsional, jika kosong dihitung dari `replacement_ratio`). |

---

## 2. Variabel Aktuaria (Actuarial Variables)

Variabel aktuaria digunakan untuk memproyeksikan probabilitas kelangsungan hidup dan memperkirakan durasi pensiun yang aman bagi pengguna:

| Nama Variabel | Tipe / Sumber | Deskripsi |
| :--- | :---: | :--- |
| `qx` | `float` / TMPI 2023 | Probabilitas kematian seseorang pada usia $x$ sebelum mencapai usia $x+1$. |
| `lx` | `float` / Dihitung | Jumlah populasi yang bertahan hidup pada usia $x$ dari kohort awal (*radix*) sebesar 100.000 jiwa. |
| `ex` | `float` / Dihitung | Rata-rata sisa harapan hidup (dalam tahun) bagi seseorang yang telah mencapai usia $x$. |
| `ae_ratio` | `float` / BPJS | *Actual-to-Expected* ratio per kelompok usia (LK/PR) hasil olahan data BPJS Kesehatan 2018–2022. Berfungsi sebagai faktor penyesuai probabilitas kematian ($q_x$) agar sesuai realitas Indonesia. |
| `survival_probability` | `float` / Dihitung | Probabilitas bersyarat pengguna tetap hidup di usia target, dengan syarat telah mencapai usia saat ini. |
| `p50_survival_age` | `int` / Dihitung | Usia median kelangsungan hidup (probabilitas bertahan hidup mencapai 50%). |
| `p90_survival_age` | `int` / Dihitung | Usia kelangsungan hidup persentil ke-90 (hanya 10% populasi sejenis yang bertahan hidup melampaui usia ini). Digunakan sebagai target planning horizon utama untuk mitigasi *longevity risk*. |
| `longevity_risk_flag` | `bool` / Dihitung | Penanda risiko umur panjang. Bernilai `True` jika perkiraan sisa hidup pasca pensiun melebihi 15 tahun. |

---

## 3. Variabel Inflasi (Inflation Variables)

Digunakan dalam model stokastik Ornstein-Uhlenbeck (OU) untuk memproyeksikan volatilitas daya beli Rupiah di masa depan:

| Nama Variabel | Tipe / Sumber | Deskripsi |
| :--- | :---: | :--- |
| `cpi_pct` | `float` / BPS | Angka inflasi CPI (*Consumer Price Index*) tahunan Indonesia (%). |
| `theta` ($\theta$) | `float` / Kalibrasi | Parameter target rata-rata inflasi jangka panjang (long-term mean) dalam model OU. |
| `kappa` ($\kappa$) | `float` / Kalibrasi | Kecepatan penyesuaian (mean-reversion speed) tingkat inflasi kembali ke nilai target ($\theta$). |
| `sigma` ($\sigma$) | `float` / Kalibrasi | Volatilitas kejutan (shock) inflasi per tahun. |
| `inflation_paths` | `np.ndarray` | Matriks hasil simulasi jalur inflasi acak berukuran ($n\_simulations \times n\_years$). |
| `sectoral_multiplier`| `float` / BPS | Faktor pengali inflasi kelompok pengeluaran sektoral terhadap CPI umum (Makanan $\approx 1.269\times$, Kesehatan $\approx 0.895\times$, Pendidikan $\approx 0.987\times$). *Catatan: Modul terbaru `inflation.py` mengkalibrasi parameter OU secara langsung per sektor untuk presisi lebih tinggi.* |

---

## 4. Variabel Portofolio & Investasi (Investment Variables)

Variabel yang mengatur performa simulasi log-normal portofolio aset keuangan:

| Nama Variabel | Tipe / Sumber | Deskripsi |
| :--- | :---: | :--- |
| `nominal_return_mean` | `float` / Kalibrasi | Rata-rata return nominal tahunan sebelum dikurangi inflasi (%). |
| `nominal_return_std`  | `float` / Kalibrasi | Volatilitas (standar deviasi) return nominal tahunan (%). |
| `real_return_mean` | `float` / Dihitung | Rata-rata return riil tahunan setelah disesuaikan dengan inflasi menggunakan rumus Fisher (%). |
| `correlation_matrix`  | `np.ndarray` | Matriks korelasi antarkelas aset (deposito, SBN, reksa dana pasar uang, pendapatan tetap, campuran, dan saham). |
| `portfolio_variance`  | `float` / Dihitung | Varians portofolio tertimbang berdasarkan bobot alokasi kelas aset ($w^T \Sigma w$). |
| `glide_path_profile`  | `str` / Logika | Nama profil risiko efektif setelah mengalami penyesuaian otomatis berdasarkan sisa tahun menuju pensiun. |
| `annual_return_pct`   | `float` / yfinance | Return tahunan IHSG Composite (`^JKSE`) dari Yahoo Finance atau data lokal. |

---

## 5. Variabel Output Simulasi (Output Variables)

Variabel-variabel yang dihasilkan dari orkestrasi simulasi Monte Carlo 10.000 iterasi di `RetirementCalculator`:

| Nama Variabel | Tipe | Deskripsi |
| :--- | :---: | :--- |
| `fund_at_retirement` | `float` (IDR) | Proyeksi nominal total dana pensiun yang terkumpul pada hari pertama pensiun. |
| `real_fund_at_retirement` | `float` (IDR) | Nilai daya beli dana pensiun saat pensiun nanti, dinyatakan dalam mata uang Rupiah hari ini (sudah di-*deflate* inflasi). |
| `annual_withdrawal_capacity`| `float` (IDR) | Jumlah penarikan dana tahunan yang dinilai aman berdasarkan persentase SWR portofolio ($fund \times SWR$). |
| `ruin_probability` | `float` (0.0–1.0) | Probabilitas kegagalan di mana saldo dana habis total (menjadi $\le 0$) sebelum pengguna mencapai batas usia planning horizon. |
| `fund_depleted_age` | `int` / `null` | Usia median di mana dana pensiun terdepresiasi penuh hingga habis (hanya relevan pada iterasi simulasi yang mengalami kegagalan/ruin). |
| `safe_withdrawal_rate` | `float` | Persentase penarikan aman tahunan (SWR) yang diaplikasikan pasca pensiun (Conservative: 3.0%, Moderate: 3.5%, Aggressive: 4.0%, Very Aggressive: 4.5%). |

---

## 6. Variabel Uji Statistik (A/B Test Variables)

Variabel pembanding efektivitas antara **Fixed Allocation** (Strategi A) dengan **Adaptive Glide Path** (Strategi B):

| Nama Variabel | Tipe | Deskripsi |
| :--- | :---: | :--- |
| `strategy_a_fixed` | `dict` | Hasil ruin probability dan parameter alokasi statis sepanjang waktu. |
| `strategy_b_glide_path` | `dict` | Hasil ruin probability dan alokasi dinamis yang melandai secara bertahap. |
| `improvement` | `float` | Penurunan probabilitas ruin dalam persentase poin (pp) ($Ruin_A - Ruin_B$). |
| `test_statistic` | `float` | Nilai statistik hitung dari uji **Wilcoxon Signed-Rank Test** (paired, one-sided). |
| `p_value` | `float` | Tingkat signifikansi statistik. Hipotesis nol ditolak jika $p < 0.05$. |
| `statistically_significant` | `bool` | `True` jika perbedaan performa kedua strategi terbukti signifikan secara statistik. |
| `winner` | `str` | Menunjukkan strategi pemenang yang memiliki ruin probability paling rendah (`A` atau `B`). |

---

## 7. Variabel Fitur Rekayasa (Derived / Engineered Features)

Fitur-fitur hasil kalkulasi terderivasi yang sering digunakan dalam proses visualisasi notebook maupun visualisasi grafik streamlit:

| Nama Fitur | Rumus / Formula | Makna Finansial |
| :--- | :--- | :--- |
| `real_return` | $\frac{1 + r_{\text{nominal}}}{1 + \pi} - 1$ | Return investasi bersih yang sudah lolos dari pengikisan inflasi. |
| `survival_weight` | $P(\text{Hidup di usia } x)$ | Faktor bobot probabilitas keberadaan pengguna untuk kebutuhan aktuaria. |
| `inflation_adj_salary`| $Salary \times (1 + \text{Real Growth})^{\text{years}}$ | Proyeksi peningkatan upah riil dalam nilai mata uang hari ini. |
| `required_nest_egg` | $\frac{\text{Pengeluaran Tahunan Pensiun}}{\text{Safe Withdrawal Rate (SWR)}}$ | Target batas aman dana pensiun yang harus dikumpulkan agar tidak bangkrut. |
| `savings_rate_gap` | $Required\_monthly - Actual\_monthly$ | Besaran nilai tabungan ekstra bulanan yang harus ditambahkan untuk mengejar target. |
| `health_inflation_burden`| Adaptasi klaster usia ($10\%, 18\%, 28\%$) | Beban tambahan biaya medis di hari tua jika tidak memiliki asuransi kesehatan. |
| `cum_inflation_factor`| $\prod_{t} (1 + \text{inflation}_t)$ | Faktor kumulatif depresiasi daya beli selama periode akumulasi tabungan. |

---

## 8. Pemetaan Berkas Data (Data Files Mapping)

### A. Data Mentah (data/raw/)
* `Tabel_Mortalitas_Penduduk_Indonesia_2023.csv` — Tabel mortalitas mentah berisi data $q_x$, $l_x$, $e_x$, dan A/E Ratio JKN per kelompok usia penduduk Indonesia.
* `CPI/` — Folder berisi data historis IHK nasional (BPS) bulanan untuk periode 2015–2019, 2020–2023, dan 2024–2026.
* `CPI Sektor/` — Folder berisi data indeks IHK sektoral bulanan untuk kelompok Makanan (Sektor 01), Kesehatan (Sektor 05), dan Pendidikan (Sektor 09).
* `Rata-rata Upah Gaji per Sektor 2015-2026 .../` — Data upah rata-rata bulanan tenaga kerja sektoral di Indonesia yang dirilis resmi oleh BPS.
* `Investasi/` — Data historis penutupan bulanan IHSG Composite, Yield obligasi pemerintah 10 tahun, dan Yield obligasi 3 tahun.

### B. Data Bersih (data/processed/)
Seluruh berkas di bawah dihasilkan setelah mengeksekusi pipeline `python scripts/wrangle_all.py`:
* `cpi_monthly.csv` — Gabungan deret waktu indeks IHK bulanan terpadu hasil metode *chain-linking* (rebased ke tahun dasar 2012=100) serta persentase MoM & YoY.
* `cpi_clean.csv` — Laju inflasi tahunan (CPI YoY Desember) untuk kalibrasi jangka panjang.
* `cpi_sektor_monthly.csv` — Deret waktu IHK kelompok pengeluaran sektoral bulanan yang bersih.
* `cpi_sektor_multiplier.csv` — Koefisien multiplier historis rata-rata laju inflasi sektoral terhadap inflasi umum.
* `mortality_clean.csv` — Data mortalitas $q_x, p_x$, sisa harapan hidup, dan *exposure* yang bersih.
* `ae_ratio_clean.csv` — Rata-rata *Actual-to-Expected* ratio kelompok kematian BPJS.
* `salary_clean.csv` — Data historis upah nominal tahunan per sektor lapangan usaha.
* `salary_growth.csv` — Hasil kalkulasi pertumbuhan gaji tahunan per sektor (CAGR normal vs CAGR terhantam krisis/covid).
* `ihsg_monthly.csv` & `ihsg_annual.csv` — Data historis pergerakan return IHSG bulanan/tahunan yang bersih.
* `investment_clean.csv` — Yield obligasi pemerintah Indonesia tenor 3 tahun dan 10 tahun terformat rapi.
