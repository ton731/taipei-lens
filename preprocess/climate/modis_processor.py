#!/usr/bin/env python3
"""
MODIS数据处理脚本 - 拼接与重投影
支持 MOD11A2 (地表温度) 和 MOD13Q1 (植被指数) 数据

功能：
1. 读取多个时间段的h28v06和h29v06瓦片HDF文件
2. 水平拼接瓦片
3. 重投影到WGS84坐标系统
4. 输出为NetCDF格式

用法:
    python modis_processor.py --product MOD13Q1 --input-dir /path/to/MOD13Q1_data --output-dir /path/to/output
    python modis_processor.py --product MOD11A2 --input-dir /path/to/MOD11A2_data --output-dir /path/to/output
"""

import os
import glob
import argparse
from pathlib import Path
import numpy as np
import warnings
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from pyhdf.SD import SD, SDC
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS
from rasterio.warp import calculate_default_transform, reproject, Resampling
import xarray as xr

warnings.filterwarnings('ignore')


@dataclass
class MODISProduct:
    """MODIS产品配置"""
    name: str
    dataset_name: str
    scale_factor_attr: str
    fill_value_attr: str
    description: str
    units: str


# 产品配置
PRODUCTS = {
    'MOD13Q1': MODISProduct(
        name='MOD13Q1',
        dataset_name='250m 16 days NDVI',
        scale_factor_attr='scale_factor',
        fill_value_attr='_FillValue',
        description='MODIS 16-day NDVI (Normalized Difference Vegetation Index)',
        units='NDVI (dimensionless)'
    ),
    'MOD11A2': MODISProduct(
        name='MOD11A2',
        dataset_name='LST_Day_1km',
        scale_factor_attr='scale_factor',
        fill_value_attr='_FillValue',
        description='MODIS 8-day Land Surface Temperature (Day)',
        units='Kelvin'
    )
}


class MODISProcessor:
    """MODIS数据处理器"""

    # MODIS正弦投影参数
    MODIS_CRS = CRS.from_proj4(
        '+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +a=6371007.181 +b=6371007.181 +units=m +no_defs'
    )
    PIXEL_SIZE = 231.65635826395834  # MOD13Q1的像素大小（米）
    PIXEL_SIZE_1KM = 926.6254331  # MOD11A2的像素大小（米）
    TILE_WIDTH = 1111950.5197665554  # 瓦片宽度（米）
    X_MIN_ORIGIN = -20015109.354
    Y_MAX_ORIGIN = 10007554.677

    def __init__(self, product: str, input_dir: str, output_dir: str, verbose: bool = True):
        """
        初始化处理器

        Args:
            product: 产品名称 ('MOD13Q1' 或 'MOD11A2')
            input_dir: 输入HDF文件目录
            output_dir: 输出NetCDF文件目录
            verbose: 是否显示详细输出
        """
        if product not in PRODUCTS:
            raise ValueError(f"不支持的产品: {product}. 支持的产品: {list(PRODUCTS.keys())}")

        self.product_config = PRODUCTS[product]
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.verbose = verbose

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 根据产品选择像素大小
        if product == 'MOD11A2':
            self.pixel_size = self.PIXEL_SIZE_1KM
        else:
            self.pixel_size = self.PIXEL_SIZE

    def log(self, message: str):
        """打印日志"""
        if self.verbose:
            print(message)

    def find_hdf_files(self) -> Dict[str, Dict[str, str]]:
        """
        查找并分组HDF文件

        Returns:
            按日期和瓦片分组的文件字典: {date: {tile: filepath}}
        """
        hdf_files = sorted(glob.glob(str(self.input_dir / "*.hdf")))

        if not hdf_files:
            raise FileNotFoundError(f"在目录 {self.input_dir} 中未找到HDF文件")

        self.log(f"找到 {len(hdf_files)} 个HDF文件")

        # 按照日期和瓦片分组
        dates = {}
        for f in hdf_files:
            filename = os.path.basename(f)
            parts = filename.split('.')

            if len(parts) < 4:
                continue

            product = parts[0]  # MOD13Q1 或 MOD11A2
            date = parts[1]     # A2020145
            tile = parts[2]     # h28v06 or h29v06

            if date not in dates:
                dates[date] = {}
            dates[date][tile] = f

        # 显示可用的日期
        self.log("\n可用的日期及瓦片：")
        for date in sorted(dates.keys()):
            tiles = list(dates[date].keys())
            self.log(f"  {date}: {tiles}")

        return dates

    def read_modis_data(self, hdf_file: str) -> Tuple[np.ndarray, float, float]:
        """
        读取MODIS HDF文件中的数据

        Args:
            hdf_file: HDF文件路径

        Returns:
            (data, fill_value, scale_factor) 元组
        """
        hdf = SD(hdf_file, SDC.READ)

        # 选择数据集
        dataset_name = self.product_config.dataset_name

        try:
            sds = hdf.select(dataset_name)
            data = sds.get()

            # 获取属性
            attrs = sds.attributes()
            fill_value = attrs.get(self.product_config.fill_value_attr, -3000)

            # 獲取縮放因子（MOD11A2用乘法，MOD13Q1用除法）
            scale_factor = attrs.get(self.product_config.scale_factor_attr, 1.0)

            # 如果scale_factor小於1，表示是乘法因子（如MOD11A2的0.02）
            # 如果大於1，表示是除法因子（如MOD13Q1的10000）
            if scale_factor < 1:
                # MOD11A2: multiply by scale_factor
                scale_factor = scale_factor
            else:
                # MOD13Q1: divide by scale_factor
                scale_factor = scale_factor

            sds.endaccess()
        except Exception as e:
            hdf.end()
            raise ValueError(f"读取数据集 '{dataset_name}' 失败: {e}")

        hdf.end()

        return data, fill_value, scale_factor

    def process_data(self, data: np.ndarray, fill_value: float, scale_factor: float) -> np.ndarray:
        """
        处理数据：应用缩放因子并处理无效值

        Args:
            data: 原始数据
            fill_value: 填充值
            scale_factor: 缩放因子

        Returns:
            处理后的数据（无效值为NaN）
        """
        # 创建掩码
        if self.product_config.name == 'MOD11A2':
            # 对于LST，有效范围通常是7500-65535（对应150K-400K）
            mask = (data == fill_value) | (data < 7500) | (data > 65535)
        else:
            # 对于NDVI，有效范围是-2000到10000
            mask = (data == fill_value) | (data < -2000) | (data > 10000)

        # 应用缩放因子
        # MOD11A2: multiply (scale_factor < 1)
        # MOD13Q1: divide (scale_factor > 1)
        if scale_factor < 1:
            processed = data.astype(float) * scale_factor
        else:
            processed = data.astype(float) / scale_factor

        # 将无效值设为NaN
        processed[mask] = np.nan

        return processed

    def mosaic_tiles(self, tile_h28: np.ndarray, tile_h29: np.ndarray) -> np.ndarray:
        """
        水平拼接两个瓦片（h28在左，h29在右）

        Args:
            tile_h28: h28v06瓦片数据
            tile_h29: h29v06瓦片数据

        Returns:
            拼接后的数据
        """
        return np.hstack([tile_h28, tile_h29])

    def save_geotiff(self, data: np.ndarray, output_file: str, tile_h: int = 28, tile_v: int = 6):
        """
        保存数据为GeoTIFF格式（MODIS正弦投影）

        Args:
            data: 数据数组
            output_file: 输出文件路径
            tile_h: 水平瓦片编号
            tile_v: 垂直瓦片编号
        """
        # 替换NaN为NoData值
        data_to_write = data.copy()
        data_to_write[np.isnan(data_to_write)] = -9999

        rows, cols = data.shape

        # 计算地理变换
        x_min = self.X_MIN_ORIGIN + tile_h * self.TILE_WIDTH
        y_max = self.Y_MAX_ORIGIN - tile_v * self.TILE_WIDTH

        # 创建仿射变换矩阵
        transform = Affine(self.pixel_size, 0.0, x_min,
                          0.0, -self.pixel_size, y_max)

        # 写入GeoTIFF
        with rasterio.open(
            output_file,
            'w',
            driver='GTiff',
            height=rows,
            width=cols,
            count=1,
            dtype=rasterio.float32,
            crs=self.MODIS_CRS,
            transform=transform,
            nodata=-9999,
            compress='lzw'
        ) as dst:
            dst.write(data_to_write.astype(rasterio.float32), 1)

            # 添加元数据
            dst.update_tags(
                DESCRIPTION=self.product_config.description,
                UNITS=self.product_config.units,
                PRODUCT=self.product_config.name
            )

    def reproject_to_wgs84(self, input_file: str, output_file: str):
        """
        将MODIS正弦投影重投影到WGS84

        Args:
            input_file: 输入GeoTIFF文件（MODIS正弦投影）
            output_file: 输出GeoTIFF文件（WGS84）
        """
        with rasterio.open(input_file) as src:
            # 计算目标变换和尺寸
            transform, width, height = calculate_default_transform(
                src.crs,
                'EPSG:4326',
                src.width,
                src.height,
                *src.bounds
            )

            # 设置输出参数
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': 'EPSG:4326',
                'transform': transform,
                'width': width,
                'height': height
            })

            # 执行重投影
            with rasterio.open(output_file, 'w', **kwargs) as dst:
                reproject(
                    source=rasterio.band(src, 1),
                    destination=rasterio.band(dst, 1),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs='EPSG:4326',
                    resampling=Resampling.bilinear
                )

    def geotiff_to_netcdf(self, geotiff_file: str, netcdf_file: str, date: str):
        """
        将GeoTIFF转换为NetCDF格式

        Args:
            geotiff_file: 输入GeoTIFF文件
            netcdf_file: 输出NetCDF文件
            date: 日期字符串（如'A2020145'）
        """
        # 读取GeoTIFF
        with rasterio.open(geotiff_file) as src:
            data = src.read(1)
            transform = src.transform
            crs = src.crs
            nodata = src.nodata
            bounds = src.bounds

            # 将nodata替换为NaN
            if nodata is not None:
                data = np.where(data == nodata, np.nan, data)

            # 计算经纬度坐标
            height, width = data.shape

            # 创建1D坐标数组（像素中心）
            lon_1d = np.linspace(bounds.left + transform.a/2,
                                bounds.right - transform.a/2,
                                width)
            lat_1d = np.linspace(bounds.top + transform.e/2,
                                bounds.bottom - transform.e/2,
                                height)

        # 解析日期
        year = int(date[1:5])
        doy = int(date[5:8])

        # 创建xarray数据集
        variable_name = 'NDVI' if self.product_config.name == 'MOD13Q1' else 'LST'

        ds = xr.Dataset(
            {
                variable_name: (['lat', 'lon'], data),
            },
            coords={
                'lon': lon_1d,
                'lat': lat_1d,
            },
            attrs={
                'title': f'{self.product_config.description}',
                'product': self.product_config.name,
                'date': date,
                'year': year,
                'day_of_year': doy,
                'crs': str(crs),
                'source': 'MODIS',
                'processed_by': 'modis_processor.py'
            }
        )

        # 添加变量属性
        ds[variable_name].attrs.update({
            'long_name': self.product_config.description,
            'units': self.product_config.units,
            'grid_mapping': 'crs',
        })

        ds['lon'].attrs.update({
            'long_name': 'Longitude',
            'units': 'degrees_east',
            'standard_name': 'longitude',
            'axis': 'X',
        })

        ds['lat'].attrs.update({
            'long_name': 'Latitude',
            'units': 'degrees_north',
            'standard_name': 'latitude',
            'axis': 'Y',
        })

        # 添加 spatial_ref 變量以確保 GDAL/QGIS 正確識別 CRS
        ds = ds.assign_coords(spatial_ref=0)
        ds['spatial_ref'].attrs.update({
            'spatial_ref': 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]',
            'crs_wkt': 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]',
            'GeoTransform': f'{lon_1d[0]} {(lon_1d[-1]-lon_1d[0])/len(lon_1d)} 0 {lat_1d[-1]} 0 {(lat_1d[0]-lat_1d[-1])/len(lat_1d)}',
        })

        # 更新數據變量的 grid_mapping
        ds[variable_name].attrs['grid_mapping'] = 'spatial_ref'
        ds[variable_name].attrs['coordinates'] = 'lon lat'

        # 更新全局屬性
        ds.attrs['Conventions'] = 'CF-1.8'

        # 保存为NetCDF
        encoding = {
            variable_name: {'zlib': True, 'complevel': 5},
            'lon': {'dtype': 'float64'},
            'lat': {'dtype': 'float64'},
        }

        ds.to_netcdf(netcdf_file, encoding=encoding, format='NETCDF4')
        self.log(f"✓ NetCDF已保存: {netcdf_file}")

    def process_single_date(self, date: str, tiles: Dict[str, str]) -> Optional[str]:
        """
        处理单个日期的数据

        Args:
            date: 日期字符串（如'A2020145'）
            tiles: 瓦片文件字典 {tile: filepath}

        Returns:
            输出的NetCDF文件路径，如果处理失败则返回None
        """
        self.log(f"\n处理日期: {date}")

        # 检查可用的瓦片
        has_h28 = 'h28v06' in tiles
        has_h29 = 'h29v06' in tiles

        if not has_h28 and not has_h29:
            self.log(f"  跳过（没有可用的瓦片）")
            return None

        try:
            # 读取数据
            if has_h28 and has_h29:
                # 两个瓦片都有，进行拼接
                self.log(f"  读取 h28v06...")
                data_h28, fill_h28, scale_h28 = self.read_modis_data(tiles['h28v06'])

                self.log(f"  读取 h29v06...")
                data_h29, fill_h29, scale_h29 = self.read_modis_data(tiles['h29v06'])

                # 处理数据
                self.log(f"  处理数据...")
                processed_h28 = self.process_data(data_h28, fill_h28, scale_h28)
                processed_h29 = self.process_data(data_h29, fill_h29, scale_h29)

                # 拼接
                self.log(f"  拼接瓦片...")
                mosaic = self.mosaic_tiles(processed_h28, processed_h29)
                tile_h = 28

            elif has_h28:
                # 只有h28v06
                self.log(f"  读取 h28v06（单瓦片）...")
                data_h28, fill_h28, scale_h28 = self.read_modis_data(tiles['h28v06'])

                self.log(f"  处理数据...")
                mosaic = self.process_data(data_h28, fill_h28, scale_h28)
                tile_h = 28

            else:
                # 只有h29v06
                self.log(f"  读取 h29v06（单瓦片）...")
                data_h29, fill_h29, scale_h29 = self.read_modis_data(tiles['h29v06'])

                self.log(f"  处理数据...")
                mosaic = self.process_data(data_h29, fill_h29, scale_h29)
                tile_h = 29

            self.log(f"  数据shape: {mosaic.shape}")
            self.log(f"  数据范围: {np.nanmin(mosaic):.4f} 到 {np.nanmax(mosaic):.4f}")

            # 保存为临时GeoTIFF（MODIS投影）
            temp_sinusoidal = self.output_dir / f"temp_{self.product_config.name}_{date}_sinusoidal.tif"
            self.log(f"  保存为MODIS投影GeoTIFF...")
            self.save_geotiff(mosaic, str(temp_sinusoidal), tile_h=tile_h)

            # 重投影到WGS84
            temp_wgs84 = self.output_dir / f"temp_{self.product_config.name}_{date}_WGS84.tif"
            self.log(f"  重投影到WGS84...")
            self.reproject_to_wgs84(str(temp_sinusoidal), str(temp_wgs84))

            # 转换为NetCDF
            output_nc = self.output_dir / f"{self.product_config.name}_{date}_WGS84.nc"
            self.log(f"  转换为NetCDF...")
            self.geotiff_to_netcdf(str(temp_wgs84), str(output_nc), date)

            # 删除临时文件
            temp_sinusoidal.unlink()
            temp_wgs84.unlink()

            self.log(f"✓ 完成: {output_nc}")

            return str(output_nc)

        except Exception as e:
            self.log(f"✗ 处理失败: {e}")
            return None

    def process_all(self) -> List[str]:
        """
        处理所有日期的数据

        Returns:
            成功处理的NetCDF文件路径列表
        """
        # 查找HDF文件
        dates = self.find_hdf_files()

        # 处理每个日期
        output_files = []
        for date in sorted(dates.keys()):
            result = self.process_single_date(date, dates[date])
            if result:
                output_files.append(result)

        self.log(f"\n{'='*60}")
        self.log(f"处理完成！")
        self.log(f"成功处理: {len(output_files)}/{len(dates)} 个日期")
        self.log(f"输出目录: {self.output_dir}")
        self.log(f"{'='*60}")

        return output_files


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='MODIS数据处理 - 拼接与重投影',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理MOD13Q1数据
  python modis_processor.py --product MOD13Q1 \\
      --input-dir ./MOD13Q1_061-20250930_094144 \\
      --output-dir ./output/MOD13Q1

  # 处理MOD11A2数据
  python modis_processor.py --product MOD11A2 \\
      --input-dir ./MOD11A2_061-20250930_091742 \\
      --output-dir ./output/MOD11A2
        """
    )

    parser.add_argument(
        '--product',
        type=str,
        required=True,
        choices=['MOD13Q1', 'MOD11A2'],
        help='MODIS产品类型'
    )

    parser.add_argument(
        '--input-dir',
        type=str,
        required=True,
        help='输入HDF文件目录'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        required=True,
        help='输出NetCDF文件目录'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='静默模式（不显示详细输出）'
    )

    args = parser.parse_args()

    # 创建处理器并运行
    processor = MODISProcessor(
        product=args.product,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        verbose=not args.quiet
    )

    processor.process_all()


if __name__ == '__main__':
    main()