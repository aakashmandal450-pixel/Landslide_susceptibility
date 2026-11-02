import pandas as pd
import numpy as np
import os
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, classification_report
import matplotlib.pyplot as plt
import seaborn as sns

# =============================================================
# 1. PATHS
# =============================================================
LS_NON_LS_PATH = r"D:\Research Landslide\Data\Filtered_Excel files\ls_non_ls_final_3x3.xlsx"
ATTR_PATH = r"D:\Research Landslide\Result\New_output\Slopeunits\Excel_file_SU\su_a300000_c0_35.xlsx"
OUT_DIR = r"D:\Research Landslide\Result\New_output\Slopeunits\Excel_file_SU"

if not os.path.exists(OUT_DIR):
    os.makedirs(OUT_DIR)

# =============================================================
# 2. DYNAMIC LOADING & MERGING
# =============================================================
print("📂 Loading files...")
df_points = pd.read_excel(LS_NON_LS_PATH)
df_attr = pd.read_excel(ATTR_PATH)

# Find the ID column in the points file (it was 'slope_units' before)
# We look for common names like 'slope_units', 'cat', 'id', 'Value'
possible_id_cols = ['slope_units', 'cat', 'id', 'ID', 'point_id', 'Value']
point_id_col = next((c for c in possible_id_cols if c in df_points.columns), df_points.columns[0])

print(f"🔗 Merging points using column: '{point_id_col}' from points file and 'cat' from attribute file...")
merged_df = pd.merge(df_points, df_attr, left_on=point_id_col, right_on='cat', how='inner')

# Identify label column (1/0)
label_col = next((c for c in merged_df.columns if c.lower() in ['label', 'class', 'landslide']), None)

if label_col is None:
    print("❌ Could not find a 'label' or 'class' column. Please check your Excel headers.")
    exit()

print(f"✅ Merge Success! Balanced Dataset Size: {len(merged_df)} rows.")

# =============================================================
# 3. TRIMMING LOGICALLY UNFEASIBLE DATA
# =============================================================
print("✂️ Trimming biased distance stats (variance/range/max/min)...")

dist_layers = ['dis_to_road', 'dis_to_river', 'dis_to_fault', 'dis_to_thrust']
biased_stats = ['variance', 'range', 'maximum', 'minimum']

to_drop = [c for c in merged_df.columns if any(l in c for l in dist_layers) 
           and any(s in c for s in biased_stats)]

# ID and spatial columns to exclude from training
ids_to_drop = [label_col, 'cat', 'cat_', 'value', 'fid', 'id', 'cat_1', 
               point_id_col, 'x_coord', 'y_coord', 'x', 'y']

X = merged_df.drop(columns=ids_to_drop + to_drop, errors='ignore')
y = merged_df[label_col]

# Infinity and NaN Fix
X = X.replace([np.inf, -np.inf], np.nan).fillna(X.mean())
X = X.clip(lower=-1e38, upper=1e38)

print(f"✅ Total features to rate: {X.shape[1]}")

# =============================================================
# 4. XGBOOST TRAINING
# =============================================================
print("🧠 Training XGBoost (Gain-based Importance)...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

model = XGBClassifier(n_estimators=100, learning_rate=0.1, max_depth=6, eval_metric='logloss', random_state=42)
model.fit(X_train_s, y_train)

# Importance Ranking
importance_df = pd.DataFrame({
    'Parameter': X.columns,
    'Score': model.feature_importances_
}).sort_values(by='Score', ascending=False)

# =============================================================
# 5. OUTPUT EXCEL & PLOT
# =============================================================
# Save Excel
out_excel = os.path.join(OUT_DIR, "Final_Balanced_Importance_Results.xlsx")
with pd.ExcelWriter(out_excel) as writer:
    importance_df.to_excel(writer, sheet_name='Feature_Ranking', index=False)
    pd.concat([X, y], axis=1).to_excel(writer, sheet_name='Cleaned_Data', index=False)

# Save Plot
plt.figure(figsize=(12, 18))
sns.barplot(data=importance_df, x='Score', y='Parameter', hue='Parameter', palette='viridis', legend=False)
plt.title("XGBoost Feature Importance: Balanced Sample", fontsize=16)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "Final_Balanced_Importance.png"), dpi=300)

# Results
y_probs = model.predict_proba(X_test_s)[:, 1]
print("-" * 30)
print(f"🚀 NEW ROC AUC SCORE: {roc_auc_score(y_test, y_probs):.4f}")
print(f"✅ Files saved to: {OUT_DIR}")