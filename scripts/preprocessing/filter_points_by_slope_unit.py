import pandas as pd
import numpy as np
import os

# ------------------------------
# USER INPUTS
# ------------------------------

input_file = r"D:\Research Landslide\Data\Excel files\ls_seeds.xlsx"  # <-- CHANGE THIS
output_file = r"D:\Research Landslide\Data\Excel files\filtered_points.xlsx"

cat_column = "cat"                # column with point names
slope_unit_column = "Slope_unit"  # column storing slope-unit values
desired_points = 400              # final number of points
min_spacing = 0.5                 # minimum allowed difference in slope-unit values

# ------------------------------
# STEP 1: LOAD EXCEL FILE
# ------------------------------

df = pd.read_excel(input_file)

print("Original rows:", len(df))

# ------------------------------
# STEP 2: REMOVE ROWS WITH ANY EMPTY CELL
# ------------------------------

df_clean = df.dropna(how='any')
print("After removing empty cells:", len(df_clean))

# ------------------------------
# STEP 3: SCATTER POINTS BY REMOVING CLOSE SLOPE-UNIT VALUES
# ------------------------------

df_sorted = df_clean.sort_values(by=slope_unit_column)

selected_rows = []
last_value = None

for _, row in df_sorted.iterrows():
    current_val = row[slope_unit_column]

    if last_value is None:
        selected_rows.append(row)
        last_value = current_val
        continue

    # keep if spacing is large enough
    if abs(current_val - last_value) >= min_spacing:
        selected_rows.append(row)
        last_value = current_val

df_spaced = pd.DataFrame(selected_rows)
print("After spacing filter:", len(df_spaced))

# ------------------------------
# STEP 4: RANDOMLY SELECT 400 POINTS
# ------------------------------

if len(df_spaced) < desired_points:
    raise ValueError(f"Not enough points after filtering. Only {len(df_spaced)} available.")

df_final = df_spaced.sample(n=desired_points, random_state=42)
print("Final samples:", len(df_final))

# ------------------------------
# STEP 5: SAVE OUTPUT
# ------------------------------

df_final.to_excel(output_file, index=False)
print(f"\nFinal filtered file saved to:\n{output_file}")

# ------------------------------
# AUTO-OPEN THE OUTPUT FILE (OPTIONAL)
# ------------------------------
try:
    os.startfile(output_file)
except:
    pass
