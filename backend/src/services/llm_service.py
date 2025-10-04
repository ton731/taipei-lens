# -*- coding: utf-8 -*-
"""
LLM Service: Handles OpenAI API communication and conversation logic
"""
import json
import logging
from typing import Optional, Tuple, List, Dict, Any
from openai import OpenAI, OpenAIError

from src.models.llm_models import HighlightArea, StatisticalAreaDetail
from src.services.tool_service import tool_service
from src.services.data_service import data_service

logger = logging.getLogger(__name__)


class ChatService:
    """Chat service class responsible for handling communication with OpenAI API and conversation flow"""

    # System prompt
    SYSTEM_PROMPT = """
        You are the AI assistant for Taipei Lens, the Taipei Urban Resilience Planning Platform.
        Your task is to help urban planners understand issues related to urban renewal, building risk assessment, and climate resilience in Taipei City.
        The Taipei Urban Resilience Planning Platform divides Taipei City into two levels: administrative districts (such as Da'an District, Xinyi District) and statistical areas (such as A6310-0024-00, A6311-0787-00). Statistical areas are finer regions than administrative districts, and one administrative district contains multiple statistical areas.

        **Language Response Rule:**
        - If the user asks a question in Chinese (Traditional Chinese), respond in Chinese.
        - Otherwise, respond in English by default.

        Please answer questions in a professional yet understandable manner and provide specific and practical suggestions.
        Please output in markdown format. Do not use #. Please mainly use markdown bullet points and bold text for presentation.
    """

    def __init__(self, api_key: str):
        """
        Initialize ChatService

        Args:
            api_key: OpenAI API key

        Raises:
            ValueError: When API key is empty
        """
        if not api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=api_key)
        # logger.info("ChatService initialized")

    def chat(
        self,
        question: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Tuple[str, str, Optional[HighlightArea]]:
        """
        Handle chat request with function calling support

        Args:
            question: User's question
            model: OpenAI model name
            temperature: Temperature parameter
            max_tokens: Maximum number of tokens

        Returns:
            Tuple[answer, model_used, highlight_areas]
            - answer: AI's response
            - model_used: Model name used
            - highlight_areas: Areas to highlight (may be None)

        Raises:
            OpenAIError: When OpenAI API call fails
        """
        try:
            logger.info(f"Processing chat request: {question[:100]}...")

            # Prepare messages
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ]

            # First call to OpenAI API (with tools)
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tool_service.TOOLS_SCHEMA,
                temperature=temperature,
                max_tokens=max_tokens
            )

            response_message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            # Initialize highlight_areas
            highlight_areas = None

            # Check if function calls are needed
            if finish_reason == "tool_calls" and response_message.tool_calls:
                # logger.info(f"LLM requested {len(response_message.tool_calls)} tool call(s)")

                # Handle function calling
                answer, model_used, highlight_areas = self._handle_function_calls(
                    messages=messages,
                    response_message=response_message,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            else:
                # No function calling needed, return answer directly
                answer = response_message.content
                model_used = response.model
                # logger.info(f"Direct response from OpenAI without function calls (model: {model_used})")

            return answer, model_used, highlight_areas

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in chat: {e}")
            raise

    def _handle_function_calls(
        self,
        messages: List[Dict[str, Any]],
        response_message: Any,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Tuple[str, str, Optional[HighlightArea]]:
        """
        Handle function calling flow

        Args:
            messages: List of conversation messages
            response_message: OpenAI response message
            model: OpenAI model name
            temperature: Temperature parameter
            max_tokens: Maximum number of tokens

        Returns:
            Tuple[answer, model_used, highlight_areas]
        """
        # Add assistant's response to messages
        messages.append(response_message)

        # Collect district information
        collected_district_ids = []
        feature_name = None  # Record the queried feature name

        # Execute all tool calls
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            # logger.info(f"Executing function: {function_name}")

            # Execute function
            function_result = tool_service.execute_function_call(function_name, function_args)

            # Collect district highlight information
            if "district" in function_name:
                # Record feature name
                if "feature" in function_args:
                    feature_name = function_args["feature"]

                # function_result is a list of dict containing district
                if isinstance(function_result, list):
                    for item in function_result:
                        if "district" in item:
                            collected_district_ids.append(item["district"])

            # Add function result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(function_result, ensure_ascii=False)
            })

        # Create highlight_areas object (if district data was collected)
        highlight_areas = None
        if collected_district_ids and feature_name:
            # Get statistical area details within districts
            try:
                stat_details_data = data_service.get_statistical_areas_by_districts(
                    district_names=collected_district_ids,
                    feature=feature_name
                )

                # Convert to StatisticalAreaDetail object list
                stat_details = [
                    StatisticalAreaDetail(**detail)
                    for detail in stat_details_data["statistical_areas"]
                ]

                highlight_areas = HighlightArea(
                    type="district",
                    ids=collected_district_ids,
                    statistical_details=stat_details,
                    feature=stat_details_data["feature"],
                    min_value=stat_details_data["min_value"],
                    max_value=stat_details_data["max_value"]
                )
                # logger.info(f"Collected {len(collected_district_ids)} districts with {len(stat_details)} statistical areas for highlighting")
            except Exception as e:
                logger.error(f"Error getting statistical area details: {e}")
                # If getting statistical area details fails, fall back to highlighting only districts
                highlight_areas = HighlightArea(
                    type="district",
                    ids=collected_district_ids
                )
        elif collected_district_ids:
            # If no feature name (e.g., using filter_district_by_conditions), only highlight districts
            highlight_areas = HighlightArea(
                type="district",
                ids=collected_district_ids
            )

        # Second call to OpenAI API (with function results)
        # logger.info("Sending function results back to OpenAI...")
        second_response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        answer = second_response.choices[0].message.content
        model_used = second_response.model
        # logger.info(f"Successfully received final response from OpenAI (model: {model_used})")

        return answer, model_used, highlight_areas


# Note: No global instance is created because API key is required for initialization
