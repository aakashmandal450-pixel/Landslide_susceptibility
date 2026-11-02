import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from docx import Document  # Added import
from docx.shared import Inches # Added import

# =========================
# CONFIG
# =========================
EXCEL_PATH = r"D:\Research Landslide\Result\Jenks verification\Outputs\LSM_Raster_Validation.xlsx"
OUTPUT_DIR = r"D:\Research Landslide\Result\Jenks verification\Outputs"

# =========================
# LOAD DATA
# =========================
df = pd.read_excel(EXCEL_PATH)
print("Loaded data:")
print(df.to_string())

# =========================
# PLOT SETTINGS
# =========================
GRID_MODELS = ["Grid_3x3", "Grid_15x15", "Grid_25x25"]
SU_MODELS   = ["SlopeUnit_3x3", "SlopeUnit_15x15", "SlopeUnit_25x25"]

STYLE_MAP = {
    "3x3":   {"color": "#E74C3C", "ls": "--",  "marker": "o"},
    "15x15": {"color": "#2E86AB", "ls": "-",   "marker": "s"},
    "25x25": {"color": "#27AE60", "ls": "-.",  "marker": "^"},
}

def get_style(name):
    for key in STYLE_MAP:
        if key in name:
            return STYLE_MAP[key]
    return {"color": "grey", "ls": "-", "marker": "o"}

def compute_curve(df, layer_name):
    sub = df[df["Layer"] == layer_name].sort_values("Class", ascending=False)
    cum_area = np.cumsum(sub["Area (%)"].values)
    cum_ls   = np.cumsum(sub["LS (%)"].values)
    cum_area = np.insert(cum_area, 0, 0)
    cum_ls   = np.insert(cum_ls,   0, 0)
    return cum_area, cum_ls

DR_OFFSETS = {
    "Grid_3x3": (5, -10),
    "Grid_15x15": (4, 2),
    "Grid_25x25": (3, -15),
    "SlopeUnit_3x3": (2, -6),
    "SlopeUnit_15x15": (2, -6),
    "SlopeUnit_25x25": (2, -6),
}

# =========================
# FIGURE
# =========================
fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)
fig.subplots_adjust(wspace=0.08)

panel_titles = ["(a) Grid-Based Models", "(b) Slope Unit Models"]
model_groups = [GRID_MODELS, SU_MODELS]

for ax, models, title in zip(axes, model_groups, panel_titles):
    ax.plot([0, 100], [0, 100], color="black", lw=1.2, ls=":", label="Random (DR = 1)", zorder=1)
    for layer in models:
        style = get_style(layer)
        cum_area, cum_ls = compute_curve(df, layer)
        kernel = [k for k in ["3×3", "15×15", "25×25"] if k.replace("×", "x") in layer or k in layer]
        label = kernel[0] if kernel else layer
        ax.plot(cum_area, cum_ls, color=style["color"], ls=style["ls"], lw=2.0, marker=style["marker"], markersize=6, markevery=1, label=f"{label} kernel", zorder=3)
        vh_row = df[(df["Layer"] == layer) & (df["Class"] == 5)]
        if not vh_row.empty:
            dr_val = vh_row["DR"].values[0]
            dx, dy = DR_OFFSETS.get(layer, (2, -6))
            ax.annotate(f"DR={dr_val:.2f}", xy=(cum_area[1], cum_ls[1]), xytext=(cum_area[1] + dx, cum_ls[1] + dy), fontsize=8, color=style["color"], arrowprops=dict(arrowstyle="-", color=style["color"], lw=0.8))

    best_layer = models[1]
    ca, cl = compute_curve(df, best_layer)
    ax.fill_between(ca, ca, cl, alpha=0.07, color=get_style(best_layer)["color"])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Cumulative Area (%) — High to Low Susceptibility", fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
    ax.legend(fontsize=8.5, loc="lower right", framealpha=0.9)
    ax.grid(True, linestyle="--", alpha=0.4, lw=0.7)
    ax.xaxis.set_minor_locator(mticker.MultipleLocator(5))
    ax.yaxis.set_minor_locator(mticker.MultipleLocator(5))
    ax.tick_params(which="both", direction="in")

axes[0].set_ylabel("Cumulative Landslide Area (%)", fontsize=10)
fig.suptitle("Success Rate Curves: Cumulative Landslide Area vs. Susceptibility Class Area\nKarnali Highway Corridor — Ensemble Model Validation", fontsize=11, y=1.01)
plt.tight_layout()

# =========================
# SAVE
# =========================
png_path = os.path.join(OUTPUT_DIR, "Success_Rate_Curves.png")
pdf_path = os.path.join(OUTPUT_DIR, "Success_Rate_Curves.pdf")
docx_path = os.path.join(OUTPUT_DIR, "Success_Rate_Curves.docx") # Added path

plt.savefig(png_path, dpi=300, bbox_inches="tight")
plt.savefig(pdf_path, bbox_inches="tight")

# Create Word Document
doc = Document()
doc.add_heading('Success Rate Curves', 0)
doc.add_paragraph('Karnali Highway Corridor — Ensemble Model Validation')
doc.add_picture(png_path, width=Inches(6.0))
doc.save(docx_path)

print(f"\nSaved PNG: {png_path}")
print(f"Saved PDF: {pdf_path}")
print(f"Saved DOCX: {docx_path}")

plt.show()