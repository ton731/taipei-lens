# -*- coding: utf-8 -*-
"""
LLM 相關的 API Router
"""
from fastapi import APIRouter, HTTPException, Depends
import logging
from openai import OpenAIError

from src.config import settings
from src.models.llm_models import ChatRequest, ChatResponse
from src.services.llm_service import ChatService
from src.security.auth import require_auth

router = APIRouter(prefix="/llm", tags=["llm"])
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, session: str = Depends(require_auth)) -> ChatResponse:
    """
    與 AI 聊天的端點，支援 function calling

    Args:
        request: 包含使用者問題的請求

    Returns:
        ChatResponse: AI 的回覆

    Raises:
        HTTPException: 當 API key 未設定或 OpenAI API 調用失敗時
    """
    try:
        # 驗證 OpenAI API key 是否存在
        if not settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY not configured")
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            )

        # 初始化 ChatService
        chat_service = ChatService(api_key=settings.OPENAI_API_KEY)

        # 調用 ChatService 處理聊天
        answer, model_used, highlight_areas = chat_service.chat(
            question=request.question,
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=1000
        )

        return ChatResponse(
            answer=answer,
            model=model_used,
            highlight_areas=highlight_areas
        )

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"OpenAI API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """檢查 LLM 服務健康狀態"""
    return {
        "status": "healthy" if settings.OPENAI_API_KEY else "unhealthy",
        "openai_configured": bool(settings.OPENAI_API_KEY)
    }
