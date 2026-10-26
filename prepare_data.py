
from pathlib import Path
import pandas as pd
import geopandas as gpd

# Project folder location
project_folder = Path(__file__).resolve().parent.parent

# Input file paths
csv_path = project_folder / "Data" / "ev_stations_raw.csv"
zones_path = project_folder / "Data" / "chennai_zones.geojson"

# Read input data
stations = pd.read_csv(csv_path)
zones = gpd.read_file(zones_path)

# Inspect the input data
print("Station rows:", len(stations))
print("Station columns:", stations.columns.tolist())

print("Zone features:", len(zones))
print(zones[["zone_id", "geometry"]].head())


# Check missing values
print("\nMissing values:")
print(stations.isna().sum())

# Check duplicate station IDs
print("\nDuplicate station IDs:")
print(stations["station_id"].duplicated().sum())

# Check coordinate data types
print("\nCoordinate data types:")
print(stations[["latitude", "longitude", "power_kw"]].dtypes)

latitude_numeric = pd.to_numeric(
    stations["latitude"],
    errors="coerce"
)
longitude_numeric = pd.to_numeric(
    stations["longitude"],
    errors="coerce"
)

print("\nInvalid longitude values:", longitude_numeric.isna().sum())

print("\nRows with invalid longitude:")
print(
    stations[longitude_numeric.isna()][
        ["station_id", "latitude", "longitude"]
    ]
)

print("Invalid latitude values:", latitude_numeric.isna().sum())
# Show rows where latitude cannot be converted to a number
invalid_latitudes = stations[latitude_numeric.isna()]

print("\nRows with invalid latitude:")
print(invalid_latitudes[["station_id", "latitude", "longitude"]])
# Convert coordinate columns to numeric
stations["latitude"] = pd.to_numeric(
    stations["latitude"], errors="coerce"
)

stations["longitude"] = pd.to_numeric(
    stations["longitude"], errors="coerce"
)

# Check valid coordinate ranges
valid_latitude = stations["latitude"].between(-90, 90)
valid_longitude = stations["longitude"].between(-180, 180)

# Identify invalid stations
invalid_coordinates = stations[
    ~(valid_latitude & valid_longitude)
]

print("\nStations to skip:")
for _, row in invalid_coordinates.iterrows():
    reasons = []

    if pd.isna(row["latitude"]):
        reasons.append("Missing or invalid latitude")
    elif not -90 <= row["latitude"] <= 90:
        reasons.append("Latitude out of range")

    if pd.isna(row["longitude"]):
        reasons.append("Missing or invalid longitude")
    elif not -180 <= row["longitude"] <= 180:
        reasons.append("Longitude out of range")

    print(row["station_id"], "-", ", ".join(reasons))

print("\nTotal stations to skip:", len(invalid_coordinates))
# Replace missing or empty station names
stations["name"] = stations["name"].fillna("Unnamed Station")

stations["name"] = stations["name"].replace(
    r"^\s*$",
    "Unnamed Station",
    regex=True
)

# Keep stations with valid coordinates
valid_stations = stations[
    stations["latitude"].between(-90, 90)
    & stations["longitude"].between(-180, 180)
].copy()

print("\nValid stations:", len(valid_stations))
print("Skipped stations:", len(stations) - len(valid_stations))

#Create a GeoDataFrame using the existing data

stations_gdf = gpd.GeoDataFrame(valid_stations,
    geometry=gpd.points_from_xy(
        valid_stations["longitude"],
        valid_stations["latitude"]
    ),
    crs="EPSG:4326"
)

print(stations_gdf.head())
print("Total features:", len(stations_gdf))
print("Geometry type:", stations_gdf.geometry.geom_type.unique())
print("CRS:", stations_gdf.crs)
# checking stations_gdf and zones CRS Data same or not.
print("Stations CRS:", stations_gdf.crs)
print("Zones CRS:", zones.crs)

print("Both CRS are same:", stations_gdf.crs == zones.crs)



result = gpd.sjoin(
    stations_gdf,
    zones,
    how="left",
    predicate="within"
)

print(result[["station_id", "zone_id"]].head())

# Find stations that do not belong to any zone
no_zone = result[result["zone_id"].isna()]

print("\nStations without a zone:")
print(no_zone["station_id"].tolist())

print("Count:", len(no_zone))

#ZONES Assignment
# Rename station name column
result = result.rename(columns={
    "name_left": "name"
})

# Keep only required properties and geometry
result = result[
    [
        "station_id",
        "name",
        "operator",
        "connector_type",
        "power_kw",
        "zone_id",
        "geometry"
    ]
].copy()

# Export GeoJSON
output_path = project_folder / "stations.geojson"
result.to_file(output_path, driver="GeoJSON")

print("GeoJSON saved:", output_path)
print(result.head())

# 1.USE projected CRS  FOR ZONE AREA
zones_projected = zones.to_crs("EPSG:32644")
zones["area_km2"] = (
    zones_projected.geometry.area / 1_000_000
).round(1)
print(zones[["zone_id", "area_km2"]])

# Keep stations that belong to a zone
zoned_stations = result.dropna(subset=["zone_id"])

# Count stations in each zone
station_count = zoned_stations.groupby("zone_id")["station_id"].count()

# Low power: below 15 kW
low_count = zoned_stations[
    zoned_stations["power_kw"] < 15
].groupby("zone_id")["station_id"].count()

# Medium power: 15 to 50 kW
medium_count = zoned_stations[
    zoned_stations["power_kw"].between(15, 50)
].groupby("zone_id")["station_id"].count()

# High power: above 50 kW
high_count = zoned_stations[
    zoned_stations["power_kw"] > 50
].groupby("zone_id")["station_id"].count()

summary = zones[["zone_id", "area_km2"]].copy()
print("Summary zone IDs:")
print(summary["zone_id"].tolist())

print("Station count index:")
print(station_count.index.tolist())

print("Station counts:")
print(station_count)
summary["station_count"] = summary["zone_id"].map(station_count).fillna(0).astype(int)
summary["low_power_count"] = summary["zone_id"].map(low_count).fillna(0).astype(int)

summary["medium_power_count"] = summary["zone_id"].map(medium_count).fillna(0).astype(int)

summary["high_power_count"] = summary["zone_id"].map(high_count).fillna(0).astype(int)
#summary["station_count"] = station_count
#summary["low_power_count"] = low_count
#summary["medium_power_count"] = medium_count
#summary["high_power_count"] = high_count
summary.to_csv(
    project_folder / "zone_summary.csv",
    index=False
)