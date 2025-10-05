import { useState, useEffect } from 'react';
import { getDistrictTilesetInfo, getDistrictMapboxUrl } from '../services/api';

/**
 * District Data Hook
 * @param {Object} mapInstance - Map instance
 * @param {boolean} isStyleLoaded - Whether style is loaded
 * @returns {Object} District source layer and Mapbox URL
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
      }
    };

    initializeDistrictData();
  }, [mapInstance, isStyleLoaded]);

  return {
    districtSourceLayer,
    districtMapboxUrl
  };
};
