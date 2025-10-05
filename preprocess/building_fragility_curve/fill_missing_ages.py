#!/usr/bin/env python3
"""
Building Age Imputation Script

實施建築年齡填補策略：
1. 優先使用建築物的max_age
2. 如果max_age為null，取該建築所有polygons中age的最大值
3. 如果所有polygon的age都是null，假設為1999年之前的結構（age = 當前年份 - 1999）
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

def fill_building_ages(geojson_file: str, output_file: str = None, reference_year: int = None) -> Dict[str, Any]:
    """
    填補建築年齡資料

    Args:
        geojson_file: 輸入GeoJSON檔案
        output_file: 輸出檔案路徑
        reference_year: 參考年份（用於計算age，預設為當前年份）

    Returns:
        Dict: 處理結果統計
    """
    if reference_year is None:
        reference_year = datetime.now().year

    print(f"Loading GeoJSON file: {geojson_file}")
    with open(geojson_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 統計資訊
    stats = {
        'total_buildings': len(data['features']),
        'used_max_age': 0,
        'used_polygon_max_age': 0,
        'used_default_age': 0,
        'buildings_updated': 0,
        'reference_year': reference_year,
        'default_construction_year': 1999
    }

    default_age = reference_year - 1999  # 1999年之前的結構假設年齡

    print(f"Processing {stats['total_buildings']} buildings...")
    print(f"Reference year: {reference_year}")
    print(f"Default age for pre-1999 structures: {default_age} years")

    for building_idx, feature in enumerate(data['features']):
        if building_idx % 10000 == 0:
            print(f"Processing building {building_idx:,}...")

        original_max_age = feature.get('max_age')
        final_age = None
        age_source = ""

        # 策略1: 優先使用max_age
        if original_max_age is not None and original_max_age != 'null' and original_max_age != '':
            try:
                final_age = float(original_max_age)
                age_source = "max_age"
                stats['used_max_age'] += 1
            except (ValueError, TypeError):
                pass

        # 策略2: 如果max_age無效，尋找polygons中的最大age
        if final_age is None:
            polygons = feature.get('polygons', [])
            polygon_ages = []

            for polygon in polygons:
                polygon_age = polygon.get('properties', {}).get('age')
                if polygon_age is not None and polygon_age != 'null' and polygon_age != '':
                    try:
                        age_value = float(polygon_age)
                        polygon_ages.append(age_value)
                    except (ValueError, TypeError):
                        continue

            if polygon_ages:
                final_age = max(polygon_ages)
                age_source = "polygon_max_age"
                stats['used_polygon_max_age'] += 1

        # 策略3: 如果都沒有有效age，使用預設值
        if final_age is None:
            final_age = default_age
            age_source = "default_pre1999"
            stats['used_default_age'] += 1

        # 更新建築物的max_age
        if feature.get('max_age') != final_age:
            feature['max_age'] = final_age
            stats['buildings_updated'] += 1

        # 添加年齡來源資訊
        feature['age_source'] = age_source
        feature['filled_age'] = final_age

    # 儲存結果
    if output_file is None:
        output_file = geojson_file.replace('.geojson', '_with_filled_ages.geojson')

    print(f"\nSaving results to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    return stats, output_file

def print_fill_report(stats: Dict[str, Any], output_file: str) -> None:
    """打印填補結果報告"""

    print("\n" + "="*70)
    print("Building Age Filling Report")
    print("="*70)

    print(f"\n📊 Processing Summary:")
    print(f"  Total buildings processed: {stats['total_buildings']:,}")
    print(f"  Buildings updated: {stats['buildings_updated']:,}")
    print(f"  Reference year: {stats['reference_year']}")
    print(f"  Default construction year: {stats['default_construction_year']}")

    print(f"\n📈 Age Source Distribution:")
    print(f"  Used original max_age: {stats['used_max_age']:,} ({stats['used_max_age']/stats['total_buildings']:.1%})")
    print(f"  Used polygon max age: {stats['used_polygon_max_age']:,} ({stats['used_polygon_max_age']/stats['total_buildings']:.1%})")
    print(f"  Used default age: {stats['used_default_age']:,} ({stats['used_default_age']/stats['total_buildings']:.1%})")

    # 簡單的視覺化
    max_age_bar = "█" * int(stats['used_max_age'] / stats['total_buildings'] * 50)
    polygon_bar = "█" * int(stats['used_polygon_max_age'] / stats['total_buildings'] * 50)
    default_bar = "█" * int(stats['used_default_age'] / stats['total_buildings'] * 50)

    print(f"\n📊 Visual Distribution:")
    print(f"  Original max_age:  {max_age_bar}")
    print(f"  Polygon max age:   {polygon_bar}")
    print(f"  Default age:       {default_bar}")

    print(f"\n✅ Output file: {output_file}")
    print("="*70)

def validate_filled_ages(geojson_file: str) -> Dict[str, Any]:
    """驗證填補後的年齡資料"""

    print(f"\nValidating filled ages in: {geojson_file}")

    with open(geojson_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    validation_stats = {
        'total_buildings': len(data['features']),
        'buildings_with_age': 0,
        'buildings_without_age': 0,
        'age_sources': {
            'max_age': 0,
            'polygon_max_age': 0,
            'default_pre1999': 0
        },
        'age_range': {
            'min_age': float('inf'),
            'max_age': 0,
            'mean_age': 0
        }
    }

    ages = []
    for feature in data['features']:
        age = feature.get('filled_age') or feature.get('max_age')
        age_source = feature.get('age_source', 'unknown')

        if age is not None and age != 'null':
            try:
                age_value = float(age)
                ages.append(age_value)
                validation_stats['buildings_with_age'] += 1

                if age_source in validation_stats['age_sources']:
                    validation_stats['age_sources'][age_source] += 1

            except (ValueError, TypeError):
                validation_stats['buildings_without_age'] += 1
        else:
            validation_stats['buildings_without_age'] += 1

    if ages:
        validation_stats['age_range']['min_age'] = min(ages)
        validation_stats['age_range']['max_age'] = max(ages)
        validation_stats['age_range']['mean_age'] = sum(ages) / len(ages)

    print(f"✅ Validation completed:")
    print(f"  Buildings with valid age: {validation_stats['buildings_with_age']:,}")
    print(f"  Buildings without age: {validation_stats['buildings_without_age']:,}")
    print(f"  Age range: {validation_stats['age_range']['min_age']:.1f} - {validation_stats['age_range']['max_age']:.1f} years")
    print(f"  Mean age: {validation_stats['age_range']['mean_age']:.1f} years")

    return validation_stats

def main():
    """主程序"""
    parser = argparse.ArgumentParser(
        description="Fill missing building ages using hierarchical strategy",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        'input_file',
        help='Input GeoJSON file'
    )

    parser.add_argument(
        '--output',
        help='Output GeoJSON file (default: input_file_with_filled_ages.geojson)'
    )

    parser.add_argument(
        '--reference-year',
        type=int,
        default=datetime.now().year,
        help='Reference year for age calculation'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate the filled ages after processing'
    )

    parser.add_argument(
        '--stats-output',
        help='Save processing statistics to JSON file'
    )

    args = parser.parse_args()

    # 檢查輸入檔案
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {args.input_file}")
        return 1

    try:
        print("🔧 Starting building age filling process...")

        # 執行年齡填補
        stats, output_file = fill_building_ages(
            args.input_file,
            args.output,
            args.reference_year
        )

        # 打印報告
        print_fill_report(stats, output_file)

        # 驗證結果
        if args.validate:
            validation_stats = validate_filled_ages(output_file)
            stats['validation'] = validation_stats

        # 儲存統計資料
        if args.stats_output:
            with open(args.stats_output, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            print(f"📊 Statistics saved to: {args.stats_output}")

        print("\n✅ Age filling completed successfully!")
        return 0

    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())