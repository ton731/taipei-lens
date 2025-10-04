import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import warnings
from typing import List, Tuple, Optional
from pathlib import Path
warnings.filterwarnings('ignore')


def load_geojson_data(ghs_path: str, osm_path: str, building_path: str) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    載入 GHS、OSM 和 Building_4326 的 GeoJSON 資料

    Args:
        ghs_path: GHS GeoJSON 檔案路徑
        osm_path: OSM GeoJSON 檔案路徑
        building_path: Building_4326 GeoJSON 檔案路徑

    Returns:
        (ghs_gdf, osm_gdf, building_gdf): GHS、OSM 和 Building_4326 的 GeoDataFrame
    """
    print("正在讀取資料...")
    ghs_gdf = gpd.read_file(ghs_path)
    osm_gdf = gpd.read_file(osm_path)
    building_gdf = gpd.read_file(building_path)

    print(f"GHS 資料筆數: {len(ghs_gdf)}")
    print(f"OSM 資料筆數: {len(osm_gdf)}")
    print(f"Building_4326 資料筆數: {len(building_gdf)}")

    return ghs_gdf, osm_gdf, building_gdf


def ensure_same_crs(ghs_gdf: gpd.GeoDataFrame, osm_gdf: gpd.GeoDataFrame, building_gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    確保三個資料集使用相同的座標系統

    Args:
        ghs_gdf: GHS GeoDataFrame
        osm_gdf: OSM GeoDataFrame
        building_gdf: Building_4326 GeoDataFrame

    Returns:
        (ghs_gdf, building_gdf): 轉換後的 GHS 和 Building_4326 GeoDataFrame
    """
    # 以 OSM 的座標系統為標準
    target_crs = osm_gdf.crs

    if ghs_gdf.crs != target_crs:
        print(f"座標系統不同，將 GHS 從 {ghs_gdf.crs} 轉換到 {target_crs}")
        ghs_gdf = ghs_gdf.to_crs(target_crs)

    if building_gdf.crs != target_crs:
        print(f"座標系統不同，將 Building_4326 從 {building_gdf.crs} 轉換到 {target_crs}")
        building_gdf = building_gdf.to_crs(target_crs)

    return ghs_gdf, building_gdf


def get_osm_important_fields() -> List[str]:
    """
    取得 OSM 重要欄位列表

    Returns:
        OSM 重要欄位列表
    """
    return [
        'building', 'building:levels', 'building:height',  # 建築基本資訊
        'height', 'min_height', 'roof:height',  # 高度相關
    ]


def get_building4326_important_fields() -> List[str]:
    """
    取得 Building_4326 重要欄位列表

    Returns:
        Building_4326 重要欄位列表
    """
    return [
        '屋頂高',   # 屋頂高度
        '樓層註',   # 樓層註記
        'area'     # 面積
    ]


def filter_osm_fields(osm_gdf: gpd.GeoDataFrame, important_fields: List[str]) -> gpd.GeoDataFrame:
    """
    篩選 OSM 資料集的欄位

    Args:
        osm_gdf: OSM GeoDataFrame
        important_fields: 要保留的重要欄位列表

    Returns:
        篩選後的 OSM GeoDataFrame
    """
    osm_fields_to_keep = ['geometry'] + [field for field in important_fields if field in osm_gdf.columns]
    osm_gdf_filtered = osm_gdf[osm_fields_to_keep].copy()

    print(f"\nOSM 保留的欄位: {[f for f in osm_fields_to_keep if f != 'geometry']}")
    return osm_gdf_filtered


def filter_building4326_fields(building_gdf: gpd.GeoDataFrame, important_fields: List[str]) -> gpd.GeoDataFrame:
    """
    篩選 Building_4326 資料集的欄位

    Args:
        building_gdf: Building_4326 GeoDataFrame
        important_fields: 要保留的重要欄位列表

    Returns:
        篩選後的 Building_4326 GeoDataFrame
    """
    building_fields_to_keep = ['geometry'] + [field for field in important_fields if field in building_gdf.columns]
    building_gdf_filtered = building_gdf[building_fields_to_keep].copy()

    print(f"Building_4326 保留的欄位: {[f for f in building_fields_to_keep if f != 'geometry']}")
    return building_gdf_filtered


def add_prefix_to_columns(gdf: gpd.GeoDataFrame, prefix: str) -> gpd.GeoDataFrame:
    """
    為 GeoDataFrame 的欄位加上前綴（除了 geometry）

    Args:
        gdf: 要處理的 GeoDataFrame
        prefix: 要加上的前綴

    Returns:
        加上前綴後的 GeoDataFrame
    """
    renamed_columns = {}
    for col in gdf.columns:
        if col != 'geometry':
            renamed_columns[col] = f'{prefix}_{col}'

    gdf_renamed = gdf.rename(columns=renamed_columns).copy()

    return gdf_renamed


def perform_spatial_join(osm_gdf: gpd.GeoDataFrame, ghs_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    以 OSM(MultiPolygon) 為主，將 GHS(Point) 屬性合併到 OSM。
    - 關係：covers（含邊界點）
    - 多點命中：取距離「面質心」最近的一點
    """
    print("\n正在執行 OSM-GHS 空間連接...")

    # 0) 幾何有效性（選用，但強烈建議）
    try:
        osm_gdf = osm_gdf.copy()
        osm_gdf["geometry"] = osm_gdf.geometry.map(make_valid)
    except Exception:
        # 若環境非 Shapely 2，可退回 buffer(0) 修補
        osm_gdf["geometry"] = osm_gdf.buffer(0)

    # 1) 保留原始索引，便於回併
    osm_gdf = osm_gdf.copy()
    osm_gdf["__osm_idx__"] = osm_gdf.index

    # 2) 預先算質心（WGS84 下為幾何參考；若要嚴謹距離，建議投影後再算距離）
    osm_gdf["__centroid__"] = osm_gdf.geometry.centroid

    # 3) 空間 join：A covers B（面涵蓋點，含邊界）
    joined = gpd.sjoin(
        osm_gdf,       # 左：面
        ghs_gdf,       # 右：點
        how="left",
        predicate="covers"
    )

    # 4) 多對一處理：同一面命中多點 → 取距離質心最近
    #    注意：sjoin 之後，點的 geometry 可能在 'geometry_right' 或 'geometry'，視 GeoPandas 版本而定
    geom_point_col = "geometry_right" if "geometry_right" in joined.columns else "geometry"
    joined["__dist__"] = joined[geom_point_col].distance(joined["__centroid__"])

    # 按距離排序後，對每個面只保留一筆（最近）
    best = (
        joined.sort_values(["__osm_idx__", "__dist__"])
              .drop_duplicates(subset="__osm_idx__", keep="first")
    )

    # 5) 準備要帶入的 GHS 欄位（白名單/自動偵測皆可）
    # 建議你明確列出要帶進來的欄位，避免把不需要的臨時欄位帶入
    ghs_cols = [c for c in ghs_gdf.columns if c != "geometry"]

    # 6) 將 GHS 欄位合併回 OSM（保留所有面；沒命中者為 NaN/None）
    b_take = best.set_index("__osm_idx__")[ghs_cols]
    out = osm_gdf.drop(columns=["__centroid__"]).set_index("__osm_idx__").join(b_take, how="left")

    # 7) 收尾：恢復原索引名與順序
    out = out.reset_index(drop=True)

    # 8) 清掉 sjoin 衍生欄位（若有殘留）
    for col in ["index_right", "__dist__"]:
        if col in out.columns:
            out = out.drop(columns=[col])

    return out


def combine_all_building_data(osm_ghs_gdf: gpd.GeoDataFrame, building_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    使用空間連接合併 OSM-GHS 資料與 Building_4326 資料

    Args:
        osm_ghs_gdf: 已合併的 OSM-GHS GeoDataFrame
        building_gdf: Building_4326 GeoDataFrame（已加前綴）

    Returns:
        包含所有三個資料源的合併 GeoDataFrame
    """
    print("\n正在執行 OSM-GHS 與 Building_4326 空間連接...")

    # 使用 intersects 來匹配重疊的建築物
    merged_gdf = gpd.sjoin(
        osm_ghs_gdf,
        building_gdf,
        how='left',
        predicate='intersects'
    )

    # 處理重複匹配
    if 'index_right' in merged_gdf.columns:
        merged_gdf = merged_gdf.drop(columns=['index_right'])

    # 統計匹配結果
    building4326_cols = [col for col in merged_gdf.columns if col.startswith('building4326_')]
    if building4326_cols:
        matched_count = merged_gdf[building4326_cols[0]].notna().sum()
        print(f"成功匹配 Building_4326 資料的 OSM 建築物: {matched_count}/{len(osm_ghs_gdf)}")

    return merged_gdf


def print_merge_statistics(merged_gdf: gpd.GeoDataFrame, total_osm: int, total_building4326: int) -> None:
    """
    印出合併統計資訊

    Args:
        merged_gdf: 合併後的 GeoDataFrame
        total_osm: OSM 建築物總數
        total_building4326: Building_4326 建築物總數
    """
    print(f"\n合併結果統計:")
    print(f"OSM 建築物總數: {len(merged_gdf)}")

    # GHS 匹配統計
    ghs_columns = [col for col in merged_gdf.columns if col.startswith('ghs_')]
    if ghs_columns:
        matched_ghs = merged_gdf[ghs_columns[0]].notna().sum()
        print(f"OSM-GHS 匹配統計:")
        print(f"  成功匹配 GHS 資料的建築物: {matched_ghs}")
        print(f"  GHS 匹配率: {matched_ghs/len(merged_gdf)*100:.2f}%")

    # Building_4326 匹配統計
    building4326_columns = [col for col in merged_gdf.columns if col.startswith('building4326_')]
    if building4326_columns:
        matched_building4326 = merged_gdf[building4326_columns[0]].notna().sum()
        print(f"OSM-Building_4326 匹配統計:")
        print(f"  成功匹配 Building_4326 資料的建築物: {matched_building4326}")
        print(f"  Building_4326 匹配率: {matched_building4326/len(merged_gdf)*100:.2f}%")


def save_merged_data(merged_gdf: gpd.GeoDataFrame, output_path: str) -> None:
    """
    儲存合併後的資料

    Args:
        merged_gdf: 合併後的 GeoDataFrame
        output_path: 輸出檔案路徑
    """
    print(f"\n正在儲存合併後的資料到 {output_path}...")
    merged_gdf.to_file(output_path, driver='GeoJSON')

    print(f"\n合併完成！")
    print(f"輸出檔案: {output_path}")
    print(f"總欄位數: {len(merged_gdf.columns) - 1} (不含 geometry)")
    print(f"總資料筆數: {len(merged_gdf)}")


def print_sample_data(merged_gdf: gpd.GeoDataFrame, sample_size: int = 3) -> None:
    """
    顯示範例資料

    Args:
        merged_gdf: 合併後的 GeoDataFrame
        sample_size: 要顯示的範例數量
    """
    print(f"\n範例資料（前{sample_size}筆建築物）:")

    sample_data = merged_gdf.head(sample_size)

    for idx, (_, row) in enumerate(sample_data.iterrows()):
        print(f"\n建築物 {idx + 1}:")

        # 顯示 OSM 資料
        osm_cols = [col for col in row.index if col.startswith('osm_') and pd.notna(row[col]) and row[col] != 'N/A']
        if osm_cols:
            print("  OSM 資料:")
            for col in osm_cols[:3]:
                print(f"    {col}: {row[col]}")

        # 顯示 GHS 資料
        ghs_cols = [col for col in row.index if col.startswith('ghs_') and pd.notna(row[col])]
        if ghs_cols:
            print("  GHS 資料:")
            for col in ghs_cols[:3]:
                print(f"    {col}: {row[col]}")
        else:
            print("  GHS 資料: 無匹配")

        # 顯示 Building_4326 資料
        building_cols = [col for col in row.index if col.startswith('building4326_') and pd.notna(row[col])]
        if building_cols:
            print("  Building_4326 資料:")
            for col in building_cols[:3]:
                print(f"    {col}: {row[col]}")
        else:
            print("  Building_4326 資料: 無匹配")


def merge_all_building_data(ghs_path: str, osm_path: str, building_path: str, output_path: str) -> gpd.GeoDataFrame:
    """
    主要合併函數，整合 OSM、GHS 和 Building_4326 資料

    Args:
        ghs_path: GHS GeoJSON 檔案路徑
        osm_path: OSM GeoJSON 檔案路徑
        building_path: Building_4326 GeoJSON 檔案路徑
        output_path: 輸出檔案路徑

    Returns:
        合併後的 GeoDataFrame
    """
    # 載入資料
    ghs_gdf, osm_gdf, building_gdf = load_geojson_data(ghs_path, osm_path, building_path)

    # 確保座標系統一致
    ghs_gdf, building_gdf = ensure_same_crs(ghs_gdf, osm_gdf, building_gdf)

    # 篩選欄位
    osm_important_fields = get_osm_important_fields()
    osm_gdf_filtered = filter_osm_fields(osm_gdf, osm_important_fields)

    building_important_fields = get_building4326_important_fields()
    building_gdf_filtered = filter_building4326_fields(building_gdf, building_important_fields)

    # 加上欄位前綴
    osm_gdf_prefixed = add_prefix_to_columns(osm_gdf_filtered, 'osm')
    ghs_gdf_prefixed = add_prefix_to_columns(ghs_gdf, 'ghs')
    building_gdf_prefixed = add_prefix_to_columns(building_gdf_filtered, 'building4326')

    # 執行空間連接（OSM + GHS）
    osm_ghs_merged = perform_spatial_join(osm_gdf_prefixed, ghs_gdf_prefixed)

    # 合併所有建築資料
    # all_merged_gdf = combine_all_building_data(osm_ghs_merged, building_gdf_prefixed)
    final_gdf = osm_ghs_merged

    # 印出統計資訊
    print_merge_statistics(final_gdf, len(osm_gdf_filtered), len(building_gdf_filtered))

    # 儲存資料
    save_merged_data(final_gdf, output_path)

    # 顯示範例資料
    print_sample_data(final_gdf)

    return final_gdf


def main():
    """主程式"""
    # 設定檔案路徑
    ghs_geojson_path = 'data/building/ghs_obat_twn_ALL.geojson'
    osm_geojson_path = 'data/building/OSM_building.geojson'
    building_geojson_path = 'data/building/building_4326.geojson'
    merged_folder = Path("data") / "building" / "merged"
    output_path = merged_folder / 'merged_all_buildings.geojson'
    merged_folder.mkdir(parents=True, exist_ok=True)

    print("=== 整合 OSM、GHS 和 Building_4326 建築資料 ===")

    # 執行三重合併
    merged_gdf = merge_all_building_data(
        ghs_geojson_path,
        osm_geojson_path,
        building_geojson_path,
        output_path
    )

    return merged_gdf


if __name__ == "__main__":
    main()