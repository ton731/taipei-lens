import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Mapbox 配置
    MAPBOX_SECRET_TOKEN: str = os.getenv("MAPBOX_SECRET_TOKEN", "")
    MAPBOX_PUBLIC_TOKEN: str = os.getenv("MAPBOX_PUBLIC_TOKEN", "")
    MAPBOX_BUILDING_TILESET_ID: str = os.getenv("MAPBOX_BUILDING_TILESET_ID", "")
    MAPBOX_DISTRICT_TILESET_ID: str = os.getenv("MAPBOX_DISTRICT_TILESET_ID", "")  # 行政區
    MAPBOX_STATISTICAL_AREA_TILESET_ID: str = os.getenv("MAPBOX_STATISTICAL_AREA_TILESET_ID", "")  # 最小統計區域

    # OpenAI 配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # API 配置
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list = ["*"]

    # Mapbox API 配置
    MAPBOX_API_BASE: str = "https://api.mapbox.com"

    def validate_mapbox_tokens(self) -> bool:
        """驗證必要的 Mapbox tokens 與 tileset ID 是否存在"""
        if not self.MAPBOX_SECRET_TOKEN:
            raise ValueError("MAPBOX_SECRET_TOKEN environment variable is required")
        if not self.MAPBOX_BUILDING_TILESET_ID:
            raise ValueError("MAPBOX_BUILDING_TILESET_ID environment variable is required")
        if not self.MAPBOX_DISTRICT_TILESET_ID:
            raise ValueError("MAPBOX_DISTRICT_TILESET_ID environment variable is required")
        if not self.MAPBOX_STATISTICAL_AREA_TILESET_ID:
            raise ValueError("MAPBOX_STATISTICAL_AREA_TILESET_ID environment variable is required")
        return True

settings = Settings()