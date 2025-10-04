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
    building_geojson_path = "data/building/geojson_w_fragility/building_extracted_with_fragility.geojson"
    
    # Environmental data paths
    lst_geojson_path = "data/ndvi_lst/result_lst_admin.geojson"
    ndvi_geojson_path = "data/ndvi_lst/result_ndvi_admin.geojson"
    viirs_geojson_path = "data/ndvi_lst/taipei_VIIRS_admin.geojson"
    
    output_path = "data/district/district_with_features_test_2.geojson"

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

        # 2.1. Read environmental data (LST and NDVI GeoJSON)
        print(f"\n2.1. Reading environmental data...")
        
        def load_environmental_geojson(geojson_path, value_key, data_name):
            """Load environmental GeoJSON and extract values by district name"""
            try:
                with open(geojson_path, 'r', encoding='utf-8') as f:
                    geojson_data = json.load(f)
                
                environmental_data = {}
                for feature in geojson_data.get('features', []):
                    properties = feature.get('properties', {})
                    district_name = properties.get('TNAME') or properties.get('TOWN')  # Try both field names
                    value = properties.get(value_key)
                    
                    if district_name and value is not None:
                        environmental_data[district_name] = value
                
                print(f"   {data_name} data: {len(environmental_data)} districts")
                return environmental_data
            except Exception as e:
                print(f"   ⚠️ Failed to load {data_name}: {e}")
                return {}

        # Load LST p90 data
        lst_data = load_environmental_geojson(lst_geojson_path, 'p90', 'LST')
        
        # Load NDVI mean data  
        ndvi_data = load_environmental_geojson(ndvi_geojson_path, 'mean', 'NDVI')
        
        # Load VIIRS mean data
        viirs_data = load_environmental_geojson(viirs_geojson_path, '_mean', 'VIIRS')

        # 3. Read building GeoJSON
        print(f"\n3. Reading building GeoJSON...")
        buildings_gdf = gpd.read_file(building_geojson_path)
        print(f"   Successfully loaded {len(buildings_gdf):,} buildings")

        # Read original JSON to preserve fragility_curve format (fix GeoPandas data corruption)
        print(f"   Reading original JSON to preserve fragility_curve format...")
        with open(building_geojson_path, 'r', encoding='utf-8') as f:
            buildings_json = json.load(f)
        
        # Build fragility_curve mapping dictionary (by index)
        fragility_curves = {}
        for i, feature in enumerate(buildings_json['features']):
            fragility_curves[i] = feature['properties'].get('fragility_curve')
        
        # Re-assign correct fragility_curve data to GeoDataFrame
        buildings_gdf['fragility_curve'] = buildings_gdf.index.map(fragility_curves)
        print(f"   Re-assigned fragility_curve data to {len(fragility_curves):,} buildings")

        # Ensure same CRS
        if buildings_gdf.crs != gdf.crs:
            print(f"   Converting buildings from {buildings_gdf.crs} to {gdf.crs}")
            buildings_gdf = buildings_gdf.to_crs(gdf.crs)

        # 4. Calculate building age statistics by district using spatial join
        print(f"\n4. Calculating building age statistics by district...")

        # Calculate building centroids for spatial join
        buildings_gdf['centroid'] = buildings_gdf.geometry.centroid

        # Perform spatial join to determine which district each building belongs to
        # Note: We exclude 'fragility_curve' from sjoin to avoid data corruption
        buildings_with_district = gpd.sjoin(
            buildings_gdf[['age', 'centroid']].set_geometry('centroid'),
            gdf[['TNAME', 'geometry']],
            how='left',
            predicate='within'
        )
        
        # Re-assign fragility_curve data after spatial join to prevent corruption
        buildings_with_district['fragility_curve'] = buildings_with_district.index.map(fragility_curves)

        print(f"   Completed spatial join")

        # Calculate average building age and fragility curve for each district
        building_stats_by_district = {}

        # Define expected fragility curve intensities
        fragility_intensities = ["3", "4", "5弱", "5強", "6弱", "6強", "7"]

        for district in gdf['TNAME'].unique():
            # Get all buildings in this district
            district_buildings = buildings_with_district[buildings_with_district['TNAME'] == district]

            # Filter out buildings with no age data
            valid_ages = district_buildings['age'].dropna()

            # Calculate average age
            if len(valid_ages) > 0:
                avg_age = valid_ages.mean()
                age_count = len(valid_ages)
            else:
                avg_age = 0
                age_count = 0

            # Calculate average fragility curve
            # Filter buildings with valid fragility curve data
            buildings_with_fragility = district_buildings[
                district_buildings['fragility_curve'].notna()
            ]
            
            fragility_sums = {intensity: 0.0 for intensity in fragility_intensities}
            fragility_counts = {intensity: 0 for intensity in fragility_intensities}
            
            for _, building in buildings_with_fragility.iterrows():
                fragility_data = building['fragility_curve']
                if isinstance(fragility_data, dict):
                    for intensity in fragility_intensities:
                        if intensity in fragility_data and fragility_data[intensity] is not None:
                            try:
                                fragility_sums[intensity] += float(fragility_data[intensity])
                                fragility_counts[intensity] += 1
                            except (ValueError, TypeError):
                                continue
            
            # Calculate averages for each intensity
            avg_fragility_curve = {}
            for intensity in fragility_intensities:
                if fragility_counts[intensity] > 0:
                    avg_fragility_curve[intensity] = round(
                        fragility_sums[intensity] / fragility_counts[intensity], 4
                    )
                else:
                    avg_fragility_curve[intensity] = 0.0

            building_stats_by_district[district] = {
                'avg_building_age': round(avg_age, 2),
                'building_count': age_count,
                'avg_fragility_curve': avg_fragility_curve,
                'fragility_building_count': len(buildings_with_fragility)
            }

        # Show statistics
        print(f"   Building statistics by district:")
        for district in sorted(building_stats_by_district.keys()):
            stats = building_stats_by_district[district]
            print(f"      {district}: {stats['building_count']:,} buildings, avg age: {stats['avg_building_age']:.2f} years")
            print(f"        Fragility curve: {stats['fragility_building_count']:,} buildings with data")
            fragility = stats['avg_fragility_curve']
            print(f"        Avg fragility: 3({fragility['3']:.3f}) 4({fragility['4']:.3f}) 5弱({fragility['5弱']:.3f}) 5強({fragility['5強']:.3f}) 6弱({fragility['6弱']:.3f}) 6強({fragility['6強']:.3f}) 7({fragility['7']:.3f})")

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
            'avg_building_age': [],
            'lst_p90': [],
            'ndvi_mean': [],
            'viirs_mean': []
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
            
            # Collect LST p90 values
            if district in lst_data:
                all_values['lst_p90'].append(lst_data[district])
            
            # Collect NDVI mean values  
            if district in ndvi_data:
                all_values['ndvi_mean'].append(ndvi_data[district])
            
            # Collect VIIRS mean values
            if district in viirs_data:
                all_values['viirs_mean'].append(viirs_data[district])

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

        # Initialize avg_fragility_curve column in gdf
        gdf['avg_fragility_curve'] = None

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
                    avg_fragility = building_stats_by_district[district]['avg_fragility_curve']
                    gdf.at[idx, 'avg_building_age'] = avg_age
                    gdf.at[idx, 'avg_fragility_curve'] = avg_fragility
                else:
                    gdf.at[idx, 'avg_building_age'] = 0
                    # Set default fragility curve with all zeros
                    default_fragility = {intensity: 0.0 for intensity in ["3", "4", "5弱", "5強", "6弱", "6強", "7"]}
                    gdf.at[idx, 'avg_fragility_curve'] = default_fragility
                    avg_age = 0

                # Environmental data (LST and NDVI)
                # LST p90 data
                if district in lst_data:
                    gdf.at[idx, 'lst_p90'] = lst_data[district]
                else:
                    gdf.at[idx, 'lst_p90'] = None
                
                # NDVI mean data
                if district in ndvi_data:
                    gdf.at[idx, 'ndvi_mean'] = ndvi_data[district]  
                else:
                    gdf.at[idx, 'ndvi_mean'] = None
                
                # VIIRS mean data
                if district in viirs_data:
                    gdf.at[idx, 'viirs_mean'] = viirs_data[district]
                else:
                    gdf.at[idx, 'viirs_mean'] = None

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
            'avg_fragility_curve',
            'lst_p90',
            'ndvi_mean',
            'viirs_mean',
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
            
            # Environmental data
            lst_val = row['lst_p90']
            ndvi_val = row['ndvi_mean']
            viirs_val = row['viirs_mean']
            print(f"  LST p90: {lst_val:.4f}" if lst_val is not None else "  LST p90: None")
            print(f"  NDVI mean: {ndvi_val:.4f}" if ndvi_val is not None else "  NDVI mean: None")
            print(f"  VIIRS mean: {viirs_val:.4f}" if viirs_val is not None else "  VIIRS mean: None")
            
            fragility = row['avg_fragility_curve']
            print(f"  Avg fragility curve:")
            print(f"    3: {fragility['3']:.4f}, 4: {fragility['4']:.4f}")
            print(f"    5弱: {fragility['5弱']:.4f}, 5強: {fragility['5強']:.4f}")
            print(f"    6弱: {fragility['6弱']:.4f}, 6強: {fragility['6強']:.4f}, 7: {fragility['7']:.4f}")
            print()

        return final_gdf

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = merge_district_geojson()
