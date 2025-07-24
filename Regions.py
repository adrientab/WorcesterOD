import csv
from collections import defaultdict
import re

def pretty_filename(filename):
    if filename.startswith('W'):
        day = 'Weekdays'
        hour = int(filename[1:].split('.')[0])
    elif filename.startswith('SAT'):
        day = 'Saturday'
        hour = int(filename[3:].split('.')[0])
    elif filename.startswith('SUN'):
        day = 'Sunday'
        hour = int(filename[3:].split('.')[0])
    else:
        return filename, -1, ''
    return day, hour, filename

# List all relevant CSV files
file_prefixes = ['W', 'SAT', 'SUN']
file_list = []
for prefix in file_prefixes:
    for i in range(24):
        file_list.append(f"{prefix}{i}.csv")

# (origin, destination, hour) -> total trips (sum across all days)
trip_counts = defaultdict(int)

for filename in file_list:
    match = re.match(r'(W|SAT|SUN)(\d+)\.csv', filename)
    if match:
        hour = int(match.group(2))
    else:
        print(f"Unrecognized filename format: {filename}")
        continue

    with open(filename, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
        for row in rows[1:]:  # skip header
            try:
                # Extract region numbers from "Region X"
                origin = int(row[0].replace("Region ", ""))
                destination = int(row[1].replace("Region ", ""))
                trips = int(float(row[2].strip()))
                #if filename.startswith('W'):
                    #trips = trips // 5
                trip_counts[(origin, destination, hour)] += trips
            except Exception as e:
                print(f"Skipping row due to error: {row} ({e})")
                continue

# Get top 100 (origin, destination, hour) by trip count
top_100 = sorted(trip_counts.items(), key=lambda x: x[1], reverse=True)[:100]

print("Top 100 most popular origin-destination-hour combinations (all days combined):")
for ((origin, destination, hour), count) in top_100:
    print(f"Hour {hour:02d}:00-{hour+1:02d}:00 | Origin {origin} → Destination {destination}: {count} trips")
