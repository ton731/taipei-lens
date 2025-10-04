#!/usr/bin/env python3
"""
視覺化 Shapefile 資料 - 支援多種編碼
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import folium
from pathlib import Path
import pandas as pd
import chardet
import warnings
warnings.filterwarnings('ignore')

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def detect_encoding(file_path):
    """檢測檔案編碼"""
    try:
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read())
            return result['encoding']
    except:
        return None


def read_shapefile_with_encoding(shp_path):
    """嘗試使用不同編碼讀取 shapefile"""
    # 常見的編碼列表
    encodings = [
        'utf-8',
        'big5',
        'cp950',
        'gbk',
        'gb2312',
        'gb18030',
        'latin1',
        'iso-8859-1',
        'windows-1252',
        'cp1252'
    ]

    # 如果是資料夾，找到 .shp 檔案
    if Path(shp_path).is_dir():
        shp_files = list(Path(shp_path).glob('*.shp'))
        if shp_files:
            shp_path = str(shp_files[0])

    # 檢測 .dbf 檔案編碼
    dbf_path = shp_path.replace('.shp', '.dbf')
    if Path(dbf_path).exists():
        detected = detect_encoding(dbf_path)
        if detected and detected not in encodings:
            encodings.insert(0, detected)
            print(f"檢測到編碼: {detected}")

    # 嘗試不同編碼
    for encoding in encodings:
        try:
            print(f"嘗試使用編碼: {encoding}")
            gdf = gpd.read_file(shp_path, encoding=encoding)
            print(f"成功使用編碼 {encoding} 讀取 shapefile")
            return gdf, encoding
        except Exception as e:
            continue

    # 如果都失敗，嘗試不指定編碼
    try:
        print("嘗試使用預設編碼...")
        gdf = gpd.read_file(shp_path)
        return gdf, 'default'
    except Exception as e:
        raise Exception(f"無法讀取 shapefile: {e}")


def visualize_shapefile(shp_path, output_html=None):
    """
    讀取並視覺化 shapefile

    Parameters:
    -----------
    shp_path : str
        Shapefile 資料夾路徑或 .shp 檔案路徑
    output_html : str, optional
        輸出的互動式地圖 HTML 檔案路徑
    """

    # 讀取 shapefile
    print(f"正在讀取 shapefile: {shp_path}")
    gdf, encoding = read_shapefile_with_encoding(shp_path)

    # 顯示基本資訊
    print("\n" + "="*50)
    print("Shapefile 基本資訊")
    print("="*50)
    print(f"成功編碼: {encoding}")
    print(f"資料筆數: {len(gdf)}")
    print(f"座標系統 (CRS): {gdf.crs}")

    # 統計幾何類型
    geom_types = gdf.geometry.type.value_counts().to_dict()
    print(f"幾何類型: {geom_types}")

    bounds = gdf.total_bounds
    print(f"邊界範圍:")
    print(f"  最小經度: {bounds[0]:.6f}")
    print(f"  最小緯度: {bounds[1]:.6f}")
    print(f"  最大經度: {bounds[2]:.6f}")
    print(f"  最大緯度: {bounds[3]:.6f}")

    # 顯示欄位資訊
    print("\n" + "="*50)
    print("欄位資訊")
    print("="*50)
    for col in gdf.columns:
        if col != 'geometry':
            dtype = gdf[col].dtype
            unique_count = gdf[col].nunique()
            null_count = gdf[col].isnull().sum()
            print(f"  {col}:")
            print(f"    - 資料型態: {dtype}")
            print(f"    - 唯一值數量: {unique_count}")
            print(f"    - 空值數量: {null_count}")

            # 如果是文字欄位，顯示前幾個範例
            if dtype == 'object' and unique_count < 20:
                sample_values = gdf[col].dropna().unique()[:5]
                print(f"    - 範例值: {list(sample_values)}")

    # 顯示前幾筆資料
    print("\n" + "="*50)
    print("前 5 筆資料 (不含 geometry)")
    print("="*50)
    print(gdf.drop('geometry', axis=1, errors='ignore').head().to_string())

    # 1. 使用 matplotlib 做靜態視覺化
    fig = plt.figure(figsize=(16, 10))

    # 基本圖形
    ax1 = plt.subplot(2, 2, 1)
    gdf.plot(ax=ax1, color='lightblue', edgecolor='black', linewidth=0.5, alpha=0.7)
    ax1.set_title('Shapefile 基本視覺化', fontsize=14, fontweight='bold')
    ax1.set_xlabel('經度')
    ax1.set_ylabel('緯度')
    ax1.grid(True, alpha=0.3)

    # 找出數值欄位
    numeric_cols = gdf.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns.tolist()
    if 'geometry' in numeric_cols:
        numeric_cols.remove('geometry')

    # 顏色視覺化
    ax2 = plt.subplot(2, 2, 2)
    if numeric_cols:
        # 使用第一個數值欄位來上色
        col_to_plot = numeric_cols[0]
        gdf.plot(column=col_to_plot, ax=ax2, legend=True,
                cmap='viridis', edgecolor='black', linewidth=0.5,
                legend_kwds={'label': col_to_plot, 'orientation': "vertical", 'shrink': 0.8})
        ax2.set_title(f'依 {col_to_plot} 上色', fontsize=14, fontweight='bold')
    else:
        # 如果沒有數值欄位，使用索引上色
        gdf['temp_id'] = range(len(gdf))
        gdf.plot(column='temp_id', ax=ax2, cmap='tab20',
                edgecolor='black', linewidth=0.5, alpha=0.7)
        ax2.set_title('區域分布（依索引上色）', fontsize=14, fontweight='bold')
        gdf.drop('temp_id', axis=1, inplace=True)

    ax2.set_xlabel('經度')
    ax2.set_ylabel('緯度')
    ax2.grid(True, alpha=0.3)

    # 面積分布（如果是多邊形）
    ax3 = plt.subplot(2, 2, 3)
    if 'Polygon' in str(geom_types):
        areas = gdf.geometry.area
        ax3.hist(areas, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
        ax3.set_title('面積分布直方圖', fontsize=14, fontweight='bold')
        ax3.set_xlabel('面積')
        ax3.set_ylabel('數量')
        ax3.grid(True, alpha=0.3)
    else:
        ax3.text(0.5, 0.5, '非多邊形資料', ha='center', va='center', fontsize=16)
        ax3.set_title('面積分布', fontsize=14, fontweight='bold')

    # 統計資訊
    ax4 = plt.subplot(2, 2, 4)
    ax4.axis('off')

    # 建立統計摘要文字
    stats_text = f"""
    資料統計摘要
    {'='*30}
    總筆數: {len(gdf)}
    座標系統: {gdf.crs}
    幾何類型: {', '.join(geom_types.keys())}

    數值欄位統計:
    """

    if numeric_cols:
        for col in numeric_cols[:3]:  # 只顯示前3個數值欄位
            stats_text += f"\n{col}:"
            stats_text += f"\n  平均: {gdf[col].mean():.2f}"
            stats_text += f"\n  標準差: {gdf[col].std():.2f}"
            stats_text += f"\n  最小值: {gdf[col].min():.2f}"
            stats_text += f"\n  最大值: {gdf[col].max():.2f}"
    else:
        stats_text += "\n(無數值欄位)"

    ax4.text(0.1, 0.9, stats_text, transform=ax4.transAxes,
             fontsize=10, verticalalignment='top', family='monospace')

    plt.tight_layout()

    # 儲存靜態圖片
    static_output = Path(shp_path).parent / "shapefile_static.png"
    plt.savefig(static_output, dpi=100, bbox_inches='tight')
    print(f"\n靜態圖片已儲存至: {static_output}")

    plt.show()

    # 2. 使用 folium 做互動式地圖
    print("\n建立互動式地圖...")

    # 轉換座標系統
    if gdf.crs and gdf.crs != 'EPSG:4326':
        print(f"轉換座標系統從 {gdf.crs} 至 WGS84 (EPSG:4326)...")
        gdf_wgs84 = gdf.to_crs('EPSG:4326')
    else:
        gdf_wgs84 = gdf

    # 計算中心點和縮放等級
    bounds = gdf_wgs84.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # 計算適當的縮放等級
    lat_range = bounds[3] - bounds[1]
    lon_range = bounds[2] - bounds[0]
    max_range = max(lat_range, lon_range)

    if max_range > 5:
        zoom_start = 8
    elif max_range > 1:
        zoom_start = 10
    elif max_range > 0.5:
        zoom_start = 11
    elif max_range > 0.1:
        zoom_start = 13
    else:
        zoom_start = 14

    # 建立 folium 地圖
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles=None
    )

    # 加入多個底圖選項
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB positron', name='淺色地圖').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='深色地圖').add_to(m)

    # 準備 GeoJson 資料
    geojson_data = gdf_wgs84.to_json()

    # 取得要顯示的欄位（排除 geometry）
    display_fields = [col for col in gdf_wgs84.columns if col != 'geometry']

    # 限制顯示欄位數量（最多10個）
    if len(display_fields) > 10:
        display_fields = display_fields[:10]

    # 加入 GeoJson 圖層
    folium.GeoJson(
        geojson_data,
        name='Shapefile 圖層',
        style_function=lambda feature: {
            'fillColor': '#3388ff',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.5,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=display_fields,
            aliases=display_fields,
            localize=True,
            sticky=False,
            labels=True,
            style="""
                background-color: white;
                border: 2px solid black;
                border-radius: 3px;
                box-shadow: 3px;
                font-size: 12px;
            """,
        ),
        highlight_function=lambda x: {
            'weight': 3,
            'fillOpacity': 0.8,
            'color': 'red'
        },
    ).add_to(m)

    # 加入圖層控制
    folium.LayerControl(position='topright').add_to(m)

    # 加入全螢幕按鈕
    folium.plugins.Fullscreen(
        position='topleft',
        title='全螢幕',
        title_cancel='退出全螢幕',
        force_separate_button=True,
    ).add_to(m)

    # 儲存互動式地圖
    if output_html:
        output_path = output_html
    else:
        output_path = Path(shp_path).parent / "shapefile_map.html"

    m.save(str(output_path))
    print(f"互動式地圖已儲存至: {output_path}")

    return gdf


def visualize_simple_shapefiles(shp_paths):
    """
    簡單視覺化多個 shapefile - 只顯示黑白邊界
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for i, shp_path in enumerate(shp_paths):
        try:
            print(f"正在讀取 shapefile {i+1}: {shp_path}")
            gdf, encoding = read_shapefile_with_encoding(shp_path)

            # 簡單的黑白視覺化
            gdf.plot(ax=axes[i], color='lightgray', edgecolor='black', linewidth=0.5)

            # 設定標題為路徑
            axes[i].set_title(str(shp_path).split('/')[-1], fontsize=12, fontweight='bold')
            axes[i].set_xlabel('經度')
            axes[i].set_ylabel('緯度')
            axes[i].grid(True, alpha=0.3)

            print(f"成功載入 {len(gdf)} 筆資料")

        except Exception as e:
            print(f"無法讀取 {shp_path}: {e}")
            axes[i].text(0.5, 0.5, f'無法讀取\n{shp_path}',
                        ha='center', va='center', fontsize=12,
                        transform=axes[i].transAxes)
            axes[i].set_title(f"錯誤: {shp_path}", fontsize=12, color='red')

    plt.tight_layout()
    plt.show()


def main():
    print("="*50)
    print("Shapefile 視覺化工具")
    print("="*50)

    # 三個 shapefile 路徑
    shp_paths = [
        "data/basic_statistical_area/11401全市細計_土地利用",
        "data/basic_statistical_area/STAT/113年12月臺北市統計區人口統計_最小統計區/113年12月臺北市統計區人口統計_最小統計區_SHP",
        "data/basic_statistical_area/STAT/113年12月臺北市統計區人口指標_最小統計區/113年12月臺北市統計區人口指標_最小統計區_SHP"
    ]

    try:
        # 視覺化三個 shapefile
        visualize_simple_shapefiles(shp_paths)

        print("\n" + "="*50)
        print("處理完成！")
        print("="*50)

    except Exception as e:
        print(f"\n錯誤: {e}")
        print("\n可能的原因:")
        print("1. Shapefile 路徑不正確")
        print("2. 缺少必要的檔案 (.shp, .shx, .dbf)")
        print("3. 檔案損壞或格式不正確")
        print("4. 需要安裝相關套件: pip install geopandas matplotlib folium chardet")


if __name__ == "__main__":
    main()