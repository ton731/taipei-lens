import geopandas as gpd
import folium
from folium import plugins
from pathlib import Path
import pandas as pd

def prepare_merged_geodataframe(gdf, sample_size=500):
    """
    準備合併後的 GeoDataFrame 並處理缺失值

    Args:
        gdf: 合併後的 GeoDataFrame
        sample_size: 要顯示的樣本數量

    Returns:
        處理後的 GeoDataFrame 和顯示欄位列表
    """
    # 取樣本資料
    gdf_sample = gdf.head(sample_size).copy()

    # 統計資料來源
    total_buildings = len(gdf_sample)
    has_ghs_data = 0
    has_osm_data = 0
    has_both = 0

    # 分類欄位
    osm_fields = [col for col in gdf_sample.columns if col.startswith('osm_')]
    ghs_fields = [col for col in gdf_sample.columns if col.startswith('ghs_')]

    # 選擇重要的顯示欄位
    important_display_fields = []

    # OSM 重要欄位（優先顯示）
    osm_priority = [
        'osm_name', 'osm_name:zh', 'osm_name:zh-Hant',
        'osm_building', 'osm_building:levels', 'osm_height',
        'osm_amenity', 'osm_shop', 'osm_addr:street'
    ]

    # GHS 重要欄位（優先顯示）
    ghs_priority = [
        'ghs_BUILT', 'ghs_POP', 'ghs_AGBH_1990', 'ghs_AGBH_2000',
        'ghs_AGBH_2010', 'ghs_AGBH_2020', 'ghs_AGBH_2025', 'ghs_AGBH_2030'
    ]

    # 加入存在的重要欄位
    for field in osm_priority + ghs_priority:
        if field in gdf_sample.columns:
            important_display_fields.append(field)

    # 加入其他欄位（限制數量避免太多）
    other_fields = [col for col in gdf_sample.columns
                   if col not in important_display_fields
                   and col != 'geometry'
                   and not col.startswith('index')]

    # 限制總欄位數量為20個
    display_fields = important_display_fields + other_fields[:max(0, 20 - len(important_display_fields))]

    # 處理缺失值和資料類型
    for field in display_fields:
        if field in gdf_sample.columns:
            # 處理時間戳記
            if gdf_sample[field].dtype == 'datetime64[ns]' or str(gdf_sample[field].dtype).startswith('datetime'):
                gdf_sample[field] = gdf_sample[field].astype(str)

            # 處理 Timestamp 物件
            try:
                gdf_sample[field] = gdf_sample[field].apply(
                    lambda x: str(x) if hasattr(x, 'timestamp') or pd.api.types.is_datetime64_any_dtype(type(x)) else x
                )
            except:
                pass

            # 填充 null 值
            gdf_sample[field] = gdf_sample[field].fillna('N/A').astype(str)

    # 統計資料完整性
    for idx, row in gdf_sample.iterrows():
        has_osm = any(row[field] != 'N/A' for field in osm_fields if field in row.index)
        has_ghs = any(row[field] != 'N/A' for field in ghs_fields if field in row.index)

        if has_osm:
            has_osm_data += 1
        if has_ghs:
            has_ghs_data += 1
        if has_osm and has_ghs:
            has_both += 1

    print(f"\n資料統計（前 {sample_size} 筆）：")
    print(f"總建築物數量: {total_buildings}")
    print(f"有 OSM 資料: {has_osm_data}")
    print(f"有 GHS 資料: {has_ghs_data}")
    print(f"同時有兩種資料: {has_both}")
    print(f"顯示欄位數: {len(display_fields)}")

    return gdf_sample, display_fields


def determine_building_color(row):
    """
    根據建築物的資料來源決定顏色

    Args:
        row: DataFrame 的一列

    Returns:
        顏色配置字典
    """
    # 檢查是否有 GHS 和 OSM 資料
    has_ghs = False
    has_osm = False

    # 檢查 GHS 欄位
    for col in row.index:
        if col.startswith('ghs_') and pd.notna(row[col]) and row[col] != 'N/A':
            has_ghs = True
            break

    # 檢查 OSM 欄位（基本上都會有，因為 geometry 來自 OSM）
    for col in row.index:
        if col.startswith('osm_') and pd.notna(row[col]) and row[col] != 'N/A':
            has_osm = True
            break

    # 根據資料完整性決定顏色
    if has_ghs and has_osm:
        # 兩種資料都有：綠色
        return {
            'color': 'darkgreen',
            'fillColor': 'lightgreen',
            'fillOpacity': 0.7,
            'weight': 2
        }
    elif has_ghs:
        # 只有 GHS 資料：紅色
        return {
            'color': 'darkred',
            'fillColor': 'lightcoral',
            'fillOpacity': 0.6,
            'weight': 2
        }
    else:
        # 只有 OSM 資料：藍色
        return {
            'color': 'darkblue',
            'fillColor': 'lightblue',
            'fillOpacity': 0.5,
            'weight': 2
        }


def create_merged_map(gdf_sample, display_fields):
    """
    建立合併資料的地圖

    Args:
        gdf_sample: 處理後的樣本資料
        display_fields: 要顯示的欄位列表

    Returns:
        Folium 地圖物件
    """
    # 計算地圖中心點
    center_point = gdf_sample.union_all().centroid
    map_center = [center_point.y, center_point.x]

    # 初始化地圖
    m = folium.Map(
        location=map_center,
        zoom_start=16,
        tiles='CartoDB positron',
        control_scale=True
    )

    # 建立三個圖層群組：完整資料、只有GHS、只有OSM
    layer_both = folium.FeatureGroup(name='完整資料 (OSM + GHS)', show=True)
    layer_ghs_only = folium.FeatureGroup(name='只有 GHS 資料', show=False)
    layer_osm_only = folium.FeatureGroup(name='只有 OSM 資料', show=False)

    # 為每個建築物建立標記
    for idx, row in gdf_sample.iterrows():
        # 決定建築物屬於哪個類別
        has_ghs = False
        has_osm = False

        for col in row.index:
            if col.startswith('ghs_') and pd.notna(row[col]) and row[col] != 'N/A':
                has_ghs = True
            if col.startswith('osm_') and pd.notna(row[col]) and row[col] != 'N/A':
                has_osm = True

        # 建立 GeoJson 物件
        geojson = folium.GeoJson(
            row['geometry'],
            style_function=lambda feature, row=row: determine_building_color(row),
            tooltip=folium.Tooltip(
                folium.Html(
                    create_tooltip_html(row, display_fields),
                    script=True,
                    width=300,
                    height=200
                )
            )
        )

        # 根據資料完整性加入不同圖層
        if has_ghs and has_osm:
            geojson.add_to(layer_both)
        elif has_ghs:
            geojson.add_to(layer_ghs_only)
        else:
            geojson.add_to(layer_osm_only)

    # 將圖層加入地圖
    layer_both.add_to(m)
    layer_ghs_only.add_to(m)
    layer_osm_only.add_to(m)

    # 加入圖層控制器
    folium.LayerControl().add_to(m)

    # 加入全螢幕按鈕
    plugins.Fullscreen().add_to(m)

    # 加入圖例
    legend_html = '''
    <div style="position: fixed;
                bottom: 50px; left: 50px; width: 200px; height: 120px;
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; border-radius:5px; padding: 10px">
        <p style="margin: 0;"><strong>資料完整性圖例</strong></p>
        <p style="margin: 5px 0;"><span style="background-color: lightgreen;
           width: 20px; height: 10px; display: inline-block;
           border: 1px solid darkgreen;"></span> OSM + GHS 資料</p>
        <p style="margin: 5px 0;"><span style="background-color: lightcoral;
           width: 20px; height: 10px; display: inline-block;
           border: 1px solid darkred;"></span> 只有 GHS 資料</p>
        <p style="margin: 5px 0;"><span style="background-color: lightblue;
           width: 20px; height: 10px; display: inline-block;
           border: 1px solid darkblue;"></span> 只有 OSM 資料</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def create_tooltip_html(row, display_fields):
    """
    建立 tooltip 的 HTML 內容

    Args:
        row: DataFrame 的一列
        display_fields: 要顯示的欄位

    Returns:
        HTML 字串
    """
    html = "<div style='font-family: monospace;'>"
    html += "<b>建築物資訊</b><br>"
    html += "-" * 30 + "<br>"

    # 分類顯示欄位
    osm_fields = [f for f in display_fields if f.startswith('osm_')]
    ghs_fields = [f for f in display_fields if f.startswith('ghs_')]

    # 顯示 OSM 資料
    if osm_fields:
        html += "<b>OSM 資料:</b><br>"
        for field in osm_fields[:5]:  # 限制顯示數量
            if field in row.index and row[field] != 'N/A':
                field_name = field.replace('osm_', '')
                html += f"{field_name}: {row[field]}<br>"

    # 顯示 GHS 資料
    if ghs_fields:
        html += "<br><b>GHS 資料:</b><br>"
        for field in ghs_fields[:5]:  # 限制顯示數量
            if field in row.index and row[field] != 'N/A':
                field_name = field.replace('ghs_', '')
                html += f"{field_name}: {row[field]}<br>"

    html += "</div>"
    return html


def main():
    """主程式"""
    # 設定檔案路徑
    merged_geojson_path = 'data/building/merged/merged.geojson'

    # 檢查檔案是否存在
    if not Path(merged_geojson_path).exists():
        print(f"錯誤：找不到合併後的檔案 {merged_geojson_path}")
        print("請先執行 2_merge_geojsons.py 來產生合併檔案")
        return

    # 讀取合併後的 GeoJSON 檔案
    print(f"正在讀取合併後的資料: {merged_geojson_path}")
    merged_gdf = gpd.read_file(merged_geojson_path)
    print(f"總資料筆數: {len(merged_gdf)}")

    # 準備資料
    gdf_sample, display_fields = prepare_merged_geodataframe(merged_gdf, sample_size=500)

    # 建立地圖
    print("\n正在建立視覺化地圖...")
    m = create_merged_map(gdf_sample, display_fields)

    # 儲存地圖
    visualization_folder = Path("data") / "building" / "visualization"
    visualization_folder.mkdir(parents=True, exist_ok=True)
    output_path = visualization_folder / 'merged.html'

    m.save(output_path)

    print(f"\n地圖已成功儲存至 {output_path}")
    print("請用瀏覽器開啟這個檔案查看互動式地圖。")
    print("\n地圖功能說明：")
    print("- 綠色建築物：同時有 OSM 和 GHS 資料")
    print("- 紅色建築物：只有 GHS 資料")
    print("- 藍色建築物：只有 OSM 資料")
    print("- 可使用圖層控制器切換不同資料類型的顯示")
    print("- 滑鼠移到建築物上可查看詳細資訊")


if __name__ == "__main__":
    main()