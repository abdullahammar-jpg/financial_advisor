# CuanSelor (Financial Advisor) — Simulasi Monte Carlo Dana Pensiun Indonesia

Proyek ini adalah sistem perencanaan keuangan pensiun berbasis **Simulasi Monte Carlo (10.000 iterasi)** yang dirancang khusus untuk kondisi ekonomi dan demografi Indonesia. Sistem ini mengintegrasikan pemodelan stokastik tingkat inflasi, analisis aktuaria harapan hidup, kalibrasi return historis pasar saham (IHSG) dan obligasi pemerintah, serta pengujian stres terhadap krisis makroekonomi historis.
---

## Fitur Utama

1. **Analisis Aktuaria Realistis (BPJS TMPI 2023):**
   * Menggunakan dataset Tabel Mortalitas Penduduk Indonesia (TMPI JKN 2023) yang diterbitkan BPJS Kesehatan, PAI, dan ITB.
   * Menyesuaikan laju kematian ($q_x$) menggunakan kalibrasi **A/E (Actual-to-Expected) Ratio** historis 2018–2022 untuk menangkap anomali kematian (termasuk dampak COVID-19).
   * Menghitung probabilitas kelangsungan hidup riil untuk menentukan *Planning Horizon* (direkomendasikan pada persentil ke-90 / P90) guna memitigasi risiko umur panjang (*longevity risk*).

2. **Model Inflasi Stokastik Ornstein-Uhlenbeck (OU):**
   * Alih-alih berasumsi inflasi flat, proyeksi menggunakan proses mean-reversion Ornstein-Uhlenbeck yang dikalibrasi secara otomatis dari data inflasi bulanan historis BPS (2016–2025).
   * Mendukung simulasi inflasi spesifik sektor (makanan, kesehatan, dan pendidikan) dengan parameter volatilitas ($\sigma$), kecepatan kembali ($\kappa$), dan rata-rata jangka panjang ($\theta$) yang disesuaikan secara empiris.

3. **Simulasi Portofolio Multi-Aset Log-Normal:**
   * Mensimulasikan return portofolio menggunakan distribusi log-normal dengan korelasi nyata antar kelas aset Indonesia (Deposito LPS, ORI/SBN, Reksa Dana Pasar Uang, RD Pendapatan Tetap, RD Campuran, dan RD Saham/IHSG).
   * Integrasi **Dynamic Glide Path (Target Date Fund):** Otomatis menyesuaikan alokasi aset pengguna ke profil yang lebih konservatif seiring mendekati masa pensiun demi melindungi modal yang terakumulasi.

4. **Uji Validasi Statistik A/B Testing:**
   * Melakukan pengujian hipotesis non-parametrik **Wilcoxon Signed-Rank Test** untuk mengevaluasi apakah strategi *Glide Path* secara signifikan mengurangi probabilitas kebangkrutan (*ruin probability*) dibandingkan dengan alokasi tetap (*Fixed Allocation*).

5. **Stress Testing Kejutan Ekonomi Historis:**
   * Menguji ketahanan dana pensiun terhadap 4 krisis makroekonomi terbesar Indonesia:
     * **Krisis Moneter 1998:** Inflasi melonjak +15%, return investasi jatuh -40%, dan gaji riil terpotong 50%.
     * **Pandemi COVID-19 (2020-2021):** Kejatuhan IHSG mendadak -38% dan pembekuan kenaikan gaji riil.
     * **Inflasi Global Berkepanjangan (2022):** Kejutan rantai pasok global yang meningkatkan inflasi di atas +8%.
     * **Stagflasi:** Inflasi tinggi jangka menengah dibarengi mandeknya pertumbuhan ekonomi (-20% return, -30% gaji).

6. **Actionable Insights & JSON Output:**
   * Memberikan langkah rekomendasi terarah untuk menutup celah dana pensiun (*fund gap*) seperti meningkatkan persentase tabungan secara bertahap atau menambah asuransi kesehatan purna jual untuk melindungi tabungan dari inflasi medis yang ekstrem (>10%/tahun).
   * Menyimpan hasil proyeksi lengkap dalam format JSON yang siap dikonsumsi oleh sistem backend lain.

---

## Struktur Direktori Proyek

```text
├── app/
│   └── streamlit_app.py         # Dashboard Web Streamlit (Visual & Interaktif)
├── data/
│   ├── raw/                     # Dataset mentah (CPI, Mortalitas BPJS, Gaji Sektoral BPS, Obligasi)
│   ├── processed/               # Dataset bersih hasil dari pipeline wrangling
│   └── data_dictionary.md       # Kamus data dan penjelasan variabel
├── gaji/
│   ├── Sektor_Gaji.ipynb        # Notebook analisis upah pekerja sektoral BPS
│   └── gaji_clean_fix.csv       # File data penunjang visualisasi gaji
├── IHK/
│   ├── Feature_IHK.ipynb        # Notebook rancangan rekayasa fitur IHK daerah
│   ├── run_feature_engineering.py # Script pembentukan fitur peramalan IHK
│   └── verify.py                # Script uji validasi kesesuaian rekayasa fitur IHK
├── Inflasi/
│   ├── preprocess_inflation.py  # Preprocessing & rekayasa fitur data inflasi BPS
│   └── Data Inflasi.xlsx        # Excel mentah data inflasi bulanan
├── notebooks/
│   ├── data_wrangling_part1_cpi.ipynb
│   ├── data_wrangling_part2_sektor_gaji_investasi.ipynb
│   └── eda_dan_data_preparation.ipynb
├── scripts/
│   ├── fix_notebooks.py         # Script pembantu perbaikan metadata notebook
│   └── wrangle_all.py           # Pipeline utama pengolah & pembersih seluruh data raw
├── src/                         # Kode sumber modul modular kalkulator
│   ├── __init__.py
│   ├── actuarial.py             # Parser mortalitas BPJS & estimasi harapan hidup
│   ├── calculator.py            # Mesin utama simulasi Monte Carlo & stress testing
│   ├── config.py                # Parameter konfigurasi proyeksi & alokasi aset
│   ├── inflation.py             # Simulator stokastik Ornstein-Uhlenbeck
│   └── investment.py            # Simulator portofolio, korelasi aset, & glide path
├── main.py                      # CLI entry point untuk eksekusi simulasi default
├── requirements.txt             # Dependensi pustaka Python
└── README.md                    # Dokumentasi proyek (Dokumen ini)
```

---

## Cara Instalasi dan Penyiapan Proyek

### 1. Prasyarat Sistem
* Python versi **3.10** atau lebih baru.
* Pengelola paket `pip` terinstal.

### 2. Kloning Repositori & Persiapan Lingkungan Virtual
Buka terminal (Command Prompt/PowerShell di Windows, atau Terminal di macOS/Linux) dan jalankan perintah berikut:

```bash
# Clone repositori ini atau unduh zip 
cd "path/to/project/Final(2)"

# Buat virtual environment (opsional)
python -m venv venv

# Aktifkan virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate
```

### 3. Instalasi Dependensi Pustaka
Instal seluruh paket yang dibutuhkan yang terdaftar dalam berkas `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 4. Ekstraksi Data Mentah (opsional)
Jika direktori `data/raw` belum berisi file data atau Anda ingin mengatur ulang dari awal:
* Pastikan file `data.zip` yang ada di root direktori telah diekstrak ke dalam folder proyek sehingga menghasilkan struktur `data/raw/...` dengan lengkap.

### 5. Jalankan Pipeline Ingesti dan Pengolahan Data
Sebelum menjalankan aplikasi, Anda harus menjalankan script wrangling untuk memproses seluruh data mentah menjadi data siap pakai di direktori `data/processed/`:

```bash
python scripts/wrangle_all.py
```
*Script ini akan memproses chain-linking IHK tahun dasar berbeda, menghitung CAGR pertumbuhan upah sektoral, menghitung A/E ratio mortalitas, dan menyelaraskan data IHSG serta obligasi.*

---

## Petunjuk Penggunaan

Sistem ini dapat dijalankan dalam tiga mode utama:

### 1. Dashboard Web Interaktif (Streamlit)
Untuk menjalankan dashboard visual yang mempermudah simulasi personal dengan slider parameter:

```bash
streamlit run app/streamlit_app.py
```

* **Cara Menggunakan Dashboard:**
  1. Masukkan data pribadi (Nama, Usia, Jenis Kelamin) di panel sebelah kiri.
  2. Tentukan variabel finansial (Gaji bulanan, bonus, persentase tabungan, aset saat ini).
  3. Pilih target usia pensiun, rasio gaya hidup pensiun, status kepemilikan asuransi kesehatan, serta profil risiko.
  4. Klik tombol **"Jalankan Simulasi Monte Carlo"**.
  5. Lihat visualisasi grafik akumulasi saldo, peluang kebangkrutan, hasil uji A/B testing taktis, serta hasil stress testing terhadap krisis ekonomi. Anda juga bisa mengunduh ringkasan laporan berformat `.txt`.

### 2. Antarmuka Baris Perintah / CLI (main.py)
Untuk melakukan pengujian kalkulasi simulasi default secara cepat langsung di terminal:

```bash
python main.py
```
Perintah ini akan menjalankan simulasi 10.000 iterasi dengan profil bawaan (Rizky, usia 25 tahun, gaji Rp8.000.000, tingkat tabungan 20%, profil moderat) dan menampilkan output lengkap mulai dari ringkasan aktuarial, proyeksi median/optimis/pesimis, A/B Testing, hingga Stress Testing krisis makro.

### 3. Rekayasa Fitur Peramalan IHK Daerah
Jika Anda ingin memproses rekayasa fitur data IHK daerah (Feature Engineering) untuk kebutuhan peramalan (forecasting):

```bash
# Pindah ke direktori IHK
cd IHK

# Jalankan proses rekayasa fitur (melt, winsorization, lag, rolling std, dll.)
python run_feature_engineering.py

# Jalankan script verifikasi untuk memastikan hasil rekayasa fitur 100% valid
python verify.py
```

---

## 💡 Informasi Penting Lainnya

### 1. Metodologi Matematika & Keuangan

#### A. Model Inflasi Ornstein-Uhlenbeck (Stokastik)
Pemodelan inflasi bulanan dilakukan menggunakan persamaan diferensial stokastik berikut:
$$d\pi_t = \kappa (\theta - \pi_t) dt + \sigma dW_t$$

Dimana:
* $\pi_t$: Tingkat inflasi pada periode $t$.
* $\kappa$ (*kappa*): Kecepatan penyesuaian (mean-reversion speed) kembali ke target jangka panjang.
* $\theta$ (*theta*): Tingkat rata-rata inflasi jangka panjang (long-term mean target dari kalibrasi empiris BPS $\approx 3.3\% - 3.5\%$).
* $\sigma$ (*sigma*): Volatilitas deviasi inflasi.
* $dW_t$: Gerak acak Brownian shock (variabel acak normal).

#### B. Persamaan Fisher (Fisher Equation)
Untuk mengonversi tingkat pengembalian nominal dari pasar keuangan menjadi pengembalian riil yang bersih dari inflasi, digunakan formula:
$$1 + r_{\text{riil}} = \frac{1 + r_{\text{nominal}}}{1 + \pi}$$

Return riil dinamis ini yang digunakan untuk melakukan proses penggandaan nilai aset (*compounding*) setiap bulannya dalam simulasi akumulasi dana pensiun.

---

### 2. Profil Risiko & Alokasi Kelas Aset Portofolio

Sistem memetakan 4 profil risiko bawaan dengan komposisi portofolio berikut:

| Nama Profil | Deposito | ORI / SBN | RD Pasar Uang | RD Pendapatan Tetap | RD Campuran | RD Saham (IHSG) | Safe Withdrawal Rate (SWR) |
|---|---|---|---|---|---|---|---|
| **Konservatif** | 30% | 40% | 20% | 10% | 0% | 0% | **3.0%** per tahun |
| **Moderat** | 10% | 25% | 10% | 15% | 25% | 15% | **3.5%** per tahun |
| **Agresif** | 5% | 10% | 5% | 10% | 25% | 45% | **4.0%** per tahun |
| **Sangat Agresif**| 0% | 5% | 0% | 5% | 15% | 75% | **4.5%** per tahun |

---

### 3. Perilaku Glide Path (Alokasi Adaptif)

Strategi *Glide Path* didasarkan pada prinsip mitigasi risiko penarikan berurutan (*Sequence of Returns Risk*). Seiring sisa waktu menjelang pensiun berkurang, portofolio digeser ke profil risiko yang lebih aman secara otomatis:
* **Sisa waktu > 20 tahun:** Mengikuti profil risiko dasar pilihan pengguna.
* **Sisa waktu 10 s.d. 20 tahun:** Bergeser 1 tingkat lebih aman dari profil dasar.
* **Sisa waktu 5 s.d. 10 tahun:** Bergeser 2 tingkat lebih aman dari profil dasar.
* **Sisa waktu < 5 tahun:** Mengunci portofolio ke profil **Konservatif** demi mengamankan dana pokok.

---

### ⚠️ Disclaimer Perencanaan Keuangan
* Proyeksi dana pensiun ini adalah estimasi matematis probabilistik berbasis model simulasi. Hasil masa lalu (data historis BPS & IHSG) tidak memberikan jaminan kepastian atas kinerja return di masa depan.
* Angka peluang kebangkrutan (*ruin probability*) ditujukan sebagai alat bantu peninjau tingkat toleransi risiko portofolio tabungan, bukan sebuah kepastian mutlak kebangkrutan keuangan. Pengguna disarankan tetap berkonsultasi dengan penasihat keuangan profesional tersertifikasi (e.g., CFP) untuk keputusan finansial penting.
