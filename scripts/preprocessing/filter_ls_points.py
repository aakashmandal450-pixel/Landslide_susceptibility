import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os

# =================================================
# USER SETTINGS (CONFIRMED)
# =================================================

input_file = r"D:\Research Landslide\Data\Excel files\ls_seeds.xlsx"
output_dir = r"D:\Research Landslide\Data"

x_col = "X"
y_col = "Y"
slope_col = "Slope_units"
id_col = "cat"

# spacing control for slope-units
min_slope_spacing = 0.5   # reduce if you want more points

# =================================================
# STEP 1: READ EXCEL
# =================================================

df = pd.read_excel(input_file)
print("Original rows:", len(df))

# =================================================
# STEP 2: REMOVE ROWS WITH ANY EMPTY CELL
# =================================================

df = df.dropna(how="any")
print("After removing empty rows:", len(df))

# =================================================
# STEP 3: SORT & REMOVE CLOSE SLOPE-UNIT VALUES
# =================================================

df = df.sort_values(by=slope_col)

selected = []
last_val = None

for _, row in df.iterrows():
    current_val = row[slope_col]

    if last_val is None or abs(current_val - last_val) >= min_slope_spacing:
        selected.append(row)
        last_val = current_val

df_final = pd.DataFrame(selected).reset_index(drop=True)
print("Final accepted points:", len(df_final))

# =================================================
# STEP 4: CREATE POINT GEOMETRY (UTM ZONE 44N)
# =================================================

geometry = [Point(xy) for xy in zip(df_final[x_col], df_final[y_col])]

# CRS FIXED HERE 👇
gdf = gpd.GeoDataFrame(df_final, geometry=geometry, crs="EPSG:32644")

# =================================================
# STEP 5: EXPORT FILES
# =================================================

n = len(gdf)

excel_out = os.path.join(output_dir, f"ls_filtered_{n}.xlsx")
shp_out = os.path.join(output_dir, f"ls_filtered_{n}.shp")
gpkg_out = os.path.join(output_dir, f"ls_filtered_{n}.gpkg")

# Excel (attributes only)
gdf.drop(columns="geometry").to_excel(excel_out, index=False)

# Shapefile & GeoPackage
gdf.to_file(shp_out)
gdf.to_file(gpkg_out, driver="GPKG")

print("\nFILES CREATED SUCCESSFULLY:")
print(excel_out)
print(shp_out)
print(gpkg_out)
