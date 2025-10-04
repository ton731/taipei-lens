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
                                "avg_building_age"
                            ],
                            "description": "The feature name to search. Options: total_population (total population), elderly_population (elderly population count), pop_elderly_percentage (elderly population ratio), low_income_percentage (low-income household ratio), elderly_alone_percentage (elderly living alone ratio), low_income_households (low-income household count), living_alone_count (people living alone count), avg_building_age (average building age)"
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
                                            "avg_building_age"
                                        ],
                                        "description": "The feature name to filter. Options: total_population (total population), elderly_population (elderly population count), pop_elderly_percentage (elderly population ratio), low_income_percentage (low-income household ratio), elderly_alone_percentage (elderly living alone ratio), low_income_households (low-income household count), living_alone_count (people living alone count), avg_building_age (average building age)"
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


# Create global instance
tool_service = ToolService()
