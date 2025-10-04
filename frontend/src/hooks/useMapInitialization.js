import { useState, useCallback } from 'react';

/**
 * Map Initialization Hook
 * @returns {Object} Map instance, style load status, initial view state, and load callback
 */
export const useMapInitialization = () => {
  const [mapInstance, setMapInstance] = useState(null);
  const [isStyleLoaded, setIsStyleLoaded] = useState(false);

  const mapboxPublicToken = import.meta.env.VITE_MAPBOX_ACCESS_PUBLIC_TOKEN;
  const styleUrl = import.meta.env.VITE_MAPBOX_STYLE_URL || 'mapbox://styles/mapbox/standard';

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

      // Hide default buildings from Mapbox Standard Style
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

          // Hide default buildings from Mapbox Standard Style
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
