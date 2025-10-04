#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Building Polygon Extraction Script
Extract individual polygons from BuildingCollection format to standard FeatureCollection
將 BuildingCollection 格式中的 polygons 拆解成獨立的 features
"""

import json
import os
from typing import Dict, List, Any, Optional
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# ==================== Configuration ====================
# Please modify these paths according to your needs
INPUT_FILE = "data/building/building_data_with_fragility.geojson"  # Input BuildingCollection file
OUTPUT_FILE = "data/building/geojson_w_fragility/building_extracted_with_fragility.geojson"  # Output FeatureCollection file

# ==================== Core Functions ====================

def load_building_collection(file_path: str) -> Dict:
    """
    載入 BuildingCollection 格式的 GeoJSON 檔案
    
    Args:
        file_path: 輸入檔案路徑
        
    Returns:
        BuildingCollection 資料字典
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 驗證檔案格式
        if data.get('type') != 'BuildingCollection':
            raise ValueError(f"Expected BuildingCollection type, got {data.get('type')}")
            
        print(f"✓ Successfully loaded BuildingCollection from {file_path}")
        print(f"  - Total buildings: {data.get('metadata', {}).get('total_buildings', 'Unknown')}")
        print(f"  - Features count: {len(data.get('features', []))}")
        
        return data
    except FileNotFoundError:
        print(f"✗ File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"✗ JSON decode error: {e}")
        raise
    except Exception as e:
        print(f"✗ Error loading file: {e}")
        raise

def extract_polygons_to_features(building_collection: Dict) -> Dict:
    """
    將 BuildingCollection 中的 polygons 拆解成獨立的 features
    
    Args:
        building_collection: BuildingCollection 格式的資料
        
    Returns:
        標準 GeoJSON FeatureCollection 格式的資料
    """
    # 初始化 FeatureCollection
    feature_collection = {
        "type": "FeatureCollection",
        "name": "building_extracted",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": []
    }
    
    # 統計資訊
    total_original_features = len(building_collection.get('features', []))
    total_extracted_features = 0
    
    print("\n開始拆解 polygons...")
    
    # 遍歷每個原始 feature
    for feature_idx, original_feature in enumerate(tqdm(building_collection.get('features', []), 
                                                       desc="Processing features")):
        
        # 取得原始 feature 的 properties (fragility 相關資料)
        original_properties = original_feature.get('properties', {})
        
        # 取得 polygons 列表
        polygons = original_feature.get('polygons', [])
        
        # 如果沒有 polygons，跳過此 feature
        if not polygons:
            print(f"  ⚠ Feature {feature_idx} has no polygons, skipping...")
            continue
        
        # 拆解每個 polygon 成為獨立的 feature
        for polygon_idx, polygon in enumerate(polygons):
            # 建立新的 feature
            new_feature = {
                "type": "Feature",
                "properties": {},
                "geometry": polygon.get('geometry', {})
            }
            
            # 1. 先複製 polygon 自己的基本 properties (area, height, floor, age)
            if 'properties' in polygon:
                new_feature['properties'] = polygon['properties'].copy()
            
            # 2. 只從原始 feature 繼承 fragility_curve，並格式化數值為小數點後三位
            if original_properties and 'fragility_curve' in original_properties:
                fragility_curve = original_properties['fragility_curve']
                
                # 格式化 fragility_curve 的數值
                formatted_fragility = {}
                for magnitude, probability in fragility_curve.items():
                    # 將科學記號轉換為一般小數，保留四位小數
                    # 對於極小的數值（< 0.0001），直接設為 0
                    if probability < 0.0001:
                        formatted_fragility[magnitude] = 0.0000
                    else:
                        formatted_fragility[magnitude] = round(probability, 4)
                
                # 只保留 fragility_curve
                new_feature['properties'] = {
                    'fragility_curve': formatted_fragility
                }
                
                # 如果 polygon 有基本屬性，也保留這些
                if 'properties' in polygon:
                    for key in ['area', 'height', 'floor', 'age']:
                        if key in polygon['properties']:
                            new_feature['properties'][key] = polygon['properties'][key]
            
            # 3. 加入追蹤資訊（可選）
            new_feature['properties']['source_feature_idx'] = feature_idx
            new_feature['properties']['polygon_idx'] = polygon_idx
            
            # 加入到 features 列表
            feature_collection['features'].append(new_feature)
            total_extracted_features += 1
    
    # 更新 metadata
    feature_collection['metadata'] = {
        'original_features': total_original_features,
        'extracted_features': total_extracted_features,
        'original_file': building_collection.get('metadata', {}).get('original_file', 'Unknown'),
        'extraction_note': '每個 polygon 只保留 fragility_curve 屬性，數值格式化為小數點後三位'
    }
    
    print(f"\n✓ 拆解完成:")
    print(f"  - 原始 features 數量: {total_original_features}")
    print(f"  - 產生的新 features 數量: {total_extracted_features}")
    
    return feature_collection

def save_feature_collection(feature_collection: Dict, output_path: str):
    """
    儲存 FeatureCollection 到檔案
    
    Args:
        feature_collection: FeatureCollection 資料
        output_path: 輸出檔案路徑
    """
    try:
        # 確保輸出目錄存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        
        # 寫入檔案
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(feature_collection, f, ensure_ascii=False)
        
        print(f"\n✓ Successfully saved FeatureCollection to {output_path}")
        
        # 計算檔案大小
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # Convert to MB
        print(f"  - File size: {file_size:.2f} MB")
        
    except Exception as e:
        print(f"✗ Error saving file: {e}")
        raise

def validate_output(feature_collection: Dict) -> bool:
    """
    驗證輸出的 FeatureCollection 格式是否正確
    
    Args:
        feature_collection: 要驗證的 FeatureCollection
        
    Returns:
        是否通過驗證
    """
    print("\n驗證輸出格式...")
    
    # 檢查必要的欄位
    required_fields = ['type', 'features']
    for field in required_fields:
        if field not in feature_collection:
            print(f"  ✗ Missing required field: {field}")
            return False
    
    # 檢查 type 是否正確
    if feature_collection['type'] != 'FeatureCollection':
        print(f"  ✗ Incorrect type: {feature_collection['type']}")
        return False
    
    # 檢查 features 是否為列表
    if not isinstance(feature_collection['features'], list):
        print("  ✗ Features is not a list")
        return False
    
    # 抽樣檢查幾個 features 的結構
    sample_size = min(5, len(feature_collection['features']))
    for i in range(sample_size):
        feature = feature_collection['features'][i]
        
        # 檢查 feature 結構
        if feature.get('type') != 'Feature':
            print(f"  ✗ Feature {i} has incorrect type")
            return False
        
        if 'geometry' not in feature:
            print(f"  ✗ Feature {i} missing geometry")
            return False
        
        if 'properties' not in feature:
            print(f"  ✗ Feature {i} missing properties")
            return False
        
        # 檢查是否有 fragility 屬性（現在是必須的）
        if 'fragility_curve' not in feature['properties']:
            print(f"  ✗ Feature {i} missing required fragility_curve")
            return False
    
    print("  ✓ Output format validation passed")
    return True

def main():
    """
    主程式進入點
    """
    print("=" * 60)
    print("Building Polygon Extraction Script")
    print("=" * 60)
    
    try:
        # Step 1: 載入 BuildingCollection
        print("\nStep 1: Loading BuildingCollection...")
        building_collection = load_building_collection(INPUT_FILE)
        
        # Step 2: 拆解 polygons
        print("\nStep 2: Extracting polygons to features...")
        feature_collection = extract_polygons_to_features(building_collection)
        
        # Step 3: 驗證輸出
        print("\nStep 3: Validating output...")
        if not validate_output(feature_collection):
            print("⚠ Validation failed, but continuing to save...")
        
        # Step 4: 儲存結果
        print("\nStep 4: Saving FeatureCollection...")
        save_feature_collection(feature_collection, OUTPUT_FILE)
        
        # 顯示範例輸出
        if feature_collection['features']:
            print("\n範例輸出 (第一個 feature):")
            first_feature = feature_collection['features'][0]
            print(f"  - Type: {first_feature.get('type')}")
            print(f"  - Properties keys: {list(first_feature.get('properties', {}).keys())}")
            print(f"  - Geometry type: {first_feature.get('geometry', {}).get('type')}")
        
        # 顯示最終統計
        print("\n最終 FeatureCollection 統計:")
        print(f"  - 總共包含 {len(feature_collection['features'])} 個 features")
        print(f"  - Metadata 記錄: {feature_collection.get('metadata', {})}")
        
        print("\n✓ 轉換完成！")
        
    except Exception as e:
        print(f"\n✗ Script failed: {e}")
        raise

if __name__ == "__main__":
    main()