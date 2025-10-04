import json
from pprint import pprint
from pathlib import Path
import random


def print_geojson_samples(geojson_path, num_samples=10):
    """
    讀取 GeoJSON 檔案並印出前幾筆資料

    Args:
        geojson_path: GeoJSON 檔案路徑
        num_samples: 要印出的資料筆數
    """
    # 檢查檔案是否存在
    if not Path(geojson_path).exists():
        print(f"錯誤：找不到檔案 {geojson_path}")
        return

    print(f"正在讀取檔案: {geojson_path}")
    print("=" * 80)

    # 讀取 GeoJSON 檔案
    with open(geojson_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)

    # 檢查是否為有效的 GeoJSON
    if 'type' not in geojson_data:
        print("錯誤：檔案不是有效的 GeoJSON 格式")
        return

    print(f"GeoJSON 類型: {geojson_data['type']}")

    # 如果有 CRS 資訊，印出來
    if 'crs' in geojson_data:
        print(f"座標參考系統 (CRS):")
        pprint(geojson_data['crs'], indent=2)
        print("-" * 80)

    # 取得 features
    if 'features' not in geojson_data:
        print("錯誤：找不到 features")
        return

    features = geojson_data['features']
    total_features = len(features)
    print(f"總共有 {total_features} 個 features")
    print(f"印出隨機 {min(num_samples, total_features)} 筆資料：")
    print("=" * 80)

    # 印出前 num_samples 筆資料
    random_features = random.sample(features, min(num_samples, total_features))
    for i in range(min(num_samples, total_features)):
        print(f"\n【第 {i+1} 筆資料】")
        print("-" * 40)

        feature = random_features[i]

        # 印出 feature 類型
        if 'type' in feature:
            print(f"Feature 類型: {feature['type']}")

        # 印出幾何資訊
        if 'geometry' in feature:
            geometry = feature['geometry']
            print(f"\n幾何資訊 (Geometry):")
            print(f"  類型: {geometry.get('type', 'N/A')}")

            # 根據幾何類型顯示不同資訊
            if geometry['type'] == 'Point':
                print(f"  座標: {geometry.get('coordinates', [])}")
            elif geometry['type'] == 'Polygon':
                coords = geometry.get('coordinates', [])
                if coords and coords[0]:
                    print(f"  多邊形頂點數: {len(coords[0])}")
                    print(f"  前3個頂點: {coords[0][:3]}")
            elif geometry['type'] == 'MultiPolygon':
                coords = geometry.get('coordinates', [])
                print(f"  多邊形數量: {len(coords)}")
                if coords and coords[0] and coords[0][0]:
                    print(f"  第一個多邊形頂點數: {len(coords[0][0])}")

        # 印出屬性資訊
        if 'properties' in feature:
            print(f"\n屬性資訊 (Properties):")
            pprint(feature['properties'], indent=2, width=120)

        print("=" * 80)

    # 統計資訊
    print(f"\n【統計資訊】")
    print("-" * 40)

    # 收集所有屬性欄位
    all_properties = set()
    for feature in features[:min(100, total_features)]:  # 只檢查前100筆避免太慢
        if 'properties' in feature and feature['properties']:
            all_properties.update(feature['properties'].keys())

    print(f"屬性欄位總數: {len(all_properties)}")
    print(f"屬性欄位列表:")
    for prop in sorted(all_properties):
        print(f"  - {prop}")

    # 幾何類型統計
    geometry_types = {}
    for feature in features[:min(1000, total_features)]:  # 檢查前1000筆
        if 'geometry' in feature and feature['geometry']:
            geom_type = feature['geometry'].get('type', 'Unknown')
            geometry_types[geom_type] = geometry_types.get(geom_type, 0) + 1

    print(f"\n幾何類型分布（前{min(1000, total_features)}筆）:")
    for geom_type, count in geometry_types.items():
        print(f"  {geom_type}: {count}")


def main():
    """主程式"""
    # 定義要檢查的 GeoJSON 檔案
    geojson_path = 'data/building/merged/merged_0925.geojson'

    print_geojson_samples(geojson_path, num_samples=10)


if __name__ == "__main__":
    main()