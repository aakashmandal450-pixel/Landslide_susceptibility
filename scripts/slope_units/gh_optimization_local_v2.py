"""
Slope-unit parameterization sensitivity plot (GH minimization)
-----------------------------------------------------------------
Reads the (a, c, Slope Units, V, wMI, GH, Status) grid-search table and
produces a single, larger line plot of GH vs c (one line per a), with
the chosen optimum highlighted with a star and the legend placed
outside the plot area (to the right) so it never overlaps the lines:
  1. An interactive HTML figure (Plotly)
  2. A static PNG + PDF figure (matplotlib) for the manuscript

Requirements (install once if needed):
    pip install openpyxl matplotlib plotly numpy
"""

import os
import openpyxl
import numpy as np

# ------------------------------------------------------------------
# 1. CONFIG — edit paths here if needed
# ------------------------------------------------------------------
INPUT_FILE = r"D:\Research Landslide\Result\Slopeunits\Excel_file_SU\Result\Graph to made data.xlsx"
OUTPUT_DIR = r"D:\Research Landslide\Result\Slopeunits\Excel_file_SU\Result"

OUT_HTML = os.path.join(OUTPUT_DIR, "GH_optimization_interactive.html")
OUT_PNG  = os.path.join(OUTPUT_DIR, "Figure_SU_parameterization_GH.png")
OUT_PDF  = os.path.join(OUTPUT_DIR, "Figure_SU_parameterization_GH.pdf")

# Manually set the optimal (a, c) combination chosen for the study
OPTIMAL_A = 300000
OPTIMAL_C = 0.35

# ------------------------------------------------------------------
# 2. LOAD DATA
# ------------------------------------------------------------------
if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(f"Input file not found:\n  {INPUT_FILE}")

wb = openpyxl.load_workbook(INPUT_FILE, data_only=True)
ws = wb.active  # first/active sheet

rows = list(ws.iter_rows(values_only=True))
header = [str(h).strip() for h in rows[0]]
data_rows = rows[1:]

# Find column indices by header name (robust to column order)
def col_index(name_options):
    for i, h in enumerate(header):
        if h.lower() in [n.lower() for n in name_options]:
            return i
    raise ValueError(f"Could not find a column matching any of {name_options} "
                      f"in header: {header}")

idx_a   = col_index(["a (m\u00b2)", "a (m2)", "a"])
idx_c   = col_index(["c"])
idx_gh  = col_index(["gh"])

records = []
for r in data_rows:
    if r[idx_a] is None or r[idx_c] is None or r[idx_gh] is None:
        continue
    records.append({
        "a": r[idx_a],
        "c": float(r[idx_c]),
        "gh": float(r[idx_gh]),
    })

a_vals = sorted(set(rec["a"] for rec in records))
c_vals = sorted(set(rec["c"] for rec in records))

lookup = {(rec["a"], rec["c"]): rec["gh"] for rec in records}

if (OPTIMAL_A, OPTIMAL_C) not in lookup:
    raise ValueError(f"Optimal combination a={OPTIMAL_A}, c={OPTIMAL_C} "
                      f"not found in the data.")
opt_gh = lookup[(OPTIMAL_A, OPTIMAL_C)]

print(f"Loaded {len(records)} rows.")
print(f"a values: {a_vals}")
print(f"c values: {c_vals}")
print(f"Optimum: a={OPTIMAL_A}, c={OPTIMAL_C}, GH={opt_gh:.6f}")

# ------------------------------------------------------------------
# 3. INTERACTIVE HTML FIGURE (Plotly)
# ------------------------------------------------------------------
import plotly.graph_objects as go

fig = go.Figure()

viridis_colors = [
    "#440154", "#3b528b", "#21918c", "#5ec962", "#fde725", "#a0da39"
]
for i, a in enumerate(a_vals):
    gh_vals = [lookup[(a, c)] for c in c_vals]
    fig.add_trace(
        go.Scatter(
            x=c_vals, y=gh_vals,
            mode="lines+markers",
            name=f"a = {a:,}",
            line=dict(color=viridis_colors[i % len(viridis_colors)], width=3),
            marker=dict(size=9),
        )
    )

# highlight optimum
fig.add_trace(
    go.Scatter(
        x=[OPTIMAL_C], y=[opt_gh],
        mode="markers",
        marker=dict(symbol="star", size=24, color="#E24B4A",
                     line=dict(color="white", width=1.5)),
        name=f"Optimum (a={OPTIMAL_A:,}, c={OPTIMAL_C})",
        hovertemplate=f"Optimum<br>GH={opt_gh:.6f}<extra></extra>",
    )
)

fig.update_xaxes(title_text="c", title_font=dict(size=18), tickfont=dict(size=14))
fig.update_yaxes(title_text="Global Heterogeneity (GH)", title_font=dict(size=18), tickfont=dict(size=14))

fig.update_layout(
    title=dict(
        text="Slope-unit parameterization sensitivity: minimization of Global Heterogeneity (GH)",
        x=0.5, xanchor="center", font=dict(size=20)
    ),
    height=700,
    width=1400,
    legend=dict(font=dict(size=14), x=1.02, y=0.5, xanchor="left", yanchor="middle"),
    margin=dict(t=90, r=180, l=80, b=70),
    font=dict(size=14),
)

fig.write_html(OUT_HTML, include_plotlyjs="cdn")
print(f"Saved interactive HTML: {OUT_HTML}")

# ------------------------------------------------------------------
# 4. STATIC FIGURE FOR THE MANUSCRIPT (matplotlib, PNG + PDF)
# ------------------------------------------------------------------
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.size": 13,
    "font.family": "sans-serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

fig2, ax = plt.subplots(figsize=(11, 7))

cmap = plt.get_cmap("viridis")
colors = [cmap(i / (len(a_vals) - 1)) for i in range(len(a_vals))]
for i, a in enumerate(a_vals):
    gh_vals = [lookup[(a, c)] for c in c_vals]
    ax.plot(c_vals, gh_vals, marker="o", markersize=7, linewidth=2.2,
            color=colors[i], label=f"a = {a:,}")

ax.scatter([OPTIMAL_C], [opt_gh], marker="*", s=500, facecolor="#E24B4A",
           edgecolor="white", linewidth=1.2, zorder=5,
           label=f"Optimum (a={OPTIMAL_A:,}, c={OPTIMAL_C})")

ax.set_xlabel("c", fontsize=15)
ax.set_ylabel("Global Heterogeneity (GH)", fontsize=15)
ax.set_title("Slope-unit parameterization sensitivity: minimization of Global Heterogeneity (GH)",
              fontsize=15, pad=15)
ax.axhline(1.0, color="grey", linewidth=0.8, linestyle=":")
ax.tick_params(axis="both", labelsize=12)

# Legend placed outside the plot area, to the right, so it never
# overlaps the data lines
ax.legend(fontsize=12, frameon=False, loc="center left", bbox_to_anchor=(1.02, 0.5))

fig2.tight_layout()

fig2.savefig(OUT_PNG, dpi=300, bbox_inches="tight")
fig2.savefig(OUT_PDF, bbox_inches="tight")
print(f"Saved static figure: {OUT_PNG}")
print(f"Saved static figure: {OUT_PDF}")