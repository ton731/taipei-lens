#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import geopandas as gpd
import pandas as pd
import json
import os

def merge_district_geojson():
    """
    Merge Taipei district shapefile with vulnerability JSON files and building statistics,
    output Mapbox-ready GeoJSON with normalized scores (0-1)
    """

    # File paths
    shp_path = "data/building/臺北市區界圖_20220915/G97_A_CADIST_P.shp"
    population_json_path = "data/social_vulnerability/processed/population_by_age_district.json"
    low_income_json_path = "data/social_vulnerability/processed/low_income_district.json"
    elderly_alone_json_path = "data/social_vulnerability/processed/live_alone_elderly_district.json"
    building_geojson_path = "data/building/geojson/building_4326_age.geojson"
    output_path = "data/district/district_with_features.geojson"

    print("=== Taipei District Vulnerability GeoJSON Generator ===")

    try:
        # 1. Read shapefile
        print(f"\n1. Reading district shapefile: {shp_path}")
        gdf = gpd.read_file(shp_path, encoding='utf-8')

        # Check coordinate system
        if gdf.crs != 'EPSG:4326':
            print("   Converting to WGS84 (EPSG:4326)")
            gdf = gdf.to_crs('EPSG:4326')

        print(f"   Successfully loaded {len(gdf)} districts")
        district_names = sorted(gdf['TNAME'].tolist())
        print(f"   Districts: {district_names}")

        # 2. Read vulnerability JSON files
        print(f"\n2. Reading vulnerability data...")

        with open(population_json_path, 'r', encoding='utf-8') as f:
            population_data = json.load(f)
        print(f"   Population data: {len(population_data)} districts")

        with open(low_income_json_path, 'r', encoding='utf-8') as f:
            low_income_data = json.load(f)
        print(f"   Low income data: {len(low_income_data)} districts")

        with open(elderly_alone_json_path, 'r', encoding='utf-8') as f:
            elderly_alone_data = json.load(f)
        print(f"   Elderly alone data: {len(elderly_alone_data)} districts")

        # 3. Read building GeoJSON
        print(f"\n3. Reading building GeoJSON...")
        buildings_gdf = gpd.read_file(building_geojson_path)
        print(f"   Successfully loaded {len(buildings_gdf):,} buildings")

        # Ensure same CRS
        if buildings_gdf.crs != gdf.crs:
            print(f"   Converting buildings from {buildings_gdf.crs} to {gdf.crs}")
            buildings_gdf = buildings_gdf.to_crs(gdf.crs)

        # 4. Calculate building age statistics by district using spatial join
        print(f"\n4. Calculating building age statistics by district...")

        # Calculate building centroids for spatial join
        buildings_gdf['centroid'] = buildings_gdf.geometry.centroid

        # Perform spatial join to determine which district each building belongs to
        buildings_with_district = gpd.sjoin(
            buildings_gdf[['age', 'centroid']].set_geometry('centroid'),
            gdf[['TNAME', 'geometry']],
            how='left',
            predicate='within'
        )

        print(f"   Completed spatial join")

        # Calculate average building age for each district
        building_stats_by_district = {}

        for district in gdf['TNAME'].unique():
            # Get all buildings in this district
            district_buildings = buildings_with_district[buildings_with_district['TNAME'] == district]

            # Filter out buildings with no age data
            valid_ages = district_buildings['age'].dropna()

            if len(valid_ages) > 0:
                avg_age = valid_ages.mean()
                building_stats_by_district[district] = {
                    'avg_building_age': round(avg_age, 2),
                    'building_count': len(valid_ages)
                }
            else:
                building_stats_by_district[district] = {
                    'avg_building_age': 0,
                    'building_count': 0
                }

        # Show statistics
        print(f"   Building statistics by district:")
        for district in sorted(building_stats_by_district.keys()):
            stats = building_stats_by_district[district]
            print(f"      {district}: {stats['building_count']:,} buildings, avg age: {stats['avg_building_age']:.2f} years")

        # 5. Check data consistency
        print(f"\n5. Checking data consistency...")
        json_districts = set(population_data.keys())
        shp_districts = set(gdf['TNAME'])

        print(f"   Shapefile districts: {sorted(shp_districts)}")
        print(f"   JSON districts: {sorted(json_districts)}")

        if json_districts == shp_districts:
            print("   ✓ All districts match perfectly!")
        else:
            missing_in_json = shp_districts - json_districts
            missing_in_shp = json_districts - shp_districts
            if missing_in_json:
                print(f"   ⚠ Missing in JSON: {missing_in_json}")
            if missing_in_shp:
                print(f"   ⚠ Missing in shapefile: {missing_in_shp}")

        # 6. Collect all values for normalization
        print(f"\n6. Collecting values for normalization...")

        # Collect values for normalization
        all_values = {
            'population_density': [],
            'pop_elderly_percentage': [],
            'low_income_percentage': [],
            'elderly_alone_percentage': [],
            'avg_building_age': []
        }

        for district in json_districts:
            if district in population_data:
                all_values['pop_elderly_percentage'].append(population_data[district]['65歲以上比例'])
            if district in low_income_data:
                all_values['low_income_percentage'].append(low_income_data[district]['低收入戶比例'])
                # Calculate population density (people per square km - assume area calculation later)
                total_pop = low_income_data[district]['行政區總人數']
                # We'll calculate actual density after we have area from shapefile
            if district in elderly_alone_data:
                all_values['elderly_alone_percentage'].append(elderly_alone_data[district]['老人獨居比例'])
            if district in building_stats_by_district:
                avg_age = building_stats_by_district[district]['avg_building_age']
                if avg_age > 0:
                    all_values['avg_building_age'].append(avg_age)

        # Calculate min-max for normalization
        normalization_ranges = {}
        for key in all_values:
            if all_values[key]:
                normalization_ranges[key] = {
                    'min': min(all_values[key]),
                    'max': max(all_values[key])
                }
                print(f"   {key}: {normalization_ranges[key]['min']:.2f} - {normalization_ranges[key]['max']:.2f}")
            else:
                normalization_ranges[key] = {'min': 0, 'max': 1}

        # 7. Merge all data into GeoJSON
        print(f"\n7. Merging data into GeoJSON...")

        # Helper function for normalization
        def normalize_value(value, key):
            """Normalize value using min-max normalization"""
            if key not in normalization_ranges:
                return 0.0
            min_val = normalization_ranges[key]['min']
            max_val = normalization_ranges[key]['max']
            if max_val - min_val == 0:
                return 0.5
            return (value - min_val) / (max_val - min_val)

        for idx, row in gdf.iterrows():
            district = row['TNAME']

            if district in population_data and district in low_income_data and district in elderly_alone_data:
                # Basic info
                gdf.at[idx, 'TOWN'] = district
                total_pop = low_income_data[district]['行政區總人數']
                gdf.at[idx, 'total_population'] = total_pop

                # Population data
                pop_data = population_data[district]
                gdf.at[idx, 'elderly_population'] = pop_data.get('65歲以上人數', 0)

                # Vulnerability indicators (original values)
                elderly_pct = pop_data['65歲以上比例']
                low_income_rate = low_income_data[district]['低收入戶比例']
                elderly_alone_rate = elderly_alone_data[district]['老人獨居比例']

                gdf.at[idx, 'pop_elderly_percentage'] = elderly_pct
                gdf.at[idx, 'low_income_percentage'] = low_income_rate
                gdf.at[idx, 'elderly_alone_percentage'] = elderly_alone_rate

                # Low income data
                gdf.at[idx, 'low_income_households'] = low_income_data[district]['低收入戶戶數']

                # Elderly alone data
                gdf.at[idx, 'living_alone_count'] = elderly_alone_data[district]['獨居人數']

                # Building statistics
                if district in building_stats_by_district:
                    avg_age = building_stats_by_district[district]['avg_building_age']
                    gdf.at[idx, 'avg_building_age'] = avg_age
                else:
                    gdf.at[idx, 'avg_building_age'] = 0
                    avg_age = 0

        # 8. Clean up and optimize GeoJSON
        print(f"\n8. Preparing final GeoJSON...")

        # Define output columns (only keep required columns)
        output_columns = [
            'TOWN',
            'total_population',
            'elderly_population',
            'pop_elderly_percentage',
            'low_income_percentage',
            'elderly_alone_percentage',
            'low_income_households',
            'living_alone_count',
            'avg_building_age',
            'geometry'
        ]

        final_gdf = gdf[output_columns].copy()

        # Rename TOWN to district
        final_gdf = final_gdf.rename(columns={'TOWN': 'district'})

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save to GeoJSON
        final_gdf.to_file(output_path, driver='GeoJSON', encoding='utf-8')

        print(f"   ✓ GeoJSON saved to: {output_path}")
        print(f"   File size: {os.path.getsize(output_path) / 1024:.1f} KB")

        # Show sample data
        print(f"\n=== Sample Data ===")
        for _, row in final_gdf.head(2).iterrows():
            print(f"District: {row['district']}")
            print(f"  Total population: {row['total_population']:,}")
            print(f"  Elderly population: {row['elderly_population']:,}")
            print(f"  Elderly %: {row['pop_elderly_percentage']:.2f}%")
            print(f"  Low income %: {row['low_income_percentage']:.2f}%")
            print(f"  Elderly alone %: {row['elderly_alone_percentage']:.2f}%")
            print(f"  Low income households: {row['low_income_households']:,}")
            print(f"  Living alone count: {row['living_alone_count']:,}")
            print(f"  Avg building age: {row['avg_building_age']:.2f} years")
            print()

        return final_gdf

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = merge_district_geojson()
