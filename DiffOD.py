import csv
import heapq
import os
import json
import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as ctx
import numpy as np
from matplotlib.widgets import Slider, Button

# Load city boundary as a polygon
city_gdf = gpd.read_file('city_boundary.geojson')
city_gdf = city_gdf.to_crs(epsg=3857)

NUM_REGIONS = 598
NUM_TOP = 50

day_types = ['W', 'SAT', 'SUN', 'ALL']
day_types2 = ['W', 'SAT', 'SUN']

# Store results: {day: {hour: (top_origins, top_destinations)}}, and counts
top_origins_per_file = {day: {} for day in day_types}
top_destinations_per_file = {day: {} for day in day_types}

# Initialize ALL as a dict to accumulate totals {hour: (top_origins, top_destinations)}
All_top_origins = {hour: {} for hour in range(24)}
All_top_destinations = {hour: {} for hour in range(24)}

for day in day_types2:
    for hour in range(24):
        filename = f"{day}{hour}.csv"
        origin_counts = {}
        dest_counts = {}
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    origin = int(row[0].replace('Region ', ''))
                    dest = int(row[1].replace('Region ', ''))
                    count = int(float(row[2]))
                    origin_counts[origin] = origin_counts.get(origin, 0) + count
                    dest_counts[dest] = dest_counts.get(dest, 0) + count
                    
                    All_top_origins[hour][origin] = All_top_origins[hour].get(origin, 0) + count
                    All_top_destinations[hour][dest] = All_top_destinations[hour].get(dest, 0) + count
                except Exception as e:
                    continue
        # Store as list of (region, count) tuples, sorted by count
        top_origins = heapq.nlargest(NUM_TOP, origin_counts.items(), key=lambda x: x[1])
        top_destinations = heapq.nlargest(NUM_TOP, dest_counts.items(), key=lambda x: x[1])
        top_origins_per_file[day][hour] = top_origins
        top_destinations_per_file[day][hour] = top_destinations

# At the end, keep only the top 50 in ALL
for hour in range(24):
    top_origins_per_file['ALL'][hour] = heapq.nlargest(NUM_TOP, All_top_origins[hour].items(), key=lambda x: x[1])
    top_destinations_per_file['ALL'][hour] = heapq.nlargest(NUM_TOP, All_top_destinations[hour].items(), key=lambda x: x[1])


# Load region polygons from MAP.json
geo_path = "MAP.json"
gdf = gpd.read_file(geo_path)
gdf.set_index("i", inplace=True)
gdf = gdf.to_crs(epsg=3857)
gdf["centroid"] = gdf.geometry.centroid


# State for current day type
current_day = 'W'  # Use list for mutability in nested functions

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 12))
plt.subplots_adjust(bottom=0.22)

slider_ax = plt.axes([0.2, 0.10, 0.6, 0.03])
slider = Slider(slider_ax, 'Hour', 0, 23, valinit=0, valstep=1)

button_axes = [plt.axes([0.2 + i*0.2, 0.02, 0.18, 0.06]) for i in range(4)]
buttons = [Button(ax, label) for ax, label in zip(button_axes, ['Weekday', 'Saturday', 'Sunday', 'All Days'])]

# Add a mapping for pretty day names
pretty_day = {'W': 'Weekdays', 'SAT': 'Saturday', 'SUN': 'Sunday', 'ALL': 'All Days'}

# Plot function
def plot_highlight(hour):
    for ax, top_regions, title, label in zip(
        [ax1, ax2],
        [top_origins_per_file[current_day][hour], top_destinations_per_file[current_day][hour]],
        [f"Top {NUM_TOP} Origins", f"Top {NUM_TOP} Destinations"],
        ["Origins", "Destinations"]):
        ax.cla()
        region_indices = [region for region, count in top_regions if region in gdf.index]
        highlight = gdf.loc[region_indices]
        gdf.plot(ax=ax, facecolor="none", edgecolor="lightgray", linewidth=0.4)
        cmap = plt.get_cmap('RdYlGn')
        colors = [cmap(i / (len(highlight)-1)) for i in range(len(highlight))]
        for i, (region_id, row) in enumerate(highlight.iterrows()):
            gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=colors[i], edgecolor='black', linewidth=1, zorder=3)
            c = row.centroid
            ax.text(c.x, c.y, str(i+1), fontsize=8, color="black", ha="center", zorder=5)
        # Overlay city boundary in blue
        city_gdf.boundary.plot(ax=ax, color='blue', linewidth=2, zorder=4)
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Voyager)
        ax.set_title(f"{title} for {pretty_day[current_day]} Hour {hour:02d}:00", fontsize=15)
        ax.set_axis_off()
        # Add label for #1 and #50
        trip1 = top_regions[0][1]
        trip50 = top_regions[NUM_TOP-1][1]
        ax.text(0.01, 0.99, f"#1: {trip1} trips\n#50: {trip50} trips", transform=ax.transAxes,
                fontsize=14, color="black", va="top", ha="left",
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
    plt.draw()

plot_highlight(0)

# Slider update
def update(val):
    plot_highlight(int(slider.val))
slider.on_changed(update)

# Button callbacks
def make_button_callback(day):
    def callback(event):
        global current_day
        current_day = day
        plot_highlight(int(slider.val))
    return callback

for btn, day in zip(buttons, day_types):
    btn.on_clicked(make_button_callback(day))

plt.show()
