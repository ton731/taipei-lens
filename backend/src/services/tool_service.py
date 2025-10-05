# -*- coding: utf-8 -*-
"""
Tool Service: Handles OpenAI Function Calling related logic
"""
import logging
from typing import Dict, Any, List
from src.services.data_service import data_service

logger = logging.getLogger(__name__)


class ToolService:
    """Tool service class responsible for managing Function Calling schema and execution logic"""

    # OpenAI Function Calling Tools Schema
    TOOLS_SCHEMA = [
        {
            "type": "function",
            "function": {
                "name": "search_top_district_by_feature",
                "description": "Search for the top N administrative districts ranked by a specified feature value. Can be used to find districts with the highest population, highest elderly population ratio, most low-income households, etc.",
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
                                "avg_building_age",
                                "lst_p90",
                                "ndvi_mean",
                                "liq_risk",
                                "viirs_mean",
                                "avg_fragility_curve"
                            ],
                            "description": "The feature name to search. Options: total_population (total population), elderly_population (elderly population count), pop_elderly_percentage (elderly population ratio), low_income_percentage (low-income household ratio), elderly_alone_percentage (elderly living alone ratio), low_income_households (low-income household count), living_alone_count (people living alone count), avg_building_age (average building age), lst_p90 (land surface temperature 90th percentile), ndvi_mean (normalized difference vegetation index mean), liq_risk (liquefaction risk), viirs_mean (nighttime light mean), avg_fragility_curve (average fragility curve risk score)"
                        },
                        "if_max": {
                            "type": "boolean",
                            "description": "True means to find districts with the highest values (descending order), False means to find districts with the lowest values (ascending order)"
                        },
                        "top_n": {
                            "type": "integer",
                            "description": "The number of top-ranked districts to return. If the user explicitly mentions 'maximum' or 'minimum', pay special attention to the top_n value. If not mentioned, default is 1.",
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
                "description": "Filter administrative districts based on multiple conditions. Can combine multiple conditions for filtering, such as requiring population greater than a certain value, elderly ratio greater than a certain value, low-income ratio greater than a certain value, etc. All conditions must be satisfied simultaneously (AND logic).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "conditions": {
                            "type": "array",
                            "description": "List of filter conditions, each containing feature (feature name), operator (comparison operator), and value (comparison value)",
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
                                            "avg_building_age",
                                            "lst_p90",
                                            "ndvi_mean",
                                            "liq_risk",
                                            "viirs_mean",
                                            "avg_fragility_curve"
                                        ],
                                        "description": "The feature name to filter. Options: total_population (total population), elderly_population (elderly population count), pop_elderly_percentage (elderly population ratio), low_income_percentage (low-income household ratio), elderly_alone_percentage (elderly living alone ratio), low_income_households (low-income household count), living_alone_count (people living alone count), avg_building_age (average building age), lst_p90 (land surface temperature 90th percentile), ndvi_mean (normalized difference vegetation index mean), liq_risk (liquefaction risk), viirs_mean (nighttime light mean), avg_fragility_curve (average fragility curve risk score)"
                                    },
                                    "operator": {
                                        "type": "string",
                                        "enum": [">", ">=", "<", "<=", "=="],
                                        "description": "Comparison operator: > (greater than), >= (greater than or equal to), < (less than), <= (less than or equal to), == (equal to)"
                                    },
                                    "value": {
                                        "type": "number",
                                        "description": "The comparison value"
                                    }
                                },
                                "required": ["feature", "operator", "value"]
                            }
                        }
                    },
                    "required": ["conditions"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_top_statistical_area_by_feature",
                "description": "Search for the top N statistical areas ranked by a specified feature value. Statistical areas are more detailed geographic units than administrative districts. Can be used to find areas with the highest temperature, vegetation coverage, liquefaction risk, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feature": {
                            "type": "string",
                            "enum": [
                                "population_density",
                                "pop_elderly_percentage",
                                "low_income_percentage",
                                "elderly_alone_percentage",
                                "avg_building_age",
                                "lst_p90",
                                "ndvi_mean",
                                "liq_risk",
                                "viirs_mean",
                                "coverage_strict_300m",
                                "avg_fragility_curve",
                                "utfvi"
                            ],
                            "description": "The feature name to search. Options: population_density (population density), pop_elderly_percentage (elderly population ratio), low_income_percentage (low-income household ratio), elderly_alone_percentage (elderly living alone ratio), avg_building_age (average building age), lst_p90 (land surface temperature 90th percentile), ndvi_mean (normalized difference vegetation index mean), liq_risk (liquefaction risk), viirs_mean (nighttime light mean), coverage_strict_300m (strict 300m coverage ratio), avg_fragility_curve (average fragility curve risk score), utfvi (urban thermal field variance index)"
                        },
                        "if_max": {
                            "type": "boolean",
                            "description": "True means to find areas with the highest values (descending order), False means to find areas with the lowest values (ascending order)"
                        },
                        "top_n": {
                            "type": "integer",
                            "description": "The number of top-ranked statistical areas to return. Maximum is 30. If not mentioned, default is 10.",
                            "default": 10
                        }
                    },
                    "required": ["feature", "if_max", "top_n"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "filter_statistical_area_by_conditions",
                "description": "Filter statistical areas based on multiple conditions. Statistical areas are more detailed geographic units than administrative districts. Can combine multiple conditions for filtering, such as requiring temperature greater than a certain value, vegetation index greater than a certain value, etc. All conditions must be satisfied simultaneously (AND logic).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "conditions": {
                            "type": "array",
                            "description": "List of filter conditions, each containing feature (feature name), operator (comparison operator), and value (comparison value)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "feature": {
                                        "type": "string",
                                        "enum": [
                                            "population_density",
                                            "pop_elderly_percentage",
                                            "low_income_percentage",
                                            "elderly_alone_percentage",
                                            "avg_building_age",
                                            "lst_p90",
                                            "ndvi_mean",
                                            "liq_risk",
                                            "viirs_mean",
                                            "coverage_strict_300m",
                                            "avg_fragility_curve",
                                            "utfvi"
                                        ],
                                        "description": "The feature name to filter. Options: population_density (population density), pop_elderly_percentage (elderly population ratio), low_income_percentage (low-income household ratio), elderly_alone_percentage (elderly living alone ratio), avg_building_age (average building age), lst_p90 (land surface temperature 90th percentile), ndvi_mean (normalized difference vegetation index mean), liq_risk (liquefaction risk), viirs_mean (nighttime light mean), coverage_strict_300m (strict 300m coverage ratio), avg_fragility_curve (average fragility curve risk score), utfvi (urban thermal field variance index)"
                                    },
                                    "operator": {
                                        "type": "string",
                                        "enum": [">", ">=", "<", "<=", "=="],
                                        "description": "Comparison operator: > (greater than), >= (greater than or equal to), < (less than), <= (less than or equal to), == (equal to)"
                                    },
                                    "value": {
                                        "type": "number",
                                        "description": "The comparison value"
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
        Dynamically execute specified function call

        Args:
            function_name: Function name to execute
            arguments: Function arguments (JSON format)

        Returns:
            Function execution result or error message
        """
        # Define available function mappings
        available_functions = {
            "search_top_district_by_feature": ToolService._search_top_district,
            "filter_district_by_conditions": ToolService._filter_district,
            "search_top_statistical_area_by_feature": ToolService._search_top_statistical_area,
            "filter_statistical_area_by_conditions": ToolService._filter_statistical_area,
        }

        # Check if function exists
        if function_name not in available_functions:
            error_msg = f"Function '{function_name}' not found"
            logger.error(error_msg)
            return error_msg

        try:
            # Execute function
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
        Search districts (internal method, calls data_service)

        Args:
            feature: Feature name
            if_max: True to find maximum values, False to find minimum values
            top_n: Number of top results to return

        Returns:
            List of dictionaries containing district and feature values
        """
        return data_service.search_top_districts(feature, if_max, top_n)

    @staticmethod
    def _filter_district(conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter districts based on multiple conditions (internal method, calls data_service)

        Args:
            conditions: List of filter conditions

        Returns:
            List of districts that satisfy all conditions
        """
        return data_service.filter_districts_by_conditions(conditions)

    @staticmethod
    def _search_top_statistical_area(feature: str, if_max: bool, top_n: int) -> List[Dict[str, Any]]:
        """
        Search statistical areas (internal method, calls data_service)

        Args:
            feature: Feature name
            if_max: True to find maximum values, False to find minimum values
            top_n: Number of top results to return

        Returns:
            List of dictionaries containing CODEBASE and feature values
        """
        return data_service.search_top_statistical_areas(feature, if_max, top_n)

    @staticmethod
    def _filter_statistical_area(conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter statistical areas based on multiple conditions (internal method, calls data_service)

        Args:
            conditions: List of filter conditions

        Returns:
            List of statistical areas that satisfy all conditions
        """
        return data_service.filter_statistical_areas_by_conditions(conditions)


# Create global instance
tool_service = ToolService()
