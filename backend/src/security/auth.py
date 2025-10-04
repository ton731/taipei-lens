# -*- coding: utf-8 -*-
"""
認證中介層模組

提供 FastAPI 的 JWT 認證依賴（Dependency）
所有需要保護的端點都使用這些依賴來驗證 JWT token
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.security.jwt_auth import verify_access_token

# HTTPBearer 自動從 Authorization: Bearer {token} 提取 token
security = HTTPBearer()


async def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    從 JWT token 取得當前匿名會話 ID

    Args:
        credentials: HTTP Bearer 憑證（由 FastAPI 自動注入）

    Returns:
        str: 會話 ID

    Raises:
        HTTPException: Token 無效或過期時
    """
    try:
        token = credentials.credentials
        payload = verify_access_token(token)
        return payload["session_id"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


def require_auth(session_id: str = Depends(get_current_session)) -> str:
    """
    要求 JWT 認證的依賴函數

    可在任何需要保護的路由中使用此依賴

    Args:
        session_id: 會話 ID（由 get_current_session 自動注入）

    Returns:
        str: 會話 ID

    Example:
        @router.get("/protected-endpoint")
        async def protected_route(session: str = Depends(require_auth)):
            return {"message": "This is a protected endpoint", "session": session}
    """
    return session_id
