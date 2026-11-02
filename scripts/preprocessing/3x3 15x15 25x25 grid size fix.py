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
# -----------------------------
GRID_CONFIG = {
    "3x3"  : {
        "res"        : 3,
        "reference"  : "slope_3x3",   # master reference map -- all others forced to match this
        "maps"       : [
            "aspect_3x3",
            "curvature_3x3",
            "dem_3m",
            "dis_to_fault_3x3",
            "dis_to_river_3x3",
            "dis_to_road_3x3",
            "dis_to_thrust_3x3",
            "ndvi_3x3",
            "ndwi_3x3",
            "roughness_3x3",
            "slope_3x3",
            "twi_3x3",
        ],
        "colors": {
            "aspect_3x3"       : "aspectcolr",
            "curvature_3x3"    : "differences",
            "dem_3m"           : "elevation",
            "dis_to_fault_3x3" : "blues",
            "dis_to_river_3x3" : "blues",
            "dis_to_road_3x3"  : "blues",
            "dis_to_thrust_3x3": "blues",
            "ndvi_3x3"         : "ndvi",
            "ndwi_3x3"         : "ndwi",
            "roughness_3x3"    : "differences",
            "slope_3x3"        : "slope",
            "twi_3x3"          : "water",
        },
    },
    "15x15": {
        "res"        : 15,
        "reference"  : "slope_15x15",  # master reference map -- all others forced to match this
        "maps"       : [
            "aspect_15x15",
            "curvature_15x15",
            "dem_filled_15m",
            "dis_to_fault_15x15",
            "dis_to_river_15x15",
            "dis_to_road_15x15",
            "dis_to_thrust_15x15",
            "ndvi_15x15",
            "ndwi_15x15",
            "roughness_15x15",
            "slope_15x15",
            "twi_15x15",
        ],
        "colors": {
            "aspect_15x15"       : "aspectcolr",
            "curvature_15x15"    : "differences",
            "dem_filled_15m"     : "elevation",
            "dis_to_fault_15x15" : "blues",
            "dis_to_river_15x15" : "blues",
            "dis_to_road_15x15"  : "blues",
            "dis_to_thrust_15x15": "blues",
            "ndvi_15x15"         : "ndvi",
            "ndwi_15x15"         : "ndwi",
            "roughness_15x15"    : "differences",
            "slope_15x15"        : "slope",
            "twi_15x15"          : "water",
        },
    },
    "25x25": {
        "res"        : 25,
        "reference"  : "slope_25x25",  # master reference map -- all others forced to match this
        "maps"       : [
            "aspect_25x25",
            "curvature_25x25",
            "dis_to_fault_25x25",
            "dis_to_river_25x25",
            "dis_to_road_25x25",
            "dis_to_thrust_25x25",
            "ndvi_25x25",
            "ndwi_25x25",
            "roughness_25x25",
            "slope_25x25",
            "twi_25x25",
        ],
        "colors": {
            "aspect_25x25"       : "aspectcolr",
            "curvature_25x25"    : "differences",
            "dis_to_fault_25x25" : "blues",
            "dis_to_river_25x25" : "blues",
            "dis_to_road_25x25"  : "blues",
            "dis_to_thrust_25x25": "blues",
            "ndvi_25x25"         : "ndvi",
            "ndwi_25x25"         : "ndwi",
            "roughness_25x25"    : "differences",
            "slope_25x25"        : "slope",
            "twi_25x25"          : "water",
        },
    },
}

# -----------------------------
# DETECT ACTIVE GRID FROM PATH
# -----------------------------
def detect_grid():
    env                  = gs.gisenv()
    current_mapset       = env.get("MAPSET", "")
    current_location     = env.get("LOCATION_NAME", "")
    current_gisdbase     = env.get("GISDBASE", "")
    full_path            = os.path.join(current_gisdbase, current_location)
    full_path_normalized = full_path.replace("\\", "/")

    print(f"Active mapset   : {current_mapset}")
    print(f"Active location : {current_location}")
    print(f"Full path       : {full_path}")

    for keyword in GRID_CONFIG:
        if keyword in full_path_normalized:
            res = GRID_CONFIG[keyword]["res"]
            print(f"Detected grid   : {keyword} -- target resolution: {res}m")
            return keyword

    print(f"ERROR: Could not detect grid size from path.")
    print(f"Full path was          : '{full_path}'")
    print(f"Expected path to contain one of: {list(GRID_CONFIG.keys())}")
    return None

# -----------------------------
# STEP 1: SET REGION FROM REFERENCE MAP
# This is the key fix -- ALL maps will be forced
# to exactly match this reference region
# -----------------------------
def set_reference_region(reference_map, target_res):
    print("\n" + "=" * 60)
    print("STEP 1: SETTING REFERENCE REGION FROM MASTER MAP")
    print("=" * 60)

    found = gs.find_file(name=reference_map, element="cell")
    if not found["name"]:
        print(f"ERROR: Reference map '{reference_map}' not found.")
        return False

    # Get reference map info
    info = gs.parse_command("r.info", map=reference_map, flags="g")
    print(f"  Reference map   : {reference_map}")
    print(f"  Reference res   : {info.get('nsres')}m x {info.get('ewres')}m")
    print(f"  Reference extent:")
    print(f"    North : {info.get('north')}")
    print(f"    South : {info.get('south')}")
    print(f"    East  : {info.get('east')}")
    print(f"    West  : {info.get('west')}")

    # Set region to EXACTLY match reference map extent and resolution
    # Do NOT use flag 'a' here -- we want exact copy of reference region
    gs.run_command(
        "g.region",
        raster=reference_map,
        flags="p",
    )

    region = gs.region()
    ref_rows  = region["rows"]
    ref_cols  = region["cols"]
    ref_cells = ref_rows * ref_cols

    print(f"\n  Region locked to reference:")
    print(f"    Resolution  : {region['nsres']}m x {region['ewres']}m")
    print(f"    Rows x Cols : {ref_rows} x {ref_cols}")
    print(f"    Total cells : {ref_cells}")
    print(f"\n  ALL maps will be forced to: {ref_rows} rows x {ref_cols} cols = {ref_cells} cells")

    return region

# -----------------------------
# STEP 2: CHECK CURRENT STATE OF ALL MAPS
# -----------------------------
def check_all_maps(maps, ref_rows, ref_cols):
    print("\n" + "=" * 60)
    print("STEP 2: CHECKING CURRENT STATE OF ALL MAPS")
    print("=" * 60)

    matches    = []
    mismatches = []
    not_found  = []

    for map_name in maps:
        found = gs.find_file(name=map_name, element="cell")
        if not found["name"]:
            print(f"  NOT FOUND  : {map_name}")
            not_found.append(map_name)
            continue

        info  = gs.parse_command("r.info", map=map_name, flags="g")
        nsres = float(info.get("nsres", 0))
        ewres = float(info.get("ewres", 0))
        rows  = int(info.get("rows",   0))
        cols  = int(info.get("cols",   0))
        cells = rows * cols

        is_match = (rows == ref_rows and cols == ref_cols)
        status   = "MATCHES" if is_match else "MISMATCH"

        print(f"  {status:10s} : {map_name}")
        print(f"    Resolution : {nsres}m x {ewres}m")
        print(f"    Rows x Cols: {rows} x {cols} = {cells} cells")

        if is_match:
            matches.append(map_name)
        else:
            mismatches.append(map_name)

    print(f"\n  Matches    : {len(matches)}  -- {matches}")
    print(f"  Mismatches : {len(mismatches)} -- {mismatches}")
    print(f"  Not found  : {len(not_found)} -- {not_found}")

    return matches, mismatches, not_found

# -----------------------------
# STEP 3: FORCE RESAMPLE ALL MAPS TO REFERENCE REGION
# Runs on ALL maps -- even those already matching
# This guarantees identical rows, cols, extent
# -----------------------------
def force_resample_all(maps, not_found, color_tables, ref_rows, ref_cols):
    print("\n" + "=" * 60)
    print("STEP 3: FORCE RESAMPLING ALL MAPS TO REFERENCE REGION")
    print("=" * 60)

    success = []
    failed  = []

    for map_name in maps:
        if map_name in not_found:
            continue

        print(f"\n  --- Force resampling: {map_name} ---")
        try:
            # Region is already locked to reference -- just resample into it
            gs.run_command(
                "r.resamp.interp",
                overwrite=True,
                input=map_name,
                output=map_name,
                method="bilinear",
            )

            # Update statistics
            gs.run_command("r.support", map=map_name, flags="s")
            univar = gs.parse_command("r.univar", map=map_name, flags="g")
            print(f"    Min  : {univar.get('min')}")
            print(f"    Max  : {univar.get('max')}")
            print(f"    Mean : {univar.get('mean')}")
            print(f"    StDev: {univar.get('stddev')}")

            # Apply color table
            color = color_tables.get(map_name, "grey")
            gs.run_command("r.colors", map=map_name, color=color)
            print(f"    Color table : {color}")

            # Verify
            info_new  = gs.parse_command("r.info", map=map_name, flags="g")
            new_rows  = int(info_new.get("rows", 0))
            new_cols  = int(info_new.get("cols", 0))
            new_cells = new_rows * new_cols
            cell_match = "MATCH" if (new_rows == ref_rows and new_cols == ref_cols) else "STILL DIFFERENT"
            print(f"    Resolution  : {info_new.get('nsres')}m x {info_new.get('ewres')}m")
            print(f"    Rows x Cols : {new_rows} x {new_cols} = {new_cells} cells -- {cell_match}")
            success.append(map_name)

        except gs.ScriptError as e:
            print(f"    GRASS Error: {e}")
            failed.append(map_name)
        except Exception as e:
            print(f"    Unexpected Error: {e}")
            failed.append(map_name)

    return success, failed

# -----------------------------
# STEP 4: FINAL VERIFICATION
# -----------------------------
def final_verification(maps, not_found, ref_rows, ref_cols):
    print("\n" + "=" * 60)
    print("STEP 4: FINAL VERIFICATION")
    print("=" * 60)

    all_cells  = []
    all_match  = True

    for map_name in maps:
        if map_name in not_found:
            print(f"  NOT FOUND  : {map_name}")
            continue

        info  = gs.parse_command("r.info", map=map_name, flags="g")
        nsres = float(info.get("nsres", 0))
        ewres = float(info.get("ewres", 0))
        rows  = int(info.get("rows",   0))
        cols  = int(info.get("cols",   0))
        cells = rows * cols
        all_cells.append(cells)

        is_match = (rows == ref_rows and cols == ref_cols)
        status   = "OK" if is_match else "STILL DIFFERENT"
        if not is_match:
            all_match = False

        print(f"  {status:16s} : {map_name}")
        print(f"    Resolution : {nsres}m x {ewres}m")
        print(f"    Rows x Cols: {rows} x {cols} = {cells} cells")

    print("\n" + "-" * 60)
    unique_cells = set(all_cells)
    if len(unique_cells) == 1:
        print(f"  All maps identical : {ref_rows} rows x {ref_cols} cols = {all_cells[0]} cells")
        print(f"  READY for susceptibility map analysis.")
    else:
        print(f"  WARNING -- Cell counts still differ: {unique_cells}")
        print(f"  Check failed maps above.")

# -----------------------------
# MAIN
# -----------------------------
def main():
    print("=" * 60)
    print("FORCE GRID STANDARDIZER -- All Rasters to Identical Size")
    print("=" * 60)

    # Detect active grid location
    grid_label = detect_grid()
    if grid_label is None:
        print("\nAborting -- switch to correct location in GRASS and rerun.")
        print("Expected folder structure:")
        print("  ...\\Grid units raster files\\3x3\\newProject\\PERMANENT")
        print("  ...\\Grid units raster files\\15x15\\newProject\\PERMANENT")
        print("  ...\\Grid units raster files\\25x25\\newProject\\PERMANENT")
        return

    config        = GRID_CONFIG[grid_label]
    target_res    = config["res"]
    reference_map = config["reference"]
    maps          = config["maps"]
    color_tables  = config["colors"]

    print(f"\nGrid label      : {grid_label}")
    print(f"Target res      : {target_res}m x {target_res}m")
    print(f"Reference map   : {reference_map}")
    print(f"Maps to process : {len(maps)}")

    # Step 1: Lock region to reference map
    region = set_reference_region(reference_map, target_res)
    if not region:
        print("Aborting -- reference map not found.")
        return

    ref_rows  = region["rows"]
    ref_cols  = region["cols"]

    # Step 2: Check current state
    matches, mismatches, not_found = check_all_maps(maps, ref_rows, ref_cols)

    # Step 3: Force resample ALL maps (skip not_found only)
    success, failed = force_resample_all(maps, not_found, color_tables, ref_rows, ref_cols)

    # Step 4: Final verification
    final_verification(maps, not_found, ref_rows, ref_cols)

    # Summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"  Grid          : {grid_label} ({target_res}m)")
    print(f"  Reference     : {reference_map} ({ref_rows} x {ref_cols})")
    print(f"  Processed     : {len(success)} maps")
    print(f"  Failed        : {len(failed)} maps -- {failed}")
    print(f"  Not found     : {len(not_found)} maps -- {not_found}")
    print("\nDone! Uncheck and recheck layers in GRASS to refresh display.")

if __name__ == "__main__":
    main()
