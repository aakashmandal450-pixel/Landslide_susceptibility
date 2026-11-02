import pandas as pd
import matplotlib.pyplot as plt
import os

# ====================================================
# BASE DIRECTORY
# ====================================================

BASE_DIR = r"D:\Research Landslide\Result\New_output"

FOLDERS = {
    "3x3": "result_3x3",
    "15x15": "result_15x15",
    "25x25": "result_25x25"
}

# ====================================================
# CREATE BAR CHARTS
# ====================================================

for grid, folder in FOLDERS.items():

    file_path = os.path.join(
        BASE_DIR,
        folder,
        "Model_Comparison_metrices.xlsx"
    )

    df = pd.read_excel(file_path)

    # -------------------------------
    # AUC BAR CHART
    # -------------------------------

    plt.figure(figsize=(7,5))
    plt.bar(df["Model"], df["AUC"])
    plt.xlabel("Machine Learning Models")
    plt.ylabel("AUC")
    plt.title(f"Model Comparison based on AUC ({grid})")
    plt.grid(axis="y", alpha=0.3)

    plt.savefig(
        os.path.join(BASE_DIR, folder, f"AUC_Comparison_{grid}.png"),
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # -------------------------------
    # ACCURACY BAR CHART
    # -------------------------------

    plt.figure(figsize=(7,5))
    plt.bar(df["Model"], df["Accuracy"])
    plt.xlabel("Machine Learning Models")
    plt.ylabel("Accuracy")
    plt.title(f"Model Comparison based on Accuracy ({grid})")
    plt.grid(axis="y", alpha=0.3)

    plt.savefig(
        os.path.join(BASE_DIR, folder, f"Accuracy_Comparison_{grid}.png"),
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

print("Bar charts successfully generated for all grid sizes.")
