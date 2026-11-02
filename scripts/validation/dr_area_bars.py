import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator

# =========================
# CONFIG
# =========================
EXCEL_PATH = r"D:\Research Landslide\Result\Jenks verification\Outputs\LSM_Raster_Validation.xlsx"
OUTPUT_DIR = r"D:\Research Landslide\Result\Jenks verification\Outputs"

# =========================
# LOAD DATA
# =========================
df = pd.read_excel(EXCEL_PATH)

CLASSES      = ["Very Low", "Low", "Moderate", "High", "Very High"]
CLASS_X      = np.arange(len(CLASSES))

MODELS       = ["Grid_3x3", "Grid_15x15", "Grid_25x25",
                "SlopeUnit_3x3", "SlopeUnit_15x15", "SlopeUnit_25x25"]
MODEL_LABELS = ["Grid 3×3", "Grid 15×15", "Grid 25×25",
                "SU 3×3", "SU 15×15", "SU 25×25"]

# Colour palette — grid models in blue family, slope unit in green family
MODEL_COLORS = {
    "Grid_3x3":        "#AED6F1",
    "Grid_15x15":      "#2E86AB",
    "Grid_25x25":      "#1A5276",
    "SlopeUnit_3x3":   "#A9DFBF",
    "SlopeUnit_15x15": "#27AE60",
    "SlopeUnit_25x25": "#1E8449",
}

N_MODELS  = len(MODELS)
BAR_WIDTH = 0.13
OFFSETS   = np.linspace(-(N_MODELS - 1) / 2 * BAR_WIDTH,
                         (N_MODELS - 1) / 2 * BAR_WIDTH,
                         N_MODELS)

# =========================
# EXTRACT VALUES
# =========================
def get_values(col):
    """Return dict: model -> array of 5 class values (Very Low … Very High)."""
    out = {}
    for m in MODELS:
        sub = df[df["Layer"] == m].sort_values("Class")
        out[m] = sub[col].values
    return out

dr_vals   = get_values("DR")
area_vals = get_values("Area (%)")
ls_vals   = get_values("LS (%)")

# ===========================================================
# FIGURE 1 — Density Ratio Bar Chart
# ===========================================================
fig1, ax1 = plt.subplots(figsize=(9, 6))

for i, (m, label) in enumerate(zip(MODELS, MODEL_LABELS)):
    bars = ax1.bar(CLASS_X + OFFSETS[i], dr_vals[m],
                   width=BAR_WIDTH, color=MODEL_COLORS[m],
                   edgecolor="white", linewidth=0.5,
                   label=label, zorder=3)
    for bar in bars:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2, h,
                 f"{h:.1f}", ha="center", va="bottom",
                 fontsize=5.5, fontweight="bold", rotation=90, zorder=5)

# Reference line DR = 1
ax1.axhline(1.0, color="black", lw=1.4, ls="--", zorder=4, label="DR = 1 (random)")

# Shade above DR=1 green, below red
ax1.axhspan(1, ax1.get_ylim()[1] if ax1.get_ylim()[1] > 1 else 4.5,
            alpha=0.04, color="#27AE60")
ax1.axhspan(0, 1, alpha=0.04, color="#E74C3C")

ax1.set_xticks(CLASS_X)
ax1.set_xticklabels(CLASSES, fontsize=9.5)
ax1.set_ylabel("Density Ratio (DR = LS% / Area%)", fontsize=10)
ax1.set_title("Density Ratio per Susceptibility Class", fontsize=11,
              fontweight="bold", pad=10)
ax1.set_ylim(0, max(max(v) for v in dr_vals.values()) * 1.25)
ax1.yaxis.set_minor_locator(MultipleLocator(0.25))
ax1.grid(axis="y", linestyle="--", alpha=0.4, lw=0.7, zorder=0)
ax1.tick_params(which="both", direction="in")

# Legend — split grid vs slope unit
grid_patches = [mpatches.Patch(color=MODEL_COLORS[m], label=l)
                for m, l in zip(MODELS[:3], MODEL_LABELS[:3])]
su_patches   = [mpatches.Patch(color=MODEL_COLORS[m], label=l)
                for m, l in zip(MODELS[3:], MODEL_LABELS[3:])]
ref_line     = Line2D([0], [0], color="black", lw=1.4, ls="--", label="DR = 1")

ax1.legend(handles=grid_patches + su_patches + [ref_line],
           fontsize=8, ncol=2, loc="upper left",
           framealpha=0.9, title="Model", title_fontsize=8.5)

fig1.tight_layout()

png1 = os.path.join(OUTPUT_DIR, "DR_Comparison.png")
pdf1 = os.path.join(OUTPUT_DIR, "DR_Comparison.pdf")
fig1.savefig(png1, dpi=300, bbox_inches="tight")
fig1.savefig(pdf1,           bbox_inches="tight")
print(f"Saved PNG: {png1}")
print(f"Saved PDF: {pdf1}")

# ===========================================================
# FIGURE 2 — LS% vs Area% Grouped Bar Chart
# ===========================================================
fig2, ax2 = plt.subplots(figsize=(9, 6))

# For figure 2: two bars per model per class (Area% and LS%)
# Re-group: x = classes, within each class group models side by side
# Each model gets 2 sub-bars (area, ls) with a small gap between them

PAIR_WIDTH  = 0.06
PAIR_GAP    = 0.005
GROUP_WIDTH = N_MODELS * (2 * PAIR_WIDTH + PAIR_GAP) + 0.04
GROUP_OFFSETS = np.linspace(-(N_MODELS - 1) / 2 * (2 * PAIR_WIDTH + PAIR_GAP + 0.01),
                              (N_MODELS - 1) / 2 * (2 * PAIR_WIDTH + PAIR_GAP + 0.01),
                              N_MODELS)

for i, (m, label) in enumerate(zip(MODELS, MODEL_LABELS)):
    base_x = CLASS_X + GROUP_OFFSETS[i]
    color  = MODEL_COLORS[m]

    # Area% bar (lighter shade)
    bars_area = ax2.bar(base_x - PAIR_WIDTH / 2, area_vals[m],
                        width=PAIR_WIDTH, color=color, alpha=0.45,
                        edgecolor="white", linewidth=0.4, zorder=3)
    for bar in bars_area:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, h,
                 f"{h:.1f}", ha="center", va="bottom",
                 fontsize=5, fontweight="bold", rotation=90, zorder=5)

    # LS% bar (full colour)
    bars_ls = ax2.bar(base_x + PAIR_WIDTH / 2, ls_vals[m],
                      width=PAIR_WIDTH, color=color, alpha=1.0,
                      edgecolor="white", linewidth=0.4, zorder=3)
    for bar in bars_ls:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, h,
                 f"{h:.1f}", ha="center", va="bottom",
                 fontsize=5, fontweight="bold", rotation=90, zorder=5)

ax2.set_xticks(CLASS_X)
ax2.set_xticklabels(CLASSES, fontsize=9.5)
ax2.set_ylabel("Percentage of Total (%)", fontsize=10)
ax2.set_title("Landslide Area % vs. Class Area % per Model", fontsize=11,
              fontweight="bold", pad=10)
ax2.set_ylim(0, max(max(max(area_vals[m]), max(ls_vals[m])) for m in MODELS) * 1.25)
ax2.yaxis.set_minor_locator(MultipleLocator(5))
ax2.grid(axis="y", linestyle="--", alpha=0.4, lw=0.7, zorder=0)
ax2.tick_params(which="both", direction="in")

# Legend for figure 2
color_patches = [mpatches.Patch(color=MODEL_COLORS[m], label=l)
                 for m, l in zip(MODELS, MODEL_LABELS)]
area_patch = mpatches.Patch(color="grey", alpha=0.45, label="Area %  (light)")
ls_patch   = mpatches.Patch(color="grey", alpha=1.0,  label="LS Area % (solid)")

ax2.legend(handles=color_patches + [area_patch, ls_patch],
           fontsize=8, ncol=2, loc="upper left",
           framealpha=0.9, title="Model / Bar Type", title_fontsize=8.5)

fig2.tight_layout()

png2 = os.path.join(OUTPUT_DIR, "Area_LS_Comparison.png")
pdf2 = os.path.join(OUTPUT_DIR, "Area_LS_Comparison.pdf")
fig2.savefig(png2, dpi=300, bbox_inches="tight")
fig2.savefig(pdf2,           bbox_inches="tight")
print(f"Saved PNG: {png2}")
print(f"Saved PDF: {pdf2}")

plt.show()