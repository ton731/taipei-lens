# -*- coding: utf-8 -*-
"""
數據服務：處理地理數據的載入與查詢
"""
import pandas as pd
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class DataService:
    """數據服務類別，負責載入與查詢統計區域及行政區資料"""

    _instance = None
    _statistical_df: pd.DataFrame = None
    _district_df: pd.DataFrame = None

    # 行政區特徵名稱到統計區特徵名稱的映射
    FEATURE_MAPPING = {
        "total_population": "population",
        "elderly_population": "population",  # 需要計算：population * pop_elderly_percentage
        "pop_elderly_percentage": "pop_elderly_percentage",
        "low_income_percentage": "low_income_percentage",
        "elderly_alone_percentage": "elderly_alone_percentage",
        "low_income_households": "household",  # 需要計算：household * low_income_percentage
        "living_alone_count": "household",  # 需要計算：household * elderly_alone_percentage
        "avg_building_age": "avg_building_age",
        "lst_p90": "lst_p90",
        "ndvi_mean": "ndvi_mean",
        "liq_risk": "liq_risk",
        "viirs_mean": "viirs_mean",
        "avg_fragility_curve": "fragility_risk_score",
        "utfvi": "utfvi"
    }

    def __new__(cls):
        """實作 Singleton 模式，確保數據只載入一次"""
        if cls._instance is None:
            cls._instance = super(DataService, cls).__new__(cls)
            cls._instance._load_data()
        return cls._instance

    @staticmethod
    def _calculate_fragility_risk_score(fragility_curve):
        """
        計算 fragility curve 的風險分數
        
        Args:
            fragility_curve: dict，包含不同地震強度下的損壞機率
            
        Returns:
            float: 0-1 的風險分數，越高表示風險越大
        """
        if not isinstance(fragility_curve, dict):
            return 0.0
            
        # 地震強度權重（越強的地震權重越高）
        weights = {
            "3": 1.0,
            "4": 2.0, 
            "5弱": 3.0,
            "5強": 4.0,
            "6弱": 6.0,
            "6強": 8.0,
            "7": 10.0
        }
        
        total_weighted_risk = 0.0
        total_weight = 0.0
        
        for magnitude, probability in fragility_curve.items():
            if magnitude in weights:
                weight = weights[magnitude]
                total_weighted_risk += probability * weight
                total_weight += weight
                
        # 返回加權平均風險分數
        return total_weighted_risk / total_weight if total_weight > 0 else 0.0

    def _load_data(self):
        """
        載入統計區域與行政區的資料（私有方法，只在初始化時調用一次）
        """
        try:
            # 載入最小統計區域資料
            with open("src/public/basic_statistical_area_with_features.geojson", "r", encoding="utf-8") as f:
                statistical_geojson = json.load(f)

            # 載入行政區資料
            with open("src/public/district_with_features.geojson", "r", encoding="utf-8") as f:
                district_geojson = json.load(f)

            # 提取 properties 並轉換為 DataFrame
            statistical_properties = [feature["properties"] for feature in statistical_geojson["features"]]
            district_properties = [feature["properties"] for feature in district_geojson["features"]]

            self._statistical_df = pd.DataFrame(statistical_properties)
            self._district_df = pd.DataFrame(district_properties)

            # 計算 fragility curve 風險分數並添加到 DataFrame
            if 'avg_fragility_curve' in self._statistical_df.columns:
                self._statistical_df['fragility_risk_score'] = self._statistical_df['avg_fragility_curve'].apply(
                    self._calculate_fragility_risk_score
                )
            
            if 'avg_fragility_curve' in self._district_df.columns:
                self._district_df['fragility_risk_score'] = self._district_df['avg_fragility_curve'].apply(
                    self._calculate_fragility_risk_score
                )

            logger.info(f"Data loaded successfully: {len(self._statistical_df)} statistical areas, {len(self._district_df)} districts")

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise

    def search_top_statistical_areas(
        self,
        feature: str,
        if_max: bool,
        top_n: int
    ) -> List[Dict[str, Any]]:
        """
        搜尋指定特徵值排名前 N 的統計區域

        Args:
            feature: 特徵名稱 (e.g., 'population_density', 'avg_building_age')
            if_max: True 表示找最大值，False 表示找最小值
            top_n: 返回前幾名（最多30個）

        Returns:
            包含 CODEBASE 和特徵值的字典列表
        """
        try:
            # 限制統計區最多回傳30個
            limited_top_n = min(top_n, 30)

            # 處理 avg_fragility_curve 特殊情況
            search_feature = feature
            if feature == 'avg_fragility_curve':
                search_feature = 'fragility_risk_score'

            # 根據 if_max 決定排序方式
            sorted_df = self._statistical_df.sort_values(
                by=search_feature,
                ascending=not if_max
            ).head(limited_top_n)

            # 只選取 CODEBASE 和指定的 feature 欄位
            result = sorted_df[["CODEBASE", search_feature]].to_dict(orient="records")
            
            # 如果是 fragility curve，需要重命名欄位
            if feature == 'avg_fragility_curve':
                for item in result:
                    item['avg_fragility_curve'] = item.pop('fragility_risk_score')

            # logger.info(f"Found top {limited_top_n} statistical areas by {feature} ({'max' if if_max else 'min'})")
            return result

        except KeyError:
            logger.error(f"Feature '{feature}' not found in statistical area data")
            raise ValueError(f"Invalid feature name: {feature}")
        except Exception as e:
            logger.error(f"Error searching statistical areas: {e}")
            raise

    def search_top_districts(
        self,
        feature: str,
        if_max: bool,
        top_n: int
    ) -> List[Dict[str, Any]]:
        """
        搜尋指定特徵值排名前 N 的行政區

        Args:
            feature: 特徵名稱 (e.g., 'total_population', 'elderly_population')
            if_max: True 表示找最大值，False 表示找最小值
            top_n: 返回前幾名

        Returns:
            包含 district 和特徵值的字典列表
        """
        try:
            # 處理 avg_fragility_curve 特殊情況
            search_feature = feature
            if feature == 'avg_fragility_curve':
                search_feature = 'fragility_risk_score'

            # 根據 if_max 決定排序方式
            sorted_df = self._district_df.sort_values(
                by=search_feature,
                ascending=not if_max
            ).head(top_n)

            # 只選取 district 和指定的 feature 欄位
            result = sorted_df[["district", search_feature]].to_dict(orient="records")
            
            # 如果是 fragility curve，需要重命名欄位
            if feature == 'avg_fragility_curve':
                for item in result:
                    item['avg_fragility_curve'] = item.pop('fragility_risk_score')

            # logger.info(f"Found top {top_n} districts by {feature} ({'max' if if_max else 'min'})")
            return result

        except KeyError:
            logger.error(f"Feature '{feature}' not found in district data")
            raise ValueError(f"Invalid feature name: {feature}")
        except Exception as e:
            logger.error(f"Error searching districts: {e}")
            raise

    def filter_statistical_areas_by_conditions(
        self,
        conditions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        根據多個條件篩選統計區域

        Args:
            conditions: 篩選條件列表，每個條件包含：
                - feature: str - 特徵名稱
                - operator: str - 比較運算符 (">", ">=", "<", "<=", "==")
                - value: float/int - 比較數值

        Returns:
            符合所有條件的統計區列表，包含 CODEBASE 和相關特徵值（最多30個）
        """
        try:
            # 複製 DataFrame 避免修改原始資料
            filtered_df = self._statistical_df.copy()

            # 逐一應用每個條件（AND 邏輯）
            for condition in conditions:
                feature = condition["feature"]
                operator = condition["operator"]
                value = condition["value"]

                # 處理 avg_fragility_curve 特殊情況
                search_feature = feature
                if feature == 'avg_fragility_curve':
                    search_feature = 'fragility_risk_score'

                if operator == ">":
                    filtered_df = filtered_df[filtered_df[search_feature] > value]
                elif operator == ">=":
                    filtered_df = filtered_df[filtered_df[search_feature] >= value]
                elif operator == "<":
                    filtered_df = filtered_df[filtered_df[search_feature] < value]
                elif operator == "<=":
                    filtered_df = filtered_df[filtered_df[search_feature] <= value]
                elif operator == "==":
                    filtered_df = filtered_df[filtered_df[search_feature] == value]

            # 限制統計區最多回傳30個
            filtered_df = filtered_df.head(30)

            # 收集所有用到的 features
            used_features = ["CODEBASE"] + [c["feature"] for c in conditions]
            # 去重（保持順序）
            used_features = list(dict.fromkeys(used_features))

            result = filtered_df[used_features].to_dict(orient="records")
            # logger.info(f"Filtered statistical areas: {len(result)} results with {len(conditions)} conditions (limited to 30)")
            return result

        except KeyError as e:
            logger.error(f"Feature not found in statistical area data: {e}")
            raise ValueError(f"Invalid feature name: {e}")
        except Exception as e:
            logger.error(f"Error filtering statistical areas: {e}")
            raise

    def filter_districts_by_conditions(
        self,
        conditions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        根據多個條件篩選行政區

        Args:
            conditions: 篩選條件列表，每個條件包含：
                - feature: str - 特徵名稱
                - operator: str - 比較運算符 (">", ">=", "<", "<=", "==")
                - value: float/int - 比較數值

        Returns:
            符合所有條件的行政區列表，包含 district 和相關特徵值
        """
        try:
            # 複製 DataFrame 避免修改原始資料
            filtered_df = self._district_df.copy()

            # 逐一應用每個條件（AND 邏輯）
            for condition in conditions:
                feature = condition["feature"]
                operator = condition["operator"]
                value = condition["value"]

                # 處理 avg_fragility_curve 特殊情況
                search_feature = feature
                if feature == 'avg_fragility_curve':
                    search_feature = 'fragility_risk_score'

                if operator == ">":
                    filtered_df = filtered_df[filtered_df[search_feature] > value]
                elif operator == ">=":
                    filtered_df = filtered_df[filtered_df[search_feature] >= value]
                elif operator == "<":
                    filtered_df = filtered_df[filtered_df[search_feature] < value]
                elif operator == "<=":
                    filtered_df = filtered_df[filtered_df[search_feature] <= value]
                elif operator == "==":
                    filtered_df = filtered_df[filtered_df[search_feature] == value]

            # 收集所有用到的 features
            used_features = ["district"] + [c["feature"] for c in conditions]
            # 去重（保持順序）
            used_features = list(dict.fromkeys(used_features))

            result = filtered_df[used_features].to_dict(orient="records")
            # logger.info(f"Filtered districts: {len(result)} results with {len(conditions)} conditions")
            return result

        except KeyError as e:
            logger.error(f"Feature not found in district data: {e}")
            raise ValueError(f"Invalid feature name: {e}")
        except Exception as e:
            logger.error(f"Error filtering districts: {e}")
            raise

    def get_statistical_areas_by_districts(
        self,
        district_names: List[str],
        feature: str
    ) -> Dict[str, Any]:
        """
        根據行政區名稱獲取該行政區內所有統計區的詳細資料

        Args:
            district_names: 行政區名稱列表（例如：["大安區", "信義區"]）
            feature: 行政區層級的特徵名稱（例如：'total_population'）

        Returns:
            包含以下資訊的字典：
            {
                "statistical_areas": [
                    {"CODEBASE": "xxx", "district": "大安區", "value": 5000},
                    ...
                ],
                "feature": "population",  # 統計區層級的特徵名稱
                "min_value": 100,
                "max_value": 8000
            }
        """
        try:
            # 映射特徵名稱
            if feature not in self.FEATURE_MAPPING:
                raise ValueError(f"Unsupported feature: {feature}")

            stat_feature = self.FEATURE_MAPPING[feature]

            # 篩選出指定行政區的統計區
            filtered_df = self._statistical_df[
                self._statistical_df['TOWN'].isin(district_names)
            ].copy()

            if filtered_df.empty:
                logger.warning(f"No statistical areas found for districts: {district_names}")
                return {
                    "statistical_areas": [],
                    "feature": stat_feature,
                    "min_value": 0,
                    "max_value": 0
                }

            # 計算特徵值（根據不同的特徵進行不同的計算）
            if feature == "total_population":
                filtered_df['value'] = filtered_df['population']
            elif feature == "elderly_population":
                # elderly_population = population * pop_elderly_percentage / 100
                filtered_df['value'] = (
                    filtered_df['population'] * filtered_df['pop_elderly_percentage'] / 100
                ).round().astype(int)
            elif feature == "low_income_households":
                # low_income_households = household * low_income_percentage / 100
                filtered_df['value'] = (
                    filtered_df['household'] * filtered_df['low_income_percentage'] / 100
                ).round().astype(int)
            elif feature == "living_alone_count":
                # living_alone_count = household * elderly_alone_percentage / 100
                filtered_df['value'] = (
                    filtered_df['household'] * filtered_df['elderly_alone_percentage'] / 100
                ).round().astype(int)
            else:
                # 其他特徵（包括新字段）直接使用統計區的欄位值
                filtered_df['value'] = filtered_df[stat_feature]

            # 準備返回資料
            result_list = filtered_df[['CODEBASE', 'TOWN', 'value']].rename(
                columns={'TOWN': 'district'}
            ).to_dict(orient='records')

            # 計算 min 和 max（用於前端計算顏色範圍）
            min_value = float(filtered_df['value'].min())
            max_value = float(filtered_df['value'].max())

            logger.info(
                f"Found {len(result_list)} statistical areas for districts {district_names} "
                f"(feature: {feature}, range: {min_value}-{max_value})"
            )

            return {
                "statistical_areas": result_list,
                "feature": stat_feature,
                "min_value": min_value,
                "max_value": max_value
            }

        except Exception as e:
            logger.error(f"Error getting statistical areas by districts: {e}")
            raise

    @property
    def statistical_data(self) -> pd.DataFrame:
        """取得統計區域資料（唯讀）"""
        return self._statistical_df.copy()

    @property
    def district_data(self) -> pd.DataFrame:
        """取得行政區資料（唯讀）"""
        return self._district_df.copy()


# 創建全局實例（Singleton）
data_service = DataService()
