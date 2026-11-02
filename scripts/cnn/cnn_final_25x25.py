# ============================================================
# CNN BASED LANDSLIDE SUSCEPTIBILITY (25x25) - FULL PIPELINE
# ============================================================

import os
import numpy as np
import pandas as pd
import rasterio
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import accuracy_score, recall_score, f1_score, roc_curve, auc

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.optimizers import Adam

from graphviz import Digraph

# ============================================================
# PATHS
# ============================================================

RASTER_FOLDER = r"D:\Research Landslide\Grass\Grid units derivatives\25x25 rasters"
EXCEL_FILE = r"D:\Research Landslide\Data\Filtered_Excel files\ls_non_ls_final_25x25.xlsx"
OUTPUT_FOLDER = r"D:\Research Landslide\Result\New_output\CNN\25x25"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

PATCH_SIZE = 25
EPOCHS = 5
BATCH_SIZE = 32

# ============================================================
# LOAD RASTER STACK
# ============================================================

factor_files = [
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

layers = []

print("Loading raster layers...")

for f in factor_files:
    with rasterio.open(os.path.join(RASTER_FOLDER, f)) as src:
        layers.append(src.read(1))
        profile = src.profile

stack = np.stack(layers, axis=-1)

# Normalize
stack = (stack - np.nanmin(stack)) / (np.nanmax(stack) - np.nanmin(stack))

rows, cols, bands = stack.shape

# ============================================================
# LOAD EXCEL INVENTORY
# ============================================================

print("Loading inventory Excel...")

df = pd.read_excel(EXCEL_FILE)

# REQUIRED COLUMNS: X , Y , ID

# ============================================================
# PATCH EXTRACTION FROM POINTS
# ============================================================

X_data = []
y_data = []

half = PATCH_SIZE // 2

with rasterio.open(os.path.join(RASTER_FOLDER, factor_files[0])) as ref:
    transform = ref.transform

print("Extracting patches...")

for idx, row in df.iterrows():

    x = row["X"]
    y = row["Y"]
    label = row["ID"]

    col, rowpix = ~transform * (x, y)
    col = int(col)
    rowpix = int(rowpix)

    if (rowpix - half >= 0 and col - half >= 0 and
        rowpix + half < rows and col + half < cols):

        patch = stack[rowpix-half:rowpix+half+1,
                      col-half:col+half+1, :]

        if patch.shape == (PATCH_SIZE, PATCH_SIZE, bands):
            X_data.append(patch)
            y_data.append(label)

X = np.array(X_data)
y = np.array(y_data)

print("Total samples:", X.shape[0])

# ============================================================
# CNN MODEL FUNCTION
# ============================================================

def create_model():
    model = Sequential([
        Conv2D(32, (3,3), activation="relu",
               input_shape=(PATCH_SIZE, PATCH_SIZE, bands)),
        MaxPooling2D(2,2),

        Conv2D(64, (3,3), activation="relu"),
        MaxPooling2D(2,2),

        Flatten(),
        Dense(128, activation="relu"),
        Dropout(0.3),
        Dense(1, activation="sigmoid")
    ])

    model.compile(
        optimizer=Adam(0.001),
        loss="binary_crossentropy",
        metrics=["accuracy"]
    )

    return model

# ============================================================
# K-FOLD CROSS VALIDATION
# ============================================================

print("Running K-Fold Cross Validation...")

kf = KFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = []

for train_idx, test_idx in kf.split(X):

    model = create_model()
    model.fit(X[train_idx], y[train_idx],
              epochs=EPOCHS,
              batch_size=BATCH_SIZE,
              verbose=0)

    preds = (model.predict(X[test_idx]) > 0.5).astype(int)
    acc = accuracy_score(y[test_idx], preds)
    cv_scores.append(acc)

with open(os.path.join(OUTPUT_FOLDER, "kfold_results.txt"), "w") as f:
    f.write(str(cv_scores))

# ============================================================
# FINAL TRAINING
# ============================================================

print("Final model training...")

model = create_model()

history = model.fit(
    X, y,
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    validation_split=0.2
)

# ============================================================
# AUC-ROC CURVE
# ============================================================

pred_prob = model.predict(X)

fpr, tpr, _ = roc_curve(y, pred_prob)
roc_auc = auc(fpr, tpr)

plt.figure()
plt.plot(fpr, tpr, label="AUC = " + str(round(roc_auc,3)))
plt.plot([0,1],[0,1],'--')
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.legend()
plt.savefig(os.path.join(OUTPUT_FOLDER, "auc_roc_curve.png"))
plt.close()

# ============================================================
# EPOCH CURVES
# ============================================================

plt.figure()
plt.plot(history.history["accuracy"], label="Train Acc")
plt.plot(history.history["val_accuracy"], label="Val Acc")
plt.xlabel("Epoch")
plt.ylabel("Accuracy")
plt.legend()
plt.savefig(os.path.join(OUTPUT_FOLDER, "epoch_vs_accuracy.png"))
plt.close()

# ============================================================
# FULL SUSCEPTIBILITY MAP
# ============================================================

print("Generating susceptibility map...")

sus_map = np.zeros((rows, cols))

for i in range(half, rows-half):
    for j in range(half, cols-half):
        patch = stack[i-half:i+half+1,
                      j-half:j+half+1, :]
        sus_map[i,j] = model.predict(
            patch.reshape(1, PATCH_SIZE, PATCH_SIZE, bands)
        )[0][0]

profile.update(dtype=rasterio.float32, count=1)

with rasterio.open(os.path.join(OUTPUT_FOLDER,
             "susceptibility_probability.tif"), "w", **profile) as dst:
    dst.write(sus_map.astype(np.float32), 1)

# ============================================================
# 5 CLASS MAP
# ============================================================

bins = [0,0.2,0.4,0.6,0.8,1.0]
five_class = np.digitize(sus_map, bins)

with rasterio.open(os.path.join(OUTPUT_FOLDER,
             "susceptibility_5class.tif"), "w", **profile) as dst:
    dst.write(five_class.astype(np.uint8), 1)

# ============================================================
# FLOWCHART
# ============================================================

dot = Digraph()

dot.node("A","Raster Factors")
dot.node("B","Excel Inventory")
dot.node("C","Patch Extraction")
dot.node("D","CNN Training")
dot.node("E","Validation")
dot.node("F","Susceptibility Map")

dot.edges([("A","C"),("B","C"),("C","D"),("D","E"),("E","F")])
dot.render(os.path.join(OUTPUT_FOLDER,"methodology_flowchart"))

# ============================================================
# SAVE MODEL
# ============================================================

model.save(os.path.join(OUTPUT_FOLDER,"cnn_model.h5"))

print("PROCESS COMPLETED SUCCESSFULLY")
