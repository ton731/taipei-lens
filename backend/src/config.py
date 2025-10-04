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

    # JWT 配置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")

    # 環境配置
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")  # development 或 production，預設為 production

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

    def is_production(self) -> bool:
        """判斷是否為生產環境"""
        return self.ENVIRONMENT.lower() == "production"

    def is_development(self) -> bool:
        """判斷是否為開發環境"""
        return self.ENVIRONMENT.lower() == "development"

settings = Settings()