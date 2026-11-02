import os
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds
import mapclassify
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# =========================
# CONFIG
# =========================
RASTER_DIR  = r"D:\QGIS_Export\Rasters"
OUTPUT_DIR  = r"D:\QGIS_Export\Outputs\FrequencyRatio"
LS_POLY     = os.path.join(RASTER_DIR, "landslide_polygon_20mbuffered.gpkg")
N_CLASSES   = 5
CLASS_LABELS = ["Very Low", "Low", "Moderate", "High", "Very High"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# FILE MAP — exact names from screenshot
# =========================
raster_files = {
    "Grid_15x15":        os.path.join(RASTER_DIR, "Ensemble_susceptibility_15x15.tif"),
    "Grid_25x25":        os.path.join(RASTER_DIR, "Ensemble_susceptibility_25x25.tif"),
    "SlopeUnit_3x3":     os.path.join(RASTER_DIR, "Ensemble_slopeunit_susceptibility_3x3.tif"),
    "SlopeUnit_15x15":   os.path.join(RASTER_DIR, "Ensemble_slopeunit_susceptibility_15x15.tif"),
    "SlopeUnit_25x25":   os.path.join(RASTER_DIR, "Ensemble_slopeunit_susceptibility_25x25.tif"),
}

# =========================
# LOAD LANDSLIDE POLYGONS
# =========================
print("Loading landslide polygons...")
ls_gdf = gpd.read_file(LS_POLY)
print(f"  Polygons: {len(ls_gdf)}, CRS: {ls_gdf.crs}")

# =========================
# CORE FUNCTION
# =========================
def process_raster(name, raster_path, ls_gdf):
    print(f"\nProcessing: {name}")

    with rasterio.open(raster_path) as src:
        arr       = src.read(1).astype(np.float32)
        transform = src.transform
        crs       = src.crs
        nodata    = src.nodata
        res_x     = abs(src.transform.a)  # pixel width  in metres
        res_y     = abs(src.transform.e)  # pixel height in metres
        height, width = arr.shape

    print(f"  CRS: {crs}, Resolution: {res_x:.1f}m x {res_y:.1f}m")
    print(f"  Shape: {height} x {width}, NoData: {nodata}")

    # Mask nodata
    if nodata is not None:
        valid_mask = arr != nodata
    else:
        valid_mask = np.isfinite(arr)

    pixel_area_km2 = (res_x * res_y) / 1e6
    print(f"  Pixel area: {pixel_area_km2:.8f} km²")

    # Reproject landslide polygons to raster CRS if needed
    if ls_gdf.crs != crs:
        print(f"  Reprojecting landslide polygons to {crs}")
        ls_proj = ls_gdf.to_crs(crs)
    else:
        ls_proj = ls_gdf.copy()

    # Rasterize landslide polygons onto same grid as susceptibility raster
    ls_raster = rasterize(
        [(geom, 1) for geom in ls_proj.geometry if geom is not None],
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype=np.uint8
    )
    ls_mask = (ls_raster == 1) & valid_mask

    total_ls_pixels = ls_mask.sum()
    print(f"  Total landslide pixels: {total_ls_pixels} ({total_ls_pixels * pixel_area_km2:.3f} km²)")

    # Jenks classification on valid pixel values
    flat_vals = arr[valid_mask]
    k = min(N_CLASSES, len(np.unique(flat_vals)))
    print(f"  Running Jenks (k={k}) on {len(flat_vals):,} pixels...")
    clf = mapclassify.NaturalBreaks(flat_vals, k=k)
    bins = clf.bins
    print(f"  Jenks bins: {[round(b, 4) for b in bins]}")

    # Assign class to every valid pixel
    classified = np.zeros_like(arr, dtype=np.uint8)
    for i, b in enumerate(bins):
        lo = flat_vals.min() if i == 0 else bins[i - 1]
        if i == 0:
            mask = valid_mask & (arr <= b)
        else:
            mask = valid_mask & (arr > bins[i - 1]) & (arr <= b)
        classified[mask] = i + 1

    # Per-class stats
    rows = []
    total_valid_pixels = valid_mask.sum()
    total_ls_area_km2  = total_ls_pixels * pixel_area_km2

    for cls_idx in range(1, k + 1):
        cls_mask = classified == cls_idx

        # Area
        n_pixels     = cls_mask.sum()
        area_km2     = n_pixels * pixel_area_km2
        area_pct     = (n_pixels / total_valid_pixels) * 100

        # Landslide area within class
        ls_in_cls    = (cls_mask & ls_mask).sum()
        ls_area_km2  = ls_in_cls * pixel_area_km2
        ls_pct       = (ls_in_cls / total_ls_pixels * 100) if total_ls_pixels > 0 else 0

        # DR
        dr = (ls_pct / area_pct) if area_pct > 0 else 0

        # Jenks range
        lo = flat_vals.min() if cls_idx == 1 else bins[cls_idx - 2]
        hi = bins[cls_idx - 1]

        rows.append({
            "layer":       name,
            "class":       cls_idx,
            "label":       CLASS_LABELS[cls_idx - 1],
            "range":       f"{lo:.4f} – {hi:.4f}",
            "area_km2":    area_km2,
            "area_pct":    area_pct,
            "ls_area_km2": ls_area_km2,
            "ls_pct":      ls_pct,
            "dr":          dr,
        })

        print(f"  Class {cls_idx} ({CLASS_LABELS[cls_idx-1]}): "
              f"Area={area_km2:.2f}km² ({area_pct:.1f}%), "
              f"LS={ls_area_km2:.3f}km² ({ls_pct:.1f}%), DR={dr:.3f}")

    return rows

# =========================
# RUN ALL RASTERS
# =========================
all_rows = []
for name, path in raster_files.items():
    rows = process_raster(name, path, ls_gdf)
    all_rows.extend(rows)

# =========================
# WRITE EXCEL
# =========================
print("\nWriting Excel...")
wb = Workbook()
ws = wb.active
ws.title = "Frequency_Ratio_Validation"

# Styles
hdr_font   = Font(bold=True, color="FFFFFF", size=11)
hdr_fill   = PatternFill("solid", fgColor="2E4057")
alt_fill   = PatternFill("solid", fgColor="F2F7F5")
grp_fill   = PatternFill("solid", fgColor="E8EDF2")  # group separator
thin       = Side(style="thin")
border     = Border(left=thin, right=thin, top=thin, bottom=thin)
c_align    = Alignment(horizontal="center", vertical="center")
l_align    = Alignment(horizontal="left",   vertical="center")
dr_green   = PatternFill("solid", fgColor="C8E6C9")
dr_red     = PatternFill("solid", fgColor="FFCDD2")

# Headers
headers    = ["Layer", "Class", "Label", "Jenks Range",
              "Area (km²)", "Area (%)",
              "LS Area (km²)", "LS (%)", "DR"]
col_widths = [22, 8, 12, 22, 14, 10, 16, 10, 10]

for ci, (h, w) in enumerate(zip(headers, col_widths), 1):
    cell = ws.cell(row=1, column=ci, value=h)
    cell.font = hdr_font; cell.fill = hdr_fill
    cell.alignment = c_align; cell.border = border
    ws.column_dimensions[get_column_letter(ci)].width = w
ws.row_dimensions[1].height = 22

# Data
current_layer = None
row_i = 2
for r in all_rows:
    is_new_group = (r["layer"] != current_layer)
    current_layer = r["layer"]
    is_alt = (r["class"] % 2 == 0)
    fill = grp_fill if is_new_group and r["class"] == 1 else (alt_fill if is_alt else None)

    values = [
        r["layer"], r["class"], r["label"], r["range"],
        round(r["area_km2"],    3),
        round(r["area_pct"],    2),
        round(r["ls_area_km2"], 4),
        round(r["ls_pct"],      2),
        round(r["dr"],          4),
    ]
    for ci, val in enumerate(values, 1):
        cell = ws.cell(row=row_i, column=ci, value=val)
        cell.border = border
        cell.alignment = l_align if ci == 1 else c_align
        if fill:
            cell.fill = fill

    # DR colour
    dr_cell = ws.cell(row=row_i, column=9)
    if r["dr"] >= 1:
        dr_cell.fill = dr_green
        dr_cell.font = Font(bold=True, color="1B5E20")
    else:
        dr_cell.fill = dr_red
        dr_cell.font = Font(bold=True, color="B71C1C")

    row_i += 1

ws.freeze_panes = "A2"

out_path = os.path.join(OUTPUT_DIR, "LSM_FrequencyRatio_Raster_Validation.xlsx")
wb.save(out_path)
print(f"\nDONE. Saved to: {out_path}")