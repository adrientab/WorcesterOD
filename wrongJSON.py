import geopandas as gpd
import matplotlib.pyplot as plt

# Load the original grid
old_grid = gpd.read_file('MAP.json')

# Load city boundary
city_gdf = gpd.read_file('City_Boundary.geojson')
city_gdf = city_gdf.to_crs(old_grid.crs)

# Plot
fig, ax = plt.subplots(figsize=(10, 10))
old_grid.plot(ax=ax, facecolor='orange', edgecolor='black', linewidth=0.5, alpha=0.7, zorder=2)
city_gdf.boundary.plot(ax=ax, color='blue', linewidth=2, zorder=3)
ax.set_title('Original Grid (MAP.json) and City Boundary Overlay')
ax.set_axis_off()
plt.tight_layout()
plt.show()
