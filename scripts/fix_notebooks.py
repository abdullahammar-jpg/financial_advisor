import json
from pathlib import Path

# Mendefinisikan direktori notebook
NB_DIR = Path(__file__).parent.parent / "notebooks"

#! 1. Pemrosesan Data Wrangling Part 1
nb1_path = NB_DIR / "data_wrangling_part1_cpi.ipynb"
with open(nb1_path, "r", encoding="utf-8") as f:
    nb1 = json.load(f)

# Pola lama dan pola baru untuk path ROOT notebook
OLD = "if ROOT.name == 'scripts': ROOT = ROOT.parent\n"
NEW = "if ROOT.name in ('scripts', 'notebooks'): ROOT = ROOT.parent\n"

#! 2. Penerapan perbaikan path ROOT di sel kode notebook Part 1
patched_count = 0
for cell in nb1["cells"]:
    if cell["cell_type"] == "code":
        new_source = []
        for line in cell["source"]:
            if OLD in line:
                line = line.replace(OLD, NEW)
                patched_count += 1
            new_source.append(line)
        cell["source"] = new_source

if patched_count == 0:
    print("WARNING: Pattern not found in Part 1 — might already be fixed or changed.")
else:
    print(f"Part 1: patched {patched_count} line(s)")

#! 3. Penghapusan riwayat output sel kode Part 1 agar berkas bersih
for cell in nb1["cells"]:
    if cell["cell_type"] == "code":
        cell["outputs"] = []
        cell["execution_count"] = None

with open(nb1_path, "w", encoding="utf-8") as f:
    json.dump(nb1, f, ensure_ascii=False, indent=1)
print(f"Part 1 saved: {nb1_path}")

#! 4. Pemrosesan Data Wrangling Part 2
nb2_path = NB_DIR / "data_wrangling_part2_sektor_gaji_investasi.ipynb"
with open(nb2_path, "r", encoding="utf-8") as f:
    nb2 = json.load(f)

#! 5. Penerapan perbaikan path ROOT di sel kode notebook Part 2
found_root_fix = False
for cell in nb2["cells"]:
    if cell["cell_type"] == "code":
        for line in cell["source"]:
            if "ROOT.name in ('scripts','notebooks')" in line or "ROOT.name in ('scripts', 'notebooks')" in line:
                found_root_fix = True

if found_root_fix:
    print("Correct")
else:
    OLD2 = "if ROOT.name == 'scripts': ROOT = ROOT.parent\n"
    NEW2 = "if ROOT.name in ('scripts', 'notebooks'): ROOT = ROOT.parent\n"
    for cell in nb2["cells"]:
        if cell["cell_type"] == "code":
            cell["source"] = [l.replace(OLD2, NEW2) for l in cell["source"]]

#! 6. Penghapusan riwayat output sel kode Part 2
for cell in nb2["cells"]:
    if cell["cell_type"] == "code":
        cell["outputs"] = []
        cell["execution_count"] = None

with open(nb2_path, "w", encoding="utf-8") as f:
    json.dump(nb2, f, ensure_ascii=False, indent=1)
print(f"Part 2 saved: {nb2_path}")
