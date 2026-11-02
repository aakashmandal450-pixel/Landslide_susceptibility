#!/usr/bin/env python3
"""
Landslide Susceptibility Mapping — ML Analysis
================================================
Models  : Random Forest (RF), Support Vector Machine (SVM), XGBoost (XGB)
Metrics : Accuracy, Sensitivity, Specificity, Precision, F1, Kappa, AUC, CV-AUC
Outputs : Metrics table, Confusion matrices, ROC curves,
          Feature importance, Susceptibility score CSV (for QGIS map)

INPUT   : slope_units_ml_ready.csv
           - One row per slope unit polygon
           - Feature columns + 'label' column (1=landslide, 0=non-landslide)

Run in VS Code:
  pip install pandas numpy scikit-learn xgboost matplotlib seaborn imbalanced-learn openpyxl
  python ml_landslide.py
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score,
    precision_score, roc_auc_score, roc_curve,
    cohen_kappa_score, classification_report
)
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE

warnings.filterwarnings('ignore')

# =============================================================
# CONFIGURATION
# =============================================================

CSV_PATH   = r"D:\Research Landslide\Result\New_output\Slopeunits\Excel_file_SU\slope_units_ml_ready.csv"
OUTPUT_DIR = r"D:\Research Landslide\Result\New_output\Slopeunits\Excel_file_SU\ML_output"

# Columns to drop before training (IDs, coordinates, internal GRASS fields)
DROP_COLS  = ['cat', 'cat_', 'cat_1', 'fid', 'id', 'x_coor', 'y_coor',
              'x', 'y', 'area_val', 'value', 'label_', 'slope_units']

# Feature columns — will be auto-detected after dropping DROP_COLS and 'label'
# These match your raster stats from v.rast.stats
# Expected: aspect, curvature, dis_to_fault, dis_to_river, dis_to_thrust,
#           dis_to_road, ndvi, ndwi, roughness, slope, twi
# (plus any _average / _stddev suffixes if v.rast.stats added them)

RANDOM_STATE = 42
CV_FOLDS     = 5
TEST_SIZE    = 0.30   # 70% train / 30% test (matches paper)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =============================================================
# 1. LOAD DATA
# =============================================================

print("\n" + "="*65)
print("  Landslide Susceptibility — RF / SVM / XGBoost")
print("="*65)

print("\n[1] Loading data...")
df = pd.read_csv(CSV_PATH)
print(f"    Shape: {df.shape}")
print(f"    Columns: {list(df.columns)}")

# Drop unwanted columns
drop_actual = [c for c in DROP_COLS if c in df.columns]
df.drop(columns=drop_actual, inplace=True)

# Separate features and target
if 'label' not in df.columns:
    raise ValueError("'label' column not found. Run build_ml_dataset.py first.")

y = df['label'].astype(int)
X = df.drop(columns=['label'])

# Auto-drop any column that looks like an internal ID
# (name starts with 'cat', or every value is unique = pure ID sequence)
id_like = [c for c in X.columns
           if c.lower().startswith('cat')
           or X[c].nunique() == len(X)]
if id_like:
    print(f"    Auto-dropping ID-like columns: {id_like}")
    X.drop(columns=id_like, inplace=True, errors='ignore')

# Drop any remaining non-numeric columns
non_numeric = X.select_dtypes(exclude=[np.number]).columns.tolist()
if non_numeric:
    print(f"    Dropping non-numeric columns: {non_numeric}")
    X.drop(columns=non_numeric, inplace=True)

# Drop columns with all NaN
X.dropna(axis=1, how='all', inplace=True)

# Fill remaining NaN with column median
X.fillna(X.median(), inplace=True)

FEATURE_NAMES = list(X.columns)
print(f"    Features ({len(FEATURE_NAMES)}): {FEATURE_NAMES}")
print(f"    Label distribution — 1: {y.sum()} ({y.mean()*100:.1f}%)  "
      f"0: {(y==0).sum()} ({(y==0).mean()*100:.1f}%)")

# =============================================================
# 2. TRAIN / TEST SPLIT (stratified, matches paper 70/30)
# =============================================================

print("\n[2] Splitting data (70% train / 30% test, stratified)...")
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y)

print(f"    Train: {len(X_train)}  Test: {len(X_test)}")
print(f"    Train label=1: {y_train.sum()}  Test label=1: {y_test.sum()}")

# =============================================================
# 3. HANDLE CLASS IMBALANCE WITH SMOTE (on train set only)
# =============================================================

print("\n[3] Applying SMOTE to training set...")
smote = SMOTE(random_state=RANDOM_STATE)
X_train_sm, y_train_sm = smote.fit_resample(X_train, y_train)
print(f"    After SMOTE — label=1: {y_train_sm.sum()}  "
      f"label=0: {(y_train_sm==0).sum()}")

# =============================================================
# 4. DEFINE MODELS
# =============================================================

models = {
    'RF': RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features='sqrt',
        class_weight='balanced',
        random_state=RANDOM_STATE,
        n_jobs=-1
    ),
    'SVM': Pipeline([
        ('scaler', StandardScaler()),
        ('svc',    SVC(
            kernel='rbf',
            C=10,
            gamma='scale',
            probability=True,
            class_weight='balanced',
            random_state=RANDOM_STATE
        ))
    ]),
    'XGB': XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric='logloss',
        random_state=RANDOM_STATE,
        n_jobs=-1
    )
}

# =============================================================
# 5. TRAIN, EVALUATE, COLLECT METRICS
# =============================================================

def compute_metrics(y_true, y_pred, y_prob):
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    accuracy    = accuracy_score(y_true, y_pred)
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0   # recall
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    precision   = precision_score(y_true, y_pred, zero_division=0)
    f1          = f1_score(y_true, y_pred, zero_division=0)
    kappa       = cohen_kappa_score(y_true, y_pred)
    auc         = roc_auc_score(y_true, y_prob)
    return {
        'Accuracy':    round(accuracy,    4),
        'Sensitivity': round(sensitivity, 4),
        'Specificity': round(specificity, 4),
        'Precision':   round(precision,   4),
        'F1':          round(f1,          4),
        'Kappa':       round(kappa,       4),
        'AUC':         round(auc,         4),
    }, cm

print("\n[4] Training and evaluating models...")
print("-"*65)

results   = {}
cms       = {}
probs_all = {}
cv_aucs   = {}

skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)

for name, model in models.items():
    print(f"\n  [{name}]")

    # Train on SMOTE-balanced training set
    model.fit(X_train_sm, y_train_sm)

    # Predict on held-out test set
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    metrics, cm = compute_metrics(y_test, y_pred, y_prob)
    results[name]   = metrics
    cms[name]       = cm
    probs_all[name] = y_prob

    # Cross-validated AUC (on original train set, no SMOTE leak)
    cv_prob = cross_val_predict(model, X_train, y_train,
                                cv=skf, method='predict_proba', n_jobs=-1)[:, 1]
    cv_auc  = roc_auc_score(y_train, cv_prob)
    cv_aucs[name] = round(cv_auc, 4)
    metrics['CV_AUC'] = cv_aucs[name]

    print(f"    Accuracy    : {metrics['Accuracy']}")
    print(f"    Sensitivity : {metrics['Sensitivity']}")
    print(f"    Specificity : {metrics['Specificity']}")
    print(f"    Precision   : {metrics['Precision']}")
    print(f"    F1          : {metrics['F1']}")
    print(f"    Kappa       : {metrics['Kappa']}")
    print(f"    AUC         : {metrics['AUC']}")
    print(f"    CV-AUC ({CV_FOLDS}-fold): {metrics['CV_AUC']}")

# =============================================================
# 6. METRICS TABLE
# =============================================================

print("\n[5] Saving metrics table...")
metrics_df = pd.DataFrame(results).T
metrics_df.index.name = 'Model'
metrics_df = metrics_df[['Accuracy','Sensitivity','Specificity',
                          'Precision','F1','Kappa','AUC','CV_AUC']]
metrics_df.to_csv(os.path.join(OUTPUT_DIR, 'metrics_table.csv'))
print(metrics_df.to_string())

# =============================================================
# 7. FIGURE — Confusion Matrices (3 side by side)
# =============================================================

print("\n[6] Plotting confusion matrices...")

fig, axes = plt.subplots(1, 3, figsize=(13, 4))
fig.suptitle('Confusion Matrices — RF, SVM, XGBoost', fontsize=13, y=1.02)

for ax, (name, cm) in zip(axes, cms.items()):
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                xticklabels=['Non-LS', 'Landslide'],
                yticklabels=['Non-LS', 'Landslide'],
                linewidths=0.5, linecolor='gray',
                annot_kws={'size': 13, 'weight': 'bold'})
    ax.set_title(f'{name}', fontsize=12, fontweight='bold')
    ax.set_xlabel('Predicted', fontsize=10)
    ax.set_ylabel('Actual', fontsize=10)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'confusion_matrices.png'),
            dpi=180, bbox_inches='tight')
plt.close()
print("    Saved: confusion_matrices.png")

# =============================================================
# 8. FIGURE — ROC Curves (all 3 on one plot)
# =============================================================

print("\n[7] Plotting ROC curves...")

fig, ax = plt.subplots(figsize=(6, 6))
colors = {'RF': '#1f77b4', 'SVM': '#d62728', 'XGB': '#2ca02c'}
linestyles = {'RF': '-', 'SVM': '--', 'XGB': '-.'}

for name, y_prob in probs_all.items():
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    auc_val = results[name]['AUC']
    ax.plot(fpr, tpr,
            color=colors[name],
            linestyle=linestyles[name],
            linewidth=2,
            label=f'{name}  AUC = {auc_val:.3f}')

ax.plot([0,1],[0,1], 'k--', linewidth=1, label='Random (AUC = 0.500)')
ax.set_xlabel('1 - Specificity  (False Positive Rate)', fontsize=11)
ax.set_ylabel('Sensitivity  (True Positive Rate)', fontsize=11)
ax.set_title('ROC Curves — RF, SVM, XGBoost', fontsize=12)
ax.legend(fontsize=10, loc='lower right')
ax.set_xlim([0, 1])
ax.set_ylim([0, 1.02])
ax.grid(True, linestyle='--', alpha=0.4)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'roc_curves.png'),
            dpi=180, bbox_inches='tight')
plt.close()
print("    Saved: roc_curves.png")

# =============================================================
# 9. FIGURE — Feature Importance (RF + XGB; SVM uses permutation)
# =============================================================

print("\n[8] Plotting feature importance...")

fig, axes = plt.subplots(1, 3, figsize=(16, 6))
fig.suptitle('Feature Importance', fontsize=13)

# ── RF importance ──────────────────────────────────────────────────────────
rf_model = models['RF']
rf_imp   = pd.Series(rf_model.feature_importances_, index=FEATURE_NAMES)
rf_imp   = rf_imp.sort_values(ascending=True)
axes[0].barh(rf_imp.index, rf_imp.values, color='#1f77b4', alpha=0.85)
axes[0].set_title('Random Forest', fontsize=11, fontweight='bold')
axes[0].set_xlabel('Importance (Gini)', fontsize=10)
axes[0].spines['top'].set_visible(False)
axes[0].spines['right'].set_visible(False)

# ── SVM — permutation importance ──────────────────────────────────────────
from sklearn.inspection import permutation_importance
print("    Computing SVM permutation importance (this may take a minute)...")
svm_perm = permutation_importance(models['SVM'], X_test, y_test,
                                  n_repeats=10, random_state=RANDOM_STATE,
                                  scoring='roc_auc', n_jobs=-1)
svm_imp = pd.Series(svm_perm.importances_mean, index=FEATURE_NAMES)
svm_imp = svm_imp.sort_values(ascending=True)
axes[1].barh(svm_imp.index, svm_imp.values, color='#d62728', alpha=0.85)
axes[1].set_title('SVM (Permutation)', fontsize=11, fontweight='bold')
axes[1].set_xlabel('Importance (AUC drop)', fontsize=10)
axes[1].spines['top'].set_visible(False)
axes[1].spines['right'].set_visible(False)

# ── XGB importance ─────────────────────────────────────────────────────────
xgb_model = models['XGB']
xgb_imp   = pd.Series(xgb_model.feature_importances_, index=FEATURE_NAMES)
xgb_imp   = xgb_imp.sort_values(ascending=True)
axes[2].barh(xgb_imp.index, xgb_imp.values, color='#2ca02c', alpha=0.85)
axes[2].set_title('XGBoost', fontsize=11, fontweight='bold')
axes[2].set_xlabel('Importance (Gain)', fontsize=10)
axes[2].spines['top'].set_visible(False)
axes[2].spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'feature_importance.png'),
            dpi=180, bbox_inches='tight')
plt.close()
print("    Saved: feature_importance.png")

# =============================================================
# 10. FIGURE 9 STYLE — Metrics bar chart (AUC + F1 + Kappa per model)
# =============================================================

print("\n[9] Plotting Figure 9 style metrics chart...")

metric_labels = ['Accuracy', 'Sensitivity', 'Specificity',
                 'Precision', 'F1', 'Kappa', 'AUC', 'CV_AUC']
model_names   = list(results.keys())
n_metrics     = len(metric_labels)
n_models      = len(model_names)

bar_width = 0.22
x = np.arange(n_metrics)
model_colors = ['#1f77b4', '#d62728', '#2ca02c']

fig, ax = plt.subplots(figsize=(14, 6))

for i, (name, color) in enumerate(zip(model_names, model_colors)):
    vals = [results[name][m] for m in metric_labels]
    bars = ax.bar(x + i*bar_width - bar_width, vals,
                  width=bar_width, color=color, alpha=0.85,
                  label=name, zorder=3)
    # Value labels on top of bars
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + 0.005,
                f'{v:.3f}', ha='center', va='bottom',
                fontsize=7, color='#333333')

ax.set_xticks(x)
ax.set_xticklabels(metric_labels, fontsize=10)
ax.set_ylabel('Score', fontsize=11)
ax.set_ylim(0, 1.10)
ax.set_title('Model Performance Metrics — RF, SVM, XGBoost\n'
             '(Optimal Slope Unit: a=300,000 m²  c=0.35)', fontsize=12)
ax.legend(fontsize=10)
ax.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'figure9_metrics.png'),
            dpi=180, bbox_inches='tight')
plt.close()
print("    Saved: figure9_metrics.png")

# =============================================================
# 11. SUSCEPTIBILITY SCORES — export for QGIS map (Figure 10)
# =============================================================

print("\n[10] Exporting susceptibility scores for QGIS...")

# Predict probability on ALL slope units (full dataset)
susc_df = df.drop(columns=['label']).copy()
susc_df.fillna(susc_df.median(numeric_only=True), inplace=True)

X_all = susc_df[FEATURE_NAMES]

for name, model in models.items():
    prob = model.predict_proba(X_all)[:, 1]
    df[f'susc_{name}'] = prob

# Classify into 5 susceptibility classes using quantile breaks
# duplicates='drop' handles cases where many polygons share the same
# probability (common when most are non-landslide -> score near 0)
for name in models.keys():
    col = f'susc_{name}'
    cut, bins = pd.qcut(
        df[col],
        q=[0, 0.20, 0.40, 0.60, 0.80, 1.0],
        labels=False,
        retbins=True,
        duplicates='drop'
    )
    # qcut with duplicates='drop' may return fewer than 5 bins
    # remap whatever bins we get to 1..5 evenly
    n_bins = cut.max() + 1
    df[f'class_{name}'] = (
        np.ceil((cut + 1) / n_bins * 5)
        .clip(1, 5)
        .astype(int)
    )

# Save
susc_out = os.path.join(OUTPUT_DIR, 'susceptibility_scores.csv')
df.to_csv(susc_out, index=False)
print(f"    Saved: susceptibility_scores.csv")
print(f"    Columns added: susc_RF, susc_SVM, susc_XGB, "
      f"class_RF, class_SVM, class_XGB")
print(f"    Class legend: 1=Very Low  2=Low  3=Medium  4=High  5=Very High")

# =============================================================
# 12. SAVE METRICS TO EXCEL
# =============================================================

print("\n[11] Saving full metrics to Excel...")

excel_path = os.path.join(OUTPUT_DIR, 'model_metrics.xlsx')
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    metrics_df.to_excel(writer, sheet_name='Metrics')

    # Feature importance sheet
    fi_df = pd.DataFrame({
        'RF_importance':  rf_model.feature_importances_,
        'XGB_importance': xgb_model.feature_importances_,
        'SVM_permutation_importance': svm_perm.importances_mean,
    }, index=FEATURE_NAMES).sort_values('RF_importance', ascending=False)
    fi_df.to_excel(writer, sheet_name='Feature_Importance')

print(f"    Saved: model_metrics.xlsx")

# =============================================================
# FINAL SUMMARY
# =============================================================

print("\n" + "="*65)
print("  ALL OUTPUTS SAVED TO:", OUTPUT_DIR)
print("="*65)
print("  confusion_matrices.png   — 3 confusion matrices")
print("  roc_curves.png           — ROC curves for all 3 models")
print("  feature_importance.png   — Feature importance / permutation")
print("  figure9_metrics.png      — Bar chart of all metrics")
print("  susceptibility_scores.csv— Scores + classes for QGIS")
print("  model_metrics.xlsx       — Full metrics + feature importance")
print("="*65)
print("\n  NEXT STEP FOR QGIS MAP (Figure 10):")
print("  1. Join susceptibility_scores.csv to your SU shapefile")
print("     using the 'cat' column as the join key")
print("  2. Style by class_RF / class_SVM / class_XGB")
print("     1=Very Low (green)  ->  5=Very High (red)")
print("="*65 + "\n")