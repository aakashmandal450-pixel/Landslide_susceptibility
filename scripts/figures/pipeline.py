"""
Landslide Susceptibility ML Pipeline - Methods Figure Generator (SPLIT LAYOUT v2)
Two-column boustrophedon layout, flow runs LEFT -> RIGHT:
  LEFT column (top -> bottom): Load Excel Data -> Feature Prep -> Train/Test
      Split -> Bayesian Tuning (RF/SVM/XGB fan-out) -> Probability Calibration
  Arrow bends RIGHT into Model Evaluation (same height as Probability Calibration)
  RIGHT column (bottom -> top): Model Evaluation -> Explainability ->
      Ensemble Construction -> Raster-Based Prediction -> Output Maps
  A loop-back arrow is routed ABOVE both columns (overpass), from Output Maps
  back down into Load Excel Data, with the repeat-kernel-size label sitting
  directly on top of that arrow.

Box heights are sized per-box to the actual number of text lines they hold,
so single-line boxes are noticeably smaller than three-line boxes instead of
all sharing one fixed height.

Journal / muted palette only. Exported as PNG (1200 dpi) and PDF (vector).

OUTPUT LOCATION: edit OUTPUT_DIR below for your machine.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

# ---------------------------------------------------------------------------
# OUTPUT LOCATION  --  edit this for your machine
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(r"D:\Research Landslide\Result\Diagrams")

# ---------------------------------------------------------------------------
# STAGE CONTENT
# ---------------------------------------------------------------------------
STAGE1 = dict(title="Load Excel Data",
              subtitle="Conditioning factors +\nlandslide / non-landslide labels\n(for kernel size k)")

STAGE2 = dict(title="Feature Preparation",
              subtitle="Drop NDWI, roughness, X, Y  ·  Drop NaN rows")

STAGE3 = dict(title="Stratified Train / Test Split  (80 / 20)",
              subtitle="Preserves landslide : non-landslide ratio")

TUNING_HEADER = dict(
    title="Bayesian Hyperparameter Tuning",
    subtitle="BayesSearchCV  ·  n_iter = 30  ·  scoring = F1  ·  StratifiedKFold (5-fold)"
)

TUNING_SUBS = [
    dict(title="Random Forest",
         subtitle="n_estimators · max_depth\nmin_samples_leaf/split\nclass_weight"),

    dict(title="SVM + Scaler",
         subtitle="StandardScaler\nC · gamma\nRBF kernel"),

    dict(title="XGBoost",
         subtitle="learning_rate · subsample\ncolsample_bytree\nmax_depth"),
]

STAGE5 = dict(
    title="Probability Calibration",
    subtitle="CalibratedClassifierCV  (cv = 3, sigmoid)"
)

# CORRECTION 2:
# Added spatial cross-validation AUC.
STAGE6 = dict(
    title="Model Evaluation",
    subtitle="Accuracy · Kappa · F1 · Precision · Recall · AUC\nSpatial CV AUC"
)

# CORRECTION 3:
# Added SVM to explainability.
STAGE7 = dict(
    title="Explainability",
    subtitle="Feature importance (RF & XGB)  ·  SHAP summary plots (RF, SVM & XGB)"
)

# CORRECTION 1:
# Replaced "Soft + weighted voting" with equal-weight averaging.
STAGE8 = dict(
    title="Ensemble Construction",
    subtitle="Equal-weight probability averaging\n"
             "Pensemble = (PRF + PSVM + PXGB) / 3\n"
             "Uncertainty = p(1−p)  ·  Disagreement = std(models)"
)

STAGE9 = dict(
    title="Raster-Based Prediction",
    subtitle="Predict per pixel on matched-scale rasters  →  save LSM GeoTIFF"
)

STAGE10 = dict(
    title="Output Maps",
    subtitle="Ensemble susceptibility map  +  uncertainty / disagreement maps"
)

# ---------------------------------------------------------------------------
# JOURNAL / MUTED PALETTE
# ---------------------------------------------------------------------------
JOURNAL = {
    1:             dict(face="#ECEFF1", text="#263238", edge="#B0BEC5"),
    2:             dict(face="#ECEFF1", text="#263238", edge="#B0BEC5"),
    3:             dict(face="#ECEFF1", text="#263238", edge="#B0BEC5"),

    "tune_header": dict(face="#E3F2FD", text="#0D47A1", edge="#90CAF9"),
    "tune_sub":    dict(face="#E3F2FD", text="#0D47A1", edge="#90CAF9"),

    5:             dict(face="#E3F2FD", text="#0D47A1", edge="#90CAF9"),
    6:             dict(face="#CFD8DC", text="#263238", edge="#90A4AE"),
    7:             dict(face="#CFD8DC", text="#263238", edge="#90A4AE"),
    8:             dict(face="#F4A100", text="white",   edge="#C77800"),
    9:             dict(face="#90CAF9", text="#0D47A1", edge="#5E97C9"),
    10:            dict(face="#90CAF9", text="#0D47A1", edge="#5E97C9"),
}

# ---------------------------------------------------------------------------
# PER-BOX HEIGHT, KEYED TO NUMBER OF SUBTITLE LINES
# ---------------------------------------------------------------------------
H_1LINE = 0.42
H_2LINE = 0.58
H_3LINE = 0.80

HEIGHTS = {
    1: H_3LINE,
    2: H_1LINE,
    3: H_1LINE,

    "tune_header": H_1LINE,
    "tune_sub": H_3LINE,

    5: H_1LINE,

    # Increased because these boxes now contain an additional text line.
    6: H_2LINE,
    7: H_2LINE,
    8: H_3LINE,

    9: H_1LINE,
    10: H_1LINE,
}

# ---------------------------------------------------------------------------
# DRAWING HELPERS
# ---------------------------------------------------------------------------
def draw_box(ax, cx, cy, w, h, title, subtitle, face, text_color,
             edge=None, title_fs=13.0, sub_fs=10.5):

    box = FancyBboxPatch(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="round,pad=0.0,rounding_size=0.10",
        facecolor=face,
        edgecolor=edge if edge else "none",
        linewidth=1.2 if edge else 0,
    )

    ax.add_patch(box)

    if subtitle:
        ax.text(
            cx,
            cy + h * 0.22,
            title,
            ha="center",
            va="center",
            fontsize=title_fs,
            fontweight="bold",
            color=text_color
        )

        ax.text(
            cx,
            cy - h * 0.24,
            subtitle,
            ha="center",
            va="center",
            fontsize=sub_fs,
            color=text_color,
            linespacing=1.5
        )

    else:
        ax.text(
            cx,
            cy,
            title,
            ha="center",
            va="center",
            fontsize=title_fs,
            fontweight="bold",
            color=text_color
        )


def v_arrow(ax, x, y_from, y_to, lw=1.6):
    ax.annotate(
        "",
        xy=(x, y_to),
        xytext=(x, y_from),
        arrowprops=dict(
            arrowstyle="-|>",
            color="black",
            lw=lw,
            shrinkA=0,
            shrinkB=0
        )
    )


def h_arrow(ax, y, x_from, x_to, lw=1.6):
    ax.annotate(
        "",
        xy=(x_to, y),
        xytext=(x_from, y),
        arrowprops=dict(
            arrowstyle="-|>",
            color="black",
            lw=lw,
            shrinkA=0,
            shrinkB=0
        )
    )


def hv_line(ax, x0, y0, x1, y1, lw=1.3):
    ax.plot(
        [x0, x1],
        [y0, y1],
        color="black",
        lw=lw,
        solid_capstyle="round"
    )


# ---------------------------------------------------------------------------
# FIGURE BUILDER
# ---------------------------------------------------------------------------
def build_figure(palette, out_png, out_pdf):

    # ---- key dimensions ----------------------------------------------------

    # Slightly smaller box width than original.
    W = 5.4

    GAP = 0.30
    SMALL_GAP = 0.20

    COL_GAP = 1.8
    LOOP_RISE = 0.55

    SUB_GAP = 0.16

    # Smaller tuning sub-box width while preserving their original
    # approximate center positions.
    ORIGINAL_W = 5.8

    SUB_W = (W - 2 * SUB_GAP) / 3

    # Preserve original relative positions of the three tuning boxes.
    ORIGINAL_SUB_W = (ORIGINAL_W - 2 * SUB_GAP) / 3
    SUB_CX = [
        -ORIGINAL_W / 2 + ORIGINAL_SUB_W / 2,
        0,
        ORIGINAL_W / 2 - ORIGINAL_SUB_W / 2
    ]

    H = HEIGHTS

    # ---- LEFT COLUMN: top -> bottom (flow START) ---------------------------
    x_L = 0.0
    cursor = 0.0
    centers = {}

    def place(key, h):
        nonlocal cursor
        centers[key] = cursor - h / 2
        cursor -= h

    place(1, H[1])
    cursor -= GAP

    place(2, H[2])
    cursor -= GAP

    place(3, H[3])
    cursor -= GAP

    place("tune_header", H["tune_header"])
    cursor -= SMALL_GAP

    place("tune_sub", H["tune_sub"])
    cursor -= GAP

    place(5, H[5])

    # ---- RIGHT COLUMN: bottom -> top ---------------------------------------
    # Keep RIGHT COLUMN CENTER POSITION unchanged from original code.
    x_R = ORIGINAL_W + COL_GAP

    y_bottom_right = centers[5]
    y_top_right = centers[1]

    n_right = 5
    n_right_gaps = n_right - 1

    span = y_top_right - y_bottom_right

    right_hs = [
        H[6],
        H[7],
        H[8],
        H[9],
        H[10]
    ]

    pairwise_sum = sum(
        (
            right_hs[i] / 2 +
            right_hs[i + 1] / 2
        )
        for i in range(n_right - 1)
    )

    G_right = (
        span - pairwise_sum
    ) / n_right_gaps

    right_keys = [6, 7, 8, 9, 10]

    y = y_bottom_right

    for i, key in enumerate(right_keys):

        if i == 0:
            centers[key] = y

        else:
            y = (
                y
                + right_hs[i - 1] / 2
                + G_right
                + right_hs[i] / 2
            )

            centers[key] = y

    # ---- figure / axes extent ----------------------------------------------

    TOP_MARGIN = 0.85
    BOT_MARGIN = 0.30
    SIDE_MARGIN = 0.40

    x_left_edge = (
        x_L -
        W / 2 -
        SIDE_MARGIN
    )

    x_right_edge = (
        x_R +
        W / 2 +
        SIDE_MARGIN
    )

    top_box_edge = max(
        centers[1] + H[1] / 2,
        centers[10] + H[10] / 2
    )

    y_top = (
        top_box_edge +
        LOOP_RISE +
        TOP_MARGIN
    )

    y_bot = (
        centers[5] -
        H[5] / 2 -
        BOT_MARGIN
    )

    data_w = x_right_edge - x_left_edge
    data_h = y_top - y_bot

    FIG_H = 9.5
    FIG_W = FIG_H * (data_w / data_h)

    fig, ax = plt.subplots(
        figsize=(FIG_W, FIG_H)
    )

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.set_xlim(
        x_left_edge,
        x_right_edge
    )

    ax.set_ylim(
        y_bot,
        y_top
    )

    ax.axis("off")

    # -----------------------------------------------------------------------
    # DRAW LEFT COLUMN BOXES
    # -----------------------------------------------------------------------

    p = palette

    draw_box(
        ax,
        x_L,
        centers[1],
        W,
        H[1],
        STAGE1["title"],
        STAGE1["subtitle"],
        p[1]["face"],
        p[1]["text"],
        p[1].get("edge")
    )

    draw_box(
        ax,
        x_L,
        centers[2],
        W,
        H[2],
        STAGE2["title"],
        STAGE2["subtitle"],
        p[2]["face"],
        p[2]["text"],
        p[2].get("edge")
    )

    draw_box(
        ax,
        x_L,
        centers[3],
        W,
        H[3],
        STAGE3["title"],
        STAGE3["subtitle"],
        p[3]["face"],
        p[3]["text"],
        p[3].get("edge")
    )

    draw_box(
        ax,
        x_L,
        centers["tune_header"],
        W,
        H["tune_header"],
        TUNING_HEADER["title"],
        TUNING_HEADER["subtitle"],
        p["tune_header"]["face"],
        p["tune_header"]["text"],
        p["tune_header"].get("edge"),
        title_fs=13.0,
        sub_fs=10.5
    )

    for cx, sub in zip(SUB_CX, TUNING_SUBS):

        draw_box(
            ax,
            cx,
            centers["tune_sub"],
            SUB_W,
            H["tune_sub"],
            sub["title"],
            sub["subtitle"],
            p["tune_sub"]["face"],
            p["tune_sub"]["text"],
            p["tune_sub"].get("edge"),
            title_fs=11.5,
            sub_fs=9.2
        )

    draw_box(
        ax,
        x_L,
        centers[5],
        W,
        H[5],
        STAGE5["title"],
        STAGE5["subtitle"],
        p[5]["face"],
        p[5]["text"],
        p[5].get("edge")
    )

    # -----------------------------------------------------------------------
    # DRAW RIGHT COLUMN BOXES
    # -----------------------------------------------------------------------

    draw_box(
        ax,
        x_R,
        centers[6],
        W,
        H[6],
        STAGE6["title"],
        STAGE6["subtitle"],
        p[6]["face"],
        p[6]["text"],
        p[6].get("edge")
    )

    draw_box(
        ax,
        x_R,
        centers[7],
        W,
        H[7],
        STAGE7["title"],
        STAGE7["subtitle"],
        p[7]["face"],
        p[7]["text"],
        p[7].get("edge")
    )

    draw_box(
        ax,
        x_R,
        centers[8],
        W,
        H[8],
        STAGE8["title"],
        STAGE8["subtitle"],
        p[8]["face"],
        p[8]["text"],
        p[8].get("edge")
    )

    draw_box(
        ax,
        x_R,
        centers[9],
        W,
        H[9],
        STAGE9["title"],
        STAGE9["subtitle"],
        p[9]["face"],
        p[9]["text"],
        p[9].get("edge")
    )

    draw_box(
        ax,
        x_R,
        centers[10],
        W,
        H[10],
        STAGE10["title"],
        STAGE10["subtitle"],
        p[10]["face"],
        p[10]["text"],
        p[10].get("edge")
    )

    # -----------------------------------------------------------------------
    # LEFT COLUMN ARROWS
    # -----------------------------------------------------------------------

    v_arrow(
        ax,
        x_L,
        centers[1] - H[1] / 2,
        centers[2] + H[2] / 2
    )

    v_arrow(
        ax,
        x_L,
        centers[2] - H[2] / 2,
        centers[3] + H[3] / 2
    )

    v_arrow(
        ax,
        x_L,
        centers[3] - H[3] / 2,
        centers["tune_header"] + H["tune_header"] / 2
    )

    y_fan = (
        centers["tune_header"]
        - H["tune_header"] / 2
        - SMALL_GAP / 2
    )

    hv_line(
        ax,
        x_L,
        centers["tune_header"] - H["tune_header"] / 2,
        x_L,
        y_fan
    )

    for cx in SUB_CX:

        ax.annotate(
            "",
            xy=(
                cx,
                centers["tune_sub"] + H["tune_sub"] / 2
            ),
            xytext=(
                x_L,
                y_fan
            ),
            arrowprops=dict(
                arrowstyle="-|>",
                color="black",
                lw=1.3,
                shrinkA=0,
                shrinkB=0
            )
        )

    y_merge = (
        centers["tune_sub"]
        - H["tune_sub"] / 2
        - GAP / 2
    )

    for cx in SUB_CX:

        hv_line(
            ax,
            cx,
            centers["tune_sub"] - H["tune_sub"] / 2,
            x_L,
            y_merge
        )

    v_arrow(
        ax,
        x_L,
        y_merge,
        centers[5] + H[5] / 2
    )

    # -----------------------------------------------------------------------
    # BRIDGE ARROW:
    # Probability Calibration -> Model Evaluation
    # -----------------------------------------------------------------------

    h_arrow(
        ax,
        centers[5],
        x_L + W / 2,
        x_R - W / 2
    )

    # -----------------------------------------------------------------------
    # RIGHT COLUMN ARROWS
    # -----------------------------------------------------------------------

    v_arrow(
        ax,
        x_R,
        centers[6] + H[6] / 2,
        centers[7] - H[7] / 2
    )

    v_arrow(
        ax,
        x_R,
        centers[7] + H[7] / 2,
        centers[8] - H[8] / 2
    )

    v_arrow(
        ax,
        x_R,
        centers[8] + H[8] / 2,
        centers[9] - H[9] / 2
    )

    v_arrow(
        ax,
        x_R,
        centers[9] + H[9] / 2,
        centers[10] - H[10] / 2
    )

    # -----------------------------------------------------------------------
    # OVERPASS LOOP-BACK:
    # Output Maps -> Load Excel Data
    # -----------------------------------------------------------------------

    loop_y = top_box_edge + LOOP_RISE

    hv_line(
        ax,
        x_R,
        centers[10] + H[10] / 2,
        x_R,
        loop_y
    )

    hv_line(
        ax,
        x_R,
        loop_y,
        x_L,
        loop_y
    )

    v_arrow(
        ax,
        x_L,
        loop_y,
        centers[1] + H[1] / 2
    )

    ax.text(
        (x_L + x_R) / 2,
        loop_y + 0.10,
        "repeat for next kernel size  $k$   "
        r"$k \in \{3{\times}3,\ 15{\times}15,\ 25{\times}25\}$",
        ha="center",
        va="bottom",
        fontsize=9.5,
        color="black"
    )

    # -----------------------------------------------------------------------
    # SAVE
    # -----------------------------------------------------------------------

    plt.tight_layout()

    fig.savefig(
        out_png,
        dpi=1200,
        facecolor="white",
        bbox_inches="tight"
    )

    fig.savefig(
        out_pdf,
        facecolor="white",
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"Saved: {out_png}")
    print(f"Saved: {out_pdf}")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    try:
        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        out_base = OUTPUT_DIR

    except Exception:
        out_base = Path(".")

    build_figure(
        JOURNAL,
        str(out_base / "pipeline_journal_split_LR.png"),
        str(out_base / "pipeline_journal_split_LR.pdf")
    )

    print("All done.")