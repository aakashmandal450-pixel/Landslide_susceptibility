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

# Base output directory
BASE_OUTPUT_DIR = r"D:\Research Landslide\Data\Raster files"

# All grid configurations
GRID_CONFIG = {
    "3x3": {
        "gisdbase" : r"D:\Research Landslide\Grass\Grid units raster files\3x3",
        "location" : "newProject",
        "mapset"   : "PERMANENT",
        "folder"   : "3x3_rasters",
        "maps"     : [
            "aspect_3x3",
            "curvature_3x3",
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
    },
    "15x15": {
        "gisdbase" : r"D:\Research Landslide\Grass\Grid units raster files\15x15",
        "location" : "newProject",
        "mapset"   : "PERMANENT",
        "folder"   : "15x15_rasters",
        "maps"     : [
            "aspect_15x15",
            "curvature_15x15",
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
    },
    "25x25": {
        "gisdbase" : r"D:\Research Landslide\Grass\Grid units raster files\25x25",
        "location" : "newProject",
        "mapset"   : "PERMANENT",
        "folder"   : "25x25_rasters",
        "maps"     : [
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
            print(f"Detected grid   : {keyword}")
            return keyword

    print(f"ERROR: Could not detect grid from path: '{full_path}'")
    print(f"Expected path to contain one of: {list(GRID_CONFIG.keys())}")
    return None

# -----------------------------
# EXPORT ONE MAP TO TIFF
# -----------------------------
def export_map(map_name, output_path):
    print(f"\n  --- Exporting: {map_name} ---")
    print(f"      Output     : {output_path}")

    # Check map exists
    found = gs.find_file(name=map_name, element="cell")
    if not found["name"]:
        print(f"      ERROR: Map '{map_name}' not found. Skipping.")
        return "skipped"

    # Set region to match this map exactly before export
    gs.run_command("g.region", raster=map_name)

    # Auto-detect map data type to avoid any precision loss
    info      = gs.parse_command("r.info", map=map_name, flags="g")
    data_type = info.get("datatype", "FCELL")
    rows      = info.get("rows")
    cols      = info.get("cols")
    nsres     = info.get("nsres")
    ewres     = info.get("ewres")

    print(f"      GRASS type : {data_type}")
    print(f"      Resolution : {nsres}m x {ewres}m")
    print(f"      Dimensions : {rows} rows x {cols} cols")

    # Map GRASS data types to GDAL output types
    # CELL  = integer   -> Int32
    # FCELL = float32   -> Float32
    # DCELL = float64   -> Float64 (TWI and other high precision maps)
    type_map = {
        "CELL" : "Int32",
        "FCELL": "Float32",
        "DCELL": "Float64",
    }
    gdal_type = type_map.get(data_type, "Float64")
    print(f"      GDAL type  : {gdal_type}")

    try:
        gs.run_command(
            "r.out.gdal",
            overwrite=True,
            input=map_name,
            output=output_path,
            format="GTiff",
            type=gdal_type,
            createopt="COMPRESS=LZW,TILED=YES,BIGTIFF=YES",
        )

        # Verify file created and report size
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"      Size       : {size_mb:.2f} MB")
            print(f"      Status     : SUCCESS")
            return "success"
        else:
            print(f"      ERROR: File not created at expected path.")
            return "failed"

    except gs.ScriptError as e:
        print(f"      GRASS Error: {e}")
        return "failed"
    except Exception as e:
        print(f"      Unexpected Error: {e}")
        return "failed"

# -----------------------------
# EXPORT ALL MAPS FOR ONE GRID
# -----------------------------
def export_grid(grid_label):
    config    = GRID_CONFIG[grid_label]
    maps      = config["maps"]
    folder    = config["folder"]

    # Create output folder
    output_dir = os.path.join(BASE_OUTPUT_DIR, folder)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n  Output folder   : {output_dir}")
    print(f"  Maps to export  : {len(maps)}")

    success = []
    failed  = []
    skipped = []

    for map_name in maps:
        output_path = os.path.join(output_dir, f"{map_name}.tif")
        result      = export_map(map_name, output_path)

        if result == "success":
            success.append(map_name)
        elif result == "failed":
            failed.append(map_name)
        elif result == "skipped":
            skipped.append(map_name)

    return success, failed, skipped, output_dir

# -----------------------------
# MAIN
# -----------------------------
def main():
    print("=" * 60)
    print("GRASS RASTER EXPORTER -- Auto Grid Detection")
    print("=" * 60)
    print(f"Base output dir : {BASE_OUTPUT_DIR}")
    print(f"Excluded maps   : dem_3m, dem_filled_15m")

    # Detect active grid location
    grid_label = detect_grid()
    if grid_label is None:
        print("\nAborting -- switch to the correct location in GRASS and rerun.")
        print("Expected folder structure:")
        print("  ...\\Grid units raster files\\3x3\\newProject\\PERMANENT")
        print("  ...\\Grid units raster files\\15x15\\newProject\\PERMANENT")
        print("  ...\\Grid units raster files\\25x25\\newProject\\PERMANENT")
        return

    print(f"\nExporting grid  : {grid_label}")

    print("\n" + "=" * 60)
    print(f"EXPORTING {grid_label} RASTERS")
    print("=" * 60)

    success, failed, skipped, output_dir = export_grid(grid_label)

    # Final summary
    print("\n" + "=" * 60)
    print("EXPORT SUMMARY")
    print("=" * 60)
    print(f"  Grid          : {grid_label}")
    print(f"  Output folder : {output_dir}")

    print(f"\n  Exported successfully : {len(success)} maps")
    for m in success:
        tif_path = os.path.join(output_dir, f"{m}.tif")
        size_mb  = os.path.getsize(tif_path) / (1024 * 1024) if os.path.exists(tif_path) else 0
        print(f"    OK   : {m}.tif ({size_mb:.2f} MB)")

    if failed:
        print(f"\n  Failed               : {len(failed)} maps")
        for m in failed:
            print(f"    FAIL : {m}")

    if skipped:
        print(f"\n  Not found / skipped  : {len(skipped)} maps")
        for m in skipped:
            print(f"    SKIP : {m}")

    total = len(success) + len(failed) + len(skipped)
    print(f"\n  Total processed : {total} maps")
    print(f"  Success rate    : {len(success)}/{total}")
    print(f"\nDone! Files saved to: {output_dir}")

if __name__ == "__main__":
    main()
