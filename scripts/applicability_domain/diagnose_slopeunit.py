"""
Diagnostic Script — Slope Unit Raster Inspection
Run this BEFORE the main analysis.
It checks raster properties, value ranges, and data types.
"""

import rasterio
import numpy as np

BASE = r"D:\Research Landslide\Applicability Domain Slopeunit"

# Check one file per type, plus all three resolutions of Trusted_mask
FILES_TO_CHECK = {
    "Trusted_mask_3x3"             : f"{BASE}\\Trusted_mask_3x3.tif",
    "Trusted_mask_15x15"           : f"{BASE}\\Trusted_mask_15x15.tif",
    "Trusted_mask_25x25"           : f"{BASE}\\Trusted_mask_25x25.tif",
    "Mahalanobis_distance_15x15"   : f"{BASE}\\Mahalanobis_distance_15x15.tif",
    "Model_disagreement_std_15x15" : f"{BASE}\\Model_disagreement_std_15x15.tif",
    "Domain_score_15x15"           : f"{BASE}\\Domain_score_15x15.tif",
    "Ensemble_susceptibility_15x15": f"{BASE}\\Ensemble_susceptibility_15x15.tif",
}

print("=" * 65)
print("  SLOPE UNIT RASTER DIAGNOSTIC")
print("=" * 65)

for name, path in FILES_TO_CHECK.items():
    print(f"\n--- {name} ---")
    try:
        with rasterio.open(path) as src:
            data     = src.read(1).astype(np.float32)
            nodata   = src.nodata
            dtype    = src.dtypes[0]
            crs      = src.crs
            shape    = src.shape
            res      = src.res

            # mask nodata
            if nodata is not None:
                data[data == nodata] = np.nan

            valid    = data[~np.isnan(data)]
            unique_vals = np.unique(valid)

            print(f"  Shape (rows x cols) : {shape}")
            print(f"  Pixel resolution    : {res}")
            print(f"  Data type           : {dtype}")
            print(f"  NoData value        : {nodata}")
            print(f"  CRS                 : {crs}")
            print(f"  Valid pixel count   : {len(valid):,}")
            print(f"  Min value           : {np.nanmin(data):.6f}")
            print(f"  Max value           : {np.nanmax(data):.6f}")
            print(f"  Mean value          : {np.nanmean(data):.6f}")
            print(f"  Unique value count  : {len(unique_vals)}")

            # if few unique values, print them all (likely categorical)
            if len(unique_vals) <= 20:
                print(f"  Unique values       : {unique_vals}")
            else:
                print(f"  Sample unique vals  : {unique_vals[:10]} ... (continuous)")

    except Exception as e:
        print(f"  ERROR reading file: {e}")

print("\n" + "=" * 65)
print("  DIAGNOSTIC COMPLETE")
print("=" * 65)
