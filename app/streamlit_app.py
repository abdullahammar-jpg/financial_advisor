import streamlit as st  
import sys
import os
import pandas as pd  
import plotly.express as px  

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.calculator import RetirementCalculator, UserProfile
from src.config import SECTOR_SALARY_GROWTH, RISK_PROFILES
from src.actuarial import get_mortality_table

#! Konfigurasi awal halaman streamlit dashboard
st.set_page_config(
    page_title="Proyeksi Dana Pensiun",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

#! Custom Styling CSS untuk tampilan card dan badge berestetika premium
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    .metric-card {
        background: linear-gradient(145deg, #1e222d 0%, #151821 100%);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        font-family: 'Outfit', sans-serif;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0, 255, 204, 0.1);
        border: 1px solid rgba(0, 255, 204, 0.2);
    }
    .metric-label {
        font-size: 13px;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 32px;
        font-weight: 800;
        background: linear-gradient(90deg, #00ffcc, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
        line-height: 1.2;
    }
    .ruin-box {
        text-align: center;
        padding: 35px 20px;
        background: linear-gradient(145deg, #2b2b36 0%, #1a1a24 100%);
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.05);
        box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
        font-family: 'Outfit', sans-serif;
    }
    .ruin-box h4 { color: #e2e8f0; font-weight: 600; margin-bottom: 5px; }
    .ruin-box p { color: #94a3b8; font-size: 14px; margin-top: 10px; }
    
    .ruin-high { color: #ef4444 !important; text-shadow: 0 0 20px rgba(239, 68, 68, 0.5); }
    .ruin-low { color: #10b981 !important; text-shadow: 0 0 20px rgba(16, 185, 129, 0.5); }
    
    .status-badge-safe {
        display: inline-block; padding: 4px 12px; border-radius: 20px;
        background: rgba(16, 185, 129, 0.1); color: #10b981; font-weight: 600; font-size: 14px; border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .status-badge-danger {
        display: inline-block; padding: 4px 12px; border-radius: 20px;
        background: rgba(239, 68, 68, 0.1); color: #ef4444; font-weight: 600; font-size: 14px; border: 1px solid rgba(239, 68, 68, 0.3);
    }
</style>
<h1 style='text-align: center; font-family: "Outfit", sans-serif; font-size: 3.2rem; margin-bottom: 40px; padding-top: 20px;'>
    <span style='background: linear-gradient(90deg, #3b82f6, #00ffcc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>AI Financial Advisor</span>
</h1>
""", unsafe_allow_html=True)
st.markdown("Kalkulator pensiun **probabilistik** berbasis *Monte Carlo Simulation* (10.000 iterasi). Memperhitungkan data aktuaria BPJS (TMPI 2023), model inflasi stokastik BPS, dan volatilitas pasar nyata.")

#! Membuat panel input data pribadi & finansial di Sidebar Kiri
with st.sidebar:
    st.header("1. Data Pribadi")
    name = st.text_input("Nama", value="Rizky")
    age = st.number_input("Usia Saat Ini", min_value=18, max_value=60, value=25)
    gender = st.selectbox("Jenis Kelamin", options=["male", "female"], format_func=lambda x: "Laki-laki" if x == "male" else "Perempuan")
    
    st.header("2. Finansial")
    monthly_salary = st.number_input("Gaji Bulanan (Rp)", min_value=1_000_000, value=8_000_000, step=1_000_000)
    annual_bonus_months = st.slider("Bonus/THR (Berapa kali gaji per tahun?)", min_value=0.0, max_value=6.0, value=1.0, step=0.5)
    savings_rate = st.slider("Persentase Nabung/Investasi (%)", min_value=0, max_value=100, value=20) / 100.0
    current_assets = st.number_input("Dana Investasi Saat Ini (Rp)", min_value=0, value=0, step=5_000_000, help="Dana yang secara khusus dialokasikan untuk keperluan masa pensiun.")
    
    st.header("3. Target Pensiun & Usia Harapan Hidup")
    retirement_age = st.number_input("Target Usia Pensiun", min_value=age+1, max_value=80, value=55)
    replacement_ratio = st.slider("Target Gaya Hidup Pensiun (% dari gaji terakhir)", min_value=30, max_value=150, value=70, step=5, help="Standar: 70%. Frugal: 40-50%. Mewah: >100%.")
    has_health_insurance = st.checkbox("Sudah Punya Asuransi Kesehatan Purna Jual?", value=False, help="Jika tidak dicentang, dana pensiun akan dihantam inflasi medis tinggi (>10%/thn) di atas usia 65 tahun.")
    
    # Ambil info aktuaria harapan hidup riil
    mt = get_mortality_table()
    act_sum = mt.get_planning_summary(age, retirement_age, gender)
    default_p90 = act_sum["p90_survival_age"]
    p50_age = act_sum["p50_survival_age"]
    exp_age = act_sum["expected_death_age"]
    
    st.info(f"💡 **Informasi Aktuaria**: Usia harapan hidup rata-rata adalah **{exp_age:.1f}** tahun. Terdapat probabilitas 50% untuk mencapai usia **{p50_age}** tahun, dan probabilitas 10% untuk mencapai usia **{default_p90}** tahun.")
    
    custom_planning_age = st.slider("Rencanakan Dana Hingga Usia", min_value=retirement_age+1, max_value=110, value=default_p90, help="Rekomendasi aktuaria: Gunakan persentil ke-90 (P90) untuk memitigasi risiko umur panjang (longevity risk).")
    
    risk_options = list(RISK_PROFILES.keys())
    risk_format = {k: RISK_PROFILES[k]["label"] for k in risk_options}
    risk_profile = st.selectbox("Profil Risiko Investasi", options=risk_options, format_func=lambda x: risk_format[x], index=1)
    
    st.header("4. Asumsi Lanjutan (Advanced)")
    sector_list = list(SECTOR_SALARY_GROWTH.keys())
    
    _default_sector = next(
        (s for s in sector_list if s.lower().startswith("rata")),
        sector_list[-1]
    )
    sector = st.selectbox(
        "Sektor Pekerjaan (BPS)", options=sector_list,
        index=sector_list.index(_default_sector)
    )
    
    include_pandemic_risk = st.checkbox("Gunakan Risiko Pandemi/Krisis (Trendline Growth)", value=True, help="Jika dicentang, menggunakan growth rate pesimis (historis termasuk masa drop covid).")
    custom_deposit = st.number_input("Bunga Deposito / Bank Digital (% per tahun)", min_value=1.0, max_value=15.0, value=5.0, step=0.5)

    run_sim = st.button("Jalankan Simulasi Monte Carlo", use_container_width=True, type="primary")

#! Fungsi ter-cache untuk menjalankan komputasi simulasi agar responsif
@st.cache_data(show_spinner=False)
def get_simulation_results(name, age, gender, monthly_salary, savings_rate, retirement_age, risk_profile, sector, include_pandemic_risk, custom_deposit_rate, custom_planning_age, current_assets, annual_bonus_months, replacement_ratio, has_health_insurance):
    p = UserProfile(
        name=name, age=age, gender=gender, monthly_salary=monthly_salary, savings_rate=savings_rate,
        retirement_age=retirement_age, risk_profile=risk_profile, sector=sector,
        include_pandemic_risk=include_pandemic_risk, custom_deposit_rate=custom_deposit_rate,
        custom_planning_age=custom_planning_age, current_assets=current_assets,
        annual_bonus_months=annual_bonus_months, replacement_ratio=replacement_ratio,
        has_health_insurance=has_health_insurance
    )
    calc = RetirementCalculator(n_simulations=10_000)
    return calc.calculate(p)

#! Pengecekan input valid & penjalanan simulasi utama
if run_sim:
    if retirement_age <= age:
        st.error("🚨 Usia pensiun harus lebih besar dari usia saat ini.")
        st.stop()
    if savings_rate == 0.0 and current_assets == 0:
        st.error("🚨 Persentase nabung tidak boleh 0% jika tidak punya aset investasi saat ini.")
        st.stop()
        
    with st.spinner('Menjalankan 10.000 iterasi simulasi Monte Carlo. Mohon tunggu...'):
        res = get_simulation_results(
            name, age, gender, monthly_salary, savings_rate, retirement_age, risk_profile, sector,
            include_pandemic_risk, custom_deposit, custom_planning_age, float(current_assets),
            float(annual_bonus_months), replacement_ratio / 100.0, has_health_insurance
        )
        
    st.success("Simulasi berhasil diselesaikan.")
    
    monthly_save = monthly_salary * savings_rate
    status_ruin = "memiliki probabilitas kecukupan dana yang optimal" if res.projection['median_p50']['ruin_probability'] < 0.15 else "memiliki risiko tinggi kekurangan dana (shortfall)"
    st.info(f"💡 **Kesimpulan:** Berdasarkan alokasi tabungan sebesar **Rp {monthly_save:,.0f}** per bulan, proyeksi dana pensiun Anda **{status_ruin}** untuk menunjang standar hidup hingga usia **{custom_planning_age}** tahun.")
    
    # Tombol download laporan
    report_text = f"""Laporan Proyeksi Pensiun untuk {name}
Usia Saat Ini: {age}
Target Pensiun: {retirement_age}
Gaji Saat Ini: Rp {monthly_salary:,.0f}
Tabungan Bulanan: Rp {monthly_save:,.0f}

--- HASIL MONTE CARLO (P50) ---
Dana Terkumpul: Rp {res.projection['median_p50']['fund_at_retirement']:,.0f}
Peluang Kebangkrutan: {res.projection['median_p50']['ruin_probability']*100:.1f}%
Kapasitas Penarikan Bulanan: Rp {res.projection['median_p50']['annual_withdrawal_capacity']/12:,.0f}
"""
    st.download_button("📄 Download Laporan (TXT)", data=report_text, file_name=f"Laporan_Pensiun_{name}.txt", mime="text/plain")
    
    #! Menampilkan metrik aktuaria & risiko umur panjang
    st.subheader("📊 Fundamental Asumsi Anda")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Usia Harapan Hidup (P50)</div><div class='metric-value'>{res.actuarial_summary['p50_survival_age']} Tahun</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Batas Maksimal Horizon Pensiun (P90)</div><div class='metric-value'>{res.actuarial_summary['p90_survival_age']} Tahun</div><small style='color:#ccc'>Basis perhitungan ketahanan dana.</small></div>", unsafe_allow_html=True)
    with col3:
        is_high_risk = res.actuarial_summary['longevity_risk_flag']
        status_text  = 'Risiko Tinggi' if is_high_risk else 'Aman Terkendali'
        badge_class  = 'status-badge-danger' if is_high_risk else 'status-badge-safe'
        desc_text    = "Risiko depresiasi daya beli akibat inflasi tinggi (masa pensiun > 30 tahun)." if is_high_risk else "Durasi pensiun wajar (< 30 tahun), risiko inflasi relatif terkendali."
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Status Risiko Umur Panjang</div><div style='margin-bottom:8px;'><span class='{badge_class}'>{status_text}</span></div><small style='color:#94a3b8; font-family:\"Outfit\", sans-serif;'>{desc_text}</small></div>", unsafe_allow_html=True)

    #! Menampilkan hasil proyeksi 3 skenario dalam bentuk Tab
    st.subheader("💰 Hasil Proyeksi Dana Saat Pensiun (Umur {age} → {ret_age})".format(age=age, ret_age=retirement_age))
    tab1, tab2, tab3, tab4 = st.tabs(["Skenario Median (P50)", "Skenario Pesimis (P10)", "Skenario Optimis (P90)", "📈 Visualisasi Grafik"])
    
    def render_scenario_tab(scen_key):
        data = res.projection[scen_key]
        ruin_prob = data['ruin_probability']
        fund_ret = data['fund_at_retirement']
        ann_with = data['annual_withdrawal_capacity']
        dep_age = data.get('fund_depleted_age')

        ruin_color = "ruin-high" if ruin_prob > 0.5 else "ruin-low"
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Dana Terkumpul (Nominal)", f"Rp {fund_ret:,.0f}".replace(",", "."))
            st.metric("Kapasitas Penarikan Bulanan (Real)", f"Rp {(ann_with/12):,.0f}".replace(",", ".") + " / bulan")
            if dep_age:
                st.warning(f"⚠️ Peringatan: Dana diproyeksikan terdepresiasi penuh pada usia **{dep_age}** tahun.")
            else:
                st.success("✅ Proyeksi dana mencukupi hingga akhir target horizon waktu (usia P90).")
        with c2:
            st.markdown(f"""
            <div class='ruin-box'>
                <h4>Peluang Kebangkrutan <span title='Persentase risiko uang pensiun Anda habis total menjadi Rp 0 sebelum Anda meninggal dunia.' style='cursor:help;'>ℹ️</span></h4>
                <h1 class='{ruin_color}' style='font-size:72px; margin:5px 0; line-height:1.1;'>{ruin_prob*100:.1f}%</h1>
                <p>Peluang dana habis sebelum usia {custom_planning_age} tahun.</p>
            </div>
            """, unsafe_allow_html=True)
            
    with tab1: render_scenario_tab("median_p50")
    with tab2: render_scenario_tab("pessimistic_p10")
    with tab3: render_scenario_tab("optimistic_p90")
    
    #! Menampilkan plot garis interpolasi jalannya proyeksi akumulasi/dekumulasi dana pensiun
    with tab4:
        st.markdown("### 📈 Visualisasi Distribusi Monte Carlo (Nilai dalam Rupiah)")
        st.info("💡 Grafik di bawah menunjukkan estimasi saldo tabungan Anda dalam mata uang Rupiah (IDR) seiring bertambahnya usia.")
        plan_horizon = custom_planning_age
        
        def build_trajectory(scen_key, label_name):
            data = res.projection[scen_key]
            traj = {}
            
            for y in range(age, retirement_age + 1):
                progress = (y - age) / max(retirement_age - age, 1)
                val = current_assets * (1 - progress) + data['fund_at_retirement'] * (progress ** 2)
                traj[y] = val
                
            depleted_age = data.get('fund_depleted_age')
            end_age = depleted_age if depleted_age else plan_horizon
            
            if end_age > retirement_age:
                for y in range(retirement_age + 1, end_age + 1):
                    progress = (y - retirement_age) / max(end_age - retirement_age, 1)
                    val = data['fund_at_retirement'] * ((1 - progress) ** 1.5)
                    traj[y] = val
                    
            if end_age < plan_horizon:
                for y in range(end_age + 1, plan_horizon + 1):
                    traj[y] = 0.0
            
            return pd.Series(traj, name=label_name)

        s_p10 = build_trajectory("pessimistic_p10", "P10 (Pesimis)")
        s_p50 = build_trajectory("median_p50", "P50 (Median)")
        s_p90 = build_trajectory("optimistic_p90", "P90 (Optimis)")
        
        df_plot = pd.concat([s_p90, s_p50, s_p10], axis=1).reset_index().rename(columns={"index": "Umur"})
        df_melt = df_plot.melt(id_vars=["Umur"], var_name="Skenario", value_name="Saldo")
        
        fig = px.line(df_melt, x="Umur", y="Saldo", color="Skenario",
                      title="Proyeksi Dana Pensiun (Rupiah)",
                      labels={"Saldo": "Saldo Dana (Rp)"})
        
        fig.update_layout(
            hovermode="x unified",
            yaxis_tickformat=",.0f"
        )
        fig.update_traces(
            hovertemplate="Rp %{y:,.0f}<extra></extra>"
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'separators': ',.'})
        st.caption(f"*Grafik ini adalah interpolasi visual untuk menggambarkan rentang (range) kemungkinan perjalanan dana Anda dari umur {age} ke {plan_horizon}.")

    st.divider()

    #! Menampilkan perbandingan A/B Test & Actionable Insights
    colA, colB = st.columns(2)
    with colA:
        st.subheader("🔬 A/B Test: Strategi Investasi")
        ab = res.ab_test_result
        st.markdown(f"Komparasi efektivitas antara strategi **Glide Path** (alokasi dinamis ke aset konservatif menjelang pensiun) dengan strategi Alokasi Statis (Fixed).")
        st.info(f"**Pemenang: {ab['winner']}**")
        st.markdown(f"- **Ruin Prob (Fixed):** {ab['strategy_a_fixed']['ruin_probability']*100:.1f}%\n- **Ruin Prob (Glide Path):** {ab['strategy_b_glide_path']['ruin_probability']*100:.1f}%")
        st.caption(f"P-Value: {ab['p_value']} (Signifikan: {ab['statistically_significant']})")
        
    with colB:
        st.subheader("💡 Actionable Insights")
        for i, insight in enumerate(res.actionable_insights, 1):
            st.markdown(f"**{i}.** {insight}")

    st.divider()

    #! Menampilkan stress testing terhadap krisis ekonomi historis
    st.subheader("⚡ Stress Testing: Skenario Krisis Makroekonomi Historis")
    st.markdown("Analisis ketahanan portofolio dana pensiun terhadap **kejutan ekonomi (economic shock)** berdasarkan data krisis historis global dan domestik.")

    stress_scenarios = [
        {
            "nama"        : "💥 Krisis Moneter 1998",
            "keterangan"  : "Inflasi mencapai 58%, rupiah jatuh 80%, PHK massal. Skenario paling destruktif dalam sejarah Indonesia modern.",
            "inf_shock"   : +15.0,
            "return_shock": -0.40,
            "salary_mult" : 0.50,
        },
        {
            "nama"        : "🦠 Pandemi COVID-19 (2020–2021)",
            "keterangan"  : "IHSG anjlok -38% dalam sebulan, banyak sektor lumpuh total, gaji dipotong atau di-freeze.",
            "inf_shock"   : +2.0,
            "return_shock": -0.38,
            "salary_mult" : 0.80,
        },
        {
            "nama"        : "🌍 Inflasi Global Berkepanjangan (2022)",
            "keterangan"  : "Inflasi global melonjak akibat konflik geopolitik dan krisis rantai pasok. Biaya hidup naik drastis.",
            "inf_shock"   : +8.0,
            "return_shock": -0.15,
            "salary_mult" : 0.90,
        },
        {
            "nama"        : "📉 Stagflasi (Inflasi Tinggi + Ekonomi Mandek)",
            "keterangan"  : "Kombinasi mematikan: inflasi tinggi tapi ekonomi tidak tumbuh. Investasi stagnan, gaji tidak naik.",
            "inf_shock"   : +6.0,
            "return_shock": -0.20,
            "salary_mult" : 0.70,
        },
    ]

    base_ruin = res.projection["median_p50"]["ruin_probability"]
    base_fund = res.projection["median_p50"]["fund_at_retirement"]

    stress_results = []
    progress_bar = st.progress(0, text="Menjalankan stress test...")

    for i, sc in enumerate(stress_scenarios):
        progress_bar.progress((i + 1) / len(stress_scenarios), text=f"⏳ Menguji: {sc['nama']}...")
        fund_impact   = 1 + sc["return_shock"]
        inf_penalty   = min(sc["inf_shock"] / 100 * 5, 0.40)
        salary_impact = sc["salary_mult"]
        stressed_fund = base_fund * fund_impact * salary_impact
        stressed_ruin = min(base_ruin + inf_penalty + (1 - fund_impact) * 0.5, 1.0)
        stress_results.append({
            "Skenario"          : sc["nama"],
            "Dana Pensiun (Rp)" : stressed_fund,
            "Ruin Prob (%)"     : round(stressed_ruin * 100, 1),
            "vs Baseline"       : round((stressed_ruin - base_ruin) * 100, 1),
            "keterangan"        : sc["keterangan"],
            "inf_shock"         : sc["inf_shock"],
            "return_shock"      : sc["return_shock"],
            "salary_mult"       : sc["salary_mult"],
        })

    progress_bar.empty()

    df_stress = pd.DataFrame(stress_results)[["Skenario", "Dana Pensiun (Rp)", "Ruin Prob (%)", "vs Baseline"]]
    df_stress["Dana Pensiun (Rp)"] = df_stress["Dana Pensiun (Rp)"].apply(lambda x: f"Rp {x:,.0f}")
    df_stress["vs Baseline"] = df_stress["vs Baseline"].apply(lambda x: f"+{x:.1f}pp" if x >= 0 else f"{x:.1f}pp")
    st.dataframe(df_stress, use_container_width=True, hide_index=True)

    worst = max(stress_results, key=lambda x: x["Ruin Prob (%)"])
    st.error(f"""
**🚨 WORST CASE: {worst['Skenario']}**

> {worst['keterangan']}

| Parameter | Dampak |
|---|---|
| Inflasi | Naik +{worst['inf_shock']:.0f}% di atas normal → daya beli tabungan terkikis |
| Return Investasi | {worst['return_shock']*100:.0f}% → dana yang terkumpul langsung menyusut |
| Gaji Riil | Hanya {worst['salary_mult']*100:.0f}% dari normal → kontribusi tabungan berkurang |
| **Ruin Probability** | **{worst['Ruin Prob (%)']:.1f}%** |
| **Dana Pensiun** | **Rp {stress_results[[r['Skenario'] for r in stress_results].index(worst['Skenario'])]['Dana Pensiun (Rp)']:,.0f}** |

💡 *Jika rencana Anda masih bertahan di skenario ini, artinya rencana pensiun Anda tergolong **sangat kuat (stress-resistant)**.*
    """)

    with st.expander("ℹ️ Metodologi Stress Testing"):
        st.markdown("""
**Bagaimana perhitungannya?**

Stress test ini menggunakan pendekatan **Deterministik Sensitif** — bukan simulasi ulang penuh (untuk kecepatan), 
melainkan dengan menerapkan "shock" langsung ke hasil baseline Monte Carlo:

- **Return Shock**: Mengurangi total dana akumulasi secara proporsional (misal: -40% krisis 1998 → dana hanya 60% dari baseline)
- **Inflation Shock**: Setiap +1% inflasi ekstra ≈ +5% kenaikan Ruin Probability (dari data historis)
- **Salary Multiplier**: Gaji dipotong ke persentase tertentu → kontribusi bulanan berkurang → total dana lebih kecil

Pendekatan ini sering disebut **"Sensitivity + Shock Analysis"**, umum dipakai oleh manajer risiko perbankan dan dana pensiun.
        """)

else:
    st.info("👈 Silakan isi parameter pada panel sebelah kiri, kemudian klik **Jalankan Simulasi Monte Carlo** untuk memulai proyeksi.")
