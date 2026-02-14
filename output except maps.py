# ============================================================
# FULL LANDSLIDE ML PIPELINE (3x3,15x15,25x25)
# RF | SVM | XGBOOST
# ============================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    confusion_matrix, roc_auc_score, roc_curve,
    accuracy_score, precision_score, recall_score,
    f1_score, cohen_kappa_score
)
from sklearn.inspection import permutation_importance
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier

# ============================================================
# PATHS
# ============================================================

INPUT_FOLDER = r"D:\Research Landslide\Data\Filtered_Excel files"
OUTPUT_BASE = r"D:\Research Landslide\Result\New_output\New folder 1"

FILES = {
    "3x3": "ls_non_ls_final_3x3.xlsx",
    "15x15": "ls_non_ls_final_15x15.xlsx",
    "25x25": "ls_non_ls_final_25x25.xlsx"
}

os.makedirs(OUTPUT_BASE, exist_ok=True)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# ============================================================
# FUNCTIONS
# ============================================================

def compute_metrics(y_true, y_pred, y_prob):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return {
        "Accuracy": accuracy_score(y_true, y_pred),
        "Sensitivity": recall_score(y_true, y_pred),
        "Specificity": tn / (tn + fp),
        "Precision": precision_score(y_true, y_pred),
        "F1": f1_score(y_true, y_pred),
        "Kappa": cohen_kappa_score(y_true, y_pred),
        "AUC": roc_auc_score(y_true, y_prob)
    }

def save_roc(y, prob, name, folder):
    fpr, tpr, _ = roc_curve(y, prob)
    auc = roc_auc_score(y, prob)

    plt.figure(figsize=(6,6))
    plt.plot(fpr, tpr, label=f"AUC={auc:.3f}")
    plt.plot([0,1],[0,1],'--')
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig(os.path.join(folder, f"{name}_ROC.png"), dpi=300)
    plt.close()

def save_corr(X, folder):
    plt.figure(figsize=(10,8))
    sns.heatmap(X.corr(), cmap="coolwarm", annot=False)
    plt.title("Correlation Matrix")
    plt.savefig(os.path.join(folder,"Correlation_Matrix.png"),dpi=300)
    plt.close()

# ============================================================
# MAIN LOOP
# ============================================================

for grid, file in FILES.items():

    print(f"\nProcessing {grid}")

    df = pd.read_excel(os.path.join(INPUT_FOLDER,file))

    y = df["ID"]
    X = df.drop(columns=["ID"])

    out = os.path.join(OUTPUT_BASE,grid)
    os.makedirs(out,exist_ok=True)

    save_corr(X,out)

    X_train, X_test, y_train, y_test = train_test_split(
        X,y,test_size=0.2,random_state=42,stratify=y)

    results = []

    # ===================== RF =====================

    rf = Pipeline([
        ("imp",SimpleImputer()),
        ("rf",RandomForestClassifier(n_estimators=300,random_state=42))
    ])

    rf.fit(X_train,y_train)
    rf_pred = rf.predict(X_test)
    rf_prob = rf.predict_proba(X_test)[:,1]

    rf_metrics = compute_metrics(y_test,rf_pred,rf_prob)
    rf_metrics["Model"]="RF"
    rf_metrics["CV_AUC"]=cross_val_score(rf,X,y,cv=cv,scoring="roc_auc").mean()

    results.append(rf_metrics)
    save_roc(y_test,rf_prob,"RF",out)

    rf_imp = rf.named_steps["rf"].feature_importances_
    pd.DataFrame({"Feature":X.columns,"Importance":rf_imp})\
        .sort_values(by="Importance",ascending=False)\
        .to_excel(os.path.join(out,"RF_Feature_Importance.xlsx"),index=False)

    # ===================== SVM =====================

    svm = Pipeline([
        ("imp",SimpleImputer()),
        ("scaler",StandardScaler()),
        ("svm",SVC(kernel="rbf",probability=True))
    ])

    svm.fit(X_train,y_train)
    svm_pred = svm.predict(X_test)
    svm_prob = svm.predict_proba(X_test)[:,1]

    svm_metrics = compute_metrics(y_test,svm_pred,svm_prob)
    svm_metrics["Model"]="SVM"
    svm_metrics["CV_AUC"]=cross_val_score(svm,X,y,cv=cv,scoring="roc_auc").mean()

    results.append(svm_metrics)
    save_roc(y_test,svm_prob,"SVM",out)

    perm = permutation_importance(
        svm,X_test,y_test,n_repeats=10,random_state=42)

    pd.DataFrame({
        "Feature":X.columns,
        "Importance":perm.importances_mean
    }).sort_values(by="Importance",ascending=False)\
     .to_excel(os.path.join(out,"SVM_Feature_Importance.xlsx"),index=False)

    # ===================== XGBOOST =====================

    xgb = Pipeline([
        ("imp",SimpleImputer()),
        ("xgb",XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=42))
    ])

    xgb.fit(X_train,y_train)
    xgb_pred = xgb.predict(X_test)
    xgb_prob = xgb.predict_proba(X_test)[:,1]

    xgb_metrics = compute_metrics(y_test,xgb_pred,xgb_prob)
    xgb_metrics["Model"]="XGB"
    xgb_metrics["CV_AUC"]=cross_val_score(xgb,X,y,cv=cv,scoring="roc_auc").mean()

    results.append(xgb_metrics)
    save_roc(y_test,xgb_prob,"XGB",out)

    xgb_imp = xgb.named_steps["xgb"].feature_importances_
    pd.DataFrame({"Feature":X.columns,"Importance":xgb_imp})\
        .sort_values(by="Importance",ascending=False)\
        .to_excel(os.path.join(out,"XGB_Feature_Importance.xlsx"),index=False)

    # ===================== SAVE COMPARISON =====================

    pd.DataFrame(results)\
        .to_excel(os.path.join(out,"Model_Comparison.xlsx"),index=False)

print("\nALL GRID SIZES COMPLETED SUCCESSFULLY")
