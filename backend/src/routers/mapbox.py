# -*- coding: utf-8 -*-
"""
Mapbox 相關的 API Router
"""
from fastapi import APIRouter, HTTPException, Response
import logging

from src.config import settings
from src.models.mapbox_models import TilesetInfo
from src.services.mapbox_service import MapboxService

router = APIRouter(prefix="/mapbox", tags=["mapbox"])
logger = logging.getLogger(__name__)


def _get_mapbox_service() -> MapboxService:
    """
    取得 MapboxService 實例（內部輔助函數）

    Returns:
        MapboxService 實例

    Raises:
        HTTPException: 當設定參數缺失時
    """
    try:
        settings.validate_mapbox_tokens()
        return MapboxService(
            api_base=settings.MAPBOX_API_BASE,
            secret_token=settings.MAPBOX_SECRET_TOKEN,
            building_tileset_id=settings.MAPBOX_BUILDING_TILESET_ID,
            district_tileset_id=settings.MAPBOX_DISTRICT_TILESET_ID,
            statistical_area_tileset_id=settings.MAPBOX_STATISTICAL_AREA_TILESET_ID
        )
    except ValueError as e:
        logger.error(f"Mapbox configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/building-mapbox-url")
async def get_building_mapbox_url():
    """回傳建築物 tileset 的 mapbox:// URL（包含 tileset ID）"""
    try:
        service = _get_mapbox_service()
        return service.get_tileset_url("building")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting building mapbox URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/building-tileset-info", response_model=TilesetInfo)
async def get_building_tileset_info() -> TilesetInfo:
    """獲取建築物 Mapbox tileset 資訊（不暴露 tileset ID）"""
    service = _get_mapbox_service()
    return await service.get_tileset_info("building")


@router.get("/building-tiles/{z}/{x}/{y}.pbf")
async def get_building_tile(z: int, x: int, y: int) -> Response:
    """代理建築物 Mapbox vector tiles 請求（不暴露 tileset ID）"""
    service = _get_mapbox_service()
    return await service.get_tile("building", z, x, y)


@router.get("/district-mapbox-url")
async def get_district_mapbox_url():
    """回傳行政區 tileset 的 mapbox:// URL（包含 tileset ID）"""
    try:
        service = _get_mapbox_service()
        return service.get_tileset_url("district")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting district mapbox URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/district-tileset-info", response_model=TilesetInfo)
async def get_district_tileset_info() -> TilesetInfo:
    """獲取行政區 Mapbox tileset 資訊（不暴露 tileset ID）"""
    service = _get_mapbox_service()
    return await service.get_tileset_info("district")


@router.get("/district-tiles/{z}/{x}/{y}.pbf")
async def get_district_tile(z: int, x: int, y: int) -> Response:
    """代理行政區 Mapbox vector tiles 請求（不暴露 tileset ID）"""
    service = _get_mapbox_service()
    return await service.get_tile("district", z, x, y)


@router.get("/statistical-area-mapbox-url")
async def get_statistical_area_mapbox_url():
    """回傳最小統計區域 tileset 的 mapbox:// URL（包含 tileset ID）"""
    try:
        service = _get_mapbox_service()
        return service.get_tileset_url("statistical_area")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistical area mapbox URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistical-area-tileset-info", response_model=TilesetInfo)
async def get_statistical_area_tileset_info() -> TilesetInfo:
    """獲取最小統計區域 Mapbox tileset 資訊（不暴露 tileset ID）"""
    service = _get_mapbox_service()
    return await service.get_tileset_info("statistical_area")


@router.get("/statistical-area-tiles/{z}/{x}/{y}.pbf")
async def get_statistical_area_tile(z: int, x: int, y: int) -> Response:
    """代理最小統計區域 Mapbox vector tiles 請求（不暴露 tileset ID）"""
    service = _get_mapbox_service()
    return await service.get_tile("statistical_area", z, x, y)



@router.get("/health")
async def health_check():
    """健康檢查端點"""
    try:
        _get_mapbox_service()
        return {"status": "healthy", "mapbox_configured": True}
    except HTTPException as e:
        return {"status": "unhealthy", "error": e.detail, "mapbox_configured": False}