from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class VectorLayer(BaseModel):
    """向量圖層資訊"""
    id: str
    description: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None

class TilesetInfo(BaseModel):
    """Tileset 資訊回應模型"""
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    vector_layers: List[VectorLayer] = []

class APIError(BaseModel):
    """API 錯誤回應模型"""
    error: str
    detail: Optional[str] = None
    status_code: int