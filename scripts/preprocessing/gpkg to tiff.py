import os
import re
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.transform import from_origin
from rasterio.features import rasterize

# =============================================================
# CONFIGURATION
# =============================================================
GPKG_FOLDER   = r"D:\Research Landslide\Result\Slopeunits\Excel_file_SU\gpkg"
OUTPUT_FOLDER = os.path.join(GPKG_FOLDER, "tif_output")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# =============================================================
# HELPER: Parse pixel size from filename
# e.g. "su_a300000_c0_35_3x3.gpkg"   → 3.0
#      "su_a300000_c0_35_15x15.gpkg" → 15.0
#      "su_a300000_c0_35_25x25.gpkg" → 25.0
# =============================================================
def get_pixel_size(filename):
    match = re.search(r"_(\d+)x\1", filename)
    if match:
        return float(match.group(1))
    return None

# =============================================================
# FIND ALL .gpkg FILES
# =============================================================
gpkg_files = sorted([f for f in os.listdir(GPKG_FOLDER) if f.endswith(".gpkg")])

if not gpkg_files:
    raise FileNotFoundError(f"No .gpkg files found in {GPKG_FOLDER}")

print(f"Found {len(gpkg_files)} .gpkg files:")
for f in gpkg_files:
    ps = get_pixel_size(f)
    print(f"  - {f}  →  pixel size: {ps}m")
print("=" * 60)

# =============================================================
# CONVERT EACH .gpkg TO .tif
# =============================================================
for fname in gpkg_files:
    fpath    = os.path.join(GPKG_FOLDER, fname)
    out_name = os.path.splitext(fname)[0] + ".tif"
    outfile  = os.path.join(OUTPUT_FOLDER, out_name)

    print(f"\nProcessing: {fname}")

    # --- Get pixel size from filename ---
    pixel_size = get_pixel_size(fname)
    if pixel_size is None:
        print(f"  ✗ Could not parse pixel size from filename: {fname}")
        print(f"    Expected pattern like '_3x3', '_15x15', '_25x25' in filename.")
        continue

    print(f"  Pixel size : {pixel_size}m  (parsed from filename)")

    try:
        # --- Load vector polygons ---
        gdf = gpd.read_file(fpath)
        print(f"  Polygons   : {len(gdf)}")
        print(f"  CRS        : {gdf.crs}")

        # --- Reproject to projected CRS if geographic (degrees → meters) ---
        if gdf.crs and gdf.crs.is_geographic:
            target_crs = gdf.estimate_utm_crs()
            gdf = gdf.to_crs(target_crs)
            print(f"  Reprojected: {target_crs}")

        # --- Compute raster dimensions ---
        minx, miny, maxx, maxy = gdf.total_bounds
        cols = int(np.ceil((maxx - minx) / pixel_size))
        rows = int(np.ceil((maxy - miny) / pixel_size))
        print(f"  Grid size  : {cols} cols x {rows} rows")

        # --- Assign unique integer ID to each polygon ---
        gdf = gdf.copy().reset_index(drop=True)
        gdf["burn_id"] = range(1, len(gdf) + 1)

        # --- Create (geometry, value) pairs for rasterization ---
        shapes = (
            (geom, int(burn_id))
            for geom, burn_id in zip(gdf.geometry, gdf["burn_id"])
        )

        # --- Define affine transform (top-left origin) ---
        transform = from_origin(minx, maxy, pixel_size, pixel_size)

        # --- Rasterize ---
        print(f"  Rasterizing...")
        raster = rasterize(
            shapes=shapes,
            out_shape=(rows, cols),
            transform=transform,
            fill=0,           # NoData value
            dtype="int32"
        )

        # --- Write GeoTIFF ---
        with rasterio.open(
            outfile,
            "w",
            driver="GTiff",
            height=rows,
            width=cols,
            count=1,
            dtype="int32",
            crs=gdf.crs,
            transform=transform,
            nodata=0,
            compress="lzw"
        ) as dst:
            dst.write(raster, 1)

        size_mb = os.path.getsize(outfile) / (1024 * 1024)
        print(f"  ✓ Saved    : {out_name}  ({size_mb:.1f} MB)")

    except Exception as e:
        print(f"  ✗ FAILED: {fname} → {e}")
        continue

# =============================================================
# SUMMARY
# =============================================================
print("\n" + "=" * 60)
print("Summary:")
for fname in gpkg_files:
    out_name = os.path.splitext(fname)[0] + ".tif"
    outfile  = os.path.join(OUTPUT_FOLDER, out_name)
    ps       = get_pixel_size(fname)
    if os.path.exists(outfile):
        size_mb = os.path.getsize(outfile) / (1024 * 1024)
        print(f"  ✓ {out_name}  |  {ps}m resolution  |  {size_mb:.1f} MB")
    else:
        print(f"  ✗ {out_name}  — not created")

print(f"\nOutput folder:\n  {OUTPUT_FOLDER}")
print("=" * 60)