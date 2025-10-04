import { useState, useEffect } from 'react';
import { getStatisticalAreaTilesetInfo, getStatisticalAreaMapboxUrl } from '../services/api';

/**
 * 最小統計區域資料 Hook
 * @param {Object} mapInstance - 地圖實例
 * @param {boolean} isStyleLoaded - 樣式是否載入完成
 * @returns {Object} 統計區域 source layer 和 Mapbox URL
 */
export const useStatisticalAreaData = (mapInstance, isStyleLoaded) => {
  const [statisticalAreaSourceLayer, setStatisticalAreaSourceLayer] = useState(null);
  const [statisticalAreaMapboxUrl, setStatisticalAreaMapboxUrl] = useState(null);

  useEffect(() => {
    const initializeStatisticalAreaData = async () => {
      if (!mapInstance || !isStyleLoaded) return;

      try {
        const [statisticalAreaInfo, mapboxUrl] = await Promise.all([
          getStatisticalAreaTilesetInfo(),
          getStatisticalAreaMapboxUrl()
        ]);

        if (statisticalAreaInfo.vector_layers && statisticalAreaInfo.vector_layers.length > 0) {
          const sourceLayerName = statisticalAreaInfo.vector_layers[0].id;
          setStatisticalAreaSourceLayer(sourceLayerName);
          setStatisticalAreaMapboxUrl(mapboxUrl);
        }
      } catch (error) {
        console.error('Failed to initialize statistical area data:', error);
      }
    };

    initializeStatisticalAreaData();
  }, [mapInstance, isStyleLoaded]);

  return {
    statisticalAreaSourceLayer,
    statisticalAreaMapboxUrl
  };
};
