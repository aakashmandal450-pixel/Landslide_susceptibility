import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
import geopandas as gpd
from shapely.geometry import Point
import os

# --- CONFIGURATION ---
excel_input = r'D:\Research Landslide\Data\Excel files\landslide_points_20mbuffred_25x25.xlsx'
gpkg_input = r'D:\Research Landslide\Data\points with attributes\landslide_points_20mbuffred_25x25.gpkg'
output_folder = r'D:\Research Landslide\Data\Filtered_Output'

target_count = 1000
# We will now automatically find the best min_dist, starting high (e.g., 5km) 
# and lowering it until we get exactly 1000 points.

# 1. Setup
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 2. Capture CRS from your GPKG
print(f"Reading CRS from original GeoPackage...")
reference_gdf = gpd.read_file(gpkg_input)
captured_crs = reference_gdf.crs

# 3. Load and Clean Data
print("Loading and cleaning data...")
df = pd.read_excel(excel_input)
cols_to_check = ['slope', 'aspect', 'river_dis', 'road_dis', 'fault_dis']
existing_cols = [c for c in cols_to_check if c in df.columns]
df_clean = df.dropna(subset=existing_cols).copy()

# IMPORTANT: Shuffle the data randomly so we don't pick points in a line/grid
df_clean = df_clean.sample(frac=1, random_state=42).reset_index(drop=True)

# 4. Find the Maximum Scattering Distance (Iterative Search)
print("Searching for the maximum scattering distance...")
coords = df_clean[["x_coor", "y_coor"]].values
tree = cKDTree(coords)

def perform_thinning(dist):
    selected = []
    used_mask = np.zeros(len(coords), dtype=bool)
    for i in range(len(coords)):
        if not used_mask[i]:
            selected.append(i)
            # Find all neighbors within the current distance
            neighbors = tree.query_ball_point(coords[i], dist)
            used_mask[neighbors] = True
        if len(selected) >= target_count:
            return selected
    return selected

# We use a binary search to find the perfect distance
low = 30
high = 10000 # Start by trying 10km apart
best_indices = []

for attempt in range(15): # 15 iterations is enough to be very precise
    mid = (low + high) / 2
    indices = perform_thinning(mid)
    
    if len(indices) >= target_count:
        best_indices = indices[:target_count]
        low = mid # Try to make them even further apart
    else:
        high = mid # Too far apart, need to reduce distance

print(f"✅ Optimized Distance found: {round(low, 2)} meters.")

# 5. Finalize Data
df_filtered = df_clean.iloc[best_indices]

# 6. Save Outputs
csv_out = os.path.join(output_folder, "ls_scattered_623.csv")
df_filtered.to_csv(csv_out, index=False)

geometry = [Point(xy) for xy in zip(df_filtered.x_coor, df_filtered.y_coor)]
gdf_final = gpd.GeoDataFrame(df_filtered, geometry=geometry, crs=captured_crs)

gpkg_out = os.path.join(output_folder, "ls_scattered_623.gpkg")
gdf_final.to_file(gpkg_out, driver="GPKG")

print(f"\n🏁 Finished!")
print(f"Selected {len(df_filtered)} points with a spacing of ~{round(low, 2)}m.")
print(f"Output saved to: {output_folder}")