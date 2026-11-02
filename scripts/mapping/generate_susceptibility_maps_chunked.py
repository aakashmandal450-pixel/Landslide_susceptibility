# ============================================================
# Landslide Susceptibility Mapping using RF, SVM, XGBoost
# Chunk-based raster prediction (memory safe)
# Removes feature-name warnings
# ============================================================

import os
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# PATH SETTINGS
# ============================================================

EXCEL_FOLDER = r"D:\Research Landslide\Data\Filtered_Excel files"
RASTER_BASE  = r"D:\Research Landslide\Grass\Grid units derivatives"
OUTPUT_BASE  = r"D:\Research Landslide\Result\Susceptibility_Maps"

GRID_CONFIG = {
    "3x3": {
        "excel": "ls_non_ls_final_3x3.xlsx",
        "rasters": "3x3 rasters"
    },
    "15x15": {
        "excel": "ls_non_ls_final_15x15.xlsx",
        "rasters": "15x15 rasters"
    },
    "25x25": {
        "excel": "ls_non_ls_final_25x25.xlsx",
        "rasters": "25x25 rasters"
    }
}

# ============================================================
# MODELS
# ============================================================

def build_models():
    rf = RandomForestClassifier(n_estimators=300, random_state=42)
    svm = SVC(kernel="rbf", probability=True, random_state=42)
    xgb = XGBClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        eval_metric="logloss",
        use_label_encoder=False
    )
    return {"RF": rf, "SVM": svm, "XGB": xgb}

# ============================================================
# MAIN LOOP
# ============================================================

for grid, cfg in GRID_CONFIG.items():

    print(f"\nProcessing {grid}")

    excel_path = os.path.join(EXCEL_FOLDER, cfg["excel"])
    raster_folder = os.path.join(RASTER_BASE, cfg["rasters"])
    out_folder = os.path.join(OUTPUT_BASE, f"result_{grid}")
    os.makedirs(out_folder, exist_ok=True)

    # --------------------------------------------------------
    # LOAD TRAINING DATA
    # --------------------------------------------------------

    df = pd.read_excel(excel_path)

    X = df.drop(columns=["ID"])
    y = df["ID"]

    imputer = SimpleImputer(strategy="median")
    X = pd.DataFrame(imputer.fit_transform(X), columns=X.columns)

    Xtrain, Xtest, ytrain, ytest = train_test_split(
        X, y, test_size=0.3, stratify=y, random_state=42
    )

    models = build_models()

    # --------------------------------------------------------
    # TRAIN MODELS
    # --------------------------------------------------------

    for name in models:
        models[name].fit(Xtrain, ytrain)

    # --------------------------------------------------------
    # READ RASTERS
    # --------------------------------------------------------

    raster_files = sorted([
        f for f in os.listdir(raster_folder)
        if f.endswith(".tif")
    ])

    raster_paths = [os.path.join(raster_folder, f) for f in raster_files]

    srcs = [rasterio.open(p) for p in raster_paths]

    profile = srcs[0].profile
    height = profile["height"]
    width = profile["width"]

    profile.update(
        dtype="float32",
        count=1,
        compress="lzw"
    )

    block = 512

    # --------------------------------------------------------
    # CREATE OUTPUT FILES
    # --------------------------------------------------------

    writers = {}
    for model in models:
        path = os.path.join(out_folder, f"{model}_susceptibility.tif")
        writers[model] = rasterio.open(path, "w", **profile)

    # --------------------------------------------------------
    # CHUNKED PREDICTION
    # --------------------------------------------------------

    for row in range(0, height, block):
        for col in range(0, width, block):

            h = min(block, height - row)
            w = min(block, width - col)

            stack = []

            for src in srcs:
                arr = src.read(1, window=Window(col, row, w, h))
                stack.append(arr)

            stack = np.stack(stack, axis=-1)

            # ---- FIXED PART (removes warnings) ----
            flat = pd.DataFrame(
                stack.reshape(-1, stack.shape[-1]),
                columns=X.columns
            )
            flat = pd.DataFrame(
                imputer.transform(flat),
                columns=X.columns
            )

            for name, model in models.items():
                probs = model.predict_proba(flat)[:, 1]
                out = probs.reshape(h, w).astype("float32")
                writers[name].write(out, 1, window=Window(col, row, w, h))

    # --------------------------------------------------------
    # CLOSE FILES
    # --------------------------------------------------------

    for src in srcs:
        src.close()

    for w in writers.values():
        w.close()

    print(f"Finished {grid}")

print("\nALL SUSCEPTIBILITY MAPS GENERATED SUCCESSFULLY")
