# -*- coding: utf-8 -*-
"""
LLM 服務：處理 OpenAI API 通訊與對話邏輯
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
    """聊天服務類別，負責處理與 OpenAI API 的通訊與對話流程"""

    # 系統提示詞
    SYSTEM_PROMPT = """
        你是台北都市韌性規劃平台 Taipei Lens 的 AI 助手。
        你的任務是協助都市規劃師了解台北市的都市更新、建築風險評估、氣候韌性等相關議題。
        這個台北都市韌性規劃平台有將台北市劃分成行政區（如大安區、信義區）、統計區/最小統計（如A6310-0024-00、A6311-0787-00）區兩種層次，統計區是比行政區更細的區域，一個行政區有包含多個統計區。
        請用專業但易懂的方式回答問題，並提供具體且實用的建議。
        請以 markdown 的格式來輸出。請不要使用 #，請主要使用 markdown 的 bullet point 以及粗體來呈現就好。
    """

    def __init__(self, api_key: str):
        """
        初始化 ChatService

        Args:
            api_key: OpenAI API key

        Raises:
            ValueError: 當 API key 為空時
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
        處理聊天請求，支援 function calling

        Args:
            question: 使用者的問題
            model: OpenAI 模型名稱
            temperature: 溫度參數
            max_tokens: 最大 token 數

        Returns:
            Tuple[answer, model_used, highlight_areas]
            - answer: AI 的回答
            - model_used: 使用的模型名稱
            - highlight_areas: 需要高亮的區域（可能為 None）

        Raises:
            OpenAIError: 當 OpenAI API 調用失敗時
        """
        try:
            logger.info(f"Processing chat request: {question[:100]}...")

            # 準備 messages
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ]

            # 第一次調用 OpenAI API（附帶 tools）
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tool_service.TOOLS_SCHEMA,
                temperature=temperature,
                max_tokens=max_tokens
            )

            response_message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            # 初始化 highlight_areas
            highlight_areas = None

            # 檢查是否需要呼叫 function
            if finish_reason == "tool_calls" and response_message.tool_calls:
                # logger.info(f"LLM requested {len(response_message.tool_calls)} tool call(s)")

                # 處理 function calling
                answer, model_used, highlight_areas = self._handle_function_calls(
                    messages=messages,
                    response_message=response_message,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            else:
                # 不需要 function calling，直接返回答案
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
        處理 function calling 流程

        Args:
            messages: 對話訊息列表
            response_message: OpenAI 的回應訊息
            model: OpenAI 模型名稱
            temperature: 溫度參數
            max_tokens: 最大 token 數

        Returns:
            Tuple[answer, model_used, highlight_areas]
        """
        # 將 assistant 的回應加入 messages
        messages.append(response_message)

        # 用於收集行政區資訊
        collected_district_ids = []
        feature_name = None  # 用於記錄查詢的特徵名稱

        # 執行所有 tool calls
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            # logger.info(f"Executing function: {function_name}")

            # 執行 function
            function_result = tool_service.execute_function_call(function_name, function_args)

            # 收集行政區 highlight 資訊
            if "district" in function_name:
                # 記錄特徵名稱
                if "feature" in function_args:
                    feature_name = function_args["feature"]

                # function_result 是一個包含 district 的 list of dict
                if isinstance(function_result, list):
                    for item in function_result:
                        if "district" in item:
                            collected_district_ids.append(item["district"])

            # 將 function 結果加入 messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(function_result, ensure_ascii=False)
            })

        # 建立 highlight_areas 物件（如果有收集到行政區資料）
        highlight_areas = None
        if collected_district_ids and feature_name:
            # 獲取行政區內的統計區詳細資料
            try:
                stat_details_data = data_service.get_statistical_areas_by_districts(
                    district_names=collected_district_ids,
                    feature=feature_name
                )

                # 轉換成 StatisticalAreaDetail 物件列表
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
                # 如果取得統計區詳細資料失敗，退回到只 highlight 行政區
                highlight_areas = HighlightArea(
                    type="district",
                    ids=collected_district_ids
                )
        elif collected_district_ids:
            # 如果沒有特徵名稱（例如使用 filter_district_by_conditions），則只 highlight 行政區
            highlight_areas = HighlightArea(
                type="district",
                ids=collected_district_ids
            )

        # 第二次調用 OpenAI API（附帶 function 結果）
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


# 注意：不創建全局實例，因為需要 API key 才能初始化
