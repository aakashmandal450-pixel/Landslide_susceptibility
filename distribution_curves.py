import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde

# ============================================================
# CONFIGURATION & PATHS
# ============================================================

INPUT_FOLDER = r"D:\Research Landslide\Data\Filtered_Output"
OUTPUT_BASE = r"D:\Research Landslide\Result\Outputs\New folder 3"

# File mapping: Grid Size -> Filename
FILES = {
    "3x3": "ls_non_ls_final_3x3.xlsx",
    "15x15": "ls_non_ls_final_15x15.xlsx",
    "25x25": "ls_non_ls_final_25x25.xlsx"
}

# Ensure output directory exists
os.makedirs(OUTPUT_BASE, exist_ok=True)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_peak_value(data):
    """Finds the value (x-axis) where the distribution curve peaks."""
    if len(data) < 2: return 0
    kde = gaussian_kde(data)
    # Scan a range to find the max density
    x_grid = np.linspace(data.min(), data.max(), 100)
    return x_grid[np.argmax(kde(x_grid))]

def calculate_separation_score(group1, group2):
    """
    Calculates Cohen's d to quantify how separated the two curves are.
    High value = Good separation (High precision).
    Low value = High overlap (Lower precision).
    """
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    
    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    
    if pooled_std == 0: return 0
    
    # Cohen's d
    d = abs(np.mean(group1) - np.mean(group2)) / pooled_std
    return d

def generate_detailed_text(col_name, ls_data, nonls_data, grid_size):
    """Generates a unique, insight-driven interpretation text."""
    
    # 1. Statistics
    mean_ls = ls_data.mean()
    mean_nonls = nonls_data.mean()
    peak_ls = get_peak_value(ls_data)
    peak_nonls = get_peak_value(nonls_data)
    separation_score = calculate_separation_score(ls_data, nonls_data)
    
    # 2. Determine Relationships
    direction = "higher" if mean_ls > mean_nonls else "lower"
    
    # 3. Analyze Separation (Discriminative Power)
    if separation_score > 0.8:
        sep_desc = "Strong Separation"
        precision_impact = (
            "Because the curves are well-separated, this parameter has high discriminative power. "
            "It will likely significantly boost the model's precision and recall."
        )
    elif separation_score > 0.4:
        sep_desc = "Moderate Overlap"
        precision_impact = (
            "The curves show some distinction but also noticeable overlap. "
            "This parameter contributes useful context, but the model will rely on combinations with other factors to distinguish difficult cases."
        )
    else:
        sep_desc = "High Overlap"
        precision_impact = (
            "The distributions are very similar (high overlap). "
            "On its own, this parameter may not effectively distinguish between landslide and non-landslide classes, potentially adding noise if not regularized."
        )

    # 4. Construct the Text
    text = f"""============================================================
DISTRIBUTION ANALYSIS: {col_name} (Grid: {grid_size})
============================================================

1. GENERAL RELATIONSHIP
   - Landslides (ID=1) tend to occur at {direction} values of {col_name} compared to stable terrain.
   - Mean Landslide Value: {mean_ls:.4f}
   - Mean Non-Landslide Value: {mean_nonls:.4f}

2. PEAK ANALYSIS (Mode of Distribution)
   - The landslide distribution peaks at approximately {peak_ls:.4f}.
   - The non-landslide distribution peaks at approximately {peak_nonls:.4f}.
   - The shift between these peaks represents the primary range where landslide susceptibility changes.

3. OVERLAP AND SEPARATION
   - Assessment: {sep_desc} (Separation Score: {separation_score:.2f})
   - Observation: 
     Distinct peaks suggest strong predictive capability. If the area under the intersection of 
     the curves is small, the classifier can easily draw a boundary. Here, we observe that the 
     landslide curve is shifted distinctively to the {direction}.

4. IMPACT ON MODEL PRECISION
   - {precision_impact}

5. CONCLUSION
   - The probability density function confirms that {col_name} is a relevant conditioning factor.
   - The specific distribution pattern affects the spatial prediction by increasing probability scores 
     in areas where {col_name} values approach {peak_ls:.4f}.
"""
    return text

# ============================================================
# MAIN PROCESSING LOOP
# ============================================================

for grid, filename in FILES.items():
    print(f"\nProcessing Grid Size: {grid}...")
    
    file_path = os.path.join(INPUT_FOLDER, filename)
    
    if not os.path.exists(file_path):
        print(f"  [WARNING] File not found: {file_path}. Skipping...")
        continue

    # Read Excel
    df = pd.read_excel(file_path)
    
    # Create Output Folder for this grid
    current_output_dir = os.path.join(OUTPUT_BASE, grid)
    os.makedirs(current_output_dir, exist_ok=True)
    
    # Identify Target and Features
    # Assuming target column is 'ID' based on your previous code
    if 'ID' not in df.columns:
        print(f"  [ERROR] Column 'ID' not found in {filename}. Skipping...")
        continue
        
    features = [c for c in df.columns if c != 'ID']
    
    for col in features:
        # Separate Data
        ls_vals = df[df['ID'] == 1][col].dropna()
        nonls_vals = df[df['ID'] == 0][col].dropna()
        
        if len(ls_vals) == 0 or len(nonls_vals) == 0:
            continue

        # -----------------------------
        # 1. GENERATE PLOT
        # -----------------------------
        plt.figure(figsize=(7, 5))
        
        # Plot Landslide (Orange/Red tone) and Non-Landslide (Blue tone)
        sns.kdeplot(nonls_vals, fill=True, color="#1f77b4", label="Non-Landslide (0)", alpha=0.3)
        sns.kdeplot(ls_vals, fill=True, color="#ff7f0e", label="Landslide (1)", alpha=0.5)
        
        plt.title(f"Distribution of {col} by Class ({grid})", fontsize=14)
        plt.xlabel(col, fontsize=12)
        plt.ylabel("Density", fontsize=12)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        
        # Save Plot
        plot_filename = f"{col}_distribution.png"
        plt.savefig(os.path.join(current_output_dir, plot_filename), dpi=300, bbox_inches='tight')
        plt.close()
        
        # -----------------------------
        # 2. GENERATE TEXT INTERPRETATION
        # -----------------------------
        interpretation_text = generate_detailed_text(col, ls_vals, nonls_vals, grid)
        
        text_filename = f"{col}_interpretation.txt"
        with open(os.path.join(current_output_dir, text_filename), "w", encoding="utf-8") as f:
            f.write(interpretation_text)

    print(f"  -> Completed {len(features)} parameters for {grid}.")

print("\n========================================================")
print("PROCESSING COMPLETE")
print(f"Results saved in: {OUTPUT_BASE}")
print("========================================================")