import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import os

# 1. Configuration: Update these paths exactly
file_path = r'D:\Research Landslide\Result\Slopeunits\Excel_file_SU\Result\Graph to made data.xlsx'
output_dir = r'D:\Research Landslide\Result\Slopeunits\Excel_file_SU\Result'

# Create the directory if it does not exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 2. Load the data
try:
    df = pd.read_csv(file_path)
except FileNotFoundError:
    print(f"Error: Could not find the file at {file_path}. Please check the path.")
    exit()

# Prepare the data for surface plotting
pivot_df = df.pivot(index='c', columns='a', values='GH')
X, Y = np.meshgrid(pivot_df.columns, pivot_df.index)
Z = pivot_df.values

# 3. 3D Surface Plot
# 
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')
surf = ax.plot_surface(X, Y, Z, cmap='viridis', edgecolor='none', alpha=0.8)
ax.set_xlabel('Area Threshold (a)')
ax.set_ylabel('Shape Parameter (c)')
ax.set_zlabel('Global Heterogeneity (GH)')
ax.set_title('GH Response Surface for Optimal Slope Units')
fig.colorbar(surf, label='GH Score', shrink=0.5, aspect=10)
plt.savefig(os.path.join(output_dir, 'GH_Response_Surface.png'), dpi=300)
plt.close()

# 4. 2D Heatmap
# 
plt.figure(figsize=(10, 8))
sns.heatmap(pivot_df, annot=True, cmap='viridis', fmt=".4f")
plt.title('GH Score Heatmap (Parameter Tuning)')
plt.ylabel('Shape Parameter (c)')
plt.xlabel('Area Threshold (a)')
plt.savefig(os.path.join(output_dir, 'GH_Heatmap.png'), dpi=300)
plt.close()

# 5. Complexity vs. Performance Scatter Plot
plt.figure(figsize=(10, 6))
sns.scatterplot(data=df, x='SlopeUnits', y='GH', hue='a', palette='viridis', size='c', sizes=(20, 200))
plt.title('Slope Units Complexity vs. GH Score')
plt.xlabel('Number of Slope Units')
plt.ylabel('Global Heterogeneity (GH)')
plt.grid(True, linestyle='--', alpha=0.6)
plt.savefig(os.path.join(output_dir, 'GH_vs_Complexity.png'), dpi=300)
plt.close()

print(f"✅ Plots successfully saved to: {output_dir}")