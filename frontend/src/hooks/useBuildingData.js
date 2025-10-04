import { useState, useEffect, useCallback } from 'react';
import { getBuildingTilesetInfo, getBuildingMapboxUrl } from '../services/api';

/**
 * 建築物資料 Hook
 * @param {Object} mapInstance - 地圖實例
 * @param {boolean} isStyleLoaded - 樣式是否載入完成
 * @returns {Object} 建築物資料、source layer 資訊等
 */
export const useBuildingData = (mapInstance, isStyleLoaded) => {
  const [sourceLayerInfo, setSourceLayerInfo] = useState(null);
  const [buildingMapboxUrl, setBuildingMapboxUrl] = useState(null);
  const [customBuildingData, setCustomBuildingData] = useState(new Map());
  const [isInitialized, setIsInitialized] = useState(false);

  // Load and index custom building data from tileset
  const loadCustomBuildingData = useCallback(async (map, sourceLayer) => {
    if (!map || !sourceLayer) {
      return;
    }

    try {
      const source = map.getSource('buildings');
      const sourceCache = map.style.sourceCaches?.['buildings'];

      if (sourceCache) {
        const buildingDataMap = new Map();
        let loadedCount = 0;

        Object.keys(sourceCache._tiles || {}).forEach(tileId => {
          const tile = sourceCache._tiles[tileId];
          if (tile && tile.vectorTile && tile.vectorTile.layers[sourceLayer]) {
            const layer = tile.vectorTile.layers[sourceLayer];

            for (let i = 0; i < layer.length; i++) {
              const feature = layer.feature(i);
              if (feature && feature.properties) {
                const properties = feature.properties;
                let key;

                if (properties.longitude && properties.latitude) {
                  key = `${properties.longitude}_${properties.latitude}`;
                } else {
                  const geometry = feature.loadGeometry()[0];
                  key = `${Math.round(geometry[0].x)}_${Math.round(geometry[0].y)}`;
                }

                buildingDataMap.set(key, properties);
                loadedCount++;
              }
            }
          }
        });

        // 即使沒有載入任何記錄，也要更新 state 來觸發 useMapInteractions
        setCustomBuildingData(buildingDataMap);
      } else {
        console.warn('Source cache not available for buildings source');
        // 設置一個空的 Map 來觸發後續流程
        setCustomBuildingData(new Map());
      }
    } catch (error) {
      console.error('Error loading custom building data:', error);
      // 即使有錯誤也要設置空 Map
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

      if (buildingTilesetInfo.vector_layers) {
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
      console.warn('Could not fetch building tileset info via backend API, trying tile inspection:', error);
    }

    // Fallback: inspect tiles for source layers
    const source = map.getSource('buildings');
    if (source) {
      const sourceCache = map.style.sourceCaches?.['buildings'];
      if (sourceCache) {
        const foundLayers = new Set();
        Object.keys(sourceCache._tiles || {}).forEach(tileId => {
          const tile = sourceCache._tiles[tileId];
          if (tile && tile.vectorTile) {
            const layerNames = Object.keys(tile.vectorTile.layers || {});
            layerNames.forEach(name => foundLayers.add(name));
          }
        });

        if (foundLayers.size > 0) {
          const layerArray = Array.from(foundLayers);
          setSourceLayerInfo(layerArray);

          setTimeout(() => {
            loadCustomBuildingData(map, layerArray[0]);
            setIsInitialized(true);
          }, 1000);
        }
      }
    }
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
