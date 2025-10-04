import { useState, useCallback } from 'react';

/**
 * 地圖初始化 Hook
 * @returns {Object} 地圖實例、樣式載入狀態、初始視圖狀態和載入回調
 */
export const useMapInitialization = () => {
  const [mapInstance, setMapInstance] = useState(null);
  const [isStyleLoaded, setIsStyleLoaded] = useState(false);

  const mapboxPublicToken = import.meta.env.VITE_MAPBOX_ACCESS_PUBLIC_TOKEN;
  const styleUrl = import.meta.env.VITE_MAPBOX_STYLE_URL || 'mapbox://styles/mapbox/standard';

  const initialViewState = {
    longitude: parseFloat(import.meta.env.VITE_MAP_INITIAL_LONGITUDE) || 121.5654,
    latitude: parseFloat(import.meta.env.VITE_MAP_INITIAL_LATITUDE) || 25.0330,
    zoom: parseFloat(import.meta.env.VITE_MAP_INITIAL_ZOOM) || 16,
    pitch: parseFloat(import.meta.env.VITE_MAP_INITIAL_PITCH) || 45,
    bearing: parseFloat(import.meta.env.VITE_MAP_INITIAL_BEARING) || 0
  };

  const onMapLoad = useCallback((event) => {
    const map = event.target;
    setMapInstance(map);

    // Check if style is already loaded
    if (map.isStyleLoaded && map.isStyleLoaded()) {
      setIsStyleLoaded(true);

      // 隱藏 Mapbox Standard Style 的預設建築物
      setTimeout(() => {
        if (map.getConfigProperty) {
          map.setConfigProperty('basemap', 'showBuildings', false);
        }
      }, 100);
    } else {
      // Set up a fallback to check style load status
      const checkStyleLoaded = () => {
        if (map.isStyleLoaded && map.isStyleLoaded()) {
          setIsStyleLoaded(true);

          // 隱藏 Mapbox Standard Style 的預設建築物
          if (map.getConfigProperty) {
            map.setConfigProperty('basemap', 'showBuildings', false);
          }
        } else {
          setTimeout(checkStyleLoaded, 100);
        }
      };
      setTimeout(checkStyleLoaded, 100);
    }
  }, []);

  return {
    mapInstance,
    isStyleLoaded,
    setIsStyleLoaded,
    initialViewState,
    mapboxPublicToken,
    styleUrl,
    onMapLoad
  };
};
