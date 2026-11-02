import os
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
import mapclassify
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# =========================
# CONFIG
# =========================
RASTER_DIR   = r"D:\QGIS_Export\Rasters"
RASTER_PATH  = os.path.join(RASTER_DIR, "Ensemble_susceptibility_3x3.tif")
LS_POLY      = os.path.join(RASTER_DIR, "landslide_polygon_20mbuffered.gpkg")
OUTPUT_PATH  = os.path.join(RASTER_DIR, "LSM_FrequencyRatio_Grid_3x3.xlsx")
N_CLASSES    = 5
CLASS_LABELS = ["Very Low", "Low", "Moderate", "High", "Very High"]

# =========================
# LOAD LANDSLIDE POLYGONS
# =========================
print("Loading landslide polygons...")
ls_gdf = gpd.read_file(LS_POLY)
print(f"  Polygons: {len(ls_gdf)}, CRS: {ls_gdf.crs}")

# =========================
# PROCESS RASTER
# =========================
print(f"\nProcessing: SlopeUnit_3x3")

with rasterio.open(RASTER_PATH) as src:
    arr       = src.read(1).astype(np.float32)
    transform = src.transform
    crs       = src.crs
    nodata    = src.nodata
    res_x     = abs(src.transform.a)
    res_y     = abs(src.transform.e)
    height, width = arr.shape

print(f"  CRS: {crs}, Resolution: {res_x:.1f}m x {res_y:.1f}m")
print(f"  Shape: {height} x {width}, NoData: {nodata}")

# Valid pixel mask
valid_mask = (arr != nodata) if nodata is not None else np.isfinite(arr)
pixel_area_km2 = (res_x * res_y) / 1e6
print(f"  Pixel area: {pixel_area_km2:.8f} km²")

# Reproject landslide polygons if needed
if ls_gdf.crs != crs:
    print(f"  Reprojecting landslide polygons to {crs}")
    ls_proj = ls_gdf.to_crs(crs)
else:
    ls_proj = ls_gdf.copy()

# Rasterize landslide polygons
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

# Jenks classification
flat_vals = arr[valid_mask]
k = min(N_CLASSES, len(np.unique(flat_vals)))
print(f"  Running Jenks (k={k}) on {len(flat_vals):,} pixels...")
clf  = mapclassify.NaturalBreaks(flat_vals, k=k)
bins = clf.bins
print(f"  Jenks bins: {[round(b, 4) for b in bins]}")

# Classify pixels
classified = np.zeros_like(arr, dtype=np.uint8)
for i, b in enumerate(bins):
    if i == 0:
        mask = valid_mask & (arr <= b)
    else:
        mask = valid_mask & (arr > bins[i - 1]) & (arr <= b)
    classified[mask] = i + 1

# Per-class stats
rows = []
total_valid_pixels = valid_mask.sum()

for cls_idx in range(1, k + 1):
    cls_mask    = classified == cls_idx
    n_pixels    = cls_mask.sum()
    area_km2    = n_pixels * pixel_area_km2
    area_pct    = (n_pixels / total_valid_pixels) * 100
    ls_in_cls   = (cls_mask & ls_mask).sum()
    ls_area_km2 = ls_in_cls * pixel_area_km2
    ls_pct      = (ls_in_cls / total_ls_pixels * 100) if total_ls_pixels > 0 else 0
    dr          = (ls_pct / area_pct) if area_pct > 0 else 0
    lo          = flat_vals.min() if cls_idx == 1 else bins[cls_idx - 2]
    hi          = bins[cls_idx - 1]

    rows.append({
        "class": cls_idx, "label": CLASS_LABELS[cls_idx - 1],
        "range": f"{lo:.4f} – {hi:.4f}",
        "area_km2": area_km2, "area_pct": area_pct,
        "ls_area_km2": ls_area_km2, "ls_pct": ls_pct, "dr": dr,
    })
    print(f"  Class {cls_idx} ({CLASS_LABELS[cls_idx-1]}): "
          f"Area={area_km2:.2f}km² ({area_pct:.1f}%), "
          f"LS={ls_area_km2:.4f}km² ({ls_pct:.1f}%), DR={dr:.3f}")

# =========================
# WRITE EXCEL
# =========================
print("\nWriting Excel...")
wb = Workbook()
ws = wb.active
ws.title = "Grid_3x3_Validation"

thin    = Side(style="thin")
border  = Border(left=thin, right=thin, top=thin, bottom=thin)
c_align = Alignment(horizontal="center", vertical="center")

headers    = ["Class", "Label", "Jenks Range",
              "Area (km²)", "Area (%)",
              "LS Area (km²)", "LS (%)", "DR"]
col_widths = [8, 12, 22, 14, 10, 16, 10, 10]

hdr_font = Font(bold=True, color="FFFFFF", size=11)
hdr_fill = PatternFill("solid", fgColor="2E4057")

for ci, (h, w) in enumerate(zip(headers, col_widths), 1):
    cell = ws.cell(row=1, column=ci, value=h)
    cell.font = hdr_font; cell.fill = hdr_fill
    cell.alignment = c_align; cell.border = border
    ws.column_dimensions[get_column_letter(ci)].width = w
ws.row_dimensions[1].height = 22

alt_fill  = PatternFill("solid", fgColor="F2F7F5")
dr_green  = PatternFill("solid", fgColor="C8E6C9")
dr_red    = PatternFill("solid", fgColor="FFCDD2")

for ri, r in enumerate(rows, 2):
    fill = alt_fill if r["class"] % 2 == 0 else None
    values = [
        r["class"], r["label"], r["range"],
        round(r["area_km2"],    3),
        round(r["area_pct"],    2),
        round(r["ls_area_km2"], 4),
        round(r["ls_pct"],      2),
        round(r["dr"],          4),
    ]
    for ci, val in enumerate(values, 1):
        cell = ws.cell(row=ri, column=ci, value=val)
        cell.border = border; cell.alignment = c_align
        if fill:
            cell.fill = fill

    dr_cell = ws.cell(row=ri, column=8)
    if r["dr"] >= 1:
        dr_cell.fill = dr_green
        dr_cell.font = Font(bold=True, color="1B5E20")
    else:
        dr_cell.fill = dr_red
        dr_cell.font = Font(bold=True, color="B71C1C")

ws.freeze_panes = "A2"
wb.save(OUTPUT_PATH)
print(f"\nDONE. Saved to: {OUTPUT_PATH}")
