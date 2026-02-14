# ============================================================
# LANDSLIDE SUSCEPTIBILITY MAP GENERATION
# RF | SVM | XGBOOST
# ============================================================

import os
import numpy as np
import pandas as pd
import rasterio

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier

# ============================================================
# PATHS
# ============================================================

RASTER_BASE = r"D:\Research Landslide\Grass\Grid units derivatives"
EXCEL_BASE  = r"D:\Research Landslide\Data\Filtered_Excel files"
OUTPUT_BASE = r"D:\Research Landslide\Result\New_output\Susceptibility_Maps"

CONFIG = {
    "3x3": {
        "raster_folder": "3x3 rasters",
        "excel": "ls_non_ls_final_3x3.xlsx",
        "rasters": [
            "aspect_3x3.tif",
            "curvature_3x3.tif",
            "dis_to_fault_3x3.tif",
            "dis_to_river_3x3.tif",
            "dis_to_road_3x3.tif",
            "dis_to_thrust_3x3.tif",
            "ndvi.tif",
            "ndwi.tif",
            "roughness_3x3.tif",
            "slope_3x3.tif",
            "twi_finescale_3x3.tif"
        ]
    },

    "15x15": {
        "raster_folder": "15x15 rasters",
        "excel": "ls_non_ls_final_15x15.xlsx",
        "rasters": [
            "aspect_15x15.tif",
            "curvature_15x15.tif",
            "dis_to_fault_15x15.tif",
            "dis_to_river_15x15.tif",
            "dis_to_road_15x15.tif",
            "dis_to_thrust_15x15.tif",
            "ndvi_15x15.tif",
            "ndwi_15x15.tif",
            "roughness_15x15.tif",
            "slope_15x15.tif",
            "twi_intermediate_15x15.tif"
        ]
    },

    "25x25": {
        "raster_folder": "25x25 rasters",
        "excel": "ls_non_ls_final_25x25.xlsx",
        "rasters": [
            "aspect_25x25.tif",
            "curvature_25x25.tif",
            "dis_to_fault_25x25.tif",
            "dis_to_river_25x25.tif",
            "dis_to_road_25x25.tif",
            "dis_to_thrust_25x25.tif",
            "ndvi_25x25.tif",
            "ndwi_25x25.tif",
            "roughness_25x25.tif",
            "slope_25x25.tif",
            "twi_coarse_25x25.tif"
        ]
    }
}

# ============================================================
# MAIN LOOP
# ============================================================

for grid, cfg in CONFIG.items():

    print(f"\nProcessing {grid}")

    df = pd.read_excel(os.path.join(EXCEL_BASE, cfg["excel"]))
    X = df.drop(columns=["ID"])
    y = df["ID"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    rf = Pipeline([
        ("imp",SimpleImputer()),
        ("rf",RandomForestClassifier(n_estimators=300,random_state=42))
    ])

    svm = Pipeline([
        ("imp",SimpleImputer()),
        ("scaler",StandardScaler()),
        ("svm",SVC(kernel="rbf",probability=True))
    ])

    xgb = Pipeline([
        ("imp",SimpleImputer()),
        ("xgb",XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=42))
    ])

    rf.fit(X_train,y_train)
    svm.fit(X_train,y_train)
    xgb.fit(X_train,y_train)

    stack = []
    meta = None

    for r in cfg["rasters"]:
        path = os.path.join(RASTER_BASE, cfg["raster_folder"], r)
        src = rasterio.open(path)
        arr = src.read(1)
        stack.append(arr)
        if meta is None:
            meta = src.meta.copy()

    stack = np.stack(stack, axis=-1)
    rows, cols, bands = stack.shape
    flat = stack.reshape(-1, bands)

    rf_map  = rf.predict_proba(flat)[:,1]
    svm_map = svm.predict_proba(flat)[:,1]
    xgb_map = xgb.predict_proba(flat)[:,1]

    rf_map  = rf_map.reshape(rows,cols)
    svm_map = svm_map.reshape(rows,cols)
    xgb_map = xgb_map.reshape(rows,cols)

    meta.update(count=1, dtype="float32")

    out_dir = os.path.join(OUTPUT_BASE,f"result_{grid}")
    os.makedirs(out_dir,exist_ok=True)

    with rasterio.open(os.path.join(out_dir,"RF_susceptibility.tif"),"w",**meta) as dst:
        dst.write(rf_map.astype("float32"),1)

    with rasterio.open(os.path.join(out_dir,"SVM_susceptibility.tif"),"w",**meta) as dst:
        dst.write(svm_map.astype("float32"),1)

    with rasterio.open(os.path.join(out_dir,"XGB_susceptibility.tif"),"w",**meta) as dst:
        dst.write(xgb_map.astype("float32"),1)

    print(f"{grid} maps generated.")

print("\nALL SUSCEPTIBILITY MAPS CREATED SUCCESSFULLY")
