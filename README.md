# Landslide Susceptibility Mapping — Karnali Highway Corridor (NH-58), Western Nepal

Code, processed data and results for the study **"Multi-Scale Pixel and Slope-Unit Landslide Susceptibility Mapping with Applicability-Domain Validation: Evidence from the Karnali Highway Corridor, Western Nepal"** (manuscript under review, *Journal of Mountain Science*).

The study maps landslide susceptibility for a ~2,155 km² corridor along the Karnali Highway using:

- **Two mapping units**: pixel (grid) units and slope units (r.slopeunits, optimal a = 300,000 m², c = 0.35)
- **Three analysis grids**: 3 m, 15 m and 25 m cell sizes, labelled `3x3`, `15x15` and `25x25` in the code and outputs (all factors derived from the 12.5 m ALOS PALSAR DEM and Sentinel-2, then resampled to each grid; see `docs/data_processing.md`)
- **Three models + ensemble**: Random Forest, RBF-SVM and XGBoost, tuned with Bayesian search (scikit-optimize), Platt-calibrated, combined as an equal-weight mean-probability ensemble
- **Spatially blocked cross-validation**: StratifiedGroupKFold with 1,000 m blocks (grid) and 2,000 m blocks (slope units) in the current notebooks
- **Applicability domain (AD)**: Ledoit–Wolf Mahalanobis distance blended with inter-model agreement (0.7 / 0.3), thresholded at 0.5 into a trusted/untrusted mask
- **Interpretability and validation**: SHAP, permutation importance, Jenks classification and frequency-ratio (density-ratio) checks

Nine conditioning factors were used after collinearity screening (|r| > 0.8): aspect, profile curvature, distance to fault, distance to river, distance to road, distance to thrust, NDVI, slope and TWI. Roughness and NDWI were dropped.

All rasters and vectors are in **WGS 84 / UTM zone 44N (EPSG:32644)**.

## Repository layout

```
notebooks/
  01_data_preparation/   NDVI and NDWI composites (Sentinel-2 via Copernicus), factor analysis, point filtering, rainfall
  02_grid_unit_models/   Grid-unit model comparison (spatial CV) and susceptibility mapping
  03_slope_unit_models/  Slope-unit model comparison and mapping
  archive/               Earlier runs kept for reference (non-spatial CV, first full pipeline, CNN test)
scripts/
  preprocessing/         Kernel raster export (GRASS), resolution fixes, sample filtering, ML dataset build
  slope_units/           Global Heterogeneity (GH) optimisation for r.slopeunits + GRASS addon launchers
  mapping/               Chunked raster prediction
  applicability_domain/  AD validation for grid and slope-unit outputs
  validation/            Jenks class verification, density-ratio bars, success-rate curve
  figures/               Pipeline diagram, distribution curves, model bar plots, feature importance
  cnn/                   Exploratory CNN (not used in the manuscript)
  legacy_ml/             Early stand-alone ML scripts, superseded by the notebooks
data/
  inventory/             Landslide polygons (460) and derived points/centroids (GPKG, SHP, KML)
  samples/               Landslide / non-landslide sample tables per grid (XLSX)
  vectors/               Roads, national highways, rivers, thrusts, study-area extent (SHP)
  slope_units/           Optimal slope-unit layer (su_a300000_c0_35.gpkg), per-grid zonal-statistics tables, su_zonal_stats.xlsx
  geology/               Digitised lithology polygons (rocks.shp; not used as a model factor)
  rainfall/              Rainfall records for station 220
  qgis/                  QGIS / ArcMap project files
results/
  grid_unit/             Per-grid metrics, predictions, best hyper-parameters, calibrated models (.pkl), plots
  grid_unit/maps/        Susceptibility / AD maps (PNG) and GeoTIFFs for 15×15 and 25×25
  slope_unit/            Per-grid metrics, best hyper-parameters, calibrated models (.pkl), plots, maps
  applicability_domain/  AD validation tables and figure
  jenks_verification/    Density-ratio / class-area validation
  slope_unit_optimization/ GH optimisation results and figures
docs/                    data_processing.md (raw data to model-ready tables), methodology notes, pipeline diagrams
```

## Workflow

1. **Factor preparation**: derive slope, aspect, profile curvature and TWI from the 12.5 m DEM; Euclidean distances to roads, rivers, faults and thrusts; NDVI as a 2021–2024 dry-season minimum composite from Sentinel-2 L2A (`notebooks/01_data_preparation/`).
2. **Grid preparation**: resample every factor to the 3 m, 15 m and 25 m grids in GRASS, align them and export them (`scripts/preprocessing/3x3 15x15 25x25 grid size fix.py`, `export_kernel_rasters_grass.py`).
3. **Sampling**: 1,000 landslide and 1,000 non-landslide pixels per kernel (`scripts/preprocessing/filter_points.py`, `data/samples/`).
4. **Slope units**: run r.slopeunits over a 6 × 7 grid of (a, c) and select by minimum GH (`scripts/slope_units/`, `results/slope_unit_optimization/`).
5. **Modelling**: run `notebooks/02_grid_unit_models/RF_XGB_SVM_Model_comparision_Spatial_Shuffle.ipynb` and `notebooks/03_slope_unit_models/Slope_Units_Model_Comparision.ipynb`.
6. **Mapping and AD**: run `RF_XGB_SVM_Mapping.ipynb` / `Slope_Units_Mapping.ipynb`, then `scripts/applicability_domain/`.
7. **Validation**: run the Jenks and density-ratio scripts in `scripts/validation/`.

The notebooks were written for Google Colab and read inputs from Google Drive (`/content/drive/MyDrive/RemoteSensingResearchRelated/...`). The scripts use local Windows paths (`D:\Research Landslide\...`). Update the path constants at the top of each file before running.

### Copernicus credentials

The NDVI and NDWI notebooks use the Copernicus Data Space Sentinel Hub API. Credentials have been removed. Set `client_id` and `client_secret` to your own values.

## Key results (holdout AUC, from `results/*/all_*_summary.csv`)

| Grid | Grid XGB | Grid Ensemble | Slope-unit XGB | Slope-unit Ensemble |
|---|---|---|---|---|
| 3×3   | 0.972 | 0.968 | 0.907 | 0.886 |
| 15×15 | 0.993 | 0.989 | 0.856 | 0.870 |
| 25×25 | 0.978 | 0.970 | 0.826 | 0.803 |

AD trusted coverage is >97% (grid) and >98% (slope units). Landslide capture inside the trusted zone is >98.7% (`results/applicability_domain/`).

## Not included (size)

These files are too large for GitHub. They are kept in the project Google Drive folder (`RemoteSensingResearchRelated`) and on the authors' machines:

- DEM (12.5 m and merged), NDVI/NDWI tiles and composites, factor rasters for all grids (the 3 m set alone is ~22 GB)
- 3 m susceptibility / AD GeoTIFFs (~1 GB each) and the per-model GeoTIFFs for 15×15 and 25×25
- The 42 candidate slope-unit layers from the GH grid search
- GRASS GIS database and installation, reference papers

## Environment

Python 3.10+ (Colab). See `requirements.txt`. GRASS GIS 8.4 with the `r.slopeunits` addon is needed for the slope-unit and kernel-export steps.

## Citation

Manuscript under review at *Journal of Mountain Science* (ID 26-11543). A full citation will be added on publication.
