# Data processing: from raw data to model-ready tables

This document records how the inputs to the models were produced. It is reconstructed from the scripts, notebooks and file names in this repository. Items marked **[confirm]** could not be recovered from the code. They were done by hand in QGIS or GRASS GIS and need to be checked by the authors.

All layers are in WGS 84 / UTM zone 44N (EPSG:32644) unless stated otherwise.

---

## 1. Source data

| Layer | Source | Native resolution / scale | Repository location |
|---|---|---|---|
| DEM | ALOS PALSAR DEM | 12.5 m | not included (size); `DEM_12.5m.tif` on Drive |
| Landslide inventory | Visual interpretation of high-resolution imagery in Google Earth Pro, digitised as polygons | 460 polygons | `data/inventory/` |
| Faults and thrusts | DMG structural geology map **[confirm: 1:400,000 sheet name / year]** | vector | thrusts: `data/vectors/Thrust.*`; faults: **not in repository [confirm source file]** |
| Lithology (not used as a factor) | Digitised from the georeferenced Karnali geology map | 3 polygons | `data/geology/rocks.*` |
| Roads | National highway network (existing + additional NH) | vector | `data/vectors/ExistingNHP.*`, `AdditionalNHP.*`, `mergedHighways.*`, `clip*NH.*` |
| Rivers | Stream network **[confirm: DEM-derived via r.stream.extract / r.watershed, or national river layer]** | vector | `data/vectors/River.*`, `ClipRiver.*` |
| Sentinel-2 L2A | Copernicus Data Space (Sentinel Hub Process API) | 10 m | derived NDVI/NDWI composites on Drive |
| Rainfall | Station 220 records (not used as a model factor) | point | `data/rainfall/` |
| Study area | Corridor extent polygon | vector | `data/vectors/study area proj.*`, `data/vectors/Extent.*` |

---

## 2. Analysis grids: 3 m, 15 m and 25 m

The labels `3x3`, `15x15` and `25x25` used throughout the code and outputs refer to **raster cell sizes of 3 m, 15 m and 25 m**. They are not moving-window sizes on the 12.5 m DEM.

Evidence in the code:

- `scripts/preprocessing/3x3 15x15 25x25 grid size fix.py` sets `"res": 3`, `"res": 15` and `"res": 25` for the three grids. It forces every factor raster onto a reference grid (`slope_3x3`, `slope_15x15`, `slope_25x25`) at that resolution with `r.resamp.interp method=bilinear`.
- The DEMs in the GRASS locations are named `dem_3m` and `dem_filled_15m`.
- The NDVI/NDWI resolution script maps `"3x3": 3, "15x15": 15, "25x25": 25` (metres).
- The valid pixel counts in `results/applicability_domain/AD_validation_results.csv` match the corridor area at those cell sizes: 236,009,064 × 9 m² ≈ 2,124 km²; 9,372,074 × 225 m² ≈ 2,109 km²; 3,317,601 × 625 m² ≈ 2,074 km².
- No moving-window operation (`r.neighbors` or an equivalent) appears in any script or notebook.

The repository's early `docs/methodology_notes.txt` says the same: "All datasets were resampled to grid resolutions of 3×3 m, 15×15 m, and 25×25 m."

Each grid has its own GRASS location (`Grass/Grid units raster files/<grid>/`), and factors were derived or resampled separately in each one.

---

## 3. Conditioning factors

Eleven candidate factors were prepared for each grid. Roughness and NDWI were later dropped for collinearity (|r| > 0.8 with slope and NDVI), leaving nine.

### 3.1 DEM preparation

1. Mosaic the ALOS PALSAR tiles (`merged_DEM.tif`) and clip to the study extent (`DEM_12.5m.tif`).
2. Resample to 3 m, 15 m and 25 m. **[confirm: method — bilinear `r.resamp.interp` as in the grid script, or `gdalwarp`]**
3. Fill sinks for the hydrological derivatives (`dem_filled_15m`). **[confirm: tool (`r.fill.dir` / `r.hydrodem`) and whether it was also done at 3 m and 25 m]**

### 3.2 Topographic and hydrological factors (per grid)

| Factor | Raster name | Method |
|---|---|---|
| Slope (°) | `slope_<grid>` | **[confirm: `r.slope.aspect`]** on the resampled DEM |
| Aspect (°) | `aspect_<grid>` | **[confirm: `r.slope.aspect`; GRASS aspect is counter-clockwise from east unless `-n` (north-based) was set; state which]** |
| Profile curvature (1/m) | `curvature_<grid>` | **[confirm: `r.slope.aspect pcurvature=`]** |
| TWI | `twi_<grid>` (`twi_fine`, `twi_intermediate`, `twi_coarse` in early notebooks) | ln(A_s / tan β). **[confirm: `r.topidx` or `r.watershed` accumulation + map algebra; flow algorithm (SFD/MFD)]** |
| Roughness (dropped) | `roughness_<grid>` | **[confirm]** |

### 3.3 Distance factors

Euclidean distance rasters were computed from the vector layers (`RoadDis.tif`, `RiverDistance.tif`, `FaultsDis.tif`, `Thrust Distance1.tif` in `Data/Distances`) **[confirm: ArcGIS Euclidean Distance or GRASS `r.grow.distance`]**. They were then resampled to each grid as `dis_to_road_<grid>`, `dis_to_river_<grid>`, `dis_to_fault_<grid>` and `dis_to_thrust_<grid>`.

### 3.4 NDVI and NDWI (Sentinel-2)

Notebooks: `notebooks/01_data_preparation/ndvi_10m.ipynb` (also `Minimum_ndvi_copernicus.ipynb`) and `ndwi_10m.ipynb`.

| Setting | Value |
|---|---|
| Collection | Sentinel-2 L2A via the Sentinel Hub Process API (Copernicus Data Space) |
| Bands | NDVI: B04 (red), B08 (NIR); NDWI: B03 (green), B08 (NIR); plus `dataMask` |
| Months | January–April and October–December (dry season), days 1–28 |
| Years | 2021, 2022, 2023, 2024 |
| Cloud filter | `maxCloudCoverage = 15` (scene-level) |
| Output grid | 10 m, EPSG:32644, requested in 20 km × 20 km tiles |
| Compositing | Per-pixel **minimum** NDVI across all dates → `absolute_min_ndvi_10m.tif`; per-pixel **maximum** NDWI → `absolute_max_ndwi_10m.tif` |
| Cloudy months | March, April, October–December split into two half-month requests to avoid server timeouts (NDWI notebook) |

The 10 m composites were resampled to 3 m, 15 m and 25 m with `r.resamp.interp method=bilinear` (`scripts/preprocessing/grass code for ndvi and ndwi resolution fix.py`).

### 3.5 Grid alignment and export

1. `scripts/preprocessing/3x3 15x15 25x25 grid size fix.py` locks the region to the grid's slope raster and resamples every factor onto it, so all layers have identical rows and columns.
2. `scripts/preprocessing/export_kernel_rasters_grass.py` exports each factor with `r.out.gdal` (`COMPRESS=LZW, TILED=YES, BIGTIFF=YES`) to `Data/Raster files/<grid>_rasters/`.

---

## 4. Landslide and non-landslide samples (grid units)

1. **Buffer and split the inventory.** The 460 polygons were buffered by 20 m (`landslide_polygon_20mbuffered.gpkg`). `scripts/preprocessing/20mbuffered.py` then splits each buffered polygon into four quadrants about its bounding-box centre and takes their centroids (`data/inventory/polygons divided and centroid/`). This gives several points per landslide.
2. **Attach factor values.** Factor values at the points were sampled from each grid's rasters (`data/samples/point_tables/landslide_points_20mbuffred_<grid>.xlsx`). **[confirm: `v.what.rast` in GRASS or "Sample raster values" in QGIS]**
3. **Spatially thin the landslide points.** `scripts/preprocessing/filter_points.py` drops rows with missing factor values, shuffles them (`random_state=42`), and binary-searches for the largest minimum spacing that still leaves the target count. This produced 1,000 scattered landslide points per grid (`data/samples/kernel_tables/ls_scattered_1000_<grid>.xlsx`).
4. **Non-landslide points.** 1,000 points per grid (`non_ls_points1000_<grid>.xlsx`) were drawn from terrain outside a buffer around the mapped polygons and inside the Low / Very Low classes of an earlier frequency-ratio susceptibility map (`Data/Frequency ratio map classification (old)/low_zones.tiff`). **[confirm: buffer distance; how the points were generated, e.g. QGIS "Random points in polygons"]**
5. **Merge.** Steps 3 and 4 were combined into `data/samples/kernel_tables/ls_non_ls_final_<grid>.xlsx` (2,000 rows, `ID` = 1 landslide / 0 non-landslide, plus X, Y and the factor columns). These are the inputs to `notebooks/02_grid_unit_models/`.

---

## 5. Slope units

1. **Delineation.** r.slopeunits (GRASS addon, launched via `scripts/slope_units/grass_bin/*.bat`) was run over a grid of minimum area *a* = 50,000–300,000 m² (step 50,000) and circular variance *c* = 0.10–0.40 (step 0.05): 42 configurations, written as `su_a<a>_c<c>.gpkg`. **[confirm: input DEM resolution for r.slopeunits, plus `thresh` and `maxiteration` settings]**
2. **Selection.** `scripts/slope_units/calculate_GH_STATSONLY_v2.py` and `gh_optimization_local_v2.py` compute the area-weighted aspect variance (V) and the global weighted Moran's I of mean aspect (wMI) for each configuration. They min-max normalise both and sum them into the global heterogeneity score GH. The minimum GH is at *a* = 300,000 m², *c* = 0.35, giving 9,952 units (`data/slope_units/su_a300000_c0_35.gpkg`; results in `results/slope_unit_optimization/`).
3. **Zonal statistics.** For each grid, the mean and standard deviation of every factor were computed per slope unit (GRASS `v.rast.stats method=average,stddev`). The results are in `data/slope_units/su_a300000_c0_35_<grid>.xlsx` and `su_zonal_stats.xlsx`.
4. **Labels.** `scripts/preprocessing/build_ml_dataset.py` sets `label = 1` for every slope unit that contains a landslide point and `label = 0` otherwise. The slope-unit notebooks use the `*_average` columns as features.

---

## 6. Hand-off to modelling

| Mapping unit | Model input | Notebook |
|---|---|---|
| Grid | `data/samples/kernel_tables/ls_non_ls_final_<grid>.xlsx` + factor rasters for mapping | `notebooks/02_grid_unit_models/` |
| Slope unit | `data/slope_units/su_a300000_c0_35_<grid>.xlsx` + `su_a300000_c0_35.gpkg` | `notebooks/03_slope_unit_models/` |

Modelling, calibration, applicability domain and validation are described in the notebooks and in the main `README.md`.
