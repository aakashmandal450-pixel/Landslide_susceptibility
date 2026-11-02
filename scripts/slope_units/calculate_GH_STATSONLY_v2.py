#!/usr/bin/env python3
"""
GRASS GIS Python Console — FIXED & IMPROVED VERSION
=========================================================================
Changes from original calculate_GH_STATSONLY.py:
  ✓ Fixed parse_csv: now uses comma separator (v.db.select format='csv')
  ✓ Fixed polygon count: uses actual DB row count, not v.info primitives
  ✓ Fixed wMI: proper sequential lag (no wrap-around from np.roll)
  ✓ Fixed v.build called BEFORE polygon count check
  ✓ Cleaner error messages with more context

USAGE:
  1. Tools > Python console in GRASS GIS
  2. Copy & paste this script (or File > Run script)
  3. Update the CONFIGURATION section below
  4. Run
=========================================================================
"""

import os
import re
import sys
import csv
import time
import grass.script as gs
import numpy as np

# =============================================================
# ⚠️  CONFIGURATION — UPDATE THESE LINES
# =============================================================

GPKG_FOLDER   = r"D:\Research Landslide\Result\New_output\Slopeunits"
ASPECT_RASTER = "aspect_3x3"
OUTPUT_CSV    = os.path.join(GPKG_FOLDER, "SlopeUnit_GH_Results.csv")
OUTPUT_EXCEL  = os.path.join(GPKG_FOLDER, "SlopeUnit_GH_Results.xlsx")

# Minimum number of valid polygons required to compute V / wMI
MIN_POLYGONS = 3

# =============================================================
# HELPERS
# =============================================================

TIMESTAMP = str(int(time.time()))


def clean_temp(mapname):
    """Silently remove a temporary GRASS vector."""
    try:
        gs.run_command('g.remove', type='vector', name=mapname,
                       flags='f', quiet=True)
    except Exception:
        pass


def parse_csv(csv_str):
    """
    Parse comma-separated output from v.db.select (format='csv').
    Returns list of dicts keyed by column name.

    BUG FIX vs original: original used '|' as separator but
    v.db.select format='csv' outputs commas. This version is correct.
    """
    lines = [l for l in csv_str.strip().split('\n') if l.strip()]
    if len(lines) < 2:
        return []

    reader = csv.DictReader(lines)
    return [row for row in reader]


def to_float(val):
    """Safely convert a value to float, returning None on failure."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def compute_wMI(asp_arr):
    """
    Compute a sequential lag-1 Moran-like index on aspect values.

    BUG FIX vs original: np.roll wraps the last element back to position 0,
    creating a spurious lag pair. This version uses proper sequential lag
    (pairs i and i+1 only, dropping the wrap-around pair).
    """
    if len(asp_arr) < 2:
        return 0.0

    mean = np.mean(asp_arr)
    deviations = asp_arr - mean

    # Sequential lag: pair each element with its neighbour (no wrap)
    numerator   = np.sum(deviations[:-1] * deviations[1:])
    denominator = np.sum(deviations ** 2)

    if denominator == 0:
        return 0.0

    wmi = numerator / denominator
    return wmi if np.isfinite(wmi) else 0.0


def compute_V(asp_arr, area_arr):
    """
    Area-weighted variance of aspect values.
    V = var(aspect) * mean(weight)  where weight = area / total_area
    """
    total_area = area_arr.sum()
    if total_area == 0:
        return 0.0
    weights = area_arr / total_area
    V = np.var(asp_arr) * np.mean(weights)
    return V if np.isfinite(V) else 0.0


# =============================================================
# MAIN
# =============================================================

print("\n" + "=" * 70)
print("GRASS GIS — Slope Unit GH Calculator  (v2 — fixed)")
print("=" * 70 + "\n")

# ── 0. Verify raster exists ───────────────────────────────────────────────
try:
    gs.run_command('r.info', map=ASPECT_RASTER, quiet=True)
    print(f"✓ Raster found: {ASPECT_RASTER}\n")
except Exception:
    print(f"✗ Raster '{ASPECT_RASTER}' not found in current GRASS mapset.")
    print("  Make sure you are inside the correct GRASS location/mapset.\n")
    sys.exit(1)

# ── 1. Collect .gpkg files ────────────────────────────────────────────────
print("[Step 1] Scanning for .gpkg files...")
try:
    all_files = os.listdir(GPKG_FOLDER)
except Exception as e:
    print(f"✗ Cannot read folder: {GPKG_FOLDER}\n  {e}")
    sys.exit(1)

gpkg_files = sorted(
    f for f in all_files
    if f.endswith('.gpkg') and f.startswith('su_a')
)

if not gpkg_files:
    print(f"✗ No matching .gpkg files (su_a*.gpkg) found in:\n  {GPKG_FOLDER}")
    sys.exit(1)

print(f"✓ Found {len(gpkg_files)} file(s)\n")

# ── 2. Process each file ──────────────────────────────────────────────────
records = []
total   = len(gpkg_files)

for idx, fname in enumerate(gpkg_files, 1):

    # Parse a and c from filename: su_a<int>_c<float_with_underscore>.gpkg
    match = re.match(r"su_a(\d+)_c([\d_]+)\.gpkg", fname)
    if not match:
        print(f"[{idx}/{total}] SKIP (filename doesn't match pattern): {fname}")
        continue

    a_val = int(match.group(1))
    c_val = float(match.group(2).replace("_", "."))
    fpath = os.path.join(GPKG_FOLDER, fname)
    temp  = f"tmp_gh_{TIMESTAMP}_{idx}"

    print(f"[{idx}/{total}] a={a_val:6d}  c={c_val:.2f} ... ", end='', flush=True)

    def fail(reason):
        """Record a failure and clean up."""
        print(f"✗ {reason}")
        records.append([a_val, c_val, None, None, None, None, reason])
        clean_temp(temp)

    try:
        # — Import —
        clean_temp(temp)
        gs.run_command('v.import', input=fpath, output=temp,
                       overwrite=True, quiet=True)

        # — Build topology (must come BEFORE any attribute/count queries) —
        gs.run_command('v.build', map=temp, quiet=True)

        # — Count polygons via DB (reliable, unlike v.info primitives) —
        count_str = gs.read_command('v.db.select', map=temp,
                                    flags='c').strip()
        # flags='c' returns column names only; use row count from full select
        all_rows = gs.read_command('v.db.select', map=temp,
                                   format='csv').strip().split('\n')
        n_polygons = max(0, len(all_rows) - 1)  # subtract header

        if n_polygons < MIN_POLYGONS:
            fail(f"too few polygons ({n_polygons} < {MIN_POLYGONS})")
            continue

        # — Compute per-polygon aspect statistics —
        try:
            gs.run_command('v.rast.stats', map=temp, raster=ASPECT_RASTER,
                           column_prefix='asp', method='average,stddev',
                           flags='c',   # skip polygons with all-NULL raster
                           quiet=True)
        except Exception as e:
            fail(f"v.rast.stats error: {str(e)[:40]}")
            continue

        # — Compute per-polygon area —
        try:
            gs.run_command('v.to.db', map=temp, option='area',
                           columns='area_val', overwrite=True, quiet=True)
        except Exception as e:
            fail(f"v.to.db error: {str(e)[:40]}")
            continue

        # — Read attribute table —
        try:
            csv_out = gs.read_command('v.db.select', map=temp, format='csv')
        except Exception as e:
            fail(f"v.db.select error: {str(e)[:40]}")
            continue

        rows = parse_csv(csv_out)
        if not rows:
            fail("no rows returned from attribute table")
            continue

        # — Extract valid (aspect, area) pairs —
        asp_vals  = []
        area_vals = []
        for row in rows:
            a  = to_float(row.get('asp_average'))
            ar = to_float(row.get('area_val'))
            if a is not None and ar is not None and ar > 0:
                asp_vals.append(a)
                area_vals.append(ar)

        if len(asp_vals) < MIN_POLYGONS:
            fail(f"only {len(asp_vals)} valid polygons (need ≥{MIN_POLYGONS})")
            continue

        # — Calculate metrics —
        asp_arr  = np.array(asp_vals)
        area_arr = np.array(area_vals)

        # Sort by aspect before computing wMI (sequential lag)
        sorted_idx = np.argsort(asp_arr)
        asp_sorted  = asp_arr[sorted_idx]
        area_sorted = area_arr[sorted_idx]

        V   = compute_V(asp_sorted, area_sorted)
        wMI = compute_wMI(asp_sorted)

        print(f"✓  n={len(asp_vals):4d}  V={V:.4f}  wMI={wMI:.4f}")
        records.append([a_val, c_val, len(asp_vals), V, wMI, None, 'Success'])

    except Exception as e:
        fail(str(e)[:50])

    finally:
        clean_temp(temp)

# ── 3. Calculate GH ───────────────────────────────────────────────────────
print("\n" + "-" * 70)
print("[Step 2] Calculating GH scores...")

success  = [r for r in records if r[6] == 'Success']
n_ok     = len(success)
print(f"  Successful: {n_ok} / {total}")

if n_ok >= 2:
    V_vals   = [r[3] for r in success]
    wMI_vals = [r[4] for r in success]

    Vmin,   Vmax   = min(V_vals),   max(V_vals)
    wMImin, wMImax = min(wMI_vals), max(wMI_vals)

    V_range   = Vmax   - Vmin   if Vmax   > Vmin   else 1.0
    wMI_range = wMImax - wMImin if wMImax > wMImin else 1.0

    print(f"  V   range : {Vmin:.6f} – {Vmax:.6f}")
    print(f"  wMI range : {wMImin:.6f} – {wMImax:.6f}")

    for r in records:
        if r[6] == 'Success':
            gh   = (r[3] - Vmin) / V_range + (r[4] - wMImin) / wMI_range
            r[5] = gh

    best = min((r for r in records if r[5] is not None), key=lambda x: x[5])
    print(f"\n  🏆 OPTIMAL PARAMETERS:")
    print(f"     a  = {int(best[0])}")
    print(f"     c  = {best[1]:.2f}")
    print(f"     GH = {best[5]:.6f}")
    print(f"     V  = {best[3]:.6f}")
    print(f"     wMI= {best[4]:.6f}")
    print(f"     Polygons = {int(best[2])}")

elif n_ok == 1:
    print("  ⚠ Only 1 successful file — GH normalisation requires ≥ 2.")
else:
    print("  ✗ No successful files. Check errors above.")

# ── 4. Save results ───────────────────────────────────────────────────────
print(f"\n[Step 3] Saving results...")

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['a', 'c', 'SlopeUnits', 'V', 'wMI', 'GH', 'Status'])
    for r in records:
        a, c, su, v, wmi, gh, st = r
        writer.writerow([
            a,
            c,
            su  if su  is not None else '',
            f"{v:.6f}"   if v   is not None else '',
            f"{wmi:.6f}" if wmi is not None else '',
            f"{gh:.6f}"  if gh  is not None else '',
            st
        ])

print(f"✓ CSV saved  : {OUTPUT_CSV}")

# Optional Excel export
try:
    import openpyxl
    import csv as _csv

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "GH Results"

    with open(OUTPUT_CSV, encoding='utf-8') as f:
        for row in _csv.reader(f):
            ws.append(row)

    # Basic header formatting
    from openpyxl.styles import Font, PatternFill
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="2E75B6")
    for cell in ws[1]:
        cell.font  = header_font
        cell.fill  = header_fill

    wb.save(OUTPUT_EXCEL)
    print(f"✓ Excel saved: {OUTPUT_EXCEL}")

except ImportError:
    print("  (openpyxl not installed — skipping Excel export, use CSV)")
except Exception as e:
    print(f"  (Excel export failed: {e} — use CSV)")

print("\n" + "=" * 70)
print("✓ DONE")
print("=" * 70 + "\n")
