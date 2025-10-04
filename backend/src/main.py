from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.config import settings
from src.routers import mapbox, llm, auth

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 根據環境決定是否啟用 API 文檔
# Development: 顯示完整 API 文檔
# Production: 完全禁用文檔，提高安全性
ENABLE_DOCS = settings.is_development()

# 建立 FastAPI 應用
app = FastAPI(
    title="Taipei Lens Backend API",
    description="台北都市韌性規劃平台後端 API",
    version="1.0.0",
    docs_url="/docs" if ENABLE_DOCS else None,          # Swagger UI
    redoc_url="/redoc" if ENABLE_DOCS else None,        # ReDoc
    openapi_url="/openapi.json" if ENABLE_DOCS else None  # OpenAPI schema
)

# 記錄當前環境與文檔狀態
logger.info(f"Environment: {settings.ENVIRONMENT}")
logger.info(f"API Documentation: {'Enabled' if ENABLE_DOCS else 'Disabled'}")

# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(auth.router, prefix=settings.API_PREFIX)  # 認證路由（無需 JWT）
app.include_router(mapbox.router, prefix=settings.API_PREFIX)
app.include_router(llm.router, prefix=settings.API_PREFIX)

@app.get("/")
async def root():
    """根路徑健康檢查"""
    return {"message": "Taipei Lens Backend API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """詳細健康檢查"""
    try:
        settings.validate_mapbox_tokens()
        return {
            "status": "healthy",
            "service": "Taipei Lens Backend API",
            "version": "1.0.0",
            "mapbox_configured": True
        }
    except ValueError as e:
        return {
            "status": "unhealthy",
            "service": "Taipei Lens Backend API",
            "version": "1.0.0",
            "error": str(e),
            "mapbox_configured": False
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)