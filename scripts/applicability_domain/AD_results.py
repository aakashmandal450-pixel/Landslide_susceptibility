"""
Applicability Domain Validation — 4-Panel Figure (Updated)
Generates a publication-quality figure for both Grid and Slope Unit pipelines
Output: PNG at 300 DPI saved to D:\\Research Landslide\\Result

CHANGES IN THIS VERSION:
- Panel (a): value labels added above every bar; legend moved to empty
  headroom band above the bars (axis extended to create that space)
- Panel (b): value labels added above every bar; legend moved to empty
  headroom band above the bars (axis extended to create that space)
- Panel (c): UNCHANGED
- Panel (d): value labels added above every bar (black text, above bar
  tops instead of inside); legend moved below the plot into the
  figure's empty whitespace
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# ─────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────
grid_path  = r"D:\Research Landslide\Result\Applicability Domain\Applicability Domain Grid\AD_validation_results.csv"
slope_path = r"D:\Research Landslide\Result\Applicability Domain\Applicability Domain Slopeunit\AD_validation_slopeunit_results.csv"
output_dir = r"D:\Research Landslide\Result"
output_png = os.path.join(output_dir, "AD_validation_figure.png")

grid_df  = pd.read_csv(grid_path).set_index("Resolution").T
slope_df = pd.read_csv(slope_path).set_index("Resolution").T

# Resolutions as labels
resolutions = ["3×3", "15×15", "25×25"]
x = np.arange(len(resolutions))
width = 0.2  # bar width

# ─────────────────────────────────────────────
# 2. COLOUR PALETTE — Elsevier-friendly
# ─────────────────────────────────────────────
GRID_TRUSTED    = "#4A90C4"   # medium blue
GRID_UNTRUSTED  = "#1A4F72"   # dark blue
SLOPE_TRUSTED   = "#F5A623"   # medium orange
SLOPE_UNTRUSTED = "#8B5E00"   # dark orange
REF_LINE        = "#E74C3C"   # red reference line

plt.rcParams.update({
    "font.family"      : "DejaVu Sans",
    "axes.spines.top"  : False,
    "axes.spines.right": False,
    "axes.grid"        : True,
    "grid.alpha"       : 0.3,
    "grid.linestyle"   : "--",
    "axes.labelsize"   : 10,
    "axes.titlesize"   : 11,
    "xtick.labelsize"  : 9,
    "ytick.labelsize"  : 9,
    "legend.fontsize"  : 8,
})

fig, axes = plt.subplots(2, 2, figsize=(14, 11))
fig.suptitle(
    "Applicability Domain Validation — Grid Units vs Slope Units",
    fontsize=13, fontweight="bold", y=0.985
)

# Helper to add value labels above bars
def add_value_labels(ax, bars, fmt="{:.2f}", offset_frac=0.01, color="black"):
    y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
    for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + y_range * offset_frac,
            fmt.format(h),
            ha="center", va="bottom",
            fontsize=7.5, fontweight="bold", color=color
        )

# ─────────────────────────────────────────────
# PANEL 1 — Trusted vs Untrusted Coverage
# ─────────────────────────────────────────────
ax1 = axes[0, 0]

# Extend y-limit to create empty headroom band for the legend
ax1.set_ylim(0, 128)

b1 = ax1.bar(x - 1.5*width, grid_df["Trusted_Coverage_pct"],  width, label="Grid — Trusted",    color=GRID_TRUSTED,    edgecolor="white")
b2 = ax1.bar(x - 0.5*width, grid_df["Untrusted_Coverage_pct"],width, label="Grid — Untrusted",  color=GRID_UNTRUSTED,  edgecolor="white")
b3 = ax1.bar(x + 0.5*width, slope_df["Trusted_Coverage_pct"], width, label="Slope — Trusted",   color=SLOPE_TRUSTED,   edgecolor="white")
b4 = ax1.bar(x + 1.5*width, slope_df["Untrusted_Coverage_pct"],width,label="Slope — Untrusted", color=SLOPE_UNTRUSTED, edgecolor="white")

for bars in [b1, b2, b3, b4]:
    add_value_labels(ax1, bars, fmt="{:.2f}%")

ax1.set_title("(a) Trusted vs Untrusted Coverage (%)", fontweight="bold")
ax1.set_ylabel("Coverage (%)")
ax1.set_xticks(x)
ax1.set_xticklabels(resolutions)
ax1.set_xlabel("Kernel Resolution")

# Legend placed in the empty headroom band created above (100-128)
ax1.legend(loc="upper center", ncol=4, framealpha=0.9)

# Add a faint horizontal line at 100% to visually separate data from legend band
ax1.axhline(y=100, color="grey", linewidth=0.6, linestyle=":", alpha=0.5)

# ─────────────────────────────────────────────
# PANEL 2 — Mahalanobis Distance Trusted vs Untrusted
# ─────────────────────────────────────────────
ax2 = axes[0, 1]

b5 = ax2.bar(x - 1.5*width, grid_df["Mean_Mahal_Dist_Trusted"],   width, label="Grid — Trusted",    color=GRID_TRUSTED,    edgecolor="white")
b6 = ax2.bar(x - 0.5*width, grid_df["Mean_Mahal_Dist_Untrusted"], width, label="Grid — Untrusted",  color=GRID_UNTRUSTED,  edgecolor="white")
b7 = ax2.bar(x + 0.5*width, slope_df["Mean_Mahal_Dist_Trusted"],  width, label="Slope — Trusted",   color=SLOPE_TRUSTED,   edgecolor="white")
b8 = ax2.bar(x + 1.5*width, slope_df["Mean_Mahal_Dist_Untrusted"],width, label="Slope — Untrusted", color=SLOPE_UNTRUSTED, edgecolor="white")

# Extend y-limit to create empty headroom band for the legend
max_b2 = max(
    grid_df["Mean_Mahal_Dist_Trusted"].max(),  grid_df["Mean_Mahal_Dist_Untrusted"].max(),
    slope_df["Mean_Mahal_Dist_Trusted"].max(), slope_df["Mean_Mahal_Dist_Untrusted"].max()
)
ax2.set_ylim(0, max_b2 * 1.35)

for bars in [b5, b6, b7, b8]:
    add_value_labels(ax2, bars, fmt="{:.2f}")

ax2.set_title("(b) Mean Mahalanobis Distance — Trusted vs Untrusted", fontweight="bold")
ax2.set_ylabel("Mean Mahalanobis Distance")
ax2.set_xticks(x)
ax2.set_xticklabels(resolutions)
# ax2.set_xlabel("Kernel Resolution")  # removed to avoid overlap with panel (d) title

# Legend placed in the empty headroom band created above
ax2.legend(loc="upper center", ncol=4, framealpha=0.9)

# ─────────────────────────────────────────────
# PANEL 3 — Threshold Sensitivity Curves  (UNCHANGED)
# ─────────────────────────────────────────────
ax3 = axes[1, 0]

ax3.plot(resolutions, grid_df["Trusted_Coverage_pct_thresh_0.4"],
         "o-", color=GRID_TRUSTED,   linewidth=2, markersize=7, label="Grid — 0.4")
ax3.plot(resolutions, grid_df["Trusted_Coverage_pct_thresh_0.5"],
         "s", color=GRID_TRUSTED,   linewidth=2, markersize=7, linestyle="--", label="Grid — 0.5 (used)")
ax3.plot(resolutions, grid_df["Trusted_Coverage_pct_thresh_0.6"],
         "^-", color=GRID_UNTRUSTED, linewidth=2, markersize=7, label="Grid — 0.6")

ax3.plot(resolutions, slope_df["Trusted_Coverage_pct_thresh_0.4"],
         "o", color=SLOPE_TRUSTED,   linewidth=2, markersize=7, linestyle=(0,(3,1,1,1)), label="Slope — 0.4")
ax3.plot(resolutions, slope_df["Trusted_Coverage_pct_thresh_0.5"],
         "s", color=SLOPE_TRUSTED,   linewidth=2, markersize=7, linestyle=":", label="Slope — 0.5 (used)")
ax3.plot(resolutions, slope_df["Trusted_Coverage_pct_thresh_0.6"],
         "^", color=SLOPE_UNTRUSTED, linewidth=2, markersize=7, linestyle=(0,(5,2)), label="Slope — 0.6")

ax3.set_title("(c) Threshold Sensitivity — Coverage vs Domain Score Threshold", fontweight="bold")
ax3.set_ylabel("Trusted Coverage (%)")
ax3.set_xlabel("Kernel Resolution")
ax3.set_ylim(60, 105)
ax3.legend(loc="lower left", framealpha=0.8, ncol=2, fontsize=8)

ax3.annotate("Sharp drop\nat threshold 0.6",
             xy=("25×25", 79.45), xytext=("15×15", 72),
             fontsize=8, color=GRID_UNTRUSTED,
             arrowprops=dict(arrowstyle="->", color=GRID_UNTRUSTED, lw=1.2))

# ─────────────────────────────────────────────
# PANEL 4 — Landslide Capture Rate
# ─────────────────────────────────────────────
ax4 = axes[1, 1]

b9  = ax4.bar(x - 0.5*width, grid_df["Landslide_Capture_Rate_pct"],  width*1.5,
              label="Grid Units",  color=GRID_TRUSTED,  edgecolor="white")
b10 = ax4.bar(x + 0.5*width, slope_df["Landslide_Capture_Rate_pct"], width*1.5,
              label="Slope Units", color=SLOPE_TRUSTED, edgecolor="white")

ref_line = ax4.axhline(y=100, color=REF_LINE, linewidth=1.5, linestyle="--", label="100% reference")

# Compute a sensible y-range with headroom for value labels above bars
d_min = min(grid_df["Landslide_Capture_Rate_pct"].min(), slope_df["Landslide_Capture_Rate_pct"].min())
ax4.set_ylim(d_min - 1.5, 102.2)

for bars in [b9, b10]:
    add_value_labels(ax4, bars, fmt="{:.2f}%", offset_frac=0.01, color="black")

ax4.set_title("(d) Landslide Capture Rate within Trusted Zone (%)", fontweight="bold")
ax4.set_ylabel("Capture Rate (%)")
ax4.set_xticks(x)
ax4.set_xticklabels(resolutions)
ax4.set_xlabel("Kernel Resolution")

# Legend moved BELOW the plot, into the figure's empty whitespace
ax4.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, framealpha=0.9)

# ─────────────────────────────────────────────
# FINAL LAYOUT AND SAVE
# ─────────────────────────────────────────────
plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig(output_png, dpi=300, bbox_inches="tight", facecolor="white")
plt.close()

print(f"Figure saved to: {output_png}")