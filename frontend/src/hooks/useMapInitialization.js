import { useState, useCallback } from 'react';

/**
 * Map Initialization Hook
 * @returns {Object} Map instance, style load status, initial view state, and load callback
 */
export const useMapInitialization = () => {
  const [mapInstance, setMapInstance] = useState(null);
  const [isStyleLoaded, setIsStyleLoaded] = useState(false);

  const mapboxPublicToken = import.meta.env.VITE_MAPBOX_ACCESS_PUBLIC_TOKEN;
  // 改為輕量樣式，降低初始化負擔
  const styleUrl = import.meta.env.VITE_MAPBOX_STYLE_URL || 'mapbox://styles/mapbox/light-v11';

  // 初始視角設為全球視角，避免載入台北建築資料
  const initialViewState = {
    longitude: 40,
    latitude: 25,
    zoom: 1,
    pitch: 0,
    bearing: 0
  };

  const onMapLoad = useCallback((event) => {
    const map = event.target;
    setMapInstance(map);

    // Check if style is already loaded
    if (map.isStyleLoaded && map.isStyleLoaded()) {
      setIsStyleLoaded(true);

      // 嘗試關閉 basemap 3D 物件以降低負擔（若可用）
      setTimeout(() => {
        if (map.getConfigProperty) {
          try { map.setConfigProperty('basemap', 'showBuildings', false); } catch (_) {}
          try { map.setConfigProperty('basemap', 'show3dObjects', false); } catch (_) {}
        }
      }, 100);
    } else {
      // Set up a fallback to check style load status
      const checkStyleLoaded = () => {
        if (map.isStyleLoaded && map.isStyleLoaded()) {
          setIsStyleLoaded(true);

          // 關閉 basemap 3D 物件
          if (map.getConfigProperty) {
            try { map.setConfigProperty('basemap', 'showBuildings', false); } catch (_) {}
            try { map.setConfigProperty('basemap', 'show3dObjects', false); } catch (_) {}
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
