"""
Applicability Domain Validation Script
Landslide Susceptibility Mapping — Karnali Highway Corridor
Output: AD validation table for paper (CSV + printed summary)
"""

import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask as rio_mask
import geopandas as gpd
from scipy.stats import spearmanr
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# 1. FILE PATHS  — change only this block
# ─────────────────────────────────────────────
BASE = r"D:\Research Landslide\Applicability Domain"

RESOLUTIONS = ["3x3", "15x15", "25x25"]

FILES = {
    res: {
        "trusted"      : f"{BASE}\\Trusted_mask_{res}.tif",
        "ensemble"     : f"{BASE}\\Ensemble_susceptibility_{res}.tif",
        "mahal"        : f"{BASE}\\Mahalanobis_distance_{res}.tif",
        "disagreement" : f"{BASE}\\Model_disagreement_std_{res}.tif",
        "domain_score" : f"{BASE}\\Domain_score_{res}.tif",
    }
    for res in RESOLUTIONS
}

INVENTORY_GPKG = f"{BASE}\\landslide_polygon_20mbuffered.gpkg"

# ─────────────────────────────────────────────
# 2. HELPER FUNCTIONS
# ─────────────────────────────────────────────

def read_raster(path):
    """Read raster, return (data array, nodata value, transform, crs)."""
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float32)
        nodata = src.nodata
        transform = src.transform
        crs = src.crs
    if nodata is not None:
        data[data == nodata] = np.nan
    return data, transform, crs


def zonal_stats_two_zones(trusted_arr, value_arr):
    """
    Compute mean, std, min, max of value_arr
    separately for trusted (1) and untrusted (0) pixels.
    Both arrays must have same shape.
    """
    # valid mask — neither array is nan
    valid = (~np.isnan(trusted_arr)) & (~np.isnan(value_arr))

    trusted_pixels   = value_arr[valid & (trusted_arr == 1)]
    untrusted_pixels = value_arr[valid & (trusted_arr == 0)]

    def stats(arr):
        if len(arr) == 0:
            return dict(count=0, mean=np.nan, std=np.nan, min=np.nan, max=np.nan)
        return dict(
            count = int(len(arr)),
            mean  = float(np.mean(arr)),
            std   = float(np.std(arr)),
            min   = float(np.min(arr)),
            max   = float(np.max(arr)),
        )

    return stats(trusted_pixels), stats(untrusted_pixels)


def landslide_capture_rate(trusted_arr, transform, crs, inventory_path):
    """
    Compute % of landslide polygons whose centroid falls in trusted zone.
    Also compute landslide pixel density (polygons per km²) in each zone.
    """
    gdf = gpd.read_file(inventory_path)

    # reproject inventory to raster CRS if needed
    if gdf.crs != crs:
        gdf = gdf.to_crs(crs)

    total_polygons = len(gdf)
    trusted_count  = 0
    untrusted_count = 0

    rows_total, cols_total = trusted_arr.shape

    for geom in gdf.geometry:
        # use centroid
        cx, cy = geom.centroid.x, geom.centroid.y
        # convert to pixel row/col
        col, row = ~transform * (cx, cy)
        row, col = int(row), int(col)
        # bounds check
        if 0 <= row < rows_total and 0 <= col < cols_total:
            val = trusted_arr[row, col]
            if np.isnan(val):
                continue
            if val == 1:
                trusted_count += 1
            else:
                untrusted_count += 1

    capture_rate = (trusted_count / total_polygons * 100) if total_polygons > 0 else np.nan

    return {
        "total_landslide_polygons" : total_polygons,
        "captured_in_trusted"      : trusted_count,
        "captured_in_untrusted"    : untrusted_count,
        "capture_rate_pct"         : round(capture_rate, 2),
    }


def spearman_correlation(arr1, arr2):
    """Spearman rank correlation between two rasters (valid pixels only)."""
    valid = (~np.isnan(arr1)) & (~np.isnan(arr2))
    if valid.sum() < 10:
        return np.nan, np.nan
    # subsample if very large to keep speed reasonable (max 500k pixels)
    idx = np.where(valid.ravel())[0]
    if len(idx) > 500_000:
        rng = np.random.default_rng(42)
        idx = rng.choice(idx, size=500_000, replace=False)
    r, p = spearmanr(arr1.ravel()[idx], arr2.ravel()[idx])
    return round(float(r), 4), float(p)


# ─────────────────────────────────────────────
# 3. MAIN ANALYSIS LOOP
# ─────────────────────────────────────────────

summary_rows = []
correlation_rows = []

print("=" * 65)
print("  APPLICABILITY DOMAIN VALIDATION")
print("=" * 65)

for res in RESOLUTIONS:
    print(f"\n--- Resolution: {res} ---")

    # load rasters
    trusted_arr,   transform, crs = read_raster(FILES[res]["trusted"])
    ensemble_arr,  _,         _   = read_raster(FILES[res]["ensemble"])
    mahal_arr,     _,         _   = read_raster(FILES[res]["mahal"])
    disagree_arr,  _,         _   = read_raster(FILES[res]["disagreement"])
    domain_arr,    _,         _   = read_raster(FILES[res]["domain_score"])

    # ── Coverage statistics ──────────────────
    valid_mask   = ~np.isnan(trusted_arr)
    total_valid  = int(valid_mask.sum())
    trusted_px   = int(np.nansum(trusted_arr == 1))
    untrusted_px = int(np.nansum(trusted_arr == 0))
    trusted_pct  = round(trusted_px   / total_valid * 100, 2)
    untrusted_pct= round(untrusted_px / total_valid * 100, 2)

    print(f"  Total valid pixels  : {total_valid:,}")
    print(f"  Trusted pixels      : {trusted_px:,}  ({trusted_pct}%)")
    print(f"  Untrusted pixels    : {untrusted_px:,}  ({untrusted_pct}%)")

    # ── Zonal stats for each variable ────────
    t_ens,  u_ens  = zonal_stats_two_zones(trusted_arr, ensemble_arr)
    t_mah,  u_mah  = zonal_stats_two_zones(trusted_arr, mahal_arr)
    t_dis,  u_dis  = zonal_stats_two_zones(trusted_arr, disagree_arr)
    t_dom,  u_dom  = zonal_stats_two_zones(trusted_arr, domain_arr)

    print(f"  Mean Ensemble Susc  : Trusted={t_ens['mean']:.4f}  Untrusted={u_ens['mean']:.4f}")
    print(f"  Mean Mahal Distance : Trusted={t_mah['mean']:.4f}  Untrusted={u_mah['mean']:.4f}")
    print(f"  Mean Disagree Std   : Trusted={t_dis['mean']:.4f}  Untrusted={u_dis['mean']:.4f}")
    print(f"  Mean Domain Score   : Trusted={t_dom['mean']:.4f}  Untrusted={u_dom['mean']:.4f}")

    # ── Landslide capture rate ────────────────
    print(f"  Computing landslide capture rate ...")
    capture = landslide_capture_rate(trusted_arr, transform, crs, INVENTORY_GPKG)
    print(f"  Landslide polygons  : {capture['total_landslide_polygons']}")
    print(f"  Captured in trusted : {capture['captured_in_trusted']}  ({capture['capture_rate_pct']}%)")
    print(f"  Captured in untrusted: {capture['captured_in_untrusted']}")

    # ── Spearman correlation: Mahal vs Disagreement ──
    r_val, p_val = spearman_correlation(mahal_arr, disagree_arr)
    print(f"  Spearman r (Mahal vs Disagree): {r_val}  (p={p_val:.4f})")

    # ── Threshold sensitivity: Domain_score at 0.4, 0.5, 0.6 ──
    for thresh in [0.4, 0.5, 0.6]:
        mask_t = domain_arr >= thresh
        count_t = int(np.nansum(mask_t & valid_mask))
        pct_t   = round(count_t / total_valid * 100, 2)
        print(f"  Threshold {thresh}: trusted coverage = {pct_t}%  ({count_t:,} px)")

    # ── Store for output table ────────────────
    summary_rows.append({
        "Resolution"                        : res,
        "Total_Valid_Pixels"                : total_valid,
        "Trusted_Pixels"                    : trusted_px,
        "Trusted_Coverage_pct"              : trusted_pct,
        "Untrusted_Pixels"                  : untrusted_px,
        "Untrusted_Coverage_pct"            : untrusted_pct,
        "Mean_Ensemble_Susc_Trusted"        : round(t_ens["mean"], 4),
        "Mean_Ensemble_Susc_Untrusted"      : round(u_ens["mean"], 4),
        "Mean_Mahal_Dist_Trusted"           : round(t_mah["mean"], 4),
        "Mean_Mahal_Dist_Untrusted"         : round(u_mah["mean"], 4),
        "Mean_Disagree_Std_Trusted"         : round(t_dis["mean"], 4),
        "Mean_Disagree_Std_Untrusted"       : round(u_dis["mean"], 4),
        "Mean_Domain_Score_Trusted"         : round(t_dom["mean"], 4),
        "Mean_Domain_Score_Untrusted"       : round(u_dom["mean"], 4),
        "Total_Landslide_Polygons"          : capture["total_landslide_polygons"],
        "Landslides_Captured_Trusted"       : capture["captured_in_trusted"],
        "Landslide_Capture_Rate_pct"        : capture["capture_rate_pct"],
        "Spearman_r_Mahal_vs_Disagree"      : r_val,
        "Trusted_Coverage_pct_thresh_0.4"   : round(np.nansum((domain_arr >= 0.4) & valid_mask) / total_valid * 100, 2),
        "Trusted_Coverage_pct_thresh_0.5"   : trusted_pct,
        "Trusted_Coverage_pct_thresh_0.6"   : round(np.nansum((domain_arr >= 0.6) & valid_mask) / total_valid * 100, 2),
    })

# ─────────────────────────────────────────────
# 4. SAVE OUTPUT CSV
# ─────────────────────────────────────────────

df = pd.DataFrame(summary_rows)

output_path = r"D:\Research Landslide\Applicability Domain\AD_validation_results.csv"
df.to_csv(output_path, index=False)

print("\n" + "=" * 65)
print("  SUMMARY TABLE")
print("=" * 65)
print(df.T.to_string())
print(f"\nResults saved to: {output_path}")
print("Done.")
