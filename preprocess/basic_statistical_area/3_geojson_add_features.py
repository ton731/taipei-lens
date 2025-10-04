#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
為最小統計區 GeoJSON 加入社會脆弱性資料
根據行政區合併人口年齡、低收入戶、獨居老人等資料
加入建築物平均年齡資訊
"""

import json
import sys
from pathlib import Path
import geopandas as gpd
from shapely.geometry import shape, Point
import warnings

warnings.filterwarnings('ignore')

# 設定編碼
sys.stdout.reconfigure(encoding='utf-8')

# 資料路徑
input_geojson_path = "data/basic_statistical_area/geojson/basic_statistical_area.geojson"
output_geojson_path = "data/basic_statistical_area/geojson/basic_statistical_area_with_features.geojson"

population_json_path = "data/social_vulnerability/processed/population_by_age_district.json"
low_income_json_path = "data/social_vulnerability/processed/low_income_district.json"
elderly_alone_json_path = "data/social_vulnerability/processed/live_alone_elderly_district.json"

building_geojson_path = "data/building/geojson/building_4326_age.geojson"


def load_json(file_path):
    """載入 JSON 檔案"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 無法讀取檔案 {file_path}: {e}")
        return None


def calculate_building_age_by_district(building_geojson_path, statistical_area_geojson_path):
    """
    計算每個最小統計區的建築物平均年齡

    Parameters:
    -----------
    building_geojson_path : str
        建築物 GeoJSON 檔案路徑
    statistical_area_geojson_path : str
        最小統計區 GeoJSON 檔案路徑

    Returns:
    --------
    dict : 以 CODEBASE 為 key，平均年齡為 value 的字典
    """
    print(f"\n🏢 正在計算建築物平均年齡...")
    print(f"   讀取建築物資料: {building_geojson_path}")

    # 讀取建築物 GeoJSON
    buildings_gdf = gpd.read_file(building_geojson_path)
    print(f"   ✅ 已讀取 {len(buildings_gdf):,} 棟建築物")

    # 讀取最小統計區 GeoJSON
    print(f"   讀取統計區資料: {statistical_area_geojson_path}")
    areas_gdf = gpd.read_file(statistical_area_geojson_path)
    print(f"   ✅ 已讀取 {len(areas_gdf):,} 個統計區")

    # 確保兩個 GeoDataFrame 使用相同的座標系統
    if buildings_gdf.crs != areas_gdf.crs:
        print(f"   🔄 轉換建築物座標系統從 {buildings_gdf.crs} 至 {areas_gdf.crs}")
        buildings_gdf = buildings_gdf.to_crs(areas_gdf.crs)

    # 計算建築物的中心點（用於空間查詢）
    print(f"   計算建築物中心點...")
    buildings_gdf['centroid'] = buildings_gdf.geometry.centroid

    # 進行空間連接（找出每棟建築物所在的統計區）
    print(f"   執行空間連接...")
    buildings_with_area = gpd.sjoin(
        buildings_gdf[['age', 'centroid']].set_geometry('centroid'),
        areas_gdf[['CODEBASE', 'geometry']],
        how='left',
        predicate='within'
    )

    print(f"   ✅ 完成空間連接")

    # 計算每個統計區的平均建築年齡
    print(f"   計算平均年齡...")
    area_avg_age = {}

    for codebase in areas_gdf['CODEBASE'].unique():
        # 取得該統計區內的所有建築物
        buildings_in_area = buildings_with_area[buildings_with_area['CODEBASE'] == codebase]

        # 過濾掉年齡為 None 的建築物
        valid_ages = buildings_in_area['age'].dropna()

        if len(valid_ages) > 0:
            # 計算平均年齡
            avg_age = valid_ages.mean()
            area_avg_age[codebase] = round(avg_age, 2)
        else:
            # 沒有有效年齡資料，設為 0
            area_avg_age[codebase] = 0

    # 統計資訊
    areas_with_buildings = sum(1 for age in area_avg_age.values() if age > 0)
    areas_without_buildings = len(area_avg_age) - areas_with_buildings

    print(f"\n   📊 統計結果:")
    print(f"      總統計區數: {len(area_avg_age):,}")
    print(f"      有建築物的統計區: {areas_with_buildings:,}")
    print(f"      無建築物的統計區: {areas_without_buildings:,}")

    if areas_with_buildings > 0:
        avg_ages = [age for age in area_avg_age.values() if age > 0]
        print(f"      平均建築年齡範圍: {min(avg_ages):.2f} ~ {max(avg_ages):.2f} 年")
        print(f"      全市平均: {sum(avg_ages) / len(avg_ages):.2f} 年")

    return area_avg_age


# 需要進行標準化的屬性列表
PROPERTIES_TO_NORMALIZE = [
    'population_density',
    'pop_elderly_percentage',
    'elderly_alone_percentage',
    'low_income_percentage',
    'avg_building_age'
]


def normalize_properties(geojson):
    """
    對 GeoJSON 中的指定屬性進行 Min-Max 標準化

    Parameters:
    -----------
    geojson : dict
        包含 features 的 GeoJSON 物件

    Returns:
    --------
    dict : 標準化後的 GeoJSON 物件
    """
    print(f"\n📊 正在進行 Min-Max 標準化...")
    print(f"   標準化屬性: {', '.join(PROPERTIES_TO_NORMALIZE)}")

    # 計算每個屬性的最大最小值
    stats = {}
    for prop in PROPERTIES_TO_NORMALIZE:
        values = []
        for feature in geojson['features']:
            value = feature['properties'].get(prop)
            if value is not None:  # 排除 None
                values.append(value)

        if values:
            stats[prop] = {
                'min': min(values),
                'max': max(values),
                'count': len(values)
            }
            print(f"   {prop}: min={stats[prop]['min']:.4f}, max={stats[prop]['max']:.4f}, count={stats[prop]['count']}")
        else:
            stats[prop] = None
            print(f"   ⚠️  {prop}: 無有效數據")

    # 對每個 feature 進行標準化
    normalized_count = 0
    for feature in geojson['features']:
        for prop in PROPERTIES_TO_NORMALIZE:
            value = feature['properties'].get(prop)
            norm_prop = f"norm_{prop}"

            # 如果該屬性有統計資料且值不為 None
            if stats.get(prop) and value is not None:
                min_val = stats[prop]['min']
                max_val = stats[prop]['max']

                # Min-Max 標準化公式: x_norm = (x - x_min) / (x_max - x_min)
                if max_val - min_val != 0:
                    normalized_value = (value - min_val) / (max_val - min_val)
                    feature['properties'][norm_prop] = round(normalized_value, 6)
                    normalized_count += 1
                else:
                    # 如果最大值等於最小值，所有值都相同，設為 0.5
                    feature['properties'][norm_prop] = 0.5
            else:
                # 沒有數據則設為 0
                feature['properties'][norm_prop] = 0.0

    print(f"   ✅ 完成標準化，共處理 {normalized_count} 個數值")

    return geojson


def add_social_vulnerability_to_geojson(
    geojson_path,
    output_path,
    population_data,
    low_income_data,
    elderly_alone_data,
    building_age_data=None
):
    """
    為 GeoJSON 的每個最小統計區加入社會脆弱性資料和建築物年齡資料

    Parameters:
    -----------
    geojson_path : str
        輸入 GeoJSON 檔案路徑
    output_path : str
        輸出 GeoJSON 檔案路徑
    population_data : dict
        人口年齡資料（以行政區為 key）
    low_income_data : dict
        低收入戶資料（以行政區為 key）
    elderly_alone_data : dict
        獨居老人資料（以行政區為 key）
    building_age_data : dict, optional
        建築物平均年齡資料（以 CODEBASE 為 key）
    """

    print(f"正在讀取 GeoJSON: {geojson_path}")
    print("-" * 60)

    # 讀取 GeoJSON
    geojson = load_json(geojson_path)
    if not geojson:
        raise Exception("無法讀取 GeoJSON 檔案")

    print(f"✓ 成功讀取 GeoJSON")
    print(f"  總特徵數: {len(geojson['features']):,}")

    # 統計資料
    districts_found = set()
    districts_not_found = set()
    features_updated = 0

    # 為每個特徵（最小統計區）加入社會脆弱性資料
    print(f"\n正在處理特徵...")

    for i, feature in enumerate(geojson['features']):
        # 取得行政區名稱和統計區代碼
        district = feature['properties'].get('TOWN', '')
        codebase = feature['properties'].get('CODEBASE', '')

        if not district:
            print(f"  ⚠️  特徵 {i} 沒有行政區資訊")
            continue

        # 記錄找到的行政區
        districts_found.add(district)

        # 初始化社會脆弱性資料
        vulnerability_data = {}

        # 加入人口年齡資料
        if district in population_data:
            pop_data = population_data[district]
            vulnerability_data.update({
                'pop_elderly_percentage': pop_data.get('65歲以上比例', 0.0),
            })

        # 加入低收入戶資料
        if district in low_income_data:
            low_income = low_income_data[district]
            vulnerability_data.update({
                'low_income_percentage': low_income.get('低收入戶比例', 0.0),
            })

        # 加入獨居老人資料
        if district in elderly_alone_data:
            elderly = elderly_alone_data[district]
            vulnerability_data.update({
                'elderly_alone_percentage': elderly.get('老人獨居比例', 0.0),
            })

        # 加入建築物平均年齡資料
        if building_age_data and codebase:
            if codebase in building_age_data:
                vulnerability_data['avg_building_age'] = building_age_data[codebase]
            else:
                vulnerability_data['avg_building_age'] = 0

        # 將資料加入 properties
        if vulnerability_data:
            feature['properties'].update(vulnerability_data)
            features_updated += 1
        else:
            districts_not_found.add(district)

        # 每 1000 個特徵顯示進度
        if (i + 1) % 1000 == 0:
            print(f"  已處理 {i + 1:,} 個特徵...")

    # 顯示統計資訊
    print(f"\n📊 處理結果:")
    print(f"  更新的特徵數: {features_updated:,} / {len(geojson['features']):,}")
    print(f"  找到的行政區: {len(districts_found)} 個")
    print(f"    {', '.join(sorted(districts_found))}")

    if districts_not_found:
        print(f"  ⚠️  未找到資料的行政區: {len(districts_not_found)} 個")
        print(f"    {', '.join(sorted(districts_not_found))}")

    # 進行 Min-Max 標準化
    print(f"\n" + "=" * 60)
    geojson = normalize_properties(geojson)

    # 確保輸出目錄存在
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 寫入輸出檔案
    print(f"\n💾 正在寫入輸出檔案: {output_path}")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, separators=(',', ':'))

        # 顯示檔案大小
        file_size = Path(output_path).stat().st_size
        if file_size > 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.2f} MB"
        elif file_size > 1024:
            size_str = f"{file_size / 1024:.2f} KB"
        else:
            size_str = f"{file_size} bytes"

        print(f"✅ 寫入完成！檔案大小: {size_str}")

    except Exception as e:
        raise Exception(f"寫入檔案失敗: {e}")

    # 顯示範例資料
    print(f"\n📋 範例資料 (第一個特徵的新增屬性):")
    if len(geojson['features']) > 0:
        example_props = geojson['features'][0]['properties']

        # 顯示原始數值
        print(f"\n  原始數值:")
        for prop in PROPERTIES_TO_NORMALIZE:
            if prop in example_props:
                print(f"    {prop}: {example_props[prop]}")

        # 顯示標準化數值
        print(f"\n  標準化數值:")
        for prop in PROPERTIES_TO_NORMALIZE:
            norm_prop = f"norm_{prop}"
            if norm_prop in example_props:
                print(f"    {norm_prop}: {example_props[norm_prop]}")


def main():
    print("=" * 60)
    print("🗺️  為最小統計區 GeoJSON 加入社會脆弱性資料與建築物年齡")
    print("=" * 60)

    # 檢查所有輸入檔案是否存在
    input_files = {
        'GeoJSON': input_geojson_path,
        '人口年齡資料': population_json_path,
        '低收入戶資料': low_income_json_path,
        '獨居老人資料': elderly_alone_json_path,
        '建築物資料': building_geojson_path,
    }

    print(f"\n📂 檢查輸入檔案:")
    for name, path in input_files.items():
        exists = Path(path).exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {name}: {path}")
        if not exists:
            raise Exception(f"找不到檔案: {path}")

    # 載入社會脆弱性資料
    print(f"\n📥 載入社會脆弱性資料:")

    population_data = load_json(population_json_path)
    print(f"  ✓ 人口年齡資料: {len(population_data)} 個行政區")

    low_income_data = load_json(low_income_json_path)
    print(f"  ✓ 低收入戶資料: {len(low_income_data)} 個行政區")

    elderly_alone_data = load_json(elderly_alone_json_path)
    print(f"  ✓ 獨居老人資料: {len(elderly_alone_data)} 個行政區")

    # 計算建築物平均年齡
    print(f"\n" + "=" * 60)
    building_age_data = calculate_building_age_by_district(
        building_geojson_path=building_geojson_path,
        statistical_area_geojson_path=input_geojson_path
    )

    # 執行合併
    print(f"\n" + "=" * 60)

    try:
        add_social_vulnerability_to_geojson(
            geojson_path=input_geojson_path,
            output_path=output_geojson_path,
            population_data=population_data,
            low_income_data=low_income_data,
            elderly_alone_data=elderly_alone_data,
            building_age_data=building_age_data
        )

        print(f"\n" + "=" * 60)
        print("🎉 處理完成！")
        print("=" * 60)
        print(f"\n輸出檔案: {output_geojson_path}")

    except Exception as e:
        print(f"\n❌ 處理失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()