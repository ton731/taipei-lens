#!/usr/bin/env python3
"""
計算 MODIS 數據的年度統計

對每一年的時間序列數據計算：
1. 最大值 (max)
2. 95百分位數 (p95)
3. 平均值 (mean)
4. 標準差 (std)

正確處理 NaN 值：每個網格點只使用該位置的有效值進行統計。
"""

import argparse
import glob
import re
from pathlib import Path
from typing import List, Dict
import numpy as np
import xarray as xr
import warnings

warnings.filterwarnings('ignore')


class AnnualStatisticsCalculator:
    """年度統計計算器"""

    def __init__(self, product: str, input_dir: str, output_dir: str, verbose: bool = True):
        """
        初始化

        Args:
            product: 產品名稱 ('MOD13Q1' 或 'MOD11A2')
            input_dir: 輸入 NetCDF 文件目錄
            output_dir: 輸出統計文件目錄
            verbose: 是否顯示詳細輸出
        """
        self.product = product
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.verbose = verbose

        # 確定變量名稱
        self.var_name = 'NDVI' if product == 'MOD13Q1' else 'LST'

        # 創建輸出目錄
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def log(self, message: str):
        """打印日誌"""
        if self.verbose:
            print(message)

    def find_files_by_year(self) -> Dict[str, List[str]]:
        """
        按年份分組文件

        Returns:
            {year: [file_paths]} 字典
        """
        files = sorted(glob.glob(str(self.input_dir / "*.nc")))

        if not files:
            raise FileNotFoundError(f"在目錄 {self.input_dir} 中未找到 NetCDF 文件")

        self.log(f"找到 {len(files)} 個 NetCDF 文件")

        # 按年份分組
        years = {}
        for f in files:
            # 從文件名提取年份：MOD13Q1_A2020145_WGS84.nc -> 2020
            match = re.search(r'A(\d{4})\d{3}', f)
            if match:
                year = match.group(1)
                if year not in years:
                    years[year] = []
                years[year].append(f)

        self.log(f"\n找到 {len(years)} 年的數據:")
        for year in sorted(years.keys()):
            self.log(f"  {year}: {len(years[year])} 個文件")

        return years

    def compute_statistics(self, files: List[str], year: str) -> xr.Dataset:
        """
        計算一年數據的統計量

        Args:
            files: NetCDF 文件路徑列表
            year: 年份

        Returns:
            包含統計結果的 xarray Dataset
        """
        self.log(f"\n處理 {year} 年 ({len(files)} 個文件)...")

        # 逐行處理以節省記憶體
        self.log(f"  初始化統計數組...")

        # 先讀取第一個文件獲取形狀和座標
        ds_first = xr.open_dataset(sorted(files)[0])
        shape = ds_first[self.var_name].shape
        coords_info = {
            'lon': ds_first['lon'].values,
            'lat': ds_first['lat'].values,
            'spatial_ref': ds_first['spatial_ref'] if 'spatial_ref' in ds_first.coords else None
        }
        ds_first.close()

        # 初始化統計數組
        max_vals = np.full(shape, -np.inf, dtype=np.float32)
        sum_vals = np.zeros(shape, dtype=np.float64)  # 使用 float64 避免精度損失
        sum_sq_vals = np.zeros(shape, dtype=np.float64)
        count_vals = np.zeros(shape, dtype=np.int32)
        all_vals_for_p95 = []  # 儲存所有值用於計算百分位數

        # 逐文件處理
        self.log(f"  處理文件並累積統計...")
        for i, f in enumerate(sorted(files)):
            ds = xr.open_dataset(f)
            data = ds[self.var_name].values
            ds.close()

            # 更新最大值
            max_vals = np.fmax(max_vals, np.nan_to_num(data, nan=-np.inf))

            # 累加求和（用於計算平均值）
            valid_mask = ~np.isnan(data)
            sum_vals = np.where(valid_mask, sum_vals + data, sum_vals)

            # 累加平方和（用於計算標準差）
            sum_sq_vals = np.where(valid_mask, sum_sq_vals + data**2, sum_sq_vals)

            # 累加計數
            count_vals += valid_mask.astype(np.int32)

            # 儲存數據用於計算百分位數（分塊存儲以節省記憶體）
            all_vals_for_p95.append(data)

            self.log(f"    已處理 {i+1}/{len(files)} 個文件")

        # 計算統計量
        self.log(f"  計算最終統計量...")
        stats_data = {}

        # 最大值
        max_vals[np.isinf(max_vals)] = np.nan
        stats_data[f'{self.var_name}_max'] = max_vals

        # 平均值
        mean_vals = np.where(count_vals > 0, sum_vals / count_vals, np.nan)
        stats_data[f'{self.var_name}_mean'] = mean_vals.astype(np.float32)

        # 標準差: std = sqrt(E[X^2] - E[X]^2)
        mean_sq = np.where(count_vals > 0, sum_sq_vals / count_vals, np.nan)
        variance = mean_sq - mean_vals**2
        variance = np.maximum(variance, 0)  # 避免數值誤差導致負值
        stats_data[f'{self.var_name}_std'] = np.sqrt(variance).astype(np.float32)

        # 95百分位數（逐像素計算以節省記憶體）
        self.log(f"    計算 95 百分位數（逐像素處理）...")
        p95_vals = np.full(shape, np.nan, dtype=np.float32)

        # 分塊處理以節省記憶體
        chunk_size = 1000  # 每次處理 1000 行
        for row_start in range(0, shape[0], chunk_size):
            row_end = min(row_start + chunk_size, shape[0])

            # 提取該區塊的所有時間步數據
            chunk_data = []
            for arr in all_vals_for_p95:
                chunk_data.append(arr[row_start:row_end, :])

            chunk_stack = np.stack(chunk_data, axis=0)  # (time, rows, cols)
            p95_vals[row_start:row_end, :] = np.nanpercentile(chunk_stack, 95, axis=0)

            if self.verbose and (row_start // chunk_size) % 2 == 0:
                progress = (row_end / shape[0]) * 100
                self.log(f"      進度: {progress:.1f}%")

        stats_data[f'{self.var_name}_p95'] = p95_vals

        # 有效觀測數
        stats_data['valid_count'] = count_vals

        # 創建 xarray Dataset
        stats = xr.Dataset(
            {key: (['lat', 'lon'], value) for key, value in stats_data.items()},
            coords={
                'lon': coords_info['lon'],
                'lat': coords_info['lat'],
            }
        )

        if coords_info['spatial_ref'] is not None:
            stats = stats.assign_coords({'spatial_ref': coords_info['spatial_ref']})

        # 添加屬性
        stats.attrs.update({
            'title': f'{self.product} Annual Statistics - {year}',
            'product': self.product,
            'year': year,
            'n_files': len(files),
            'source': 'MODIS',
            'Conventions': 'CF-1.8',
            'description': f'Annual statistics (max, 95th percentile, mean, std) for {year}',
            'created_by': 'compute_annual_statistics.py'
        })

        # 添加變量屬性
        var_unit = 'NDVI (dimensionless)' if self.var_name == 'NDVI' else 'Kelvin'

        stats[f'{self.var_name}_max'].attrs.update({
            'long_name': f'Maximum {self.var_name}',
            'units': var_unit,
            'description': f'Maximum {self.var_name} value across all time steps in {year}',
        })

        stats[f'{self.var_name}_p95'].attrs.update({
            'long_name': f'95th Percentile {self.var_name}',
            'units': var_unit,
            'description': f'95th percentile {self.var_name} value across all time steps in {year}',
        })

        stats[f'{self.var_name}_mean'].attrs.update({
            'long_name': f'Mean {self.var_name}',
            'units': var_unit,
            'description': f'Mean {self.var_name} value across all time steps in {year}',
        })

        stats[f'{self.var_name}_std'].attrs.update({
            'long_name': f'Standard Deviation of {self.var_name}',
            'units': var_unit,
            'description': f'Standard deviation of {self.var_name} across all time steps in {year}',
        })

        stats['valid_count'].attrs.update({
            'long_name': 'Number of valid observations',
            'units': 'count',
            'description': 'Number of non-NaN observations used in statistics calculation',
        })

        # 打印統計摘要
        self.log(f"\n  統計摘要 ({year}):")
        for var in [f'{self.var_name}_max', f'{self.var_name}_p95',
                    f'{self.var_name}_mean', f'{self.var_name}_std']:
            values = stats[var].values
            valid = values[~np.isnan(values)]
            if len(valid) > 0:
                self.log(f"    {var}: min={valid.min():.4f}, max={valid.max():.4f}, mean={valid.mean():.4f}")

        return stats

    def save_statistics(self, stats: xr.Dataset, year: str):
        """
        保存統計結果

        Args:
            stats: 統計數據集
            year: 年份
        """
        output_file = self.output_dir / f"{self.product}_{year}_annual_statistics.nc"

        # 編碼設置
        encoding = {}
        for var in stats.data_vars:
            encoding[var] = {'zlib': True, 'complevel': 5, 'dtype': 'float32'}

        encoding['lon'] = {'dtype': 'float64'}
        encoding['lat'] = {'dtype': 'float64'}

        # 保存
        stats.to_netcdf(output_file, encoding=encoding, format='NETCDF4')
        self.log(f"  ✓ 已保存: {output_file}")

    def process_all_years(self):
        """處理所有年份"""
        # 按年份分組文件
        years_files = self.find_files_by_year()

        # 處理每一年
        results = []
        for year in sorted(years_files.keys()):
            try:
                stats = self.compute_statistics(years_files[year], year)
                self.save_statistics(stats, year)
                results.append(year)
            except Exception as e:
                self.log(f"✗ {year} 年處理失敗: {e}")

        self.log(f"\n{'='*60}")
        self.log(f"處理完成！")
        self.log(f"成功處理: {len(results)}/{len(years_files)} 年")
        self.log(f"輸出目錄: {self.output_dir}")
        self.log(f"{'='*60}")

        return results


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='計算 MODIS 年度統計',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 計算 MOD13Q1 年度統計
  python compute_annual_statistics.py --product MOD13Q1 \\
      --input-dir ./output/MOD13Q1 \\
      --output-dir ./output/MOD13Q1_annual_stats

  # 計算 MOD11A2 年度統計
  python compute_annual_statistics.py --product MOD11A2 \\
      --input-dir ./output/MOD11A2 \\
      --output-dir ./output/MOD11A2_annual_stats
        """
    )

    parser.add_argument(
        '--product',
        type=str,
        required=True,
        choices=['MOD13Q1', 'MOD11A2'],
        help='MODIS 產品類型'
    )

    parser.add_argument(
        '--input-dir',
        type=str,
        required=True,
        help='輸入 NetCDF 文件目錄'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        required=True,
        help='輸出統計文件目錄'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='靜默模式（不顯示詳細輸出）'
    )

    args = parser.parse_args()

    # 創建計算器並運行
    calculator = AnnualStatisticsCalculator(
        product=args.product,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        verbose=not args.quiet
    )

    calculator.process_all_years()


if __name__ == '__main__':
    main()
