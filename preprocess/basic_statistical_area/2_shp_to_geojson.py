#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
將 Shapefile 轉換為 GeoJSON 格式
"""

import geopandas as gpd
import pandas as pd
import json
from pathlib import Path
import chardet
import warnings
import sys
import locale

warnings.filterwarnings('ignore')

# 設定編碼
sys.stdout.reconfigure(encoding='utf-8')
locale.setlocale(locale.LC_ALL, '')


def detect_encoding(file_path):
    """檢測檔案編碼"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result['encoding']
    except Exception as e:
        print(f"編碼檢測失敗: {e}")
        return None


def read_shapefile_with_encoding(shp_path):
    """嘗試使用不同編碼讀取 shapefile"""

    # 如果是資料夾，找到 .shp 檔案（支援大小寫）
    if Path(shp_path).is_dir():
        # 先嘗試小寫
        shp_files = list(Path(shp_path).glob('*.shp'))
        # 如果沒找到，嘗試大寫
        if not shp_files:
            shp_files = list(Path(shp_path).glob('*.SHP'))

        if shp_files:
            shp_path = str(shp_files[0])
            print(f"找到 shapefile: {shp_path}")
        else:
            # 列出資料夾內容以便除錯
            all_files = list(Path(shp_path).glob('*'))
            file_list = [f.name for f in all_files]
            raise Exception(f"在資料夾 {shp_path} 中找不到 .shp 或 .SHP 檔案。找到的檔案: {file_list}")

    # 常見的編碼列表（針對台灣地區）
    encodings = [
        'utf-8',
        'cp950',      # Windows 繁體中文
        'big5',       # Big5 繁體中文
        'big5hkscs',  # Big5 香港增補字符集
        'gbk',        # 簡體中文
        'gb2312',
        'gb18030',
        'latin1',
        'iso-8859-1',
        'windows-1252',
        'cp1252'
    ]

    # 檢測 .dbf 檔案編碼（支援大小寫）
    dbf_path_lower = shp_path.replace('.shp', '.dbf').replace('.SHP', '.dbf')
    dbf_path_upper = shp_path.replace('.shp', '.DBF').replace('.SHP', '.DBF')

    dbf_path = None
    if Path(dbf_path_lower).exists():
        dbf_path = dbf_path_lower
    elif Path(dbf_path_upper).exists():
        dbf_path = dbf_path_upper

    if dbf_path:
        print(f"找到 DBF 檔案: {dbf_path}")
        detected = detect_encoding(dbf_path)
        if detected and detected.lower() not in [enc.lower() for enc in encodings]:
            encodings.insert(0, detected)
            print(f"檢測到編碼: {detected}")

    # 嘗試不同編碼
    last_error = None
    for encoding in encodings:
        try:
            print(f"嘗試編碼: {encoding}")
            gdf = gpd.read_file(shp_path, encoding=encoding)

            # 檢查是否有中文字符能正確顯示
            for col in gdf.columns:
                if col != 'geometry' and gdf[col].dtype == 'object':
                    sample = gdf[col].dropna().iloc[0] if len(gdf[col].dropna()) > 0 else ""
                    if sample:
                        # 嘗試顯示樣本來驗證編碼
                        print(f"樣本資料 ({col}): {sample}")
                        break

            print(f"✓ 成功使用編碼 {encoding} 讀取 shapefile")
            return gdf, encoding

        except Exception as e:
            last_error = e
            print(f"✗ 編碼 {encoding} 失敗: {str(e)[:100]}")
            continue

    # 如果都失敗，嘗試不指定編碼
    try:
        print("嘗試預設編碼...")
        gdf = gpd.read_file(shp_path)
        print("✓ 成功使用預設編碼")
        return gdf, 'default'
    except Exception as e:
        raise Exception(f"無法讀取 shapefile，最後錯誤: {last_error}")


def load_csv_data(csv_paths):
    """
    載入 CSV 資料並建立以 CODEBASE 為索引的字典

    Parameters:
    -----------
    csv_paths : dict
        包含 'population' 和 'indicators' 鍵的字典，對應各 CSV 檔案路徑

    Returns:
    --------
    dict : 以 CODEBASE 為鍵的資料字典
    """
    print(f"\n📊 正在讀取 CSV 資料...")

    # 讀取人口統計 CSV（戶數、人口數）
    pop_df = pd.read_csv(csv_paths['population'], encoding='utf-8-sig')
    print(f"   ✅ 已讀取人口統計資料: {len(pop_df)} 筆")

    # 讀取人口指標 CSV（人口密度、戶量）
    ind_df = pd.read_csv(csv_paths['indicators'], encoding='utf-8-sig')
    print(f"   ✅ 已讀取人口指標資料: {len(ind_df)} 筆")

    # 建立資料字典
    data_dict = {}

    # 合併兩個 DataFrame
    for _, row in pop_df.iterrows():
        codebase = row['CODEBASE']
        data_dict[codebase] = {
            'H_CNT': row['H_CNT'],      # 戶數
            'P_CNT': row['P_CNT'],      # 人口數
            'M_CNT': row['M_CNT'],      # 男性人口數
            'F_CNT': row['F_CNT']       # 女性人口數
        }

    # 加入人口指標資料
    for _, row in ind_df.iterrows():
        codebase = row['CODEBASE']
        if codebase in data_dict:
            data_dict[codebase].update({
                'P_DEN': row['P_DEN'],      # 人口密度
                'P_H_CNT': row['P_H_CNT'],  # 戶量（平均每戶人數）
                'M_F_RAT': row['M_F_RAT']   # 性比例
            })

    print(f"   ✅ 已建立 {len(data_dict)} 個統計區的資料字典\n")

    return data_dict


def shp_to_geojson(shp_path, output_path, csv_paths=None, compress=True):
    """
    將 Shapefile 轉換為 GeoJSON，並加入 CSV 資料

    Parameters:
    -----------
    shp_path : str
        Shapefile 資料夾路徑或 .shp 檔案路徑
    output_path : str
        輸出的 GeoJSON 檔案路徑
    csv_paths : dict, optional
        包含 'population' 和 'indicators' 鍵的字典，對應各 CSV 檔案路徑
    compress : bool
        是否壓縮輸出（移除空白和縮排）
    """

    print(f"正在讀取 Shapefile: {shp_path}")
    print("-" * 50)

    # 載入 CSV 資料（如果有提供）
    csv_data = None
    if csv_paths:
        csv_data = load_csv_data(csv_paths)

    # 讀取 shapefile
    gdf, encoding = read_shapefile_with_encoding(shp_path)

    # 顯示基本資訊
    print(f"\n📄 基本資訊:")
    print(f"   使用編碼: {encoding}")
    print(f"   資料筆數: {len(gdf):,}")
    print(f"   座標系統: {gdf.crs}")
    print(f"   幾何類型: {gdf.geometry.type.value_counts().to_dict()}")

    # 顯示欄位資訊
    print(f"\n📊 欄位資訊:")
    for col in gdf.columns:
        if col != 'geometry':
            dtype = gdf[col].dtype
            unique_count = gdf[col].nunique()
            null_count = gdf[col].isnull().sum()
            print(f"   {col}: {dtype} (唯一值: {unique_count:,}, 空值: {null_count:,})")

            # 顯示範例值
            if dtype == 'object' and not gdf[col].dropna().empty:
                sample_values = gdf[col].dropna().unique()[:3]
                print(f"      範例: {list(sample_values)}")

    # 轉換座標系統至 WGS84 (如果需要)
    if gdf.crs is None:
        # 沒有座標系統資訊，先假設為台灣常用的 TWD97 TM2
        print("\n⚠️  警告: 沒有座標系統資訊，假設為 TWD97 TM2 (EPSG:3826)")
        gdf.crs = 'EPSG:3826'

    if str(gdf.crs) != 'EPSG:4326':
        print(f"\n🔄 轉換座標系統從 {gdf.crs} 至 WGS84 (EPSG:4326)...")
        original_crs = gdf.crs
        try:
            gdf = gdf.to_crs('EPSG:4326')
            print(f"   ✅ 成功轉換從 {original_crs} 至 EPSG:4326")
        except Exception as e:
            # 如果轉換失敗，可能需要嘗試其他台灣常用座標系統
            print(f"   ⚠️  使用 {original_crs} 轉換失敗，嘗試 TWD97 TM2 (EPSG:3826)...")
            gdf.crs = 'EPSG:3826'
            gdf = gdf.to_crs('EPSG:4326')
            print(f"   ✅ 成功轉換從 EPSG:3826 至 EPSG:4326")

    # 加入 CSV 資料到 GeoDataFrame
    if csv_data:
        print(f"\n🔧 正在合併 CSV 資料到 Shapefile...")

        # 檢查 CODEBASE 欄位
        if 'CODEBASE' in gdf.columns:
            print(f"   找到 CODEBASE 欄位")

            # 為每一行加入對應的 CSV 資料
            matched_count = 0
            unmatched_count = 0

            for idx, row in gdf.iterrows():
                codebase = row['CODEBASE']
                if codebase in csv_data:
                    # 將 CSV 資料加入到 GeoDataFrame，並確保資料型別正確
                    for key, value in csv_data[codebase].items():
                        # 轉換資料型別
                        if key in ['H_CNT', 'P_CNT']:  # 戶數、人口數
                            gdf.at[idx, key] = int(value) if value is not None and not pd.isna(value) else 0
                        elif key == 'P_DEN':  # 人口密度
                            gdf.at[idx, key] = float(value) if value is not None and not pd.isna(value) else 0.0
                        else:
                            gdf.at[idx, key] = value
                    matched_count += 1
                else:
                    unmatched_count += 1

            print(f"   ✅ 成功合併 {matched_count} 筆資料")
            if unmatched_count > 0:
                print(f"   ⚠️  有 {unmatched_count} 筆資料找不到對應的 CODEBASE")
        else:
            print(f"   ⚠️  警告: 找不到 CODEBASE 欄位，無法合併 CSV 資料")
            print(f"   可用欄位: {[c for c in gdf.columns if c != 'geometry']}")

    # 精簡屬性，保留需要的欄位
    print(f"\n🔧 整理屬性欄位...")
    original_columns = list(gdf.columns)
    print(f"   原始欄位數: {len([c for c in original_columns if c != 'geometry'])}")

    # 決定要保留的欄位
    keep_columns = ['geometry']

    # 保留 TOWN 或 CODEBASE
    if 'TOWN' in gdf.columns:
        keep_columns.append('TOWN')
    if 'CODEBASE' in gdf.columns:
        keep_columns.append('CODEBASE')

    # 保留 CSV 加入的資料欄位（只保留需要的）
    if csv_data:
        csv_fields = ['H_CNT', 'P_CNT', 'P_DEN']  # 戶數、人口數、人口密度
        for field in csv_fields:
            if field in gdf.columns:
                keep_columns.append(field)

    # 只保留需要的欄位
    gdf = gdf[keep_columns]

    # 重新命名欄位
    rename_map = {
        'H_CNT': 'household',           # 戶數
        'P_CNT': 'population',          # 人口數
        'P_DEN': 'population_density'   # 人口密度
    }
    gdf = gdf.rename(columns=rename_map)

    # 確保資料型別正確
    if 'household' in gdf.columns:
        gdf['household'] = gdf['household'].fillna(0).astype(int)
    if 'population' in gdf.columns:
        gdf['population'] = gdf['population'].fillna(0).astype(int)
    if 'population_density' in gdf.columns:
        gdf['population_density'] = gdf['population_density'].fillna(0.0).astype(float)

    final_fields = [c for c in gdf.columns if c != 'geometry']
    print(f"   ✅ 已整理至 {len(final_fields)} 個屬性欄位: {final_fields}")

    # 移除 Z 坐標（高度），只保留 X, Y 坐標
    print(f"\n🔧 移除 Z 坐標，只保留經緯度...")

    def remove_z_coordinate(geom):
        """移除幾何圖形的 Z 坐標"""
        try:
            from shapely.ops import transform
            from shapely.geometry import Point, LineString, Polygon, MultiPolygon

            if geom is None:
                return geom

            def remove_z(x, y, z=None):
                return (x, y)

            return transform(remove_z, geom)
        except Exception as e:
            print(f"   警告: 移除 Z 坐標時發生錯誤: {e}")
            return geom

    # 對所有幾何圖形移除 Z 座標
    gdf['geometry'] = gdf['geometry'].apply(remove_z_coordinate)

    print(f"   ✅ 已移除 Z 坐標，現在只有經度 (X) 和緯度 (Y)")

    # 顯示座標範圍
    bounds = gdf.total_bounds
    print(f"\n📍 座標範圍:")
    print(f"   經度範圍: {bounds[0]:.6f} ~ {bounds[2]:.6f}")
    print(f"   緯度範圍: {bounds[1]:.6f} ~ {bounds[3]:.6f}")

    # 確保輸出目錄存在
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 轉換為 GeoJSON 格式
    print(f"\n💾 正在轉換為 GeoJSON...")

    try:
        # 確保輸出為 2D 座標（無 Z 值）
        print("   確保輸出格式為 2D 座標...")

        if compress:
            # 壓縮輸出 - 無縮排，無空格，確保無 Z 坐標
            geojson_str = gdf.to_json(
                ensure_ascii=False,
                separators=(',', ':'),
                drop_id=True,
                to_wgs84=False  # 避免額外座標轉換
            )
            print("   使用壓縮格式（2D 座標）")
        else:
            # 格式化輸出 - 有縮排，確保無 Z 坐標
            geojson_str = gdf.to_json(
                ensure_ascii=False,
                indent=2,
                drop_id=True,
                to_wgs84=False  # 避免額外座標轉換
            )
            print("   使用格式化輸出（2D 座標）")

        # 檢查並移除可能殘留的 Z 坐標
        import json
        geojson_data = json.loads(geojson_str)

        def clean_coordinates(coords):
            """清理座標，確保只有 X, Y"""
            if isinstance(coords, list):
                if len(coords) > 0 and isinstance(coords[0], (int, float)):
                    # 這是座標點 [x, y] 或 [x, y, z]
                    return coords[:2]  # 只取前兩個值
                else:
                    # 這是座標陣列，遞迴處理
                    return [clean_coordinates(coord) for coord in coords]
            return coords

        # 清理所有特徵的座標
        if 'features' in geojson_data:
            for feature in geojson_data['features']:
                if 'geometry' in feature and 'coordinates' in feature['geometry']:
                    feature['geometry']['coordinates'] = clean_coordinates(
                        feature['geometry']['coordinates']
                    )

        # 重新序列化
        if compress:
            geojson_str = json.dumps(geojson_data, ensure_ascii=False, separators=(',', ':'))
        else:
            geojson_str = json.dumps(geojson_data, ensure_ascii=False, indent=2)

        # 寫入檔案
        print(f"   寫入檔案: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(geojson_str)

        # 顯示檔案大小
        file_size = Path(output_path).stat().st_size
        if file_size > 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.2f} MB"
        elif file_size > 1024:
            size_str = f"{file_size / 1024:.2f} KB"
        else:
            size_str = f"{file_size} bytes"

        print(f"✅ 轉換完成！檔案大小: {size_str}")

    except Exception as e:
        raise Exception(f"GeoJSON 轉換失敗: {e}")

    return gdf


def main():
    print("=" * 60)
    print("🗺️  Shapefile 轉 GeoJSON 工具")
    print("=" * 60)

    # 指定 Shapefile 路徑和輸出路徑
    shp_path = "data/basic_statistical_area/STAT/113年12月臺北市統計區人口統計_最小統計區/113年12月臺北市統計區人口統計_最小統計區_SHP"
    output_path = "data/basic_statistical_area/geojson/basic_statistical_area.geojson"

    # 指定 CSV 路徑
    csv_paths = {
        'population': 'data/basic_statistical_area/STAT/113年12月臺北市統計區人口統計_最小統計區/113年12月臺北市統計區人口統計_最小統計區.csv',
        'indicators': 'data/basic_statistical_area/STAT/113年12月臺北市統計區人口指標_最小統計區/113年12月臺北市統計區人口指標_最小統計區.csv'
    }

    print(f"📂 Shapefile 路徑: {shp_path}")
    print(f"📊 人口統計 CSV: {csv_paths['population']}")
    print(f"📊 人口指標 CSV: {csv_paths['indicators']}")
    print(f"📁 輸出路徑: {output_path}")

    try:
        # 檢查輸入路徑是否存在
        if not Path(shp_path).exists():
            raise Exception(f"找不到 Shapefile 路徑: {shp_path}")

        # 檢查 CSV 檔案是否存在
        for key, csv_path in csv_paths.items():
            if not Path(csv_path).exists():
                raise Exception(f"找不到 CSV 檔案: {csv_path}")

        # 執行轉換
        gdf = shp_to_geojson(
            shp_path=shp_path,
            output_path=output_path,
            csv_paths=csv_paths,
            compress=True  # 壓縮輸出
        )

        print(f"\n" + "=" * 60)
        print("🎉 轉換作業完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 轉換失敗: {e}")
        print("\n可能原因:")
        print("1. Shapefile 路徑不正確")
        print("2. 缺少必要檔案 (.shp, .shx, .dbf)")
        print("3. 檔案編碼問題")
        print("4. 權限不足")


if __name__ == "__main__":
    main()