import geopandas as gpd
import folium
from folium import plugins
from pathlib import Path

# --- 1. 讀取您的 GeoJSON 檔案 ---
building_geojson_path = 'data/building/building_daan_4326.geojson'
ghs_geojson_path = 'data/building/ghs_obat_twn_daan.geojson'
osm_geojson_path = 'data/building/OSM_building.geojson'

# 讀取三個資料集
datasets = {
    'Building (台北市建物)': {
        'gdf': gpd.read_file(building_geojson_path),
        'number_of_sample': 300,
        'color': 'blue',
        'fillColor': 'lightblue',
        'fillOpacity': 0.5
    },
    'GHS (全球人類聚落層)': {
        'gdf': gpd.read_file(ghs_geojson_path),
        'number_of_sample': 50,
        'color': 'red',
        'fillColor': 'lightcoral',
        'fillOpacity': 0.5
    },
    'OSM (開放街圖)': {
        'gdf': gpd.read_file(osm_geojson_path),
        'number_of_sample': 200,
        'color': 'green',
        'fillColor': 'lightgreen',
        'fillOpacity': 0.5
    },
}


# --- 2. 處理資料與建立地圖 ---
def prepare_geodataframe(gdf, name, number_of_sample=100):
    """準備 GeoDataFrame 並處理缺失值"""
    # 取前 1000 筆資料作為示範（如果資料太多可能會讓地圖載入很慢）
    gdf_sample = gdf.head(number_of_sample).copy()  # 使用 copy() 避免 SettingWithCopyWarning

    # 檢查並顯示可用欄位
    print(f"\n{name} 的欄位：")
    print(f"總共 {len(gdf_sample.columns)} 個欄位")

    # 根據不同資料集選擇要顯示的欄位
    if 'OSM' in name:
        # OSM 資料集只選擇特定的建築相關欄位
        osm_important_fields = [
            'name', 'name:zh', 'name:zh-Hant', 'name:en',  # 名稱相關
            'building', 'building:levels', 'building:height',  # 建築基本資訊
            'building:levels:underground', 'building:use', 'building:material',  # 建築詳細資訊
            'height', 'min_height', 'roof:height',  # 高度相關
            'year_of_construction', 'construction_date', 'start_date',  # 年份相關
            'building:start_date', 'opening_date',  # 更多年份相關
            'amenity', 'shop', 'office', 'tourism',  # 用途相關
            'addr:housenumber', 'addr:street', 'addr:city'  # 地址相關
        ]

        # 只選擇存在的欄位
        display_fields = []
        for field in osm_important_fields:
            if field in gdf_sample.columns and field != 'geometry':
                display_fields.append(field)
                # 處理時間戳記
                if gdf_sample[field].dtype == 'datetime64[ns]' or str(gdf_sample[field].dtype).startswith('datetime'):
                    gdf_sample[field] = gdf_sample[field].astype(str)

        print(f"OSM 選擇顯示的欄位: {display_fields}")

    else:
        # Building 和 GHS 資料集顯示所有欄位（最多前15個）
        display_fields = []
        for col in gdf_sample.columns:
            if col != 'geometry':
                # 檢查欄位類型，如果是時間戳記則轉換為字串
                if gdf_sample[col].dtype == 'datetime64[ns]' or str(gdf_sample[col].dtype).startswith('datetime'):
                    gdf_sample[col] = gdf_sample[col].astype(str)
                display_fields.append(col)

    # 填充 null 值並確保所有值都是字串
    for field in display_fields:
        # 先檢查並轉換任何 Timestamp 或 datetime 類型
        if field in gdf_sample.columns:
            # 將 pandas Timestamp 轉換為字串
            try:
                # 如果欄位包含 Timestamp 物件，轉換為字串
                gdf_sample[field] = gdf_sample[field].apply(
                    lambda x: str(x) if hasattr(x, 'timestamp') or pd.api.types.is_datetime64_any_dtype(type(x)) else x
                )
            except:
                pass

            # 填充 null 值並轉換為字串
            gdf_sample[field] = gdf_sample[field].fillna('N/A').astype(str)

    return gdf_sample, display_fields



# 使用第一個資料集的中心點作為地圖中心
first_gdf = list(datasets.values())[0]['gdf']
center_point = first_gdf.head(100).union_all().centroid
map_center = [center_point.y, center_point.x]

# 初始化地圖
m = folium.Map(
    location=map_center,
    zoom_start=16,
    tiles='CartoDB positron',
    control_scale=True
)

# --- 3. 將各個資料集加入地圖 ---
# 建立圖層群組（可以在地圖上開關顯示）
layer_groups = {}

for name, dataset in datasets.items():
    # 準備資料
    gdf_sample, display_fields = prepare_geodataframe(dataset['gdf'], name, dataset['number_of_sample'])

    # 建立圖層群組
    layer_group = folium.FeatureGroup(name=name)

    # 加入 GeoJSON 到圖層
    style_function = lambda feature, color=dataset['color'], fillColor=dataset['fillColor'], fillOpacity=dataset['fillOpacity']: {
        'color': color,
        'weight': 2,
        'fillColor': fillColor,
        'fillOpacity': fillOpacity
    }

    folium.GeoJson(
        gdf_sample,
        name=name,
        style_function=style_function,
        tooltip=folium.features.GeoJsonTooltip(
            fields=display_fields,
            # aliases=[f"{field}:" for field in display_fields],
            localize=True
        )
    ).add_to(layer_group)

    # 將圖層加入地圖
    layer_group.add_to(m)
    layer_groups[name] = layer_group

# 加入圖層控制器（可以開關不同的資料集）
folium.LayerControl().add_to(m)

# 加入全螢幕按鈕
plugins.Fullscreen().add_to(m)

# --- 4. 儲存地圖 ---
visualization_folder = Path("data") / "building" / "visualization"
output_path = visualization_folder / 'visualize_different_geojson.html'
visualization_folder.mkdir(parents=True, exist_ok=True)
m.save(output_path)

print(f"地圖已成功儲存至 {output_path}")
print("請用瀏覽器開啟這個檔案查看互動式地圖。")
