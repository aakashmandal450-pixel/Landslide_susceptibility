import geopandas as gpd
import pandas as pd
from shapely.geometry import box, Point
import os

def split_polygon_to_quadrants(poly):
    """Divides a polygon into 4 parts based on its bounding box center."""
    minx, miny, maxx, maxy = poly.bounds
    midx, midy = (minx + maxx) / 2, (miny + maxy) / 2
    
    # Create the four quadrant boxes
    nw = box(minx, midy, midx, maxy)
    ne = box(midx, midy, maxx, maxy)
    sw = box(minx, miny, midx, midy)
    se = box(midx, miny, maxx, midy)
    
    # Intersect original polygon with each quadrant
    parts = [poly.intersection(q) for q in [nw, ne, sw, se]]
    # Filter out empty intersections
    return [p for p in parts if not p.is_empty]

# 1. Load your file
input_path = r'D:\Research Landslide\Data\landslide_polygon_20mbuffered.gpkg'
gdf = gpd.read_file(input_path)

# 2. Process each landslide
split_polygons = []
centroid_points = []

for idx, row in gdf.iterrows():
    original_geom = row.geometry
    parts = split_polygon_to_quadrants(original_geom)
    
    for i, part in enumerate(parts):
        # Store Polygon Part
        poly_data = row.copy()
        poly_data.geometry = part
        poly_data['sub_id'] = f"{idx}_{i}"
        split_polygons.append(poly_data)
        
        # Store Centroid of that Part
        point_data = row.copy()
        point_data.geometry = part.centroid
        point_data['sub_id'] = f"{idx}_{i}"
        centroid_points.append(point_data)

# 3. Create GeoDataFrames
gdf_parts = gpd.GeoDataFrame(split_polygons, crs=gdf.crs)
gdf_centroids = gpd.GeoDataFrame(centroid_points, crs=gdf.crs)

# 4. Save to Google Drive / Local Path
output_folder = r'D:\Research Landslide\Data'
os.makedirs(output_folder, exist_ok=True)

# Export GPKG
gdf_parts.to_file(f"{output_folder}/landslides_divided.gpkg", driver="GPKG")
gdf_centroids.to_file(f"{output_folder}/landslides_centroids.gpkg", driver="GPKG")

# Export KML (Requires fiona to support KML or convert to WGS84 first)
gdf_parts_wgs84 = gdf_parts.to_crs(epsg=4326)
gdf_centroids_wgs84 = gdf_centroids.to_crs(epsg=4326)

gdf_parts_wgs84.to_file(f"{output_folder}/landslides_divided.kml", driver='KML')
gdf_centroids_wgs84.to_file(f"{output_folder}/landslides_centroids.kml", driver='KML')

print(f"Files saved successfully in {output_folder}")