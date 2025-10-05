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
import numpy as np
import geopandas as gpd
from shapely.geometry import shape, Point
import warnings

warnings.filterwarnings('ignore')

# 設定編碼
sys.stdout.reconfigure(encoding='utf-8')

# 資料路徑
input_geojson_path = "data/basic_statistical_area/geojson/basic_statistical_area.geojson"
output_geojson_path = "data/basic_statistical_area/geojson/basic_statistical_area_with_features_w_fragility_test_2.geojson"

population_json_path = "data/social_vulnerability/processed/population_by_age_district.json"
low_income_json_path = "data/social_vulnerability/processed/low_income_district.json"
elderly_alone_json_path = "data/social_vulnerability/processed/live_alone_elderly_district.json"

building_geojson_path = "data/building/geojson_w_fragility/building_extracted_with_fragility.geojson"

# LST、NDVI 和 VIIRS 資料路徑
lst_geojson_path = "data/ndvi_lst/utfvi_result_mean.geojson"
ndvi_geojson_path = "data/ndvi_lst/ndvi_average_result.geojson"
viirs_geojson_path = "data/ndvi_lst/taipei_VIIRS_statmin.geojson"

# 土壤液化風險和綠地覆蓋率資料路徑
liq_risk_geojson_path = "data/ndvi_lst/taipei_liquefaction_risk.geojson"  # 待確認路徑
coverage_geojson_path = "data/ndvi_lst/taipei_open_space_coverage_ndvi.geojson"  # 待確認路徑

# ==================== 測試參數 ====================
# 設定為 True 進行小量測試，False 使用全部資料
TEST_MODE = False
TEST_BUILDING_LIMIT = 360000  # 測試時只使用前 N 棟建築物
TEST_AREA_LIMIT = 50       # 測試時只使用前 N 個統計區


def load_json(file_path):
    """載入 JSON 檔案"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 無法讀取檔案 {file_path}: {e}")
        return None


def load_environmental_data(geojson_path, value_key, data_name):
    """
    載入環境資料（LST 或 NDVI）GeoJSON 並提取指定數值
    
    Parameters:
    -----------
    geojson_path : str
        GeoJSON 檔案路徑
    value_key : str
        要提取的數值 key（如 'p90' 或 'mean'）
    data_name : str
        資料名稱（用於顯示訊息）
    
    Returns:
    --------
    dict : 以 CODEBASE 為 key，數值為 value 的字典
    """
    print(f"\n📊 正在載入 {data_name} 資料...")
    print(f"   讀取檔案: {geojson_path}")
    
    try:
        # 載入 GeoJSON
        geojson_data = load_json(geojson_path)
        if not geojson_data:
            raise Exception(f"無法載入 {data_name} 檔案")
        
        # 提取資料
        environmental_data = {}
        features = geojson_data.get('features', [])
        
        # 測試模式下限制處理的 features 數量
        if TEST_MODE:
            original_count = len(features)
            features = features[:TEST_AREA_LIMIT * 10]  # 多處理一些以確保有足夠的對應
            print(f"   🧪 測試模式：處理前 {len(features):,} 個 features（共 {original_count:,} 個）")
        
        for feature in features:
            properties = feature.get('properties', {})
            codebase = properties.get('CODEBASE')
            value = properties.get(value_key)
            
            if codebase and value is not None:
                environmental_data[codebase] = value
        
        print(f"   ✅ 成功載入 {len(environmental_data):,} 筆 {data_name} 資料")
        return environmental_data
        
    except Exception as e:
        print(f"   ❌ 載入 {data_name} 失敗: {e}")
        return {}


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
    
    # 測試模式：限制建築物數量
    if TEST_MODE:
        original_count = len(buildings_gdf)
        buildings_gdf = buildings_gdf.head(TEST_BUILDING_LIMIT)
        print(f"   🧪 測試模式：使用前 {len(buildings_gdf):,} 棟建築物（共 {original_count:,} 棟）")
    else:
        print(f"   ✅ 已讀取 {len(buildings_gdf):,} 棟建築物")

    # 讀取最小統計區 GeoJSON
    print(f"   讀取統計區資料: {statistical_area_geojson_path}")
    areas_gdf = gpd.read_file(statistical_area_geojson_path)
    
    # 測試模式：限制統計區數量
    if TEST_MODE:
        original_area_count = len(areas_gdf)
        areas_gdf = areas_gdf.head(TEST_AREA_LIMIT)
        print(f"   🧪 測試模式：使用前 {len(areas_gdf):,} 個統計區（共 {original_area_count:,} 個）")
    else:
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


def calculate_fragility_curve_by_district(building_geojson_path, statistical_area_geojson_path):
    """
    計算每個最小統計區的 fragility curve 平均值
    
    Parameters:
    -----------
    building_geojson_path : str
        建築物 GeoJSON 檔案路徑（含 fragility_curve）
    statistical_area_geojson_path : str
        最小統計區 GeoJSON 檔案路徑
    
    Returns:
    --------
    dict : 以 CODEBASE 為 key，fragility curve 平均值為 value 的字典
    """
    print(f"\n🏢 正在計算 fragility curve 平均值...")
    print(f"   讀取建築物資料: {building_geojson_path}")
    
    # 讀取建築物 GeoJSON（使用 geopandas 搭配特殊處理保持 fragility_curve 格式）
    buildings_gdf = gpd.read_file(building_geojson_path)
    
    # 測試模式：限制建築物數量
    if TEST_MODE:
        original_count = len(buildings_gdf)
        buildings_gdf = buildings_gdf.head(TEST_BUILDING_LIMIT)
        print(f"   🧪 測試模式：使用前 {len(buildings_gdf):,} 棟建築物（共 {original_count:,} 棟）")
    else:
        print(f"   ✅ 已讀取 {len(buildings_gdf):,} 棟建築物")
    
    # 讀取原始 JSON 來獲取正確的 fragility_curve 資料
    print(f"   讀取原始 JSON 以保持 fragility_curve 格式...")
    with open(building_geojson_path, 'r', encoding='utf-8') as f:
        buildings_json = json.load(f)
    
    # 建立 fragility_curve 對應字典（以索引為 key）
    # 測試模式下只處理對應的建築物
    fragility_curves = {}
    limit = TEST_BUILDING_LIMIT if TEST_MODE else len(buildings_json['features'])
    for i, feature in enumerate(buildings_json['features'][:limit]):
        fragility_curves[i] = feature['properties'].get('fragility_curve')
    
    # 將 fragility_curve 加入 GeoDataFrame
    buildings_gdf['fragility_curve'] = buildings_gdf.index.map(fragility_curves)
    
    # 讀取最小統計區 GeoJSON
    print(f"   讀取統計區資料: {statistical_area_geojson_path}")
    areas_gdf = gpd.read_file(statistical_area_geojson_path)
    
    # 測試模式：限制統計區數量
    if TEST_MODE:
        original_area_count = len(areas_gdf)
        areas_gdf = areas_gdf.head(TEST_AREA_LIMIT)
        print(f"   🧪 測試模式：使用前 {len(areas_gdf):,} 個統計區（共 {original_area_count:,} 個）")
    else:
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
        buildings_gdf[['fragility_curve', 'centroid']].set_geometry('centroid'),
        areas_gdf[['CODEBASE', 'geometry']],
        how='left',
        predicate='within'
    )
    
    print(f"   ✅ 完成空間連接")
    
    # 計算每個統計區的 fragility curve 平均值
    print(f"   計算 fragility curve 平均值...")
    area_avg_fragility = {}
    
    # 定義震度級別
    magnitude_levels = ['3', '4', '5弱', '5強', '6弱', '6強', '7']
    
    for codebase in areas_gdf['CODEBASE'].unique():
        # 取得該統計區內的所有建築物
        buildings_in_area = buildings_with_area[buildings_with_area['CODEBASE'] == codebase]
        
        # 收集所有有效的 fragility curve
        valid_curves = []
        for _, building in buildings_in_area.iterrows():
            fragility_data = building['fragility_curve']
            
            if fragility_data is not None and isinstance(fragility_data, dict):
                valid_curves.append(fragility_data)
        
        if valid_curves:
            # 計算每個震度級別的平均機率
            avg_curve = {}
            for magnitude in magnitude_levels:
                # 收集該震度下所有建築物的機率值
                probabilities = []
                for curve in valid_curves:
                    if magnitude in curve and curve[magnitude] is not None:
                        probabilities.append(curve[magnitude])
                
                # 計算平均值
                if probabilities:
                    avg_value = sum(probabilities) / len(probabilities)
                    avg_curve[magnitude] = round(avg_value, 6)  # 保留更多精度
                else:
                    print(f"   ⚠️  統計區 {codebase} 沒有 fragility curve 資料")
                    avg_curve[magnitude] = 0.0000
            
            area_avg_fragility[codebase] = avg_curve
        else:
            # 沒有建築物或沒有 fragility curve 資料，設為預設值
            print(f"   ⚠️  統計區 {codebase} 沒有 fragility curve 資料")
            area_avg_fragility[codebase] = {
                '3': 0.0000,
                '4': 0.0000,
                '5弱': 0.0000,
                '5強': 0.0000,
                '6弱': 0.0000,
                '6強': 0.0000,
                '7': 0.0000
            }
    
    # 統計資訊
    areas_with_fragility = sum(1 for curve in area_avg_fragility.values() 
                               if any(v > 0 for v in curve.values()))
    areas_without_fragility = len(area_avg_fragility) - areas_with_fragility
    
    print(f"\n   📊 統計結果:")
    print(f"      總統計區數: {len(area_avg_fragility):,}")
    print(f"      有 fragility curve 的統計區: {areas_with_fragility:,}")
    print(f"      無 fragility curve 的統計區: {areas_without_fragility:,}")
    
    return area_avg_fragility


# 需要進行標準化的屬性列表
PROPERTIES_TO_NORMALIZE = [
    'population_density',
    'pop_elderly_percentage',
    'elderly_alone_percentage',
    'low_income_percentage',
    'avg_building_age',
    'lst_p90',           # 地表溫度 p90 值
    'utfvi',             # UTFVI 值（需標準化）
    'viirs_mean',  # VIIRS 平均值（用於標準化）
    'coverage_strict_300m',  # 綠地覆蓋率（需標準化）
    # 注意：liq_risk 不加入此列表，因為不需要標準化
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
    building_age_data=None,
    fragility_curve_data=None,
    lst_data=None,
    utfvi_data=None,
    ndvi_data=None,
    viirs_data=None,
    liq_risk_data=None,
    coverage_data=None
):
    """
    為 GeoJSON 的每個最小統計區加入社會脆弱性資料、建築物年齡資料、fragility curve 和環境資料

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
    fragility_curve_data : dict, optional
        fragility curve 平均值資料（以 CODEBASE 為 key）
    lst_data : dict, optional
        LST p90 資料（以 CODEBASE 為 key）
    utfvi_data : dict, optional
        UTFVI 資料（以 CODEBASE 為 key）
    ndvi_data : dict, optional
        NDVI mean 資料（以 CODEBASE 為 key）
    viirs_data : dict, optional
        VIIRS mean 資料（以 CODEBASE 為 key）
    liq_risk_data : dict, optional
        土壤液化風險資料（以 CODEBASE 為 key）
    coverage_data : dict, optional
        綠地覆蓋率資料（以 CODEBASE 為 key）
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
        
        # 加入 fragility curve 平均值資料（不需標準化）
        if fragility_curve_data and codebase:
            if codebase in fragility_curve_data:
                vulnerability_data['avg_fragility_curve'] = fragility_curve_data[codebase]  # 保持屬性名稱以維持相容性
            else:
                # 如果沒有建築物，設定預設值
                vulnerability_data['avg_fragility_curve'] = {
                    '3': 0.0000,
                    '4': 0.0000,
                    '5弱': 0.0000,
                    '5強': 0.0000,
                    '6弱': 0.0000,
                    '6強': 0.0000,
                    '7': 0.0000
                }
        
        # 加入 LST p90 資料
        if lst_data and codebase:
            if codebase in lst_data:
                vulnerability_data['lst_p90'] = lst_data[codebase]
            else:
                vulnerability_data['lst_p90'] = None
        
        # 加入 UTFVI 資料
        if utfvi_data and codebase:
            if codebase in utfvi_data:
                vulnerability_data['utfvi'] = utfvi_data[codebase]
            else:
                vulnerability_data['utfvi'] = None
        
        # 加入 NDVI mean 資料
        if ndvi_data and codebase:
            if codebase in ndvi_data:
                vulnerability_data['ndvi_mean'] = ndvi_data[codebase]
            else:
                vulnerability_data['ndvi_mean'] = None
        
        # 加入 VIIRS mean 資料
        if viirs_data and codebase:
            if codebase in viirs_data:
                viirs_value = viirs_data[codebase]
                vulnerability_data['viirs_mean'] = viirs_value  # 原始值
            else:
                vulnerability_data['viirs_mean'] = None

        # 加入土壤液化風險資料（不需標準化）
        if liq_risk_data and codebase:
            if codebase in liq_risk_data:
                vulnerability_data['liq_risk'] = liq_risk_data[codebase]
            else:
                vulnerability_data['liq_risk'] = None
        
        # 加入綠地覆蓋率資料（需標準化）
        if coverage_data and codebase:
            if codebase in coverage_data:
                vulnerability_data['coverage_strict_300m'] = coverage_data[codebase]
            else:
                vulnerability_data['coverage_strict_300m'] = None

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
        
        # 顯示 fragility curve（如果存在）
        if 'avg_fragility_curve' in example_props:
            print(f"\n  Fragility Curve 平均值 (不標準化):")
            for magnitude, probability in example_props['avg_fragility_curve'].items():
                print(f"    震度 {magnitude}: {probability}")
        
        # 顯示土壤液化風險（如果存在）
        if 'liq_risk' in example_props:
            print(f"\n  土壤液化風險 (不標準化): {example_props['liq_risk']}")


def main():
    print("=" * 60)
    if TEST_MODE:
        print("🧪 測試模式：為最小統計區 GeoJSON 加入社會脆弱性、建築物年齡、LST 和 NDVI 資料")
        print(f"   - 建築物限制：{TEST_BUILDING_LIMIT:,} 棟")
        print(f"   - 統計區限制：{TEST_AREA_LIMIT:,} 個")
    else:
        print("🗺️  為最小統計區 GeoJSON 加入社會脆弱性、建築物年齡、LST 和 NDVI 資料")
    print("=" * 60)

    # 檢查所有輸入檔案是否存在
    input_files = {
        'GeoJSON': input_geojson_path,
        '人口年齡資料': population_json_path,
        '低收入戶資料': low_income_json_path,
        '獨居老人資料': elderly_alone_json_path,
        '建築物資料': building_geojson_path,
        'LST 資料': lst_geojson_path,
        'NDVI 資料': ndvi_geojson_path,
        'VIIRS 資料': viirs_geojson_path,
        '土壤液化風險資料': liq_risk_geojson_path,
        '綠地覆蓋率資料': coverage_geojson_path,
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

    # 載入環境資料
    print(f"\n📥 載入環境資料:")
    lst_data = load_environmental_data(lst_geojson_path, 'LST_mean', 'LST')
    utfvi_data = load_environmental_data(lst_geojson_path, 'UTFVI', 'UTFVI')  # 從同一個 LST 檔案載入 UTFVI
    ndvi_data = load_environmental_data(ndvi_geojson_path, 'NDVI_mean', 'NDVI')
    viirs_data = load_environmental_data(viirs_geojson_path, '_mean', 'VIIRS')  # 使用 '_mean' 欄位名
    liq_risk_data = load_environmental_data(liq_risk_geojson_path, 'liq_risk', '土壤液化風險')  # 使用正確欄位名 'liq_risk'
    coverage_data = load_environmental_data(coverage_geojson_path, 'coverage_strict_300m', '綠地覆蓋率')  # 使用正確欄位名 'coverage_strict_300m'

    # 計算建築物平均年齡
    print(f"\n" + "=" * 60)
    building_age_data = calculate_building_age_by_district(
        building_geojson_path=building_geojson_path,
        statistical_area_geojson_path=input_geojson_path
    )
    
    # 計算 fragility curve 平均值
    print(f"\n" + "=" * 60)
    fragility_curve_data = calculate_fragility_curve_by_district(
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
            building_age_data=building_age_data,
            fragility_curve_data=fragility_curve_data,
            lst_data=lst_data,
            utfvi_data=utfvi_data,
            ndvi_data=ndvi_data,
            viirs_data=viirs_data,
            liq_risk_data=liq_risk_data,
            coverage_data=coverage_data
        )

        print(f"\n" + "=" * 60)
        if TEST_MODE:
            print("🧪 測試完成！")
            print(f"   - 處理了 {TEST_BUILDING_LIMIT:,} 棟建築物")
            print(f"   - 處理了 {TEST_AREA_LIMIT:,} 個統計區")
            print("   - 如需處理全部資料，請將 TEST_MODE 設為 False")
        else:
            print("🎉 處理完成！")
        print("=" * 60)
        print(f"\n輸出檔案: {output_geojson_path}")

    except Exception as e:
        print(f"\n❌ 處理失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()