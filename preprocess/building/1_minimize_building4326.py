#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

def minimize_geojson_properties(input_file, output_file, keep_fields, field_mapping=None):
    """
    讀取 GeoJSON 檔案，過濾每個 feature 的 properties，只保留指定欄位

    Args:
        input_file (str): 輸入 GeoJSON 檔案路徑
        output_file (str): 輸出 GeoJSON 檔案路徑
        keep_fields (list): 要保留的欄位名稱列表
        field_mapping (dict): 欄位重新命名對應 (可選)
    """

    # 讀取輸入檔案
    with open(input_file, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)

    # 處理每個 feature 並過濾不合理的建築物
    filtered_features = []
    original_count = len(geojson_data['features'])
    filtered_count = 0

    for feature in geojson_data['features']:
        if 'properties' in feature:
            # 只保留指定的欄位
            filtered_properties = {}
            for field in keep_fields:
                if field in feature['properties']:
                    # 取得欄位值
                    value = feature['properties'][field]

                    # 決定新的欄位名稱
                    new_field_name = field
                    if field_mapping and field in field_mapping:
                        new_field_name = field_mapping[field]

                    # 特別處理 height 欄位，轉換為 float
                    if new_field_name == 'height' and value is not None:
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            value = None

                    filtered_properties[new_field_name] = value

            # 更新 properties
            feature['properties'] = filtered_properties

            # 過濾掉 height 超過 1000 公尺的建築物
            height_value = filtered_properties.get('height')
            if height_value is None or height_value <= 1000:
                filtered_features.append(feature)
            else:
                filtered_count += 1

    # 更新 features
    geojson_data['features'] = filtered_features

    # 確保輸出目錄存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 輸出處理後的檔案（不使用 indent 以減少檔案大小）
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson_data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"處理完成！輸出檔案：{output_file}")
    print(f"原始建築物數量：{original_count}")
    print(f"過濾後建築物數量：{len(geojson_data['features'])}")
    print(f"移除的不合理建築物數量：{filtered_count} (height > 1000m)")
    print(f"保留欄位：{keep_fields}")
    if field_mapping:
        print(f"欄位對應：{field_mapping}")

if __name__ == "__main__":
    # 設定檔案路徑 (placeholder)
    INPUT_FILE = "data/building/building_4326.geojson"
    OUTPUT_FILE = "data/building/geojson/building_4326_minimized.geojson"

    # 設定要保留的欄位 (placeholder)
    KEEP_FIELDS = [
        "area",
        "屋頂高",
        "樓層註"
    ]

    # 定義欄位重新命名對應
    FIELD_MAPPING = {
        "屋頂高": "height",
        "樓層註": "floor"
        # area 保持不變，不需要加入對應
    }

    # 執行處理
    minimize_geojson_properties(INPUT_FILE, OUTPUT_FILE, KEEP_FIELDS, FIELD_MAPPING)