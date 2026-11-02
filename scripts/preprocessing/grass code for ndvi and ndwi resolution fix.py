import grass.script as gs
import sys
import os

# -----------------------------
# 1. ENCODING FIX
# -----------------------------
os.environ["PYTHONUTF8"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# -----------------------------
# 2. CONFIGURATION
# -----------------------------
INPUT_NDVI = "absolute_min_ndvi_10m@PERMANENT"
INPUT_NDWI = "absolute_max_ndwi_10m@PERMANENT"

GRID_CONFIG = {
    "3x3"  : 3,
    "15x15": 15,
    "25x25": 25,
}

# -----------------------------
# 3. DETECT GRID SIZE FROM FULL PATH
# -----------------------------
def detect_grid_size():
    env              = gs.gisenv()
    current_mapset   = env.get("MAPSET", "")
    current_location = env.get("LOCATION_NAME", "")
    current_gisdbase = env.get("GISDBASE", "")

    full_path            = os.path.join(current_gisdbase, current_location)
    full_path_normalized = full_path.replace("\\", "/")

    print(f"Active mapset   : {current_mapset}")
    print(f"Active location : {current_location}")
    print(f"Full path       : {full_path}")

    for keyword, resolution in GRID_CONFIG.items():
        if keyword in full_path_normalized:
            print(f"Detected grid size : {keyword} -- target resolution: {resolution}m")
            return keyword, resolution

    print(f"ERROR: Could not detect grid size from path.")
    print(f"Full path was          : '{full_path}'")
    print(f"Expected path to contain one of: {list(GRID_CONFIG.keys())}")
    return None, None

# -----------------------------
# 4. RESAMPLE ONE MAP
# -----------------------------
def resample_map(input_map, output_map, target_res, mapset):
    print(f"\n--- Processing: {input_map} --> {output_map} ---")

    # Check input exists in PERMANENT
    map_name = input_map.split("@")[0]
    found    = gs.find_file(name=map_name, element="cell", mapset="PERMANENT")
    if not found["name"]:
        print(f"ERROR: Input map '{input_map}' not found in PERMANENT. Skipping.")
        return False

    # Step 1: Compute input statistics
    print("Step 1: Computing input map statistics...")
    gs.run_command("r.support", map=input_map, flags="s")

    info = gs.parse_command("r.info", map=input_map, flags="g")
    print(f"  Input resolution : {info.get('nsres')}m x {info.get('ewres')}m")
    print(f"  Input dimensions : {info.get('rows')} rows x {info.get('cols')} cols")

    univar_in = gs.parse_command("r.univar", map=input_map, flags="g")
    print(f"  Min  : {univar_in.get('min')}")
    print(f"  Max  : {univar_in.get('max')}")
    print(f"  Mean : {univar_in.get('mean')}")
    print(f"  StDev: {univar_in.get('stddev')}")

    # Step 2: Set region aligned to input extent at target resolution
    print(f"Step 2: Setting region to {target_res}m aligned to input extent...")
    gs.run_command(
        "g.region",
        n=info.get("north"),
        s=info.get("south"),
        e=info.get("east"),
        w=info.get("west"),
        res=target_res,
        flags="ap",
    )

    region = gs.region()
    print(f"  New region res  : {region['nsres']}m x {region['ewres']}m")
    print(f"  New region size : {region['rows']} rows x {region['cols']} cols")

    # Step 3: Resample using bilinear interpolation
    print(f"Step 3: Resampling to {target_res}m using bilinear interpolation...")
    try:
        gs.run_command(
            "r.resamp.interp",
            overwrite=True,
            input=input_map,
            output=output_map,
            method="bilinear",
        )
        print(f"  Output map created: {output_map}@{mapset}")
        return True

    except gs.ScriptError as e:
        print(f"GRASS Error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return False

# -----------------------------
# 5. FIX COLOR TABLE FOR ONE MAP
# -----------------------------
def fix_colors(map_name, color_table):
    print(f"\n--- Fixing colors: {map_name} ---")

    found = gs.find_file(name=map_name, element="cell")
    if not found["name"]:
        print(f"  Skipping -- map not found.")
        return

    # Compute full statistics
    print(f"  Computing statistics...")
    gs.run_command("r.support", map=map_name, flags="s")
    univar = gs.parse_command("r.univar", map=map_name, flags="g")
    print(f"  Min  : {univar.get('min')}")
    print(f"  Max  : {univar.get('max')}")
    print(f"  Mean : {univar.get('mean')}")
    print(f"  StDev: {univar.get('stddev')}")

    # Assign color table
    print(f"  Assigning '{color_table}' color table...")
    gs.run_command(
        "r.colors",
        map=map_name,
        color=color_table,
    )

    # Verify
    info = gs.parse_command("r.info", map=map_name, flags="g")
    print(f"  Verified Min : {info.get('min')}")
    print(f"  Verified Max : {info.get('max')}")
    print(f"  Colors fixed : {map_name}")

# -----------------------------
# 6. MAIN
# -----------------------------
def main():
    print("=" * 55)
    print("NDVI and NDWI Resampler -- Auto Grid Detection")
    print("=" * 55)

    # Detect grid size from active location path
    grid_label, target_res = detect_grid_size()
    if grid_label is None:
        print("\nAborting: Could not determine grid size.")
        print("Make sure you have switched to the correct location in GRASS.")
        print("Expected folder structure:")
        print("  ...\\Grid units raster files\\3x3\\newProject\\PERMANENT")
        print("  ...\\Grid units raster files\\15x15\\newProject\\PERMANENT")
        print("  ...\\Grid units raster files\\25x25\\newProject\\PERMANENT")
        return

    current_mapset = gs.gisenv()["MAPSET"]
    output_ndvi    = f"ndvi_{grid_label}"    # e.g. ndvi_3x3, ndvi_25x25
    output_ndwi    = f"ndwi_{grid_label}"    # e.g. ndwi_3x3, ndwi_25x25

    print(f"\nTarget resolution   : {target_res}m")
    print(f"Output mapset       : {current_mapset}")
    print(f"NDVI output map     : {output_ndvi}@{current_mapset}")
    print(f"NDWI output map     : {output_ndwi}@{current_mapset}")

    # Process NDVI
    print("\n" + "=" * 55)
    print("PROCESSING NDVI")
    print("=" * 55)
    ndvi_success = resample_map(INPUT_NDVI, output_ndvi, target_res, current_mapset)

    # Fix NDVI colors immediately after resampling
    if ndvi_success:
        fix_colors(output_ndvi, "ndvi")

    # Process NDWI
    print("\n" + "=" * 55)
    print("PROCESSING NDWI")
    print("=" * 55)
    ndwi_success = resample_map(INPUT_NDWI, output_ndwi, target_res, current_mapset)

    # Fix NDWI colors immediately after resampling
    if ndwi_success:
        fix_colors(output_ndwi, "ndwi")

    # Also fix source maps in PERMANENT in case they display flat too
    print("\n" + "=" * 55)
    print("FIXING SOURCE MAP COLORS IN PERMANENT")
    print("=" * 55)
    fix_colors("absolute_min_ndvi_10m", "ndvi")
    fix_colors("absolute_max_ndwi_10m", "ndwi")

    # Reset region to output NDWI if successful, else NDVI
    print("\n" + "=" * 55)
    print("FINALIZING REGION")
    print("=" * 55)
    if ndwi_success:
        gs.run_command("g.region", raster=output_ndwi, flags="p")
        print(f"Region reset to: {output_ndwi}@{current_mapset}")
    elif ndvi_success:
        gs.run_command("g.region", raster=output_ndvi, flags="p")
        print(f"Region reset to: {output_ndvi}@{current_mapset}")

    # Final summary
    print("\n" + "=" * 55)
    print("SUMMARY")
    print("=" * 55)
    print(f"  Grid size   : {grid_label} ({target_res}m resolution)")
    print(f"  NDVI output : {'SUCCESS -- ' + output_ndvi + '@' + current_mapset if ndvi_success else 'FAILED'}")
    print(f"  NDWI output : {'SUCCESS -- ' + output_ndwi + '@' + current_mapset if ndwi_success else 'FAILED'}")
    print("\nDone! Uncheck and recheck layers in GRASS to refresh display.")

if __name__ == "__main__":
    main()