# -*- coding: utf-8 -*-
"""
Mapbox 服務：處理 Mapbox API 代理邏輯
"""
import httpx
import logging
from typing import Dict, Any, Tuple
from fastapi import HTTPException, Response

from src.models.mapbox_models import TilesetInfo, VectorLayer

logger = logging.getLogger(__name__)


class MapboxService:
    """Mapbox 服務類別，負責處理 Mapbox API 的代理請求"""

    def __init__(
        self,
        api_base: str,
        secret_token: str,
        building_tileset_id: str,
        district_tileset_id: str,
        statistical_area_tileset_id: str
    ):
        """
        初始化 MapboxService

        Args:
            api_base: Mapbox API 基礎 URL
            secret_token: Mapbox secret token
            building_tileset_id: 建築物 tileset ID
            district_tileset_id: 行政區 tileset ID
            statistical_area_tileset_id: 最小統計區域 tileset ID

        Raises:
            ValueError: 當必要參數為空時
        """
        if not secret_token:
            raise ValueError("Mapbox secret token is required")

        self.api_base = api_base
        self.secret_token = secret_token
        self.tilesets = {
            "building": building_tileset_id,
            "district": district_tileset_id,
            "statistical_area": statistical_area_tileset_id
        }

        # 驗證所有 tileset ID 都已設定
        for tileset_type, tileset_id in self.tilesets.items():
            if not tileset_id:
                raise ValueError(f"Mapbox {tileset_type} tileset ID is required")

        # logger.info("MapboxService initialized")

    def get_tileset_url(self, tileset_type: str) -> Dict[str, str]:
        """
        取得 tileset 的 mapbox:// URL

        Args:
            tileset_type: tileset 類型 ("building", "district", "statistical_area")

        Returns:
            包含 URL 的字典

        Raises:
            ValueError: 當 tileset_type 無效時
        """
        tileset_id = self._get_tileset_id(tileset_type)
        # logger.info(f"Returning tileset URL for {tileset_type}")
        return {"url": f"mapbox://{tileset_id}"}

    async def get_tileset_info(self, tileset_type: str) -> TilesetInfo:
        """
        獲取 tileset 資訊（不暴露 tileset ID）

        Args:
            tileset_type: tileset 類型 ("building", "district", "statistical_area")

        Returns:
            TilesetInfo 物件

        Raises:
            HTTPException: 當 API 請求失敗時
        """
        tileset_id = self._get_tileset_id(tileset_type)
        url = f"{self.api_base}/tilesets/v1/{tileset_id}"
        params = {"access_token": self.secret_token}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)

                # 處理各種錯誤狀態
                if response.status_code == 404:
                    raise HTTPException(status_code=404, detail=f"{tileset_type} tileset not found")
                elif response.status_code == 401:
                    raise HTTPException(status_code=401, detail="Invalid Mapbox secret token")
                elif not response.is_success:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Mapbox API error: {response.text}"
                    )

                data = response.json()

                # 轉換 vector_layers 格式
                vector_layers = []
                if "vector_layers" in data:
                    for layer in data["vector_layers"]:
                        vector_layers.append(VectorLayer(
                            id=layer.get("id", ""),
                            description=layer.get("description"),
                            fields=layer.get("fields", {})
                        ))

                # 返回資訊但不包含實際 tileset ID（安全性考量）
                # logger.info(f"Successfully fetched tileset info for {tileset_type}")
                return TilesetInfo(
                    id=tileset_type,  # 使用通用名稱而非實際 tileset ID
                    name=data.get("name"),
                    description=data.get("description"),
                    vector_layers=vector_layers
                )

        except httpx.RequestError as e:
            logger.error(f"Network error when fetching {tileset_type} tileset info: {e}")
            raise HTTPException(status_code=503, detail="Unable to connect to Mapbox API")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error when fetching {tileset_type} tileset info: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_tile(self, tileset_type: str, z: int, x: int, y: int) -> Response:
        """
        代理 Mapbox vector tiles 請求（不暴露 tileset ID）

        Args:
            tileset_type: tileset 類型 ("building", "district", "statistical_area")
            z: 縮放等級
            x: X 座標
            y: Y 座標

        Returns:
            FastAPI Response 物件

        Raises:
            HTTPException: 當 API 請求失敗時
        """
        tileset_id = self._get_tileset_id(tileset_type)
        url = f"{self.api_base}/v4/{tileset_id}/{z}/{x}/{y}.vector.pbf"
        params = {"access_token": self.secret_token}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)

                # 處理 404（tile 不存在）
                if response.status_code == 404:
                    # 404 是正常情況，表示該 tile 不存在，回傳空的 tile
                    logger.debug(f"Tile not found for {tileset_type} at {z}/{x}/{y}")
                    return Response(
                        content=b"",
                        media_type="application/x-protobuf",
                        status_code=204  # No Content
                    )

                # 處理其他錯誤
                elif response.status_code == 401:
                    raise HTTPException(status_code=401, detail="Invalid Mapbox secret token")
                elif not response.is_success:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Mapbox API error: {response.status_code}"
                    )

                # 回傳原始的 protobuf 資料
                logger.debug(f"Successfully fetched tile for {tileset_type} at {z}/{x}/{y}")
                return Response(
                    content=response.content,
                    media_type="application/x-protobuf",
                    headers={
                        "Content-Encoding": "gzip" if "gzip" in response.headers.get("content-encoding", "") else "",
                        "Cache-Control": "public, max-age=86400"  # 快取 1 天
                    }
                )

        except httpx.RequestError as e:
            logger.error(f"Network error when fetching {tileset_type} tile: {e}")
            raise HTTPException(status_code=503, detail="Unable to connect to Mapbox API")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error when fetching {tileset_type} tile: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def _get_tileset_id(self, tileset_type: str) -> str:
        """
        取得 tileset ID（私有方法）

        Args:
            tileset_type: tileset 類型

        Returns:
            tileset ID

        Raises:
            ValueError: 當 tileset_type 無效時
        """
        if tileset_type not in self.tilesets:
            raise ValueError(f"Invalid tileset type: {tileset_type}. Must be one of {list(self.tilesets.keys())}")

        return self.tilesets[tileset_type]


# 注意：不創建全局實例，因為需要設定參數才能初始化
