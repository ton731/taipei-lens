#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
General GeoJSON Buildings Visualization Script
Visualize buildings from any GeoJSON file using Folium
"""

import json
import folium
from folium import plugins
import numpy as np
from typing import Dict, List, Optional
import webbrowser
import os

# ==================== Configuration ====================
INPUT_JSON = "data/building/geojson/building_4326_combined.geojson"  # Input buildings JSON
OUTPUT_HTML = "data/building/visualization/buildings_map.html"  # Output HTML map
NUM_BUILDINGS_TO_SHOW = 10000  # Number of buildings to visualize

# Map center (Taipei coordinates)
MAP_CENTER = [25.0330, 121.5654]
MAP_ZOOM = 12

# ==================== Helper Functions ====================

def get_building_color(building: Dict) -> str:
    """
    Get color for building

    Args:
        building: Building dictionary

    Returns:
        str: Color string
    """
    # Use consistent blue color for all buildings
    return '#4169E1'  # Royal Blue

def get_building_popup_content(building: Dict, index: int) -> str:
    """
    Generate popup content for a building

    Args:
        building: Building dictionary
        index: Building index

    Returns:
        str: HTML content for popup
    """
    area = building.get('area_sqm', 'N/A')
    max_height = building.get('max_height', 'N/A')
    max_age = building.get('max_age', 'N/A')
    floor = building.get('floor', 'N/A')

    if isinstance(area, (int, float)):
        area = f"{area:.1f} m²"

    popup_html = f"""
    <div style="font-family: Arial, sans-serif; width: 200px;">
        <h4 style="color: #4169E1; margin-bottom: 10px;">
            Building #{index + 1}
        </h4>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 4px; font-weight: bold;">Area:</td>
                <td style="padding: 4px;">{area}</td>
            </tr>
            <tr style="background-color: #f0f0f0;">
                <td style="padding: 4px; font-weight: bold;">Floor:</td>
                <td style="padding: 4px;">{floor}</td>
            </tr>
            <tr>
                <td style="padding: 4px; font-weight: bold;">Max Height:</td>
                <td style="padding: 4px;">{max_height}</td>
            </tr>
            <tr style="background-color: #f0f0f0;">
                <td style="padding: 4px; font-weight: bold;">Max Age:</td>
                <td style="padding: 4px;">{max_age}</td>
            </tr>
        </table>
    </div>
    """
    return popup_html

def create_building_layer(m: folium.Map, buildings: List[Dict], max_buildings: int):
    """
    Add building polygons to the map

    Args:
        m: Folium map object
        buildings: List of building dictionaries
        max_buildings: Maximum number of buildings to show
    """
    # Create feature group for buildings
    building_group = folium.FeatureGroup(name="Buildings")

    buildings_to_show = buildings[:max_buildings]

    for i, building in enumerate(buildings_to_show):
        bounding_polygon = building.get('bounding_polygon')

        if not bounding_polygon:
            continue

        try:
            # Get color based on building properties
            color = get_building_color(building)

            # Create popup content
            popup_content = get_building_popup_content(building, i)

            # Add polygon to map
            folium.GeoJson(
                bounding_polygon,
                style_function=lambda feature, color=color: {
                    'fillColor': color,
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.6,
                },
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"Building #{i + 1}"
            ).add_to(building_group)

        except Exception as e:
            print(f"Warning: Could not add building {i + 1}: {e}")
            continue

    building_group.add_to(m)

def create_legend(m: folium.Map):
    """
    Add legend to the map

    Args:
        m: Folium map object
    """
    legend_html = """
    <div style="position: fixed;
                top: 10px; right: 10px; width: 150px; height: 70px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px">
        <h4 style="margin-top: 0;">Building Legend</h4>
        <p><i class="fa fa-square" style="color:#4169E1"></i> Buildings</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

def create_statistics_panel(buildings: List[Dict], max_buildings: int) -> str:
    """
    Create statistics panel HTML

    Args:
        buildings: List of building dictionaries
        max_buildings: Maximum number of buildings shown

    Returns:
        str: HTML content for statistics panel
    """
    total_buildings = len(buildings)
    shown_buildings = min(max_buildings, total_buildings)

    # Calculate statistics for shown buildings
    shown = buildings[:max_buildings]

    if shown:
        # Area statistics
        areas = [b.get('area_sqm', 0) for b in shown if b.get('area_sqm') is not None]
        if areas:
            avg_area = np.mean(areas)
            max_area = max(areas)
            min_area = min(areas)
        else:
            avg_area = max_area = min_area = 0
    else:
        avg_area = max_area = min_area = 0

    stats_html = f"""
    <div style="position: fixed;
                bottom: 10px; left: 10px; width: 250px; height: 130px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:12px; padding: 10px; overflow-y: auto;">
        <h4 style="margin-top: 0; color: #4169E1;">Statistics</h4>
        <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
            <tr><td><b>Total Buildings:</b></td><td>{total_buildings:,}</td></tr>
            <tr style="background-color: #f0f0f0;"><td><b>Shown:</b></td><td>{shown_buildings:,}</td></tr>
            <tr><td><b>Avg Area:</b></td><td>{avg_area:.0f} m²</td></tr>
            <tr style="background-color: #f0f0f0;"><td><b>Max Area:</b></td><td>{max_area:.0f} m²</td></tr>
            <tr><td><b>Min Area:</b></td><td>{min_area:.0f} m²</td></tr>
        </table>
    </div>
    """
    return stats_html

def main():
    """Main function to create the visualization"""
    print("========== GeoJSON Buildings Visualization ==========")
    print(f"Input file: {INPUT_JSON}")
    print(f"Output file: {OUTPUT_HTML}")
    print(f"Buildings to show: {NUM_BUILDINGS_TO_SHOW}")
    print("=" * 55)

    try:
        # Load buildings data
        print("\nLoading buildings data...")
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)

        buildings = data.get('features', [])
        total_buildings = len(buildings)

        print(f"Loaded {total_buildings} buildings")

        if total_buildings == 0:
            print("No buildings found in the input file.")
            return

        # Create base map
        print("\nCreating map...")
        m = folium.Map(
            location=MAP_CENTER,
            zoom_start=MAP_ZOOM,
            tiles='CartoDB positron',
            control_scale=True
        )

        # # Add additional tile layers
        # folium.TileLayer('CartoDB positron', name='CartoDB Positron').add_to(m)
        # folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)

        # Add building polygons
        print(f"Adding {min(NUM_BUILDINGS_TO_SHOW, total_buildings)} buildings to map...")
        create_building_layer(m, buildings, NUM_BUILDINGS_TO_SHOW)

        # Add legend
        create_legend(m)

        # Add statistics panel
        stats_html = create_statistics_panel(buildings, NUM_BUILDINGS_TO_SHOW)
        m.get_root().html.add_child(folium.Element(stats_html))

        # Add layer control
        folium.LayerControl().add_to(m)

        # Add fullscreen button
        plugins.Fullscreen().add_to(m)

        # Add measure control
        plugins.MeasureControl().add_to(m)

        # Save map
        print("\nSaving map...")
        output_dir = os.path.dirname(OUTPUT_HTML)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        m.save(OUTPUT_HTML)

        print(f"\nMap saved to: {OUTPUT_HTML}")

        # Open in browser
        try:
            webbrowser.open(f'file://{os.path.abspath(OUTPUT_HTML)}')
            print("Map opened in default browser")
        except:
            print("Could not open browser automatically")

        print("\nVisualization completed successfully!")

        # Print summary
        print(f"\nSummary:")
        print(f"- Total buildings available: {total_buildings:,}")
        print(f"- Buildings visualized: {min(NUM_BUILDINGS_TO_SHOW, total_buildings):,}")
        print(f"- Map center: {MAP_CENTER}")

    except FileNotFoundError as e:
        print(f"\nError: File not found - {e}")
        print("Please check if the input file path is correct")
        print("Make sure you have run the building combination script first")

    except json.JSONDecodeError as e:
        print(f"\nError: JSON parsing failed - {e}")
        print("Please check if the input file format is correct")

    except Exception as e:
        print(f"\nUnexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()