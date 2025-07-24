import json
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box, mapping
import numpy as np

# Load MAP.json as GeoDataFrame
gdf = gpd.read_file('MAP.json')

# Load city boundary
gdf_city = gpd.read_file('City_Boundary.geojson')
gdf_city = gdf_city.to_crs(gdf.crs)
city_boundary = gdf_city.unary_union

# --- Determine grid cell size from MAP.json ---
sample_poly = gdf.geometry.iloc[0]
minx, miny, maxx, maxy = sample_poly.bounds
cell_width = maxx - minx
cell_height = maxy - miny

# --- Generate grid covering the city boundary ---
city_minx, city_miny, city_maxx, city_maxy = city_boundary.bounds
cols = int(np.ceil((city_maxx - city_minx) / cell_width))
rows = int(np.ceil((city_maxy - city_miny) / cell_height))

# Use integer grid indices for all cells
grid_indices = set()
for i in range(cols):
    for j in range(rows):
        x1 = city_minx + i * cell_width
        y1 = city_miny + j * cell_height
        x2 = x1 + cell_width
        y2 = y1 + cell_height
        cell = box(x1, y1, x2, y2)
        if cell.intersects(city_boundary):
            grid_indices.add((i, j))

# Add missing neighbors for each cell
all_indices = set(grid_indices)
for i, j in list(grid_indices):
    for di, dj in [(-2,0), (2,0), (0,-2), (0,2)]:
        neighbor = (i + di, j + dj)
        all_indices.add(neighbor)

# Now create all cells from all_indices
all_cells = []
for i, j in all_indices:
    x1 = city_minx + i * cell_width
    y1 = city_miny + j * cell_height
    x2 = x1 + cell_width
    y2 = y1 + cell_height
    all_cells.append(box(x1, y1, x2, y2))

gdf_grid = gpd.GeoDataFrame(geometry=all_cells, crs=gdf.crs)

# Output as MAP.json style GeoJSON FeatureCollection
features = []
for idx, row in gdf_grid.iterrows():
    features.append({
        "type": "Feature",
        "properties": {"id": int(idx)},
        "geometry": mapping(row.geometry)
    })
geojson = {
    "type": "FeatureCollection",
    "features": features
}
with open('City_Grid_MAPstyle.json', 'w') as f:
    json.dump(geojson, f)
print(f"Wrote {len(features)} grid cells to City_Grid_MAPstyle.json (MAP.json style)")

# --- Plotting ---
fig, ax = plt.subplots(figsize=(10, 10))
gdf_city.boundary.plot(ax=ax, color='blue', linewidth=2, zorder=1)
gdf_grid.plot(ax=ax, facecolor='orange', edgecolor='black', linewidth=0.5, alpha=0.7, zorder=2)
ax.set_title('Grid covering City Boundary (no overlaps, all edge neighbors)')
ax.set_axis_off()
plt.tight_layout()
plt.show()
