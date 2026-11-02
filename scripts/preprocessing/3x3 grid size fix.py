import grass.script as gs
import sys
import os

os.environ["PYTHONUTF8"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# -----------------------------
# CONFIGURATION
# Change these if needed
# -----------------------------
REFERENCE_MAP = "aspect_3x3@PERMANENT"   # map whose region/cells you want to match
INPUT_NDVI    = "absolute_min_ndvi_10m@PERMANENT"
INPUT_NDWI    = "absolute_max_ndwi_10m@PERMANENT"
OUTPUT_NDVI   = "ndvi_3x3"               # will overwrite existing
OUTPUT_NDWI   = "ndwi_3x3"              # will overwrite existing

def match_and_resample():
    print("=" * 55)
    print("Resampling NDVI and NDWI to match reference map region")
    print("=" * 55)

    # Step 1: Verify reference map exists
    ref_name = REFERENCE_MAP.split("@")[0]
    found = gs.find_file(name=ref_name, element="cell", mapset="PERMANENT")
    if not found["name"]:
        print(f"ERROR: Reference map '{REFERENCE_MAP}' not found.")
        return

    # Step 2: Set region EXACTLY to reference map
    # This ensures identical extent, resolution and cell count
    print(f"\nStep 1: Setting region to match '{REFERENCE_MAP}'...")
    gs.run_command("g.region", raster=REFERENCE_MAP, flags="p")

    region = gs.region()
    print(f"  nsres : {region['nsres']}m")
    print(f"  ewres : {region['ewres']}m")
    print(f"  rows  : {region['rows']}")
    print(f"  cols  : {region['cols']}")
    print(f"  cells : {region['rows'] * region['cols']}")

    # Step 3: Resample NDVI to this exact region
    print(f"\nStep 2: Resampling NDVI to match region...")
    try:
        gs.run_command(
            "r.resamp.interp",
            overwrite=True,
            input=INPUT_NDVI,
            output=OUTPUT_NDVI,
            method="bilinear",
        )
        print(f"  Created: {OUTPUT_NDVI}")
    except Exception as e:
        print(f"  ERROR resampling NDVI: {e}")
        return

    # Step 4: Resample NDWI to this exact region
    print(f"\nStep 3: Resampling NDWI to match region...")
    try:
        gs.run_command(
            "r.resamp.interp",
            overwrite=True,
            input=INPUT_NDWI,
            output=OUTPUT_NDWI,
            method="bilinear",
        )
        print(f"  Created: {OUTPUT_NDWI}")
    except Exception as e:
        print(f"  ERROR resampling NDWI: {e}")
        return

    # Step 5: Fix colors and compute stats for both outputs
    for map_name, color_table in [(OUTPUT_NDVI, "ndvi"), (OUTPUT_NDWI, "ndwi")]:
        print(f"\nStep 4: Fixing colors and stats for {map_name}...")
        gs.run_command("r.support", map=map_name, flags="s")
        gs.run_command("r.colors", map=map_name, color=color_table)

        info   = gs.parse_command("r.info",   map=map_name, flags="g")
        univar = gs.parse_command("r.univar", map=map_name, flags="g")
        print(f"  nsres      : {info.get('nsres')}m")
        print(f"  ewres      : {info.get('ewres')}m")
        print(f"  Rows x Cols: {info.get('rows')} x {info.get('cols')}")
        print(f"  Cells      : {int(info.get('rows', 0)) * int(info.get('cols', 0))}")
        print(f"  Min        : {univar.get('min')}")
        print(f"  Max        : {univar.get('max')}")
        print(f"  Mean       : {univar.get('mean')}")
        print(f"  StDev      : {univar.get('stddev')}")

    # Step 6: Verify cell count matches reference
    print("\n" + "=" * 55)
    print("VERIFICATION")
    print("=" * 55)
    ref_info  = gs.parse_command("r.info", map=REFERENCE_MAP, flags="g")
    ndvi_info = gs.parse_command("r.info", map=OUTPUT_NDVI,   flags="g")
    ndwi_info = gs.parse_command("r.info", map=OUTPUT_NDWI,   flags="g")

    ref_cells  = int(ref_info.get("rows",  0)) * int(ref_info.get("cols",  0))
    ndvi_cells = int(ndvi_info.get("rows", 0)) * int(ndvi_info.get("cols", 0))
    ndwi_cells = int(ndwi_info.get("rows", 0)) * int(ndwi_info.get("cols", 0))

    print(f"  {REFERENCE_MAP} cells : {ref_cells}")
    print(f"  {OUTPUT_NDVI} cells   : {ndvi_cells} {'OK' if ndvi_cells == ref_cells else 'MISMATCH'}")
    print(f"  {OUTPUT_NDWI} cells   : {ndwi_cells} {'OK' if ndwi_cells == ref_cells else 'MISMATCH'}")

    print("\nDone! Refresh display in GRASS to see updated maps.")

if __name__ == "__main__":
    match_and_resample()
