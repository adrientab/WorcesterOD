import os
import csv

# Function to convert file name to a nice string
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
        return filename  # fallback
    return f"{day} {hour:02d}:00"

# List all relevant CSV files
file_prefixes = ['W', 'SAT', 'SUN']
file_list = []
for prefix in file_prefixes:
    for i in range(24):
        file_list.append(f"{prefix}{i}.csv")

trip_counts = {}

for filename in file_list:
    total_trips = 0
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            # If the first column is a label, skip it
            # Try to sum all numeric values in the row
            for value in row:
                try:
                    total_trips += int(value)
                except ValueError:
                    continue  # skip non-numeric values (e.g., headers or labels)
    # If file starts with 'W', divide total_trips by 5
    if filename.startswith('W'):
        total_trips = total_trips // 5  # Use integer division for consistency
    trip_counts[filename] = total_trips

# Sort files by total trips, descending
sorted_files = sorted(trip_counts.items(), key=lambda x: x[1], reverse=True)

print("Order of files by total trips (most to least):")
for fname, count in sorted_files:
    print(f"{pretty_filename(fname)}: {count} trips")



