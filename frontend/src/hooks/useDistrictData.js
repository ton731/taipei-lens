import { useState, useEffect } from 'react';
import { getDistrictTilesetInfo, getDistrictMapboxUrl } from '../services/api';

/**
 * 行政區資料 Hook
 * @param {Object} mapInstance - 地圖實例
 * @param {boolean} isStyleLoaded - 樣式是否載入完成
 * @returns {Object} 行政區 source layer 和 Mapbox URL
 */
export const useDistrictData = (mapInstance, isStyleLoaded) => {
  const [districtSourceLayer, setDistrictSourceLayer] = useState(null);
  const [districtMapboxUrl, setDistrictMapboxUrl] = useState(null);

  useEffect(() => {
    const initializeDistrictData = async () => {
      if (!mapInstance || !isStyleLoaded) return;

      try {
        const [districtInfo, mapboxUrl] = await Promise.all([
          getDistrictTilesetInfo(),
          getDistrictMapboxUrl()
        ]);

        if (districtInfo.vector_layers && districtInfo.vector_layers.length > 0) {
          const sourceLayerName = districtInfo.vector_layers[0].id;
          setDistrictSourceLayer(sourceLayerName);
          setDistrictMapboxUrl(mapboxUrl);
        }
      } catch (error) {
        console.error('Failed to initialize district data:', error);
      }
    };

    initializeDistrictData();
  }, [mapInstance, isStyleLoaded]);

  return {
    districtSourceLayer,
    districtMapboxUrl
  };
};
