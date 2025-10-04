# -*- coding: utf-8 -*-
"""
JWT 驗證核心模組 - 簡化版（匿名驗證）

此模組提供 JWT token 的生成、驗證和刷新功能
用於無需登入的匿名用戶驗證，保護後端 API
"""
import base64
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from jose import jwt, JWTError
from fastapi import HTTPException, status

from src.config import settings

# JWT 配置
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 60 分鐘
REFRESH_TOKEN_EXPIRE_HOURS = 6     # 12 小時


def get_jwt_secret() -> bytes:
    """
    從環境變數取得 JWT secret key

    Returns:
        bytes: 解碼後的 secret key

    Raises:
        ValueError: 當 JWT_SECRET_KEY 未設定時
    """
    secret = settings.JWT_SECRET_KEY
    if not secret:
        raise ValueError("JWT_SECRET_KEY environment variable not set")
    return base64.b64decode(secret.encode())


class JWTManager:
    """JWT Token 管理器"""

    def __init__(self):
        self.secret_key = get_jwt_secret()
        self.algorithm = JWT_ALGORITHM

    def create_access_token(self, session_id: str) -> str:
        """
        創建 access token（匿名用戶）

        Args:
            session_id: 匿名會話 ID（可以是隨機生成的 UUID）

        Returns:
            str: JWT access token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "session_id": session_id,
            "token_type": "access",
            "iat": now,        # issued at
            "exp": expire      # expiration time
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, session_id: str) -> str:
        """
        創建 refresh token

        Args:
            session_id: 匿名會話 ID

        Returns:
            str: JWT refresh token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)

        payload = {
            "session_id": session_id,
            "token_type": "refresh",
            "iat": now,
            "exp": expire
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        驗證並解碼 JWT token

        Args:
            token: JWT token 字串
            token_type: token 類型 ("access" 或 "refresh")

        Returns:
            Dict: Token payload

        Raises:
            HTTPException: Token 無效或過期
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 驗證 token 類型
            if payload.get("token_type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )


# 全域 JWT Manager 實例
jwt_manager = JWTManager()


def create_anonymous_token_pair(session_id: str) -> Dict[str, Any]:
    """
    為匿名用戶創建 token pair

    Args:
        session_id: 匿名會話 ID

    Returns:
        Dict: 包含 access_token 和 refresh_token 的字典
    """
    access_token = jwt_manager.create_access_token(session_id)
    refresh_token = jwt_manager.create_refresh_token(session_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 以秒為單位
    }


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    驗證 access token

    Args:
        token: JWT access token

    Returns:
        Dict: Token payload
    """
    return jwt_manager.verify_token(token, "access")


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """
    使用 refresh token 刷新 access token

    Args:
        refresh_token: JWT refresh token

    Returns:
        Dict: 新的 token pair
    """
    # 驗證 refresh token
    payload = jwt_manager.verify_token(refresh_token, "refresh")
    session_id = payload["session_id"]

    # 創建新的 access token（保留原有的 refresh token）
    new_access_token = jwt_manager.create_access_token(session_id)

    return {
        "access_token": new_access_token,
        "refresh_token": refresh_token,  # 重複使用現有的 refresh token
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }
