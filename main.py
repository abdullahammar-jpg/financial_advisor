import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.calculator import RetirementCalculator, UserProfile
from src.inflation import get_inflation_summary, calibrate_ou_params
from src.investment import get_instrument_comparison_table, fetch_idx_historical_returns
from src.actuarial import get_mortality_table

def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def main():
    
    #! 1. Definisikan profil pengguna simulasi bawaan
    profile = UserProfile(
        name           = "Rizky",
        age            = 25,
        gender         = "male", 
        monthly_salary = 8000000,   
        savings_rate   = 0.20,         
        retirement_age = 55,
        risk_profile   = "moderate",
        sector         = "Pertanian, Kehutanan, dan Perikanan",
        include_pandemic_risk = True,
        custom_deposit_rate = 8.0, 
    )

    from src.calculator import get_salary_growth
    growth_rate = get_salary_growth(profile)

    print(f"Profil: {profile.name} | Usia: {profile.age} thn | "
          f"Gaji: Rp {profile.monthly_salary:,} | "
          f"Target Pensiun: {profile.retirement_age} thn")
    print(f"Sektor: {profile.sector}")
    print(f"Salary Growth: {growth_rate*100:.2f}%/tahun (Pandemic Risk: {profile.include_pandemic_risk})")
    print(f"Custom Deposit Rate: {profile.custom_deposit_rate}% (Bunga Bank Digital/BPR)")

    #! 2. Tampilkan metrik aktuaria harapan hidup
    print_section("1. Ringkasan Aktuarial")
    mt = get_mortality_table() 
    actuarial = mt.get_planning_summary(profile.age, profile.retirement_age, profile.gender) 
    
    print(f"  Sumber data mortalitas : {actuarial['source']}") 
    print(f"  Expected death age     : {actuarial['expected_death_age']} tahun") 
    print(f"  P50 survival age       : {actuarial['p50_survival_age']} tahun (50% masih hidup)") 
    print(f"  P90 survival age       : {actuarial['p90_survival_age']} tahun (10% masih hidup)")
    print(f"  Planning horizon       : {actuarial['planning_horizon_post_retirement']} tahun setelah pensiun")
    print(f"  Longevity risk flag    : {'[!] YA' if actuarial['longevity_risk_flag'] else '[OK] TIDAK'}")
    
    #! 3. Tampilkan parameter kalibrasi model inflasi OU
    print_section("2. Proyeksi Inflasi (Ornstein-Uhlenbeck)")
    ou_params = calibrate_ou_params()
    print(f"  Parameter kalibrasi dari: {ou_params['calibrated_from']}")
    print(f"  (long-term mean): {ou_params['theta']}%")
    print(f"  (mean-reversion speed): {ou_params['kappa']}")
    print(f"  (volatilitas): {ou_params['sigma']}%") 

    inf_summary = get_inflation_summary(n_years=30)
    print(f"\n  Proyeksi 30 tahun ke depan:")
    print(f"    P10 (skenario ringan) : {inf_summary['projected_p10_pct']}% per tahun")
    print(f"    P50 (median)          : {inf_summary['projected_p50_pct']}% per tahun")
    print(f"    P90 (skenario berat)  : {inf_summary['projected_p90_pct']}% per tahun")

    #! 4. Tampilkan daftar instrumen investasi
    print_section("3. Instrumen Investasi yang Tersedia")
    df = get_instrument_comparison_table()
    print(df[["Instrumen", "Return Nominal (mean)", "Volatilitas", "Risk Level"]].to_string(index=False))

    #! 5. Tampilkan data return IHSG historis
    print_section("4. Data Historis IDX Composite (via yfinance)")
    idx_df = fetch_idx_historical_returns(period="10y")
    print(idx_df.tail(10).to_string(index=False))
    print(f"\n  Rata-rata return IDX 10Y : {idx_df['annual_return_pct'].mean():.2f}%")
    print(f"  Std Dev (volatilitas)    : {idx_df['annual_return_pct'].std():.2f}%")

    #! 6. Eksekusi Simulasi Monte Carlo Pensiun
    print_section("5. Menjalankan Monte Carlo Simulation (10.000 iterasi)...")
    print("  [Ini mungkin membutuhkan 30-60 detik...]\n")

    calculator = RetirementCalculator(n_simulations=10_000)
    result     = calculator.calculate(profile)

    #! 7. Tampilkan hasil simulasi per skenario persentil
    print_section("6. Hasil Proyeksi")
    for key, scenario in result.projection.items():
        print(f"\n  [{scenario['percentile']}]")
        print(f"    Dana saat pensiun      : Rp {scenario['fund_at_retirement']:>15,.0f}")
        print(f"    Nilai real (hari ini)  : Rp {scenario['real_fund_at_retirement']:>15,.0f}")
        print(f"    Kapasitas tarik/tahun  : Rp {scenario['annual_withdrawal_capacity']:>15,.0f}")
        print(f"    Ruin probability       : {scenario['ruin_probability']*100:.1f}%")
        if scenario['fund_depleted_age']:
            print(f"    Dana habis di usia     : {scenario['fund_depleted_age']} tahun")

    #! 8. Tampilkan rekomendasi umum kalkulator
    print_section("7. Rekomendasi")
    rec = result.recommendations
    print(f"  On track           : {'[OK] YA' if rec['is_on_track'] else '[X] TIDAK'}")
    print(f"  Effective profile  : {rec['effective_risk_profile'].upper()}")
    print(f"  Glide path applied : {'Ya' if rec['glide_path_applied'] else 'Tidak'}")
    print(f"  Fund gap           : Rp {rec['fund_gap_positive_means_surplus']:>15,.0f} "
          f"({'SURPLUS' if rec['fund_gap_positive_means_surplus'] >= 0 else 'DEFICIT'})")

    #! 9. Tampilkan hasil uji A/B testing
    print_section("8. A/B Test: Fixed vs Glide Path")
    ab = result.ab_test_result
    print(f"  Strategy A (Fixed)      : {ab['strategy_a_fixed']['ruin_probability']*100:.1f}% ruin prob")
    print(f"  Strategy B (Glide Path) : {ab['strategy_b_glide_path']['ruin_probability']*100:.1f}% ruin prob")
    print(f"  Winner                  : {ab['winner']}")
    print(f"  p-value                 : {ab['p_value']}")
    print(f"  Signifikan              : {'[OK] YA (p<0.05)' if ab['statistically_significant'] else '[X] TIDAK'}")

    #! 10. Jalankan & Tampilkan uji Stress Testing krisis makro ekonomi
    print_section("9. Stress Testing — Skenario Krisis")
    print("  Menjalankan 4 skenario terburuk dalam sejarah ekonomi Indonesia...\n")

    stress_scenarios = [
        {
            "nama"        : "Krisis Moneter 1998",
            "keterangan"  : "Inflasi mencapai 58%, rupiah jatuh 80%, PHK massal di mana-mana.",
            "inf_shock"   : +15.0,   
            "return_shock": -0.40,   
            "salary_mult" : 0.50,    
        },
        {
            "nama"        : "Pandemi COVID-19 (2020-2021)",
            "keterangan"  : "IHSG turun -38% dalam 1 bulan, banyak sektor lumpuh, salary freeze.",
            "inf_shock"   : +2.0,
            "return_shock": -0.38,
            "salary_mult" : 0.80,
        },
        {
            "nama"        : "Inflasi Tinggi Berkepanjangan (à la 2022 Global)",
            "keterangan"  : "Inflasi global naik tajam akibat konflik geopolitik & supply chain shock.",
            "inf_shock"   : +8.0,
            "return_shock": -0.15,
            "salary_mult" : 0.90,
        },
        {
            "nama"        : "Stagflasi (Inflasi Tinggi + Ekonomi Mandek)",
            "keterangan"  : "Inflasi tinggi tapi ekonomi tidak tumbuh. Skenario paling mematikan untuk tabungan.",
            "inf_shock"   : +6.0,
            "return_shock": -0.20,
            "salary_mult" : 0.70,
        },
    ]

    stress_results = []
    for i, sc in enumerate(stress_scenarios, 1):
        print(f"  [ ] Menjalankan: {sc['nama']}...", end="\r")

        from dataclasses import replace as dc_replace
        stressed_profile = UserProfile(
            name                 = profile.name,
            age                  = profile.age,
            gender               = profile.gender,
            monthly_salary       = profile.monthly_salary,
            savings_rate         = profile.savings_rate,
            retirement_age       = profile.retirement_age,
            risk_profile         = profile.risk_profile,
            sector               = profile.sector,
            include_pandemic_risk= profile.include_pandemic_risk,
            custom_deposit_rate  = profile.custom_deposit_rate,
            current_assets       = profile.current_assets,
            annual_bonus_months  = profile.annual_bonus_months * sc["salary_mult"],
            replacement_ratio    = profile.replacement_ratio,
            has_health_insurance = profile.has_health_insurance,
        )

        base_ruin   = result.projection["median_p50"]["ruin_probability"]
        base_fund   = result.projection["median_p50"]["fund_at_retirement"]

        fund_impact   = 1 + sc["return_shock"]                     
        inf_penalty   = min(sc["inf_shock"] / 100 * 5, 0.40)      
        salary_impact = sc["salary_mult"]

        stressed_fund = base_fund * fund_impact * salary_impact
        stressed_ruin = min(base_ruin + inf_penalty + (1 - fund_impact) * 0.5, 1.0)
        stressed_ruin = round(stressed_ruin, 4)

        stress_results.append({
            "nama"         : sc["nama"],
            "keterangan"   : sc["keterangan"],
            "fund_stressed": stressed_fund,
            "ruin_prob"    : stressed_ruin,
            "inf_shock"    : sc["inf_shock"],
            "return_shock" : sc["return_shock"],
            "salary_mult"  : sc["salary_mult"],
        })

        status = "[OK]" if stressed_ruin < 0.50 else "[!!]"
        print(f"  {status} {sc['nama']:<45} Ruin: {stressed_ruin*100:.1f}% | Dana: Rp {stressed_fund:>15,.0f}")

    worst = max(stress_results, key=lambda x: x["ruin_prob"])

    print(f"\n  {'='*58}")
    print(f"  [WORST CASE] Skenario Terburuk: {worst['nama']}")
    print(f"  {'='*58}")
    print(f"  Ruin Probability  : {worst['ruin_prob']*100:.1f}%")
    print(f"  Dana saat pensiun : Rp {worst['fund_stressed']:>15,.0f}")
    print(f"\n  Kenapa ini skenario terburuk?")
    print(f"  - Inflasi naik +{worst['inf_shock']:.0f}% di atas normal → daya beli tabungan terkikis drastis.")
    print(f"  - Return investasi: {worst['return_shock']*100:.0f}% → dana yang terkumpul langsung menyusut.")
    print(f"  - Gaji riil hanya {worst['salary_mult']*100:.0f}% dari normal → kontribusi tabungan berkurang.")
    print(f"\n  {worst['keterangan']}")
    print(f"\n  Catatan: Jika kamu masih bisa bertahan di skenario ini,")
    print(f"  rencana pensiunmu tergolong SANGAT KUAT (stress-resistant).")

    #! 11. Tampilkan Actionable Insights final
    print_section("10. Actionable Insights")
    for i, insight in enumerate(result.actionable_insights, 1):
        print(f"  {i}. {insight}")

    output_path = "data/processed/result_output.json"
    os.makedirs("data/processed", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.to_json())

    print_section("[DONE] Selesai")
    print(f"  JSON output disimpan di: {output_path}")
    print("  Siap disambungkan ke front-end / AI Engineer.")

if __name__ == "__main__":
    main()
