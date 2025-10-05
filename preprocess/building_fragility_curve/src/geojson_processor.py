#!/usr/bin/env python3
"""
GeoJSON Processing Module

此模組負責處理大型GeoJSON檔案，支援建築資料的讀取、分類、
易損性曲線結果寫入，以及檔案完整性驗證。

主要功能：
1. 大型GeoJSON檔案的分段處理
2. 建築屬性提取和分類
3. 易損性曲線結果寫入
4. 檔案備份和完整性檢查
5. 進度追蹤和錯誤處理
"""

import json
import os
import sys
import time
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Iterator, Tuple, Any
from datetime import datetime
import tempfile

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from building_classifier import BuildingClassifier, BuildingProperties
from fragility_cache import FragilityCurveResult

logger = logging.getLogger(__name__)


class GeoJSONProcessor:
    """
    GeoJSON處理器

    專為大型建築資料檔案設計，支援分段讀取和寫入
    """

    def __init__(self,
                 geojson_file: str,
                 chunk_size: int = 1000,
                 backup_original: bool = True):
        """
        初始化GeoJSON處理器

        Args:
            geojson_file: GeoJSON檔案路徑
            chunk_size: 分段處理大小
            backup_original: 是否備份原始檔案
        """
        self.geojson_file = Path(geojson_file)
        self.chunk_size = chunk_size
        self.backup_original = backup_original

        # 初始化建築分類器
        self.building_classifier = BuildingClassifier()

        # 統計資訊
        self.stats = {
            'total_buildings': 0,
            'classified_buildings': 0,
            'classification_errors': 0,
            'fragility_results_added': 0,
            'processing_time': 0.0
        }

        # 驗證檔案存在
        if not self.geojson_file.exists():
            raise FileNotFoundError(f"GeoJSON file not found: {self.geojson_file}")

        logger.info(f"GeoJSON processor initialized for file: {self.geojson_file}")
        logger.info(f"File size: {self.geojson_file.stat().st_size / (1024*1024):.1f} MB")

    def create_backup(self) -> Optional[Path]:
        """
        建立原始檔案備份

        Returns:
            Path: 備份檔案路徑，失敗時返回None
        """
        if not self.backup_original:
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.geojson_file.with_suffix(f".backup_{timestamp}{self.geojson_file.suffix}")

            logger.info(f"Creating backup: {backup_file}")
            shutil.copy2(self.geojson_file, backup_file)

            logger.info(f"Backup created successfully: {backup_file}")
            return backup_file

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def load_geojson_metadata(self) -> Dict[str, Any]:
        """
        載入GeoJSON元數據

        Returns:
            Dict: GeoJSON元數據
        """
        try:
            with open(self.geojson_file, 'r', encoding='utf-8') as f:
                # 讀取檔案開頭來獲取結構資訊
                first_chunk = f.read(10000)  # 讀取前10KB

            # 解析部分JSON以獲取基本結構
            if first_chunk.strip().startswith('{"type"'):
                # 嘗試解析元數據
                start_brace = first_chunk.find('{')
                if start_brace != -1:
                    # 尋找metadata部分
                    if '"metadata"' in first_chunk:
                        metadata_start = first_chunk.find('"metadata"')
                        metadata_part = first_chunk[metadata_start:metadata_start + 1000]

                        # 簡單解析（這裡可能需要更強健的解析）
                        logger.debug("Found metadata section in GeoJSON")

            # 獲取檔案統計
            file_size = self.geojson_file.stat().st_size
            modification_time = datetime.fromtimestamp(self.geojson_file.stat().st_mtime)

            metadata = {
                'file_path': str(self.geojson_file),
                'file_size_mb': file_size / (1024 * 1024),
                'last_modified': modification_time.isoformat(),
                'encoding': 'utf-8'
            }

            logger.info(f"GeoJSON metadata loaded: {file_size / (1024*1024):.1f} MB")
            return metadata

        except Exception as e:
            logger.error(f"Failed to load GeoJSON metadata: {e}")
            return {}

    def extract_buildings_generator(self) -> Iterator[Tuple[int, Dict]]:
        """
        生成器：逐一提取建築資料

        Yields:
            Tuple[int, Dict]: (建築索引, 建築特徵資料)
        """
        try:
            with open(self.geojson_file, 'r', encoding='utf-8') as f:
                # 讀取整個檔案（對於大檔案，這可能需要優化）
                logger.info("Loading GeoJSON file...")
                data = json.load(f)

                if 'features' not in data:
                    logger.error("Invalid GeoJSON format: no 'features' found")
                    return

                features = data['features']
                self.stats['total_buildings'] = len(features)

                logger.info(f"Found {len(features)} building features")

                # 逐一產生建築資料
                for i, feature in enumerate(features):
                    yield i, feature

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Error reading GeoJSON file: {e}")

    def classify_buildings_batch(self,
                               max_buildings: Optional[int] = None) -> List[Tuple[BuildingProperties, str]]:
        """
        批量分類建築

        Args:
            max_buildings: 最大處理建築數量，None表示處理所有

        Returns:
            List[Tuple[BuildingProperties, str]]: (建築屬性, 建築ID)列表
        """
        classified_buildings = []
        processed_count = 0

        logger.info(f"Starting building classification (max: {max_buildings or 'all'})")
        start_time = time.time()

        try:
            for building_idx, feature in self.extract_buildings_generator():
                if max_buildings and processed_count >= max_buildings:
                    break

                try:
                    # 生成建築ID
                    building_id = f"building_{building_idx:06d}"

                    # 分類建築
                    building_props = self.building_classifier.classify_building(feature)

                    if building_props is not None:
                        # 額外驗證：確保建築屬性物件的有效性
                        if hasattr(building_props, 'validate') and callable(building_props.validate):
                            if building_props.validate():
                                classified_buildings.append((building_props, building_id))
                                self.stats['classified_buildings'] += 1
                                logger.debug(f"Successfully classified building {building_id}: {building_props.get_archetype_code()}")
                            else:
                                self.stats['classification_errors'] += 1
                                logger.warning(f"Building {building_id} failed validation: {building_props}")
                        else:
                            # 基本型別檢查
                            from building_classifier import BuildingProperties
                            if isinstance(building_props, BuildingProperties):
                                classified_buildings.append((building_props, building_id))
                                self.stats['classified_buildings'] += 1
                                logger.debug(f"Successfully classified building {building_id}: {building_props.get_archetype_code()}")
                            else:
                                self.stats['classification_errors'] += 1
                                logger.error(f"Building {building_id} returned invalid type: {type(building_props)}")
                    else:
                        self.stats['classification_errors'] += 1
                        logger.debug(f"Failed to classify building {building_id}")

                    processed_count += 1

                    # 進度報告
                    if processed_count % self.chunk_size == 0:
                        logger.info(f"Classified {processed_count} buildings "
                                   f"({self.stats['classified_buildings']} successful)")

                except Exception as e:
                    self.stats['classification_errors'] += 1
                    logger.error(f"Error classifying building {building_idx}: {e}")

            # 最終統計
            processing_time = time.time() - start_time
            self.stats['processing_time'] = processing_time

            success_rate = (self.stats['classified_buildings'] / processed_count * 100) if processed_count > 0 else 0

            logger.info(f"Building classification complete:")
            logger.info(f"  Processed: {processed_count} buildings")
            logger.info(f"  Successful: {self.stats['classified_buildings']} ({success_rate:.1f}%)")
            logger.info(f"  Errors: {self.stats['classification_errors']}")
            logger.info(f"  Processing time: {processing_time:.1f}s")

            # 記錄年齡填補統計
            self.building_classifier.log_age_statistics()

            return classified_buildings

        except Exception as e:
            logger.error(f"Batch classification failed: {e}")
            return classified_buildings

    def get_archetype_statistics(self,
                               classified_buildings: List[Tuple[str, BuildingProperties]]) -> Dict[str, Any]:
        """
        獲取建築原型統計

        Args:
            classified_buildings: 已分類建築列表

        Returns:
            Dict: 統計資訊
        """
        if not classified_buildings:
            return {}

        # 提取建築屬性列表
        building_props_list = [props for props, _ in classified_buildings]

        # 使用建築分類器的統計功能
        stats = self.building_classifier.get_building_statistics(building_props_list)

        # 添加原型編碼統計
        archetype_counts = {}
        for building_props, _ in classified_buildings:
            code = building_props.get_archetype_code()
            archetype_counts[code] = archetype_counts.get(code, 0) + 1

        stats['archetype_distribution'] = archetype_counts
        stats['unique_archetypes'] = len(archetype_counts)

        logger.info(f"Archetype statistics: {len(archetype_counts)} unique types")

        return stats

    def write_fragility_results_to_geojson(self,
                                         fragility_results: Dict[str, Optional[FragilityCurveResult]],
                                         output_file: Optional[str] = None) -> bool:
        """
        將易損性曲線結果寫入GeoJSON檔案

        Args:
            fragility_results: 易損性結果字典 {building_id: result}
            output_file: 輸出檔案路徑，None表示覆蓋原檔案

        Returns:
            bool: 是否成功
        """
        if output_file is None:
            output_file = self.geojson_file

        output_path = Path(output_file)
        temp_file = None

        try:
            # 建立備份
            if self.backup_original and output_path == self.geojson_file:
                self.create_backup()

            logger.info(f"Writing fragility results to: {output_path}")
            logger.info(f"Total results to write: {len(fragility_results)}")

            start_time = time.time()

            # 建立臨時檔案
            with tempfile.NamedTemporaryFile(mode='w', delete=False,
                                           suffix='.json', encoding='utf-8') as temp:
                temp_file = temp.name

                # 讀取原始資料
                with open(self.geojson_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'features' not in data:
                    logger.error("Invalid GeoJSON format")
                    return False

                # 更新建築特徵
                updated_count = 0
                for i, feature in enumerate(data['features']):
                    building_id = f"building_{i:06d}"

                    if building_id in fragility_results:
                        result = fragility_results[building_id]

                        if result is not None:
                            # 添加易損性曲線到特徵屬性
                            if 'properties' not in feature:
                                feature['properties'] = {}

                            feature['properties']['fragility_curve'] = result.collapse_probabilities

                            # 可選：添加分析元數據
                            feature['properties']['fragility_metadata'] = {
                                'archetype_code': result.archetype_code,
                                'computed_timestamp': result.computed_timestamp,
                                'computation_time': result.computation_time
                            }

                            updated_count += 1
                        else:
                            # 標記分析失敗
                            if 'properties' not in feature:
                                feature['properties'] = {}
                            feature['properties']['fragility_analysis_failed'] = True

                    # 進度報告
                    if (i + 1) % self.chunk_size == 0:
                        logger.info(f"Updated {i + 1} features ({updated_count} with results)")

                # 更新元數據
                if 'metadata' not in data:
                    data['metadata'] = {}

                data['metadata']['fragility_analysis'] = {
                    'analysis_timestamp': datetime.now().isoformat(),
                    'buildings_analyzed': len(fragility_results),
                    'successful_results': sum(1 for r in fragility_results.values() if r is not None),
                    'failed_analyses': sum(1 for r in fragility_results.values() if r is None)
                }

                # 寫入臨時檔案
                json.dump(data, temp, indent=None, separators=(',', ':'), ensure_ascii=False)

            # 移動臨時檔案到最終位置
            shutil.move(temp_file, output_path)
            temp_file = None

            # 統計
            processing_time = time.time() - start_time
            self.stats['fragility_results_added'] = updated_count

            logger.info(f"Successfully wrote fragility results:")
            logger.info(f"  Updated buildings: {updated_count}")
            logger.info(f"  Processing time: {processing_time:.1f}s")
            logger.info(f"  Output file: {output_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to write fragility results: {e}")

            # 清理臨時檔案
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass

            return False

    def validate_geojson_integrity(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        驗證GeoJSON檔案完整性（使用輕量級驗證，避免OOM）

        Args:
            file_path: 要驗證的檔案路徑，None表示驗證原檔案

        Returns:
            Dict: 驗證結果
        """
        if file_path is None:
            file_path = self.geojson_file

        validation_results = {
            'file_exists': False,
            'valid_json': False,
            'valid_geojson': False,
            'feature_count': 0,
            'features_with_fragility': 0,
            'file_size_mb': 0.0,
            'validation_errors': []
        }

        try:
            file_path = Path(file_path)

            # 檢查檔案存在
            if not file_path.exists():
                validation_results['validation_errors'].append(f"File does not exist: {file_path}")
                return validation_results

            validation_results['file_exists'] = True
            file_size = file_path.stat().st_size
            validation_results['file_size_mb'] = file_size / (1024 * 1024)

            # 對於大檔案（>100MB），使用輕量級驗證避免 OOM
            if file_size > 100 * 1024 * 1024:  # 100 MB
                logger.info(f"Large file detected ({validation_results['file_size_mb']:.1f} MB), using lightweight validation")

                # 讀取檔案前 10KB 來檢查基本結構
                with open(file_path, 'r', encoding='utf-8') as f:
                    header = f.read(10240)  # 讀取前 10KB

                    # 檢查基本 JSON 結構
                    if not header.strip().startswith('{'):
                        validation_results['validation_errors'].append("File does not start with JSON object")
                        return validation_results

                    validation_results['valid_json'] = True

                    # 檢查 type 欄位
                    valid_types = ['FeatureCollection', 'BuildingCollection']
                    type_found = False
                    for vtype in valid_types:
                        if f'"type": "{vtype}"' in header or f'"type":"{vtype}"' in header:
                            type_found = True
                            break

                    if not type_found:
                        validation_results['validation_errors'].append(f"Missing or invalid 'type' field, expected one of: {valid_types}")
                        return validation_results

                    # 檢查 features 欄位
                    if '"features"' not in header:
                        validation_results['validation_errors'].append("Missing 'features' field")
                        return validation_results

                    validation_results['valid_geojson'] = True

                    # 嘗試從 metadata 讀取建築數量（如果有的話）
                    if '"total_buildings"' in header:
                        import re
                        match = re.search(r'"total_buildings"\s*:\s*(\d+)', header)
                        if match:
                            validation_results['feature_count'] = int(match.group(1))
                            logger.info(f"Feature count from metadata: {validation_results['feature_count']}")

                    # 如果沒有從 metadata 取得，設為未知
                    if validation_results['feature_count'] == 0:
                        validation_results['feature_count'] = -1  # -1 表示未知（檔案太大無法載入）
                        logger.info("Feature count unknown (file too large for full scan)")

                    # 大檔案不統計 fragility_count，避免載入整個檔案
                    validation_results['features_with_fragility'] = -1  # -1 表示未統計

                    logger.info(f"Lightweight GeoJSON validation complete:")
                    logger.info(f"  File size: {validation_results['file_size_mb']:.1f} MB")
                    logger.info(f"  Features: {validation_results['feature_count'] if validation_results['feature_count'] >= 0 else 'unknown'}")
                    logger.info(f"  Validation method: lightweight (avoiding OOM)")

            else:
                # 小檔案使用完整驗證
                logger.info(f"Small file ({validation_results['file_size_mb']:.1f} MB), using full validation")

                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        validation_results['valid_json'] = True
                    except json.JSONDecodeError as e:
                        validation_results['validation_errors'].append(f"Invalid JSON format: {e}")
                        return validation_results

                # 檢查GeoJSON結構 - 支援 FeatureCollection 和 BuildingCollection
                valid_types = ['FeatureCollection', 'BuildingCollection']
                if 'type' not in data or data['type'] not in valid_types:
                    if 'type' not in data:
                        validation_results['validation_errors'].append("Missing 'type' field")
                    else:
                        validation_results['validation_errors'].append(f"Invalid type: {data['type']}, expected one of: {valid_types}")
                    return validation_results

                if 'features' not in data:
                    validation_results['validation_errors'].append("Missing 'features' field")
                    return validation_results

                validation_results['valid_geojson'] = True
                validation_results['feature_count'] = len(data['features'])

                # 檢查易損性結果
                fragility_count = 0
                for feature in data['features']:
                    if (isinstance(feature.get('properties'), dict) and
                        'fragility_curve' in feature['properties']):
                        fragility_count += 1

                validation_results['features_with_fragility'] = fragility_count

                logger.info(f"Full GeoJSON validation complete:")
                logger.info(f"  File size: {validation_results['file_size_mb']:.1f} MB")
                logger.info(f"  Features: {validation_results['feature_count']}")
                logger.info(f"  With fragility: {fragility_count}")

        except Exception as e:
            validation_results['validation_errors'].append(f"Validation error: {e}")
            logger.error(f"Validation failed: {e}")

        return validation_results

    def get_processing_statistics(self) -> Dict[str, Any]:
        """獲取處理統計資訊"""
        return self.stats.copy()

    def cleanup_temp_files(self) -> None:
        """清理臨時檔案"""
        try:
            # 清理同目錄下的臨時檔案
            temp_pattern = f"{self.geojson_file.stem}_temp_*{self.geojson_file.suffix}"
            for temp_file in self.geojson_file.parent.glob(temp_pattern):
                try:
                    temp_file.unlink()
                    logger.debug(f"Removed temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {temp_file}: {e}")

        except Exception as e:
            logger.error(f"Temp file cleanup failed: {e}")


def test_geojson_processor():
    """測試GeoJSON處理器"""
    import tempfile
    import json

    print("Testing GeoJSON Processor...")

    # 建立測試GeoJSON檔案
    test_data = {
        "type": "FeatureCollection",
        "metadata": {
            "total_buildings": 3
        },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "area_sqm": 120.0,
                    "max_height": 17.5,
                    "max_age": 30,
                    "floor": "5R"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "area_sqm": 300.0,
                    "max_height": 28.0,
                    "max_age": 15,
                    "floor": "8R"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "area_sqm": 800.0,
                    "max_height": 42.0,
                    "max_age": 35,
                    "floor": "12M"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]
                }
            }
        ]
    }

    # 建立臨時檔案
    with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as f:
        json.dump(test_data, f)
        temp_geojson = f.name

    try:
        # 測試處理器
        processor = GeoJSONProcessor(temp_geojson, backup_original=False)

        # 測試元數據載入
        metadata = processor.load_geojson_metadata()
        print(f"Metadata: {metadata}")

        # 測試建築分類
        classified_buildings = processor.classify_buildings_batch(max_buildings=10)
        print(f"Classified {len(classified_buildings)} buildings:")

        for props, building_id in classified_buildings:
            print(f"  {building_id}: {props.get_archetype_code()}")

        # 測試統計
        stats = processor.get_archetype_statistics(classified_buildings)
        print(f"Statistics: {stats}")

        # 測試驗證
        validation = processor.validate_geojson_integrity()
        print(f"Validation: {validation}")

        print("GeoJSON Processor test completed successfully!")

    finally:
        # 清理
        if os.path.exists(temp_geojson):
            os.unlink(temp_geojson)


if __name__ == "__main__":
    # 設定日誌
    logging.basicConfig(level=logging.INFO)

    # 執行測試
    test_geojson_processor()