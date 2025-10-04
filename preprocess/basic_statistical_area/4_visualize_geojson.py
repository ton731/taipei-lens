#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡單視覺化 GeoJSON 檔案 - 只顯示邊界
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from shapely.geometry import shape
import matplotlib.patches as patches
from matplotlib.collections import PatchCollection

# ==================== Configuration ====================
INPUT_GEOJSON = "data/basic_statistical_area/geojson/basic_statistical_area_with_vulnerability.geojson"
OUTPUT_PNG = "data/basic_statistical_area/visualization/geojson_boundaries.png"

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_geojson(geojson_path):
    """載入 GeoJSON 檔案"""
    try:
        print(f"📂 載入 GeoJSON: {geojson_path}")

        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 處理不同的 GeoJSON 格式
        if 'features' in data:
            features = data['features']
        elif 'type' in data and data['type'] == 'FeatureCollection':
            features = data.get('features', [])
        elif isinstance(data, list):
            features = data
        else:
            features = [data]

        print(f"✅ 成功載入 {len(features)} 個區域")
        return features

    except Exception as e:
        print(f"❌ 載入失敗: {e}")
        return None

def create_polygon_patches(features):
    """將 GeoJSON features 轉換為 matplotlib patches"""
    patches_list = []

    print("🔄 處理多邊形資料...")

    for i, feature in enumerate(features):
        try:
            # 使用 shapely 處理幾何資料
            geom = shape(feature['geometry'])

            # 處理不同類型的幾何圖形
            if geom.geom_type == 'Polygon':
                # 單一多邊形
                coords = list(geom.exterior.coords)
                patch = patches.Polygon(coords, closed=True)
                patches_list.append(patch)

            elif geom.geom_type == 'MultiPolygon':
                # 多個多邊形
                for poly in geom.geoms:
                    coords = list(poly.exterior.coords)
                    patch = patches.Polygon(coords, closed=True)
                    patches_list.append(patch)

        except Exception as e:
            print(f"⚠️  處理第 {i+1} 個區域時發生錯誤: {e}")
            continue

    print(f"✅ 成功處理 {len(patches_list)} 個多邊形")
    return patches_list

def visualize_boundaries(features):
    """視覺化邊界"""

    # 轉換為 matplotlib patches
    polygon_patches = create_polygon_patches(features)

    if not polygon_patches:
        print("❌ 沒有可視覺化的多邊形")
        return None

    # 建立圖形
    fig, ax = plt.subplots(1, 1, figsize=(15, 12))

    # 建立 PatchCollection
    patch_collection = PatchCollection(
        polygon_patches,
        facecolors='lightblue',
        edgecolors='red',
        linewidths=1.5,
        alpha=0.6
    )

    # 加入到圖形
    ax.add_collection(patch_collection)

    # 設定圖形範圍
    ax.autoscale()

    # 設定標題和標籤
    ax.set_title('GeoJSON 區域邊界視覺化', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('經度', fontsize=12)
    ax.set_ylabel('緯度', fontsize=12)

    # 加入網格
    ax.grid(True, alpha=0.3)

    # 設定等比例
    ax.set_aspect('equal')

    # 加入統計資訊
    total_areas = len(features)
    total_polygons = len(polygon_patches)

    stats_text = f"""
統計資訊:
• 總區域數: {total_areas}
• 總多邊形數: {total_polygons}
• 邊界顏色: 紅色
• 填色: 淺藍色
    """

    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()

    return fig

def main():
    """主函數"""
    print("=" * 60)
    print("🗺️  GeoJSON 邊界視覺化工具")
    print("=" * 60)
    print(f"📂 輸入檔案: {INPUT_GEOJSON}")
    print(f"📁 輸出檔案: {OUTPUT_PNG}")
    print("-" * 60)

    try:
        # 檢查輸入檔案
        if not Path(INPUT_GEOJSON).exists():
            raise FileNotFoundError(f"找不到檔案: {INPUT_GEOJSON}")

        # 載入 GeoJSON
        features = load_geojson(INPUT_GEOJSON)
        if not features:
            return

        # 顯示檔案基本資訊
        print(f"\n📊 檔案資訊:")
        if features:
            sample_feature = features[0]
            properties = sample_feature.get('properties', {})
            print(f"   第一個區域的屬性: {list(properties.keys())[:5]}")
            print(f"   幾何類型: {sample_feature.get('geometry', {}).get('type', 'Unknown')}")

        # 視覺化
        print(f"\n🎨 開始視覺化...")
        fig = visualize_boundaries(features)

        if fig is None:
            print("❌ 視覺化失敗")
            return

        # 確保輸出目錄存在
        output_dir = Path(OUTPUT_PNG).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # 儲存圖片
        print(f"💾 儲存圖片...")
        fig.savefig(OUTPUT_PNG, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')

        # 顯示檔案大小
        file_size = Path(OUTPUT_PNG).stat().st_size
        if file_size > 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.2f} MB"
        elif file_size > 1024:
            size_str = f"{file_size / 1024:.2f} KB"
        else:
            size_str = f"{file_size} bytes"

        print(f"✅ 圖片已儲存: {OUTPUT_PNG}")
        print(f"   檔案大小: {size_str}")

        # 顯示圖片
        plt.show()

        print(f"\n" + "=" * 60)
        print("🎉 視覺化完成！")
        print(f"📊 摘要:")
        print(f"   • 總區域數: {len(features):,}")
        print(f"   • 輸出圖片: {OUTPUT_PNG}")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"❌ 檔案錯誤: {e}")

    except json.JSONDecodeError as e:
        print(f"❌ JSON 格式錯誤: {e}")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()