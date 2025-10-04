import { useState, useEffect, useCallback } from 'react';
import { getBuildingTilesetInfo, getBuildingMapboxUrl } from '../services/api';

/**
 * Building Data Hook
 * @param {Object} mapInstance - Map instance
 * @param {boolean} isStyleLoaded - Whether style is loaded
 * @returns {Object} Building data, source layer information, etc.
 */
export const useBuildingData = (mapInstance, isStyleLoaded) => {
  const [sourceLayerInfo, setSourceLayerInfo] = useState(null);
  const [buildingMapboxUrl, setBuildingMapboxUrl] = useState(null);
  const [customBuildingData, setCustomBuildingData] = useState(new Map());
  const [isInitialized, setIsInitialized] = useState(false);

  // Load and index custom building data from tileset
  const loadCustomBuildingData = useCallback(async (map, sourceLayer) => {
    // 僅在樣式載入完成且存在 buildings source 時執行；不再讀取私有欄位
    if (!map || !sourceLayer || !map.isStyleLoaded || !map.isStyleLoaded() || !map.getSource('buildings')) {
      return;
    }

    try {
      // 這裡不從 tiles 讀取私有資料，改為保守：初始化為空 Map，後續互動依現有屬性使用
      setCustomBuildingData(new Map());
    } catch (error) {
      console.error('Error during custom building data init:', error);
      setCustomBuildingData(new Map());
    }
  }, []);

  // Initialize source layers and custom building data
  const initializeBuildingData = useCallback(async (map) => {
    if (!map || isInitialized) {
      return;
    }

    try {
      const [buildingTilesetInfo, mapboxUrl] = await Promise.all([
        getBuildingTilesetInfo(),
        getBuildingMapboxUrl()
      ]);

      if (buildingTilesetInfo && Array.isArray(buildingTilesetInfo.vector_layers) && buildingTilesetInfo.vector_layers.length > 0) {
        const apiLayers = buildingTilesetInfo.vector_layers.map(layer => layer.id);
        setSourceLayerInfo(apiLayers);
        setBuildingMapboxUrl(mapboxUrl);

        setTimeout(() => {
          loadCustomBuildingData(map, apiLayers[0]);
          setIsInitialized(true);
        }, 1000);
        return;
      }
    } catch (error) {
      console.warn('Could not fetch building tileset info via backend API. Skipping private tiles inspection.', error);
    }

    // 若 API 不可用或沒有 vector_layers，則暫不嘗試任何私有 tiles fallback，僅設定已初始化避免重覆嘗試
    setIsInitialized(true);
  }, [isInitialized, loadCustomBuildingData]);

  // Auto-initialize when map and style are ready
  useEffect(() => {
    if (mapInstance && isStyleLoaded && !isInitialized) {
      setTimeout(() => {
        initializeBuildingData(mapInstance);
      }, 1000);
    }
  }, [mapInstance, isStyleLoaded, isInitialized, initializeBuildingData]);

  // Prepare building data source
  const buildingData = buildingMapboxUrl ? {
    type: 'vector',
    url: buildingMapboxUrl
  } : null;

  const detectedSourceLayer = sourceLayerInfo && sourceLayerInfo[0];
  const sourceLayerName = detectedSourceLayer || 'building_4326_minimized-c4mi1h';

  return {
    buildingData,
    sourceLayerName,
    customBuildingData,
    initializeBuildingData
  };
};
