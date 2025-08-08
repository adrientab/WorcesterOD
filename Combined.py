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
NUM_TOP = 1

day_types = ['W', 'SAT', 'SUN', 'ALL']
day_types2 = ['W', 'SAT', 'SUN']

# Store results: {day: {hour: (top_origins, top_destinations)}}, and counts
top_origins_per_file = {day: {hour: {} for hour in range(24)} for day in day_types}
top_destinations_per_file = {day: {hour: {} for hour in range(24)} for day in day_types}
top_combined_per_file = {day: {hour: {} for hour in range(24)} for day in day_types}

# Initialize ALL as a dict to accumulate totals {hour: (top_origins, top_destinations)}
All_top_origins = {hour: {} for hour in range(24)}
All_top_destinations = {hour: {} for hour in range(24)}
All_top_combined = {hour: {} for hour in range(24)}

for day in day_types2:
    for hour in range(24):
        filename = f"{day}{hour}.csv"
        origin_counts = {}
        dest_counts = {}
        combined_counts = {}
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    origin = int(row[0].replace('Region ', ''))
                    dest = int(row[1].replace('Region ', ''))
                    count = int(float(row[2]))

                    origin_counts[origin] = origin_counts.get(origin, 0) + count
                    dest_counts[dest] = dest_counts.get(dest, 0) + count
                    combined_counts[origin] = combined_counts.get(origin, 0) + count
                    combined_counts[dest] = combined_counts.get(dest, 0) + count

                    All_top_origins[hour][origin] = All_top_origins[hour].get(origin, 0) + count
                    All_top_destinations[hour][dest] = All_top_destinations[hour].get(dest, 0) + count
                    All_top_combined[hour][origin] = All_top_combined[hour].get(origin, 0) + count
                    All_top_combined[hour][dest] = All_top_combined[hour].get(dest, 0) + count
                except Exception as e:
                    continue
        # Store as list of (region, count) tuples, sorted by count
        top_origins = heapq.nlargest(NUM_TOP, origin_counts.items(), key=lambda x: x[1])
        top_destinations = heapq.nlargest(NUM_TOP, dest_counts.items(), key=lambda x: x[1])
        top_combined = heapq.nlargest(NUM_TOP, combined_counts.items(), key=lambda x: x[1])


        top_origins_per_file[day][hour] = top_origins
        top_destinations_per_file[day][hour] = top_destinations
        top_combined_per_file[day][hour] = top_combined

# At the end, keep only the top 50 in ALL
for hour in range(24):
    top_origins_per_file['ALL'][hour] = heapq.nlargest(NUM_TOP, All_top_origins[hour].items(), key=lambda x: x[1])
    top_destinations_per_file['ALL'][hour] = heapq.nlargest(NUM_TOP, All_top_destinations[hour].items(), key=lambda x: x[1])
    top_combined_per_file['ALL'][hour] = heapq.nlargest(NUM_TOP, All_top_combined[hour].items(), key=lambda x: x[1])

# Load region polygons from MAP.json
geo_path = "MAP.json"
gdf = gpd.read_file(geo_path)
gdf.set_index("i", inplace=True)
gdf = gdf.to_crs(epsg=3857)
gdf["centroid"] = gdf.geometry.centroid


# State for current day type
current_day = ['W']  # Use list for mutability in nested functions

# Update to 3 subplots for Origins, Destinations, Combined
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(24, 12))
plt.subplots_adjust(bottom=0.22, top=0.88)  # Increase top margin to avoid title overlap

slider_ax = plt.axes([0.1, 0.10, 0.6, 0.03])
slider = Slider(slider_ax, 'Hour', 0, 23, valinit=0, valstep=1)

button_axes = [plt.axes([0.1 + i*0.2, 0.02, 0.18, 0.06]) for i in range(4)]
buttons = [Button(ax, label) for ax, label in zip(button_axes, ['Weekday', 'Saturday', 'Sunday', 'All Days'])]

# Add a mapping for pretty day names
pretty_day = {'W': 'Weekdays', 'SAT': 'Saturday', 'SUN': 'Sunday', 'ALL': 'All Days'}

# Add a toggle button for BRT overlay
brt_button_ax = plt.axes([0.82, 0.10, 0.075, 0.06])
brt_button = Button(brt_button_ax, 'Toggle\nBRT Stations')

# Add a toggle button for landmark overlay
poi_button_ax = plt.axes([0.745, 0.10, 0.075, 0.06])
poi_button = Button(poi_button_ax, 'Toggle\nLandmarks')

# Worcester landmarks data
worcester_landmarks = {
    'schools': [
        {'name': 'Worcester Polytechnic Institute (WPI)', 'lat': 42.2746, 'lon': -71.8063, 'type': 'university'},
        {'name': 'Clark University', 'lat': 42.2507, 'lon': -71.8229, 'type': 'university'},
        {'name': 'College of the Holy Cross', 'lat': 42.3378, 'lon': -71.8064, 'type': 'university'},
        {'name': 'UMass Medical School', 'lat': 42.2733, 'lon': -71.7622, 'type': 'university'},
        {'name': 'Worcester State University', 'lat': 42.2669, 'lon': -71.8644, 'type': 'university'},
        {'name': 'Assumption University', 'lat': 42.2584, 'lon': -71.8483, 'type': 'university'},
        {'name': 'Quinsigamond Community College', 'lat': 42.2583, 'lon': -71.8230, 'type': 'college'},
        {'name': 'Worcester Academy', 'lat': 42.2625, 'lon': -71.8028, 'type': 'high_school'},
        {'name': 'Bancroft School', 'lat': 42.2792, 'lon': -71.8222, 'type': 'high_school'},
        {'name': 'Worcester Technical High School', 'lat': 42.2750, 'lon': -71.8400, 'type': 'high_school'},
    ],
    
    'employment': [
        {'name': 'UMass Memorial Medical Center', 'lat': 42.2733, 'lon': -71.7622, 'type': 'hospital'},
        {'name': 'Saint Vincent Hospital', 'lat': 42.2681, 'lon': -71.7975, 'type': 'hospital'},
        {'name': 'The Hanover Insurance Group', 'lat': 42.2625, 'lon': -71.8028, 'type': 'corporate'},
        {'name': 'Polar Beverages', 'lat': 42.2750, 'lon': -71.8300, 'type': 'corporate'},
        {'name': 'Fallon Health', 'lat': 42.2650, 'lon': -71.8100, 'type': 'corporate'},
        {'name': 'Reliant Medical Group', 'lat': 42.2700, 'lon': -71.8200, 'type': 'medical'},
        {'name': 'Worcester Recovery Center', 'lat': 42.2600, 'lon': -71.8000, 'type': 'hospital'},
        {'name': 'Allegro MicroSystems', 'lat': 42.2800, 'lon': -71.8100, 'type': 'corporate'},
        {'name': 'Saint-Gobain', 'lat': 42.2900, 'lon': -71.8200, 'type': 'corporate'},
        {'name': 'Family Health Center', 'lat': 42.2550, 'lon': -71.8150, 'type': 'medical'},
    ],
    
    'commercial': [
        {'name': 'CitySquare/Mercantile Center', 'lat': 42.2625, 'lon': -71.8028, 'type': 'shopping'},
        {'name': 'Downtown Worcester', 'lat': 42.2626, 'lon': -71.8023, 'type': 'shopping'},
        {'name': 'Worcester Public Market', 'lat': 42.2600, 'lon': -71.8050, 'type': 'shopping'},
        #{'name': 'The Shops at Blackstone Valley', 'lat': 42.1333, 'lon': -71.6167, 'type': 'shopping'},
        {'name': 'Greendale Mall Area', 'lat': 42.2333, 'lon': -71.8667, 'type': 'shopping'},
        {'name': 'Midtown Mall', 'lat': 42.2620, 'lon': -71.8020, 'type': 'shopping'},
        {'name': 'Lincoln Plaza', 'lat': 42.2700, 'lon': -71.8300, 'type': 'shopping'},
        {'name': 'Park Avenue Shopping', 'lat': 42.2800, 'lon': -71.8400, 'type': 'shopping'},
    ]
}

# Define color and marker mapping for different landmark types
landmark_style_map = {
    'university': {'color': 'purple', 'marker': 'U'},
    'college': {'color': 'purple', 'marker': 'C'},
    'high_school': {'color': 'blue', 'marker': 'H'},
    'hospital': {'color': 'red', 'marker': 'H'},
    'corporate': {'color': 'darkgreen', 'marker': 'C'},
    'medical': {'color': 'pink', 'marker': 'M'},
    'shopping': {'color': 'orange', 'marker': 'S'}
}

# Flatten landmarks into a single list
landmark_data = []
for category, landmarks in worcester_landmarks.items():
    for landmark in landmarks:
        landmark_type = landmark['type']
        if landmark_type in landmark_style_map:
            landmark_data.append({
                'name': landmark['name'],
                'lat': landmark['lat'],
                'lon': landmark['lon'],
                'type': landmark_type,
                'category': category,
                'color': landmark_style_map[landmark_type]['color'],
                'marker': landmark_style_map[landmark_type]['marker']
            })

# Transform landmark coordinates to map projection
landmark_xy = [transformer.transform(landmark['lon'], landmark['lat']) for landmark in landmark_data]

# State for landmark overlay
overlay_landmarks = [False]



# Plot function
def plot_highlight(hour):
    # Set main title with day and hour
    fig.suptitle(f"Top {NUM_TOP} Regions for {pretty_day[current_day[0]]}, Hour {hour:02d}:00", fontsize=18, y=0.97)
    for ax, top_regions, title in zip(
        [ax1, ax2, ax3],
        [top_origins_per_file[current_day[0]][hour], top_destinations_per_file[current_day[0]][hour], top_combined_per_file[current_day[0]][hour]],
        ["Origins", "Destinations", "Combined"]):
        ax.cla()
        region_indices = [region for region, count in top_regions if region in gdf.index]
        highlight = gdf.loc[region_indices]
        gdf.plot(ax=ax, facecolor="none", edgecolor="lightgray", linewidth=0.4)
        cmap = plt.get_cmap('RdYlGn')
        colors = [cmap(i / (len(highlight)-1)) for i in range(len(highlight))] if len(highlight) > 1 else ['red']*len(highlight)
        for i, (region_id, row) in enumerate(highlight.iterrows()):
            gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=colors[i], edgecolor='black', linewidth=1, zorder=3)
            c = row.centroid
            ax.text(c.x, c.y, str(i+1), fontsize=8, color="black", ha="center", zorder=5)
        # Overlay city boundary in blue
        city_gdf.boundary.plot(ax=ax, color='blue', linewidth=2, zorder=4)
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Voyager)
        ax.set_title(title, fontsize=15, pad=18)
        ax.set_axis_off()
        # Add label for #1 and #50
        if len(top_regions) >= NUM_TOP:
            trip1 = top_regions[0][1]
            trip50 = top_regions[NUM_TOP-1][1]
            ax.text(0.01, 0.99, f"#1: {trip1} trips\n#{NUM_TOP}: {trip50} trips", transform=ax.transAxes,
                    fontsize=14, color="black", va="top", ha="left",
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
        elif len(top_regions) > 0:
            trip1 = top_regions[0][1]
            ax.text(0.01, 0.99, f"#1: {trip1} trips", transform=ax.transAxes,
                    fontsize=14, color="black", va="top", ha="left",
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
        # Overlay BRT stations if toggled
        if overlay_brt[0]:
            xs, ys = zip(*brt_xy)
            ax.scatter(xs, ys, c='deepskyblue', s=80, marker='o', edgecolor='black', zorder=10, label='BRT Station')
        # Overlay POIs if toggled
        if overlay_landmarks[0]:
            for i, (landmark, (x, y)) in enumerate(zip(landmark_data, landmark_xy)):
                ax.scatter(x, y, c=landmark['color'], s=100, marker='o', edgecolor='black', zorder=11)
                ax.text(x, y, landmark['name'], fontsize=3.5, color='white', ha='center', va='center', 
                       weight='bold', zorder=12, bbox=dict(facecolor='black', alpha=0.7, edgecolor='none', pad=1))
    plt.draw()

plot_highlight(0)

# Slider update
def update(val):
    plot_highlight(int(slider.val))
slider.on_changed(update)

    # Function to switch day type
def switch_day(day, button):
    current_day[0] = day
    plot_highlight(int(slider.val))

# Button callbacks
def make_button_callback(day, button):
    def callback(event):
        switch_day(day, button)
    return callback

for btn, day in zip(buttons, day_types):
    btn.on_clicked(make_button_callback(day, btn))

# Set initial day type (Weekday is selected by default)
switch_day('W', buttons[0])

# BRT toggle button callback
def toggle_brt(event):
    overlay_brt[0] = not overlay_brt[0]
    plot_highlight(int(slider.val))
brt_button.on_clicked(toggle_brt)

# POI toggle button callback
def toggle_poi(event):
    overlay_landmarks[0] = not overlay_landmarks[0]
    plot_highlight(int(slider.val))
poi_button.on_clicked(toggle_poi)


# Keyboard event handler for arrow keys
def on_key(event):
    if event.key == 'left':
        slider.set_val((slider.val - 1) % 24)
    elif event.key == 'right':
        slider.set_val((slider.val + 1) % 24)
    elif event.key == 'tab':
        if (current_day[0] == 'W'):
            switch_day('SAT', buttons[1])
        elif (current_day[0] == 'SAT'):
            switch_day('SUN', buttons[2])
        elif (current_day[0] == 'SUN'):
            switch_day('ALL', buttons[3])
        elif (current_day[0] == 'ALL'):
            switch_day('W', buttons[0])

# Connect the key press event
fig.canvas.mpl_connect('key_press_event', on_key)

plt.show()