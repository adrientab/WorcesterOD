import csv
import heapq
import os
import json
import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as ctx
import numpy as np
from matplotlib.widgets import Slider, Button
from pyproj import Transformer
import pandas as pd
import re
from matplotlib.patches import FancyArrowPatch
from matplotlib.colors import LinearSegmentedColormap
import warnings

# Suppress OGR field type warnings
warnings.filterwarnings('ignore', message='.*unsupported OGR type.*')

# BRT station coordinates (WGS84)
brt_stations = [
    {"id": "brt_1", "lat": 42.314139, "lon": -71.791083},
    {"id": "brt_2", "lat": 42.301139, "lon": -71.801972},
    {"id": "brt_3", "lat": 42.276472, "lon": -71.801556},
    {"id": "brt_4", "lat": 42.271686, "lon": -71.800596},
    {"id": "brt_5", "lat": 42.264190, "lon": -71.795404},
    {"id": "brt_6", "lat": 42.255527, "lon": -71.797340},
    {"id": "brt_7", "lat": 42.241968, "lon": -71.801111},
    {"id": "brt_8", "lat": 42.232811, "lon": -71.793633},
    {"id": "brt_9", "lat": 42.268892, "lon": -71.842723},
    {"id": "brt_10", "lat": 42.262146, "lon": -71.822375},
    {"id": "brt_11", "lat": 42.248583, "lon": -71.829806},
    {"id": "brt_12", "lat": 42.265997, "lon": -71.785728},
    {"id": "brt_13", "lat": 42.276670, "lon": -71.763703}
]
brt_ids = [x['id'] for x in brt_stations]

# Transform BRT station coordinates to map projection (EPSG:3857)
transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)
brt_xy = [transformer.transform(station['lon'], station['lat']) for station in brt_stations]

# State for BRT overlay
overlay_brt = [False]

# Load city boundary as a polygon
city_gdf = gpd.read_file('city_boundary.geojson')
city_gdf = city_gdf.to_crs(epsg=3857)

NUM_REGIONS = 598
NUM_TOP = 30

day_types = ['W', 'SAT', 'SUN', 'ALL']
day_types2 = ['W', 'SAT', 'SUN']

# Store results: {day: {hour: (top_origins, top_destinations)}}, and counts
top_per_file = {day: {} for day in day_types}

# Initialize ALL as a dict to accumulate totals {hour: (top_origins, top_destinations)}
all_top = {hour: {} for hour in range(24)}

for day in day_types2:
    for hour in range(24):
        filename = f"{day}{hour}.csv"
        counts = {}
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    origin = int(row[0].replace('Region ', ''))
                    dest = int(row[1].replace('Region ', ''))
                    count = int(float(row[2]))

                    counts[(origin, dest)] = count
                    if (day == 'W'):
                        count = count / 5
                    all_top[hour][(origin, dest)] = all_top[hour].get((origin, dest), 0) + count
                except Exception as e:
                    continue
        # Store as list of (region, count) tuples, sorted by count
        top_per_file[day][hour] = heapq.nlargest(NUM_TOP, counts.items(), key=lambda x: x[1])

# At the end, keep only the top 50 in ALL
for hour in range(24):
    top_per_file['ALL'][hour] = heapq.nlargest(NUM_TOP, all_top[hour].items(), key=lambda x: x[1])

# Load region polygons from MAP.json
geo_path = "MAP.json"
gdf = gpd.read_file(geo_path)
gdf.set_index("i", inplace=True)
gdf = gdf.to_crs(epsg=3857)
gdf["centroid"] = gdf.geometry.centroid


# State for current day type
current_day = ['W']  # Use list for mutability in nested functions

# Update to 1 subplot for Top OD Arrows
fig, ax = plt.subplots(1, 1, figsize=(12, 12))
plt.subplots_adjust(bottom=0.22, top=0.88)

slider_ax = plt.axes([0.1, 0.10, 0.6, 0.03])
slider = Slider(slider_ax, 'Hour', 0, 23, valinit=0, valstep=1)

button_axes = [plt.axes([0.1 + i*0.2, 0.02, 0.18, 0.06]) for i in range(4)]
buttons = [Button(ax, label) for ax, label in zip(button_axes, ['Weekday', 'Saturday', 'Sunday', 'All Days'])]

# Add a mapping for pretty day names
pretty_day = {'W': 'Weekdays', 'SAT': 'Saturday', 'SUN': 'Sunday', 'ALL': 'All Days'}

# Add a toggle button for BRT overlay
brt_button_ax = plt.axes([0.82, 0.10, 0.075, 0.06])
brt_button = Button(brt_button_ax, 'Toggle\nBRT Stations')

# Add a toggle button for POI overlay
poi_button_ax = plt.axes([0.745, 0.10, 0.075, 0.06])
poi_button = Button(poi_button_ax, 'Toggle POIs')

# Load POI data from JSON file
with open('POIs.json', 'r') as f:
    poi_json = json.load(f)

# Define color and marker mapping for different POI types
poi_style_map = {
    'fire_station': {'color': 'firebrick', 'marker': 'F'},
    'library': {'color': 'brown', 'marker': 'L'},
    'school': {'color': 'blue', 'marker': 'S'},
    'courthouse': {'color': 'darkblue', 'marker': 'C'},
    'supermarket': {'color': 'orange', 'marker': 'S'},
    'post_office': {'color': 'darkred', 'marker': 'PO'},
    'police': {'color': 'navy', 'marker': 'P'},
    'attraction': {'color': 'yellow', 'marker': 'A'}
}

# Extract POI data from JSON
poi_data = []
for element in poi_json['elements']:
    if element['type'] == 'node' and 'tags' in element:
        tags = element['tags']
        # Check for amenity type
        amenity_type = None
        if 'amenity' in tags:
            amenity_type = tags['amenity']
        elif 'shop' in tags:
            amenity_type = tags['shop']
        elif 'tourism' in tags:
            amenity_type = tags['tourism']
        
        if amenity_type and amenity_type in poi_style_map:
            poi_data.append({
                'type': amenity_type,
                'lat': element['lat'],
                'lon': element['lon'],
                'color': poi_style_map[amenity_type]['color'],
                'marker': poi_style_map[amenity_type]['marker'],
                'name': tags.get('name', amenity_type)
            })

# Transform POI coordinates to map projection
poi_xy = [transformer.transform(poi['lon'], poi['lat']) for poi in poi_data]


# State for POI overlay
overlay_poi = [False]

# Custom colormap from red to green, with more intermediate steps for better color variation
red_green_cmap = LinearSegmentedColormap.from_list('RedGreen', ['red', 'darkorange', 'limegreen', 'green'], N=256)

# Helper: check if two regions are adjacent or the same (for now, just same)
def is_adjacent_or_same(origin, destination):
    return origin == destination

# Plot function
def plot_highlight(hour):
    fig.suptitle(f"Top {NUM_TOP} OD Routes for {pretty_day[current_day[0]]}, Hour {hour:02d}:00", fontsize=18, y=0.97)
    ax.cla()
    gdf.plot(ax=ax, facecolor="none", edgecolor="lightgray", linewidth=0.4)
    top_od = top_per_file[current_day[0]][hour]
    cmap = red_green_cmap
    for i, ((origin, destination), trips) in enumerate(top_od):
        if origin not in gdf.index or destination not in gdf.index:
            continue
        p1 = gdf.loc[origin].centroid
        p2 = gdf.loc[destination].centroid
        linewidth = 1.5 + (trips / top_od[0][1]) * 3 if top_od else 2
        color = cmap(1 - (i / (NUM_TOP-1)))
        arrow = FancyArrowPatch(
            (p1.x, p1.y), (p2.x, p2.y),
            arrowstyle='->',
            color=color,
            linewidth=8 * ((1 - ((i + 1) / NUM_TOP))),
            alpha=0.85,
            mutation_scale=10 + linewidth * 2,
            zorder=4
        )
        ax.add_patch(arrow)
    # Overlay city boundary in blue
    city_gdf.boundary.plot(ax=ax, color='blue', linewidth=2, zorder=3)
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Voyager)
    ax.set_title("Top OD Arrows", fontsize=15, pad=18)
    ax.set_axis_off()
    if len(top_od) >= NUM_TOP:
        trip1 = top_od[0][1]
        trip50 = top_od[NUM_TOP-1][1]
        ax.text(0.01, 0.99, f"#1: {trip1} trips\n#{NUM_TOP}: {trip50} trips", transform=ax.transAxes,
                fontsize=14, color="black", va="top", ha="left",
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
    elif len(top_od) > 0:
        trip1 = top_od[0][1]
        ax.text(0.01, 0.99, f"#1: {trip1} trips", transform=ax.transAxes,
                fontsize=14, color="black", va="top", ha="left",
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
    # Overlay BRT stations if toggled
    if overlay_brt[0]:
        xs, ys = zip(*brt_xy)
        ax.scatter(xs, ys, c='deepskyblue', s=80, marker='o', edgecolor='black', zorder=10, label='BRT Station')
    # Overlay POIs if toggled
    if overlay_poi[0]:
        for i, (poi, (x, y)) in enumerate(zip(poi_data, poi_xy)):
            ax.scatter(x, y, c=poi['color'], s=100, marker='o', edgecolor='black', zorder=11)
            ax.text(x, y, poi['marker'], fontsize=10, color='white', ha='center', va='center', 
                   weight='bold', zorder=12)
    plt.draw()

plot_highlight(0)

# Slider update
def update(val):
    plot_highlight(int(slider.val))
slider.on_changed(update)

# Button callbacks
def make_button_callback(day):
    def callback(event):
        current_day[0] = day
        plot_highlight(int(slider.val))
    return callback

for btn, day in zip(buttons, day_types):
    btn.on_clicked(make_button_callback(day))

# BRT toggle button callback
def toggle_brt(event):
    overlay_brt[0] = not overlay_brt[0]
    plot_highlight(int(slider.val))
brt_button.on_clicked(toggle_brt)

# POI toggle button callback
def toggle_poi(event):
    overlay_poi[0] = not overlay_poi[0]
    plot_highlight(int(slider.val))
poi_button.on_clicked(toggle_poi)

plt.show()
