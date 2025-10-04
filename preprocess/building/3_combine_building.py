#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Building Polygon Combination Script
Combine multiple polygons that belong to the same building based on proximity
"""

import json
import os
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from shapely.geometry import shape, Polygon, MultiPolygon, mapping
from shapely.ops import unary_union
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# ==================== Configuration ====================
# Please modify these paths according to your needs
INPUT_GEOJSON = "data/building/geojson/building_4326_age.geojson"  # Input GeoJSON file with building polygons
OUTPUT_JSON = "data/building/geojson/building_4326_combined.geojson"  # Output JSON file with combined buildings

# No distance threshold needed for iterative merging
# Polygons are merged based on geometric intersection/containment only

# ==================== Helper Functions ====================

def get_polygon_centroid(geometry: Dict) -> Tuple[float, float]:
    """
    Get the centroid of a polygon or multipolygon

    Args:
        geometry: GeoJSON geometry object

    Returns:
        Tuple[float, float]: (longitude, latitude)
    """
    geom = shape(geometry)
    centroid = geom.centroid
    return (centroid.x, centroid.y)

def create_bounding_polygon(geometries: List[Dict]) -> Dict:
    """
    Create a union polygon that contains all input geometries (not convex hull!)

    Args:
        geometries: List of GeoJSON geometry objects

    Returns:
        Dict: GeoJSON polygon that represents the union of all input geometries
    """
    # Convert all geometries to shapely objects and fix invalid ones
    shapes = []
    for geom in geometries:
        try:
            shp = shape(geom)
            # Fix invalid geometries
            if not shp.is_valid:
                shp = shp.buffer(0)  # Common fix for invalid geometries
            if shp.is_valid and not shp.is_empty:
                shapes.append(shp)
        except Exception as e:
            print(f"Warning: Could not process geometry: {e}")
            continue

    if not shapes:
        # If no valid shapes, return a simple point geometry
        return {"type": "Point", "coordinates": [0, 0]}

    try:
        # Union all shapes - this is the actual combined shape, not just a bounding box
        union = unary_union(shapes)

        # Don't use convex hull! Use the actual union which preserves the real shape
        # bounding = union.convex_hull  # This was the problem!

        # Convert back to GeoJSON
        return mapping(union)
    except Exception as e:
        print(f"Warning: Could not create union, using envelope instead: {e}")
        # Fallback: use envelope of all geometries
        all_coords = []
        for shp in shapes:
            bounds = shp.bounds
            all_coords.extend([[bounds[0], bounds[1]], [bounds[2], bounds[3]]])

        if all_coords:
            from shapely.geometry import MultiPoint
            envelope = MultiPoint(all_coords).envelope
            return mapping(envelope)
        else:
            return {"type": "Point", "coordinates": [0, 0]}

def calculate_area(geometry: Dict) -> float:
    """
    Calculate the area of a polygon in square meters (approximate)

    Args:
        geometry: GeoJSON geometry object

    Returns:
        float: Area in square meters
    """
    geom = shape(geometry)

    # Convert degrees to meters (approximate)
    # At latitude 25 (approximately Taipei), 1 degree H 111000 meters in longitude
    # and 1 degree H 110500 meters in latitude
    # This is a simplified calculation

    # Get the bounds
    minx, miny, maxx, maxy = geom.bounds
    center_lat = (miny + maxy) / 2

    # Approximate conversion factors
    meters_per_degree_lon = 111000 * np.cos(np.radians(center_lat))
    meters_per_degree_lat = 110500

    # Calculate area in degrees squared
    area_degrees = geom.area

    # Convert to square meters (approximate)
    area_meters = area_degrees * meters_per_degree_lon * meters_per_degree_lat

    return area_meters

def get_max_height(features: List[Dict]) -> Optional[float]:
    """
    Get the maximum height/floor value from a list of features

    Args:
        features: List of GeoJSON features

    Returns:
        float: Maximum height/floor value, or None if not found
    """
    max_height = None

    for feature in features:
        props = feature.get('properties', {})

        # Try different possible height/floor field names
        height_fields = ['屋頂高', 'height', 'floors', '樓層', '樓層註']

        for field in height_fields:
            if field in props:
                try:
                    height = float(props[field]) if props[field] is not None else None
                    if height is not None:
                        if max_height is None or height > max_height:
                            max_height = height
                except (ValueError, TypeError):
                    continue

    return max_height

def get_max_age(features: List[Dict]) -> Optional[str]:
    """
    Get the maximum age from a list of features

    Args:
        features: List of GeoJSON features

    Returns:
        str: Maximum age value, or None if not found
    """
    max_age = None

    for feature in features:
        props = feature.get('properties', {})
        age = props.get('age')

        if age is not None:
            try:
                # Try to convert to int for comparison
                age_int = int(age) if age != '' else 0
                max_age_int = int(max_age) if max_age is not None and max_age != '' else 0

                if max_age is None or age_int > max_age_int:
                    max_age = age
            except (ValueError, TypeError):
                # If conversion fails, use string comparison
                if max_age is None or str(age) > str(max_age):
                    max_age = age

    return max_age

def get_mode_floor(features: List[Dict]) -> Optional[int]:
    """
    Get the mode (most frequent) floor value from a list of features

    Args:
        features: List of GeoJSON features

    Returns:
        int: Mode floor value, or None if not found
    """
    from collections import Counter

    floor_values = []

    for feature in features:
        props = feature.get('properties', {})

        # Try different possible floor field names
        floor_fields = ['floors', 'floor', '樓層', '樓層數', 'FLOORS']

        for field in floor_fields:
            if field in props:
                try:
                    floor = props[field]
                    if floor is not None and floor != '':
                        # Try to convert to int
                        floor_int = int(float(str(floor)))
                        floor_values.append(floor_int)
                        break  # Found a valid floor value, move to next feature
                except (ValueError, TypeError):
                    continue

    if not floor_values:
        return None

    # Get the mode (most frequent value)
    floor_counter = Counter(floor_values)
    mode_floor, count = floor_counter.most_common(1)[0]

    return mode_floor

def iterative_merge_polygons(features: List[Dict]) -> List[List[int]]:
    """
    Iteratively merge polygons that intersect or contain each other using spatial indexing

    Args:
        features: List of GeoJSON features

    Returns:
        List[List[int]]: List of merged groups, each group is a list of feature indices
    """
    print("Starting optimized iterative polygon merging...")

    # Convert all features to shapely geometries and track valid indices
    geometries = []
    valid_indices = []
    bounds_list = []

    for i, feature in enumerate(features):
        if 'geometry' in feature and feature['geometry'] is not None:
            try:
                geom = shape(feature['geometry'])
                # Fix invalid geometries
                if not geom.is_valid:
                    geom = geom.buffer(0)
                if geom.is_valid and not geom.is_empty:
                    geometries.append(geom)
                    valid_indices.append(i)
                    bounds_list.append(geom.bounds)
            except Exception as e:
                print(f"Warning: Could not process geometry for feature {i}: {e}")
                continue

    if not geometries:
        return []

    print(f"Loaded {len(geometries)} valid geometries")

    # Build spatial index using RTrees for fast intersection queries
    try:
        from rtree import index
        print("Building spatial index...")

        # Create spatial index
        idx = index.Index()
        for i, bounds in enumerate(tqdm(bounds_list, desc="Building spatial index")):
            idx.insert(i, bounds)

        print("✅ Spatial index built successfully")
        use_spatial_index = True
    except ImportError:
        print("⚠️  RTrees not available, falling back to bounds-based optimization")
        use_spatial_index = False

    # Initialize: each polygon is its own group
    groups = [[i] for i in range(len(geometries))]
    group_bounds = bounds_list.copy()  # Track bounds for each group

    round_num = 1
    total_merges = 0

    while True:
        print(f"\n=== Round {round_num} ===")
        print(f"Processing {len(groups)} groups...")
        merges_this_round = 0
        new_groups = []
        new_group_bounds = []
        merged_indices = set()

        # Check each group for potential merges
        with tqdm(total=len(groups), desc=f"Round {round_num} - Checking groups") as pbar:
            for i in range(len(groups)):
                if i in merged_indices:
                    pbar.update(1)
                    continue

                current_group = groups[i]
                current_bounds = group_bounds[i]

                # Get union of all geometries in current group
                current_geometries = [geometries[idx] for idx in current_group]
                try:
                    if len(current_geometries) == 1:
                        current_union = current_geometries[0]
                    else:
                        current_union = unary_union(current_geometries)
                        if not current_union.is_valid:
                            current_union = current_union.buffer(0)
                except Exception:
                    # If union fails, skip this group
                    new_groups.append(current_group)
                    new_group_bounds.append(current_bounds)
                    merged_indices.add(i)
                    pbar.update(1)
                    continue

                # Find potential intersection candidates
                merged_with = []

                if use_spatial_index:
                    # Use spatial index to find candidates
                    candidate_indices = list(idx.intersection(current_bounds))
                    # Filter to only include groups we haven't processed yet
                    candidate_indices = [j for j in candidate_indices
                                       if j > i and j < len(groups) and j not in merged_indices]
                else:
                    # Use bounds-based filtering for faster candidate selection
                    minx, miny, maxx, maxy = current_bounds
                    candidate_indices = []

                    for j in range(i + 1, len(groups)):
                        if j in merged_indices:
                            continue

                        # Quick bounds check before expensive geometry operations
                        other_bounds = group_bounds[j]
                        ominx, ominy, omaxx, omaxy = other_bounds

                        # Check if bounding boxes overlap OR one contains the other
                        # Standard overlap check
                        boxes_overlap = (minx <= omaxx and maxx >= ominx and
                                       miny <= omaxy and maxy >= ominy)

                        # Additional check for containment (one box completely inside another)
                        current_contains_other = (minx <= ominx and maxx >= omaxx and
                                                miny <= ominy and maxy >= omaxy)
                        other_contains_current = (ominx <= minx and omaxx >= maxx and
                                                ominy <= miny and omaxy >= maxy)

                        # Use bounding box as initial filter, but add a small buffer to account for precision issues
                        # This is just for candidate selection - actual merging decision is made by geometry checks
                        if boxes_overlap or current_contains_other or other_contains_current:
                            candidate_indices.append(j)

                # Check geometric intersection for candidates only
                for j in candidate_indices:
                    if j in merged_indices:
                        continue

                    other_group = groups[j]
                    other_geometries = [geometries[idx] for idx in other_group]

                    try:
                        if len(other_geometries) == 1:
                            other_union = other_geometries[0]
                        else:
                            other_union = unary_union(other_geometries)
                            if not other_union.is_valid:
                                other_union = other_union.buffer(0)
                    except Exception:
                        continue

                    # Check if they should be merged
                    try:
                        should_merge = False

                        # IMPORTANT: First verify that the polygons actually have a geometric relationship
                        # This prevents false positives from bounding box overlaps
                        if not current_union.disjoint(other_union):
                            # They have some kind of geometric relationship (not completely separate)

                            # 1. Check if one polygon completely contains the other
                            if current_union.contains(other_union) or other_union.contains(current_union):
                                should_merge = True

                            # 2. Check if they overlap significantly (share interior area)
                            elif current_union.overlaps(other_union):
                                # overlaps() returns True only if geometries share interior points
                                # This means they actually overlap in 2D space, not just touch
                                should_merge = True

                            # 3. Check if they intersect with meaningful area
                            elif current_union.intersects(other_union):
                                try:
                                    intersection = current_union.intersection(other_union)
                                    # Check if intersection has area (not just touching at points/edges)
                                    if hasattr(intersection, 'area') and intersection.area > 0:
                                        # Additional check: intersection area should be meaningful relative to smaller polygon
                                        smaller_area = min(current_union.area, other_union.area)
                                        if intersection.area > smaller_area * 0.01:  # At least 1% overlap
                                            should_merge = True
                                except Exception:
                                    pass

                            # 4. Check for adjacent polygons (with strict conditions)
                            # Only consider if they actually touch (not just close)
                            if not should_merge and current_union.touches(other_union):
                                try:
                                    # Additional validation: only merge if they share a significant boundary
                                    # Get the boundary intersection
                                    boundary_intersection = current_union.boundary.intersection(other_union.boundary)

                                    # Only merge if the shared boundary is substantial
                                    if hasattr(boundary_intersection, 'length') and boundary_intersection.length > 0:
                                        # Calculate the relative length of shared boundary
                                        current_perimeter = current_union.boundary.length
                                        other_perimeter = other_union.boundary.length
                                        min_perimeter = min(current_perimeter, other_perimeter)

                                        # Only merge if shared boundary is at least 10% of the smaller polygon's perimeter
                                        if boundary_intersection.length > min_perimeter * 0.1:
                                            should_merge = True
                                except Exception as e:
                                    # If boundary analysis fails, be conservative and don't merge
                                    pass

                                # Removed buffer checking - even small gaps indicate separate buildings

                        # 5. Check if one polygon is very close to being inside another (for edge cases)
                        if not should_merge:
                            try:
                                # Check if a large percentage of one polygon is within the other
                                current_in_other = current_union.intersection(other_union.buffer(0.00001))
                                other_in_current = other_union.intersection(current_union.buffer(0.00001))

                                if hasattr(current_in_other, 'area') and hasattr(other_in_current, 'area'):
                                    current_overlap_ratio = current_in_other.area / current_union.area if current_union.area > 0 else 0
                                    other_overlap_ratio = other_in_current.area / other_union.area if other_union.area > 0 else 0

                                    # If a large portion of either polygon is within the other, merge them
                                    if current_overlap_ratio > 0.8 or other_overlap_ratio > 0.8:
                                        should_merge = True
                            except Exception:
                                pass

                        if should_merge:
                            merged_with.append(j)
                            merged_indices.add(j)
                            merges_this_round += 1

                    except Exception:
                        # If geometric operations fail, don't merge
                        pass

                # Merge current group with all groups it intersects with
                merged_group = current_group.copy()
                merged_bounds = list(current_bounds)

                for j in merged_with:
                    merged_group.extend(groups[j])
                    # Update bounds to encompass all merged groups
                    other_bounds = group_bounds[j]
                    merged_bounds[0] = min(merged_bounds[0], other_bounds[0])  # minx
                    merged_bounds[1] = min(merged_bounds[1], other_bounds[1])  # miny
                    merged_bounds[2] = max(merged_bounds[2], other_bounds[2])  # maxx
                    merged_bounds[3] = max(merged_bounds[3], other_bounds[3])  # maxy

                new_groups.append(merged_group)
                new_group_bounds.append(tuple(merged_bounds))
                merged_indices.add(i)
                pbar.update(1)

        print(f"Round {round_num} results: {merges_this_round} merges performed")
        print(f"Groups reduced from {len(groups)} to {len(new_groups)}")
        total_merges += merges_this_round

        # If no merges happened, we're done
        if merges_this_round == 0:
            break

        groups = new_groups
        group_bounds = new_group_bounds
        round_num += 1

        # Rebuild spatial index for next round if using it
        if use_spatial_index and merges_this_round > 0:
            idx = index.Index()
            for i, bounds in enumerate(group_bounds):
                idx.insert(i, bounds)

        # Safety check - don't run forever
        if round_num > 20:
            print("    Warning: Stopped after 20 rounds to prevent infinite loop")
            break

        # Diagnostic: if we haven't merged anything for 2 rounds, try a more aggressive approach
        if round_num > 2 and merges_this_round == 0:
            print("    🔍 No merges in this round - checking for missed containments...")

            # Do a final pass to catch any remaining containments we might have missed
            additional_merges = 0
            final_new_groups = []
            final_merged_indices = set()

            with tqdm(total=len(groups), desc="Final containment check", leave=False) as pbar:
                for i in range(len(groups)):
                    if i in final_merged_indices:
                        pbar.update(1)
                        continue

                    current_group = groups[i]
                    current_geoms = [geometries[idx] for idx in current_group]

                    try:
                        if len(current_geoms) == 1:
                            current_union = current_geoms[0]
                        else:
                            current_union = unary_union(current_geoms)
                            if not current_union.is_valid:
                                current_union = current_union.buffer(0)
                    except Exception:
                        final_new_groups.append(current_group)
                        final_merged_indices.add(i)
                        pbar.update(1)
                        continue

                    # Check ALL other groups (not just remaining ones) for containment
                    final_merged_with = []
                    for j in range(len(groups)):
                        if j == i or j in final_merged_indices:
                            continue

                        other_group = groups[j]
                        other_geoms = [geometries[idx] for idx in other_group]

                        try:
                            if len(other_geoms) == 1:
                                other_union = other_geoms[0]
                            else:
                                other_union = unary_union(other_geoms)
                                if not other_union.is_valid:
                                    other_union = other_union.buffer(0)
                        except Exception:
                            continue

                        # Enhanced containment and adjacency check
                        try:
                            # Check containment
                            if current_union.contains(other_union) or other_union.contains(current_union):
                                final_merged_with.append(j)
                                final_merged_indices.add(j)
                                additional_merges += 1
                            # Check if they touch (with boundary validation)
                            elif current_union.touches(other_union):
                                # Only merge if they share substantial boundary
                                try:
                                    boundary_intersection = current_union.boundary.intersection(other_union.boundary)
                                    if hasattr(boundary_intersection, 'length') and boundary_intersection.length > 0:
                                        current_perimeter = current_union.boundary.length
                                        other_perimeter = other_union.boundary.length
                                        min_perimeter = min(current_perimeter, other_perimeter)

                                        # Only merge if shared boundary is at least 10% of smaller perimeter
                                        if boundary_intersection.length > min_perimeter * 0.1:
                                            final_merged_with.append(j)
                                            final_merged_indices.add(j)
                                            additional_merges += 1
                                except Exception:
                                    pass
                        except Exception:
                            pass

                    # Merge if found any
                    final_merged_group = current_group.copy()
                    for j in final_merged_with:
                        final_merged_group.extend(groups[j])

                    final_new_groups.append(final_merged_group)
                    final_merged_indices.add(i)
                    pbar.update(1)

            if additional_merges > 0:
                print(f"    ✅ Found {additional_merges} additional containment merges!")
                groups = final_new_groups
                # Update bounds for merged groups
                new_group_bounds = []
                for group in groups:
                    group_geoms = [geometries[idx] for idx in group]
                    all_bounds = [geometries[idx].bounds for idx in group]
                    if all_bounds:
                        minx = min(b[0] for b in all_bounds)
                        miny = min(b[1] for b in all_bounds)
                        maxx = max(b[2] for b in all_bounds)
                        maxy = max(b[3] for b in all_bounds)
                        new_group_bounds.append((minx, miny, maxx, maxy))
                    else:
                        new_group_bounds.append((0, 0, 0, 0))
                group_bounds = new_group_bounds
                merges_this_round = additional_merges
                total_merges += additional_merges

                # Rebuild spatial index
                if use_spatial_index:
                    idx = index.Index()
                    for i, bounds in enumerate(group_bounds):
                        idx.insert(i, bounds)
            else:
                print("    ℹ️  No additional containments found")
                break

    # Skip final cleanup - it's too slow for large datasets
    print(f"\n⏭️  Skipping final cleanup to avoid long processing time...")

    print(f"\n🎉 Merging completed!")
    print(f"📊 Summary:")
    print(f"   • Total rounds: {round_num-1}")
    print(f"   • Total merges: {total_merges}")
    print(f"   • Original polygons: {len(geometries)}")
    print(f"   • Final groups: {len(groups)}")
    print(f"   • Reduction: {len(geometries) - len(groups)} polygons merged")

    # Convert back to original feature indices
    final_groups = []
    for group in groups:
        original_indices = [valid_indices[idx] for idx in group]
        final_groups.append(original_indices)

    return final_groups

def combine_building_cluster(features: List[Dict], indices: List[int]) -> Dict:
    """
    Combine a cluster of features into a single building object

    Args:
        features: List of all GeoJSON features
        indices: List of indices representing features in this cluster

    Returns:
        Dict: Combined building object
    """
    # Get features in this cluster
    cluster_features = [features[i] for i in indices]

    # Extract geometries
    geometries = [f['geometry'] for f in cluster_features if 'geometry' in f and f['geometry'] is not None]

    if not geometries:
        return None

    # Create bounding polygon
    bounding_polygon = create_bounding_polygon(geometries)

    # Calculate area
    area = calculate_area(bounding_polygon)

    # Get maximum height
    max_height = get_max_height(cluster_features)

    # Get maximum age
    max_age = get_max_age(cluster_features)

    # Get mode floor (most frequent floor value)
    mode_floor = get_mode_floor(cluster_features)

    # Create combined building object
    building = {
        'bounding_polygon': bounding_polygon,
        'area_sqm': round(area, 2),
        'max_height': max_height,
        'max_age': max_age,
        'floor': mode_floor,
        'num_polygons': len(cluster_features),
        'polygons': cluster_features
    }

    return building

def process_buildings(input_file: str, output_file: str):
    """
    Main processing function to combine building polygons

    Args:
        input_file: Path to input GeoJSON file
        output_file: Path to output JSON file
    """
    print("========== Building Polygon Combination ==========")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print("Method: Iterative geometric merging")
    print("=" * 50)

    try:
        # Load GeoJSON
        print("\nLoading GeoJSON data...")
        with open(input_file, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)

        features = geojson_data.get('features', [])
        print(f"Loaded {len(features)} polygon features")

        # Merge intersecting/overlapping polygons
        print("\nMerging intersecting/overlapping polygons...")
        merged_groups = iterative_merge_polygons(features)
        print(f"Found {len(merged_groups)} merged building groups")

        # Combine merged groups into buildings
        print("\nCombining polygon groups into buildings...")
        buildings = []

        for group_indices in tqdm(merged_groups, desc="Processing buildings"):
            building = combine_building_cluster(features, group_indices)
            if building is not None:
                buildings.append(building)

        print(f"Successfully processed {len(buildings)} buildings")

        # Statistics
        total_polygons = sum(b['num_polygons'] for b in buildings)
        avg_polygons = total_polygons / len(buildings) if buildings else 0
        max_polygons = max(b['num_polygons'] for b in buildings) if buildings else 0
        single_polygon_buildings = sum(1 for b in buildings if b['num_polygons'] == 1)

        print("\n===== Statistics =====")
        print(f"Total buildings: {len(buildings)}")
        print(f"Total polygons: {total_polygons}")
        print(f"Average polygons per building: {avg_polygons:.2f}")
        print(f"Maximum polygons in a building: {max_polygons}")
        print(f"Buildings with single polygon: {single_polygon_buildings}")

        # Save results
        print("\nSaving results...")
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_data = {
            'type': 'BuildingCollection',
            'metadata': {
                'total_buildings': len(buildings),
                'total_polygons': total_polygons,
                'merge_method': 'iterative_geometric',
                'source_file': input_file
            },
            'features': buildings
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False)

        print(f"\nResults saved to: {output_file}")
        print("\nProgram completed successfully!")

    except FileNotFoundError as e:
        print(f"\nError: File not found - {e}")
        print("Please check if input file path is correct")

    except json.JSONDecodeError as e:
        print(f"\nError: JSON parsing failed - {e}")
        print("Please check if JSON file format is correct")

    except Exception as e:
        print(f"\nUnexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main entry point"""
    process_buildings(
        INPUT_GEOJSON,
        OUTPUT_JSON
    )

if __name__ == "__main__":
    main()