import { useState, useEffect } from 'react';
import { getStatisticalAreaTilesetInfo, getStatisticalAreaMapboxUrl } from '../services/api';

/**
 * Statistical Area Data Hook
 * @param {Object} mapInstance - Map instance
 * @param {boolean} isStyleLoaded - Whether style is loaded
 * @returns {Object} Statistical area source layer and Mapbox URL
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
      }
    };

    initializeStatisticalAreaData();
  }, [mapInstance, isStyleLoaded]);

  return {
    statisticalAreaSourceLayer,
    statisticalAreaMapboxUrl
  };
};
