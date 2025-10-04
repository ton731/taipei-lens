# -*- coding: utf-8 -*-
"""
LLM 相關的資料模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class ChatRequest(BaseModel):
    """聊天請求模型"""
    question: str = Field(..., description="使用者的問題", min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "question": "台北市哪些行政區的高齡人口比例最高？請給我前5名。"
            }
        }


class StatisticalAreaDetail(BaseModel):
    """統計區詳細資訊"""
    CODEBASE: str = Field(..., description="統計區代碼")
    district: str = Field(..., description="所屬行政區名稱")
    value: float = Field(..., description="特徵數值")


class HighlightArea(BaseModel):
    """需要在地圖上高亮顯示的區域資訊"""
    type: Literal["district", "statistical_area"] = Field(..., description="區域類型：district（行政區）或 statistical_area（統計區域）")
    ids: List[str] = Field(..., description="區域的 ID 列表。行政區使用區域名稱，統計區域使用 CODEBASE")
    statistical_details: Optional[List[StatisticalAreaDetail]] = Field(None, description="當 type 為 district 時，包含該行政區內所有統計區的詳細資料（用於漸變色渲染）")
    feature: Optional[str] = Field(None, description="特徵名稱（統計區層級），用於前端判斷")
    min_value: Optional[float] = Field(None, description="特徵值的最小值，用於前端計算顏色範圍")
    max_value: Optional[float] = Field(None, description="特徵值的最大值，用於前端計算顏色範圍")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "district",
                "ids": ["萬華區", "信義區", "大安區"],
                "statistical_details": [
                    {"CODEBASE": "A6310-0024-00", "district": "大安區", "value": 5000},
                    {"CODEBASE": "A6310-0025-00", "district": "大安區", "value": 3000}
                ],
                "feature": "population",
                "min_value": 1000,
                "max_value": 8000
            }
        }


class ChatResponse(BaseModel):
    """聊天回應模型"""
    answer: str = Field(..., description="AI 的回覆")
    model: Optional[str] = Field(None, description="使用的模型名稱")
    highlight_areas: Optional[HighlightArea] = Field(None, description="需要在地圖上高亮的區域資訊，如果不需要高亮則為 None")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "台北市的都市更新重點區域主要包括...",
                "model": "gpt-4",
                "highlight_areas": {
                    "type": "district",
                    "ids": ["萬華區", "信義區"]
                }
            }
        }
