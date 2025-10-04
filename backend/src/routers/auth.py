# -*- coding: utf-8 -*-
"""
認證 API Router

提供匿名 JWT token 的獲取和刷新端點
"""
import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import logging

from src.security.jwt_auth import create_anonymous_token_pair, refresh_access_token

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


class RefreshTokenRequest(BaseModel):
    """刷新 token 請求"""
    refresh_token: str


class TokenResponse(BaseModel):
    """Token 回應"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


@router.post("/anonymous", response_model=TokenResponse)
async def get_anonymous_token() -> TokenResponse:
    """
    為匿名用戶獲取 JWT token pair

    此端點無需任何認證，任何人都可以調用
    每次調用都會生成一個新的匿名會話 ID

    Returns:
        TokenResponse: 包含 access_token 和 refresh_token
    """
    try:
        # 生成隨機的會話 ID
        session_id = str(uuid.uuid4())

        # 創建 token pair
        tokens = create_anonymous_token_pair(session_id)

        logger.info(f"Generated anonymous token for session: {session_id}")

        return TokenResponse(**tokens)

    except Exception as e:
        logger.error(f"Error generating anonymous token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate token"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest) -> TokenResponse:
    """
    刷新 access token

    使用有效的 refresh_token 來獲取新的 access_token
    refresh_token 會被重複使用

    Args:
        request: 包含 refresh_token 的請求

    Returns:
        TokenResponse: 新的 access_token 和原有的 refresh_token

    Raises:
        HTTPException: 當 refresh_token 無效或過期時
    """
    try:
        # 刷新 access token
        tokens = refresh_access_token(request.refresh_token)

        logger.info("Access token refreshed successfully")

        return TokenResponse(**tokens)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@router.get("/health")
async def health_check():
    """檢查認證服務健康狀態"""
    return {
        "status": "healthy",
        "service": "authentication"
    }
