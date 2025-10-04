#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Building Age Matching Script
Match building ages from district point data to building polygons in GeoJSON
"""

import json
import os
import glob
from typing import Dict, List, Tuple, Optional
import numpy as np
from scipy.spatial import KDTree
from shapely.geometry import shape, Point
from shapely.ops import transform
import pyproj
from functools import partial
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# ==================== Configuration ====================
# Please modify these paths according to your needs
INPUT_BUILDING_GEOJSON = "data/building/geojson/building_4326_minimized.geojson"  # Input building GeoJSON file
INPUT_AGE_FOLDER = "data/building/taipei_house_age"  # Folder containing district age data
OUTPUT_GEOJSON = "data/building/geojson/building_4326_age.geojson"  # Output GeoJSON file

# Distance threshold (meters)
# Matches beyond this distance will be ignored to avoid incorrect matching
MAX_DISTANCE_METERS = 50

# ==================== Helper Functions ====================

def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calculate geographic distance between two points using Haversine formula

    Args:
        lon1, lat1: Longitude and latitude of first point
        lon2, lat2: Longitude and latitude of second point

    Returns:
        float: Distance in meters
    """
    # Earth radius in meters
    R = 6371000

    # Convert to radians
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    # Haversine formula
    a = np.sin(delta_phi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

    return R * c

def get_polygon_centroid(geometry: Dict) -> Tuple[float, float]:
    """
    Calculate centroid of Polygon or MultiPolygon

    Args:
        geometry: GeoJSON geometry object

    Returns:
        Tuple[float, float]: (longitude, latitude)
    """
    geom = shape(geometry)
    centroid = geom.centroid
    return (centroid.x, centroid.y)

def load_age_data(folder_path: str) -> Tuple[np.ndarray, List[Dict]]:
    """
    Load all district age data and build spatial index

    Args:
        folder_path: Path to folder containing age data JSON files

    Returns:
        Tuple[np.ndarray, List[Dict]]: (coordinate array, age data list)
    """
    all_age_data = []
    coordinates = []

    # Find all JSON files
    json_files = glob.glob(os.path.join(folder_path, "*.json"))

    print(f"Found {len(json_files)} district data files")

    for json_file in tqdm(json_files, desc="Loading age data"):
        district_name = os.path.basename(json_file).replace('.json', '')

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Process each feature
            for feature in data:
                if feature.get('type') == 'Feature':
                    props = feature.get('properties', {})

                    # Use long and lat from properties (these are the correct coordinates)
                    lon = props.get('long')
                    lat = props.get('lat')
                    age = props.get('age', None)

                    if lon is not None and lat is not None:
                        coordinates.append([lon, lat])
                        all_age_data.append({
                            'lon': lon,
                            'lat': lat,
                            'age': age
                        })

        except Exception as e:
            print(f"Error reading {district_name}: {e}")

    print(f"Total {len(all_age_data)} age records loaded")

    if len(coordinates) == 0:
        raise ValueError("No age data loaded")

    return np.array(coordinates), all_age_data

def match_building_ages(building_geojson: Dict, age_coords: np.ndarray,
                       age_data: List[Dict], max_distance: float) -> Dict:
    """
    Match nearest age data for each building

    Args:
        building_geojson: Building GeoJSON data
        age_coords: Age data coordinate array
        age_data: Age data list
        max_distance: Maximum matching distance (meters)

    Returns:
        Dict: Updated GeoJSON data
    """
    # Build KDTree for fast nearest neighbor search
    kdtree = KDTree(age_coords)

    matched_count = 0
    no_match_count = 0
    distance_stats = []

    features = building_geojson.get('features', [])

    print(f"Starting to match ages for {len(features)} buildings...")

    for feature in tqdm(features, desc="Matching ages"):
        geometry = feature.get('geometry')

        if geometry:
            try:
                # Calculate building centroid
                centroid = get_polygon_centroid(geometry)

                # Find nearest age point
                distance, index = kdtree.query(centroid)

                # Get actual age data
                nearest_age_data = age_data[index]

                # Calculate actual geographic distance (meters)
                actual_distance = haversine_distance(
                    centroid[0], centroid[1],
                    nearest_age_data['lon'], nearest_age_data['lat']
                )

                # Check if distance is within threshold
                if actual_distance <= max_distance:
                    # Add age to feature properties
                    if 'properties' not in feature:
                        feature['properties'] = {}

                    # Check if age is NA or invalid, convert to None
                    age_raw = nearest_age_data['age']
                    if age_raw and str(age_raw).strip() != "NA":
                        # 這個年齡資料是 2017 年的資料，現在是 2025 年，所以需要加上 8 年，修正年齡
                        try:
                            age_value = int(age_raw)
                            feature['properties']['age'] = age_value + 8
                        except (ValueError, TypeError):
                            # 如果無法轉換成整數，設為 None
                            feature['properties']['age'] = None
                    else:
                        # If age is NA or empty, set to None
                        feature['properties']['age'] = None

                    matched_count += 1
                    distance_stats.append(actual_distance)
                else:
                    # Distance too far, don't match
                    if 'properties' not in feature:
                        feature['properties'] = {}
                    feature['properties']['age'] = None

                    no_match_count += 1

            except Exception as e:
                print(f"Error processing building: {e}")
                no_match_count += 1

    # Output statistics
    print("\n===== Matching Statistics =====")
    print(f"Successfully matched: {matched_count} buildings")
    print(f"Not matched: {no_match_count} buildings")

    if distance_stats:
        print(f"Matching distance statistics:")
        print(f"  Min: {min(distance_stats):.2f} meters")
        print(f"  Max: {max(distance_stats):.2f} meters")
        print(f"  Mean: {np.mean(distance_stats):.2f} meters")
        print(f"  Median: {np.median(distance_stats):.2f} meters")

    return building_geojson

def main():
    """Main program"""
    print("========== Building Age Matching Program ==========")
    print(f"Input building file: {INPUT_BUILDING_GEOJSON}")
    print(f"Input age folder: {INPUT_AGE_FOLDER}")
    print(f"Output file: {OUTPUT_GEOJSON}")
    print(f"Max matching distance: {MAX_DISTANCE_METERS} meters")
    print("=" * 50)

    try:
        # 1. Load building GeoJSON
        print("\nLoading building data...")
        with open(INPUT_BUILDING_GEOJSON, 'r', encoding='utf-8') as f:
            building_geojson = json.load(f)
        print(f"Loaded {len(building_geojson.get('features', []))} buildings")

        # 2. Load age data
        print("\nLoading age data...")
        age_coords, age_data = load_age_data(INPUT_AGE_FOLDER)

        # 3. Perform matching
        print("\nStarting age matching...")
        updated_geojson = match_building_ages(
            building_geojson,
            age_coords,
            age_data,
            MAX_DISTANCE_METERS
        )

        # 4. Post-process: Clean up any remaining "NA" values
        print("\nCleaning up NA values...")
        for feature in updated_geojson.get('features', []):
            if 'properties' in feature and 'age' in feature['properties']:
                age_value = feature['properties']['age']
                if isinstance(age_value, str) and age_value.strip() == "NA":
                    feature['properties']['age'] = None

        # 5. Save results
        print("\nSaving results...")
        # Ensure output directory exists
        output_dir = os.path.dirname(OUTPUT_GEOJSON)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(OUTPUT_GEOJSON, 'w', encoding='utf-8') as f:
            json.dump(updated_geojson, f, ensure_ascii=False, indent=2)

        print(f"\nResults saved to: {OUTPUT_GEOJSON}")
        print("\nProgram completed successfully!")

    except FileNotFoundError as e:
        print(f"\nError: File not found - {e}")
        print("Please check if input file paths are correct")

    except json.JSONDecodeError as e:
        print(f"\nError: JSON parsing failed - {e}")
        print("Please check if JSON file format is correct")

    except Exception as e:
        print(f"\nUnexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()