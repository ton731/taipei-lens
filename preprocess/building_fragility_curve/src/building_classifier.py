#!/usr/bin/env python3
"""
Building Classifier Module

此模組負責將GeoJSON中的建築資料進行分類，根據PRD定義的四維分類系統：
1. 結構系統 (RC/SC)
2. 設計年代 (PRE/POST 1999)
3. 樓層數 (實際樓層)
4. 佔地面積規模 (S/M/L)

生成標準化的原型編碼，用於後續的結構分析。
"""

import re
import logging
from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class BuildingProperties:
    """建築物基本屬性"""
    floor_count: int
    structural_system: str  # 'RC' or 'SC'
    construction_era: str   # 'PRE' or 'POST'
    area_scale: str        # 'S', 'M', or 'L'
    area_sqm: float        # 實際面積
    representative_area_sqm: float  # 代表性面積（用於結構分析）
    height: float
    age: Optional[int]

    def get_archetype_code(self) -> str:
        """生成標準化的原型編碼"""
        return f"{self.structural_system}-{self.construction_era}-{self.floor_count}F-{self.area_scale}"

    def __getstate__(self) -> Dict:
        """自定義序列化狀態，確保多進程相容性"""
        return {
            'floor_count': self.floor_count,
            'structural_system': self.structural_system,
            'construction_era': self.construction_era,
            'area_scale': self.area_scale,
            'area_sqm': self.area_sqm,
            'representative_area_sqm': self.representative_area_sqm,
            'height': self.height,
            'age': self.age
        }

    def __setstate__(self, state: Dict) -> None:
        """自定義反序列化狀態，確保多進程相容性"""
        self.floor_count = state['floor_count']
        self.structural_system = state['structural_system']
        self.construction_era = state['construction_era']
        self.area_scale = state['area_scale']
        self.area_sqm = state['area_sqm']
        self.representative_area_sqm = state.get('representative_area_sqm', state['area_sqm'])  # 向後兼容
        self.height = state['height']
        self.age = state['age']

    def validate(self) -> bool:
        """驗證物件數據的有效性"""
        try:
            return (
                isinstance(self.floor_count, int) and self.floor_count > 0 and
                isinstance(self.structural_system, str) and self.structural_system in ['RC', 'SC'] and
                isinstance(self.construction_era, str) and self.construction_era in ['PRE', 'POST'] and
                isinstance(self.area_scale, str) and self.area_scale in ['S', 'M', 'L'] and
                isinstance(self.area_sqm, (int, float)) and self.area_sqm > 0 and
                isinstance(self.representative_area_sqm, (int, float)) and self.representative_area_sqm > 0 and
                isinstance(self.height, (int, float)) and self.height > 0 and
                (self.age is None or (isinstance(self.age, int) and self.age >= 0))
            )
        except:
            return False

    def __repr__(self) -> str:
        """提供更清晰的字符串表示"""
        return (f"BuildingProperties(archetype='{self.get_archetype_code()}', "
                f"floor_count={self.floor_count}, area_sqm={self.area_sqm:.1f}, "
                f"representative_area={self.representative_area_sqm:.1f}, "
                f"height={self.height:.1f}m, age={self.age})")


class BuildingClassifier:
    """
    建築分類器

    根據PRD定義的分類系統，解析GeoJSON中的建築屬性並生成分類編碼
    """

    def __init__(self):
        # 面積規模分類閾值 (平方米)
        self.area_thresholds = {
            'small': 150,     # < 150 m²
            'large': 500      # > 500 m²
        }

        # 921地震發生年份 (分水嶺)
        self.earthquake_year = 1999
        self.current_year = datetime.now().year

        # 年齡填補統計
        self.age_stats = {
            'used_max_age': 0,
            'used_polygon_max_age': 0,
            'used_default_age': 0,
            'total_processed': 0
        }

        # 面積標準值 (從 project_config 導入)
        self._area_standards = None

    def get_area_standards(self) -> Dict:
        """
        獲取面積分類標準值

        Returns:
            Dict: 面積標準值配置
        """
        if self._area_standards is None:
            try:
                # 動態導入避免循環引用
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from project_config import ProjectConfig
                config = ProjectConfig()
                self._area_standards = config.get_area_scale_standards()
            except Exception as e:
                logger.warning(f"Failed to load area standards from config: {e}")
                # 使用預設值
                self._area_standards = {
                    'S': {'representative_area': 100.0},
                    'M': {'representative_area': 300.0},
                    'L': {'representative_area': 700.0}
                }
        return self._area_standards

    def get_representative_area(self, area_scale: str) -> float:
        """
        根據面積分類獲取代表性面積

        Args:
            area_scale: 面積分類 ('S', 'M', 'L')

        Returns:
            float: 代表性面積 (平方米)
        """
        area_standards = self.get_area_standards()
        if area_scale in area_standards:
            return area_standards[area_scale]['representative_area']
        else:
            logger.warning(f"Unknown area scale: {area_scale}, using default 300.0 m²")
            return 300.0  # 預設中型面積

    def parse_floor_info(self, floor_str: Optional[str]) -> Tuple[int, str]:
        """
        解析樓層資訊

        從 floor 屬性中提取樓層數和結構系統
        格式: "9R" (9層RC結構) 或 "12M" (12層鋼構)

        Args:
            floor_str: 樓層字串，如 "9R", "12M"

        Returns:
            tuple: (樓層數, 結構系統)

        Raises:
            ValueError: 如果格式不符合預期
        """
        if not floor_str:
            raise ValueError("Floor information is missing")

        # 使用正則表達式解析樓層資訊
        match = re.match(r'^(\d+)([A-Z])$', floor_str.upper())

        if not match:
            raise ValueError(f"Invalid floor format: {floor_str}")

        floor_count = int(match.group(1))
        system_code = match.group(2)

        # 轉換為標準結構系統代碼
        # M = 鋼構 (SC), 其他都是 RC (包括 R, B, 等)
        structural_system = 'SC' if system_code == 'M' else 'RC'

        return floor_count, structural_system

    def extract_floor_info(self, feature: Dict, floor_info: Optional[str]) -> Tuple[int, str]:
        """
        提取樓層資訊，支援從polygons中查找最大樓層數

        Args:
            feature: 完整的建築feature
            floor_info: 根層級的floor屬性

        Returns:
            tuple: (樓層數, 結構系統)
        """
        # 如果根層級有樓層資訊，直接使用
        if floor_info is not None:
            return self.parse_floor_info(floor_info)

        # 否則從polygons中提取最大樓層數
        polygons = feature.get('polygons', [])
        if not polygons:
            raise ValueError("Floor information is missing and no polygons found")

        max_floor_count = 0
        best_structural_system = 'RC'  # 預設值

        # 遍歷所有polygons，找出最大樓層數
        for polygon in polygons:
            properties = polygon.get('properties', {})
            polygon_floor = properties.get('floor')

            if polygon_floor:
                try:
                    floor_count, structural_system = self.parse_floor_info(polygon_floor)

                    # 更新最大樓層數和對應的結構系統
                    if floor_count > max_floor_count:
                        max_floor_count = floor_count
                        best_structural_system = structural_system

                except ValueError as e:
                    logger.debug(f"Skip invalid floor info in polygon: {polygon_floor}, error: {e}")
                    continue

        if max_floor_count == 0:
            raise ValueError("Floor information is missing in all polygons")

        logger.debug(f"Extracted max floor from polygons: {max_floor_count}{best_structural_system[0]}")
        return max_floor_count, best_structural_system

    def determine_construction_era(self, age: Optional[int]) -> str:
        """
        判斷建築建造年代

        根據建築年齡判斷是921地震前後建造

        Args:
            age: 建築年齡

        Returns:
            str: 'PRE' (1999年前) 或 'POST' (1999年後)
        """
        if age is None:
            # 如果年齡不明，預設為較保守的921前
            logger.warning("Building age is None, defaulting to PRE-1999")
            return 'PRE'

        construction_year = self.current_year - age

        if construction_year <= self.earthquake_year:
            return 'PRE'
        else:
            return 'POST'

    def classify_area_scale(self, area_sqm: float) -> str:
        """
        分類佔地面積規模

        根據PRD定義的面積閾值進行分類

        Args:
            area_sqm: 佔地面積 (平方米)

        Returns:
            str: 'S' (小型), 'M' (中型), 'L' (大型)
        """
        if area_sqm < self.area_thresholds['small']:
            return 'S'
        elif area_sqm <= self.area_thresholds['large']:
            return 'M'
        else:
            return 'L'

    def extract_building_age(self, feature: Dict) -> Optional[int]:
        """
        提取建築年齡，實施三層填補策略（僅用於分類，不修改原始資料）

        1. 優先使用建築物的max_age
        2. 如果max_age為null，取該建築所有polygons中age的最大值
        3. 如果所有polygon的age都是null，假設為1999年之前的結構

        注意：此方法僅用於分類過程，不會修改原始GeoJSON資料

        Args:
            feature: GeoJSON feature object (只讀，不修改)

        Returns:
            int: 建築年齡，若無法確定則返回PRE-1999年齡
        """
        self.age_stats['total_processed'] += 1

        # 策略1: 優先使用max_age
        max_age = feature.get('max_age')
        if max_age is not None and max_age != 'null' and max_age != '':
            try:
                age_value = int(float(max_age))
                if age_value > 0:
                    self.age_stats['used_max_age'] += 1
                    logger.debug(f"Using max_age: {age_value}")
                    return age_value
            except (ValueError, TypeError):
                pass

        # 策略2: 如果max_age無效，尋找polygons中的最大age
        polygons = feature.get('polygons', [])
        polygon_ages = []

        for polygon in polygons:
            polygon_age = polygon.get('properties', {}).get('age')
            if polygon_age is not None and polygon_age != 'null' and polygon_age != '':
                try:
                    age_value = int(float(polygon_age))
                    if age_value > 0:
                        polygon_ages.append(age_value)
                except (ValueError, TypeError):
                    continue

        if polygon_ages:
            max_polygon_age = max(polygon_ages)
            self.age_stats['used_polygon_max_age'] += 1
            logger.debug(f"Using polygon max age: {max_polygon_age}")
            return max_polygon_age

        # 策略3: 如果都沒有有效age，使用預設值(1999年之前)
        default_age = self.current_year - self.earthquake_year
        self.age_stats['used_default_age'] += 1
        logger.debug(f"Using default PRE-1999 age: {default_age}")
        return default_age

    def classify_building(self, feature: Dict) -> Optional[BuildingProperties]:
        """
        對單一建築進行分類

        從GeoJSON feature中提取屬性並進行分類

        Args:
            feature: GeoJSON feature object

        Returns:
            BuildingProperties: 分類結果，若分類失敗則返回None
        """
        try:
            # 提取基本屬性
            area_sqm = feature.get('area_sqm')
            height = feature.get('max_height')
            floor_info = feature.get('floor')

            # 驗證必要屬性
            if area_sqm is None or height is None:
                logger.warning(f"Missing required attributes: area_sqm={area_sqm}, height={height}")
                return None

            # 解析樓層資訊
            floor_count, structural_system = self.extract_floor_info(feature, floor_info)

            # 提取建築年齡（使用三層填補策略）
            age = self.extract_building_age(feature)

            # 判斷建造年代
            construction_era = self.determine_construction_era(age)

            # 分類面積規模
            area_scale = self.classify_area_scale(area_sqm)

            # 獲取代表性面積
            representative_area = self.get_representative_area(area_scale)

            # 建立建築屬性物件
            properties = BuildingProperties(
                floor_count=floor_count,
                structural_system=structural_system,
                construction_era=construction_era,
                area_scale=area_scale,
                area_sqm=area_sqm,
                representative_area_sqm=representative_area,
                height=height,
                age=age
            )

            logger.debug(f"Successfully classified building: {properties.get_archetype_code()}")
            return properties

        except Exception as e:
            logger.error(f"Failed to classify building: {str(e)}")
            return None

    def get_age_statistics(self) -> Dict[str, Any]:
        """
        獲取年齡填補統計資訊

        Returns:
            Dict: 年齡填補統計
        """
        total = self.age_stats['total_processed']
        if total == 0:
            return self.age_stats.copy()

        stats = self.age_stats.copy()
        stats['usage_percentages'] = {
            'max_age_usage': (stats['used_max_age'] / total) * 100,
            'polygon_age_usage': (stats['used_polygon_max_age'] / total) * 100,
            'default_age_usage': (stats['used_default_age'] / total) * 100
        }
        return stats

    def log_age_statistics(self) -> None:
        """記錄年齡填補統計到日誌"""
        stats = self.get_age_statistics()
        total = stats['total_processed']

        if total > 0:
            logger.info(f"Age Filling Statistics:")
            logger.info(f"  Total buildings processed: {total:,}")
            logger.info(f"  Used max_age: {stats['used_max_age']:,} ({stats['usage_percentages']['max_age_usage']:.1f}%)")
            logger.info(f"  Used polygon max age: {stats['used_polygon_max_age']:,} ({stats['usage_percentages']['polygon_age_usage']:.1f}%)")
            logger.info(f"  Used default PRE-1999 age: {stats['used_default_age']:,} ({stats['usage_percentages']['default_age_usage']:.1f}%)")

    def get_building_statistics(self, classified_buildings: List[BuildingProperties]) -> Dict:
        """
        計算建築分類統計

        Args:
            classified_buildings: 已分類的建築列表

        Returns:
            dict: 統計結果
        """
        if not classified_buildings:
            return {}

        # 統計各個維度的分佈
        stats = {
            'total_buildings': len(classified_buildings),
            'structural_systems': {},
            'construction_eras': {},
            'floor_counts': {},
            'area_scales': {},
            'archetype_codes': {}
        }

        for building in classified_buildings:
            # 結構系統統計
            stats['structural_systems'][building.structural_system] = \
                stats['structural_systems'].get(building.structural_system, 0) + 1

            # 建造年代統計
            stats['construction_eras'][building.construction_era] = \
                stats['construction_eras'].get(building.construction_era, 0) + 1

            # 樓層數統計
            stats['floor_counts'][building.floor_count] = \
                stats['floor_counts'].get(building.floor_count, 0) + 1

            # 面積規模統計
            stats['area_scales'][building.area_scale] = \
                stats['area_scales'].get(building.area_scale, 0) + 1

            # 原型編碼統計
            code = building.get_archetype_code()
            stats['archetype_codes'][code] = \
                stats['archetype_codes'].get(code, 0) + 1

        return stats


def test_building_classifier():
    """測試建築分類器"""
    classifier = BuildingClassifier()

    # 測試樣本
    test_features = [
        {
            'area_sqm': 120.5,
            'max_height': 15.2,
            'max_age': 30,
            'floor': '5R'
        },
        {
            'area_sqm': 300.0,
            'max_height': 60.0,
            'max_age': 15,
            'floor': '20M'
        },
        {
            'area_sqm': 800.0,
            'max_height': 42.0,
            'max_age': 35,
            'floor': '12R'
        }
    ]

    print("Testing Building Classifier...")
    for i, feature in enumerate(test_features):
        result = classifier.classify_building(feature)
        if result:
            print(f"Sample {i+1}: {result.get_archetype_code()}")
            print(f"  - Floor: {result.floor_count}, System: {result.structural_system}")
            print(f"  - Era: {result.construction_era}, Area Scale: {result.area_scale}")
            print(f"  - Actual Area: {result.area_sqm:.1f} m², Representative: {result.representative_area_sqm:.1f} m²")
        else:
            print(f"Sample {i+1}: Classification failed")
        print()


if __name__ == "__main__":
    # 設定日誌
    logging.basicConfig(level=logging.DEBUG)

    # 執行測試
    test_building_classifier()