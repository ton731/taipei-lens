from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.config import settings
from src.routers import mapbox, llm

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 建立 FastAPI 應用
app = FastAPI(
    title="Taipei Lens Backend API",
    description="台北都市韌性規劃平台後端 API",
    version="1.0.0"
)

# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 包含路由
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