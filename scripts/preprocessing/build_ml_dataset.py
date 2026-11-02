#!/usr/bin/env python3
"""
GRASS GIS Python Console — Build ML-Ready Dataset
=========================================================================
Your landslide inventory CSV already contains:
  - All conditioning factors (aspect, curvature, dis_to_fault, etc.)
  - A 'slope_units' column linking each landslide point to its SU polygon

Strategy:
  1. Read the landslide CSV to get which slope_unit IDs contain landslides
  2. Read the full SU attribute table (already has raster stats from v.rast.stats)
  3. Merge: label=1 if SU id is in landslide set, else label=0
  4. Export final ML-ready CSV

No v.select or spatial geometry needed — pure attribute join.

USAGE:
  Update the 3 paths below, paste into GRASS Python console, run.
=========================================================================
"""

import os
import csv
import sys
import grass.script as gs

# =============================================================
# CONFIGURATION — update these 3 paths
# =============================================================

# Your landslide inventory CSV (the one with slope_units column)
LS_CSV     = r"D:\Research Landslide\Result\ls_scattered_1000_3x3.csv"

# The optimal slope unit vector already loaded in GRASS
# (must already have raster stats columns from v.rast.stats)
SU_MAP     = "su_a300000_c0_35"   # <-- change to your exact GRASS map name

# Output ML-ready CSV
OUTPUT_CSV = r"D:\Research Landslide\Result\ML_input\slope_units_ml_ready.csv"

# =============================================================
# STEP 1 — Read landslide CSV, collect SU ids that have landslides
# =============================================================

print("\n" + "="*65)
print("  Building ML-ready dataset")
print("="*65)

print("\n[1/4] Reading landslide inventory CSV...")

if not os.path.exists(LS_CSV):
    print(f"ERROR: File not found: {LS_CSV}")
    sys.exit(1)

ls_su_ids = set()   # slope_unit IDs that contain at least one landslide

with open(LS_CSV, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows_read = 0
    rows_skipped = 0
    for row in reader:
        su_val = row.get('slope_units', '').strip()
        if su_val == '' or su_val is None:
            rows_skipped += 1
            continue
        try:
            ls_su_ids.add(int(float(su_val)))
            rows_read += 1
        except ValueError:
            rows_skipped += 1

print(f"      Landslide points read : {rows_read}")
print(f"      Rows skipped (no SU)  : {rows_skipped}")
print(f"      Unique SU ids with LS : {len(ls_su_ids)}")
print(f"      Sample SU ids         : {sorted(list(ls_su_ids))[:10]} ...")

# =============================================================
# STEP 2 — Read full SU attribute table from GRASS
# =============================================================

print(f"\n[2/4] Reading slope unit attribute table from GRASS map '{SU_MAP}'...")

# Check map exists
try:
    gs.run_command('v.info', map=SU_MAP, quiet=True)
except Exception:
    print(f"ERROR: Map '{SU_MAP}' not found in GRASS.")
    print("       Run: g.list type=vector  to see available maps.")
    sys.exit(1)

# Get column names
cols_raw = gs.read_command('v.db.select', map=SU_MAP, flags='c')
columns = [c.strip() for c in cols_raw.strip().splitlines()]
print(f"      Columns found ({len(columns)}): {columns}")

# Check required columns exist
# v.rast.stats should have created these — adjust prefix if you used different ones
EXPECTED_PREFIXES = ['aspect', 'curvature', 'slope', 'twi', 'ndvi', 'ndwi',
                     'dis_to_fault', 'dis_to_river', 'dis_to_road', 'dis_to_thrust',
                     'roughness']

missing = []
for prefix in EXPECTED_PREFIXES:
    found = any(prefix in c.lower() for c in columns)
    if not found:
        missing.append(prefix)

if missing:
    print(f"\n  WARNING: These expected factor columns were not found: {missing}")
    print("  Make sure v.rast.stats has been run for all rasters.")
    print("  Continuing anyway — check your output CSV carefully.\n")
else:
    print("      All expected factor columns present.")

# Read the full attribute table
su_raw = gs.read_command('v.db.select', map=SU_MAP, separator='comma', format='csv')
su_lines = su_raw.strip().splitlines()
su_header = su_lines[0].split(',')
print(f"      Slope unit rows: {len(su_lines)-1}")

# =============================================================
# STEP 3 — Identify the SU identifier column
# =============================================================

print("\n[3/4] Identifying slope unit ID column and assigning labels...")

# The SU table has a 'cat' column (GRASS category = polygon ID)
# We match this against the slope_units values from the landslide CSV
# Try common column names in order
ID_CANDIDATES = ['cat', 'cat_', 'id', 'fid', 'su_id', 'slope_units']
id_col = None
for candidate in ID_CANDIDATES:
    if candidate in [c.lower() for c in su_header]:
        id_col = next(c for c in su_header if c.lower() == candidate)
        break

if id_col is None:
    print(f"ERROR: Cannot find ID column. Available: {su_header}")
    print("       Set id_col manually below.")
    sys.exit(1)

print(f"      Using '{id_col}' as slope unit identifier")
id_idx = su_header.index(id_col)

# =============================================================
# STEP 4 — Write ML-ready CSV with label column
# =============================================================

print(f"\n[4/4] Writing ML-ready CSV...")

os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

label_1_count = 0
label_0_count = 0

out_header = su_header + ['label']

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as fout:
    writer = csv.writer(fout)
    writer.writerow(out_header)

    for line in su_lines[1:]:
        if not line.strip():
            continue
        vals = line.split(',')
        if len(vals) != len(su_header):
            continue

        try:
            su_id = int(float(vals[id_idx]))
        except ValueError:
            su_id = -1

        label = 1 if su_id in ls_su_ids else 0

        if label == 1:
            label_1_count += 1
        else:
            label_0_count += 1

        writer.writerow(vals + [label])

total = label_1_count + label_0_count

print(f"      Total slope units : {total}")
print(f"      Landslide  (1)    : {label_1_count}  ({label_1_count/total*100:.1f}%)")
print(f"      Non-landslide (0) : {label_0_count}  ({label_0_count/total*100:.1f}%)")
print(f"      Saved -> {OUTPUT_CSV}")

# =============================================================
# SUMMARY
# =============================================================

print("\n" + "-"*65)
print("  COLUMN GUIDE FOR ML")
print("-"*65)
feature_cols = [c for c in su_header
                if c.lower() not in ('cat', 'cat_', 'fid', 'id', 'label',
                                     'x_coor', 'y_coor', 'x', 'y',
                                     'area_val', 'value')]
print(f"  Feature columns ({len(feature_cols)}):")
for c in feature_cols:
    print(f"    - {c}")
print(f"  Target column : label  (1=landslide, 0=non-landslide)")
print(f"  Drop before ML: cat, cat_, x_coor, y_coor, area_val (if present)")

print("\n" + "="*65)
print("  DONE — CSV is ready for RF / SVM / XGBoost")
print("="*65 + "\n")
