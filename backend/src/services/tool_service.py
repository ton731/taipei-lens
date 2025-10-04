# -*- coding: utf-8 -*-
"""
工具服務：處理 OpenAI Function Calling 相關邏輯
"""
import logging
from typing import Dict, Any, List
from src.services.data_service import data_service

logger = logging.getLogger(__name__)


class ToolService:
    """工具服務類別，負責管理 Function Calling 的 schema 與執行邏輯"""

    # OpenAI Function Calling Tools Schema
    TOOLS_SCHEMA = [
        {
            "type": "function",
            "function": {
                "name": "search_top_district_by_feature",
                "description": "搜尋指定特徵值排名前N的行政區。可用於找出人口最多、高齡人口比例最高、低收入戶最多等行政區。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feature": {
                            "type": "string",
                            "enum": [
                                "total_population",
                                "elderly_population",
                                "pop_elderly_percentage",
                                "low_income_percentage",
                                "elderly_alone_percentage",
                                "low_income_households",
                                "living_alone_count",
                                "avg_building_age"
                            ],
                            "description": "要搜尋的特徵名稱。可選擇：total_population(總人口), elderly_population(高齡人口數), pop_elderly_percentage(高齡人口比例), low_income_percentage(低收入戶比例), elderly_alone_percentage(獨居老人比例), low_income_households(低收入戶數), living_alone_count(獨居人口數), avg_building_age(平均建築屋齡)"
                        },
                        "if_max": {
                            "type": "boolean",
                            "description": "True 表示要找最高值的行政區（降序排列），False 表示要找最低值的行政區（升序排列）"
                        },
                        "top_n": {
                            "type": "integer",
                            "description": "要返回前幾名的行政區數量，若使用者明確提到「最大」或「最小」，請特別注意 top_n 的數量，若沒有提到，則預設為 1。",
                            "default": 1
                        }
                    },
                    "required": ["feature", "if_max", "top_n"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "filter_district_by_conditions",
                "description": "根據多個條件篩選行政區。可組合多個條件進行篩選，例如同時要求人口數大於某值、高齡比例大於某值、低收入比例大於某值等。所有條件必須同時滿足（AND 邏輯）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "conditions": {
                            "type": "array",
                            "description": "篩選條件列表，每個條件包含 feature（特徵名稱）、operator（比較運算符）、value（比較數值）",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "feature": {
                                        "type": "string",
                                        "enum": [
                                            "total_population",
                                            "elderly_population",
                                            "pop_elderly_percentage",
                                            "low_income_percentage",
                                            "elderly_alone_percentage",
                                            "low_income_households",
                                            "living_alone_count",
                                            "avg_building_age"
                                        ],
                                        "description": "要篩選的特徵名稱。可選擇：total_population(總人口), elderly_population(高齡人口數), pop_elderly_percentage(高齡人口比例), low_income_percentage(低收入戶比例), elderly_alone_percentage(獨居老人比例), low_income_households(低收入戶數), living_alone_count(獨居人口數), avg_building_age(平均建築屋齡)"
                                    },
                                    "operator": {
                                        "type": "string",
                                        "enum": [">", ">=", "<", "<=", "=="],
                                        "description": "比較運算符：> (大於), >= (大於等於), < (小於), <= (小於等於), == (等於)"
                                    },
                                    "value": {
                                        "type": "number",
                                        "description": "比較的數值"
                                    }
                                },
                                "required": ["feature", "operator", "value"]
                            }
                        }
                    },
                    "required": ["conditions"]
                }
            }
        }
    ]

    @staticmethod
    def execute_function_call(function_name: str, arguments: Dict[str, Any]) -> Any:
        """
        動態執行指定的 function call

        Args:
            function_name: 要執行的函數名稱
            arguments: 函數參數（JSON 格式）

        Returns:
            函數執行結果，或錯誤訊息
        """
        # 定義可用的函數映射
        available_functions = {
            "search_top_district_by_feature": ToolService._search_top_district,
            "filter_district_by_conditions": ToolService._filter_district,
        }

        # 檢查函數是否存在
        if function_name not in available_functions:
            error_msg = f"Function '{function_name}' not found"
            logger.error(error_msg)
            return error_msg

        try:
            # 執行函數
            function_to_call = available_functions[function_name]
            result = function_to_call(**arguments)
            # print("***** result: ", result)
            # logger.info(f"Successfully executed function '{function_name}' with {len(result) if isinstance(result, list) else 0} results")
            return result

        except Exception as e:
            error_msg = f"Error executing function '{function_name}': {str(e)}"
            logger.error(error_msg)
            return error_msg

    @staticmethod
    def _search_top_district(feature: str, if_max: bool, top_n: int) -> List[Dict[str, Any]]:
        """
        搜尋行政區（內部方法，調用 data_service）

        Args:
            feature: 特徵名稱
            if_max: True 表示找最大值，False 表示找最小值
            top_n: 返回前幾名

        Returns:
            包含 district 和特徵值的字典列表
        """
        return data_service.search_top_districts(feature, if_max, top_n)

    @staticmethod
    def _filter_district(conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根據多個條件篩選行政區（內部方法，調用 data_service）

        Args:
            conditions: 篩選條件列表

        Returns:
            符合所有條件的行政區列表
        """
        return data_service.filter_districts_by_conditions(conditions)


# 創建全局實例
tool_service = ToolService()
