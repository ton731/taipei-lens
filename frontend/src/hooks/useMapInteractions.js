import { useState, useCallback, useEffect } from 'react';

/**
 * Map Interactions Hook - Handles mouse events and hover effects
 * @param {Object} mapInstance - Map instance
 * @param {Map} customBuildingData - Custom building data
 * @param {string} statisticalAreaSourceLayer - Statistical area source layer name
 * @param {Function} externalSetHoverInfo - External setHoverInfo function (optional)
 * @returns {Object} Hover info, highlighted building, setup interaction function
 */
export const useMapInteractions = (mapInstance, customBuildingData, statisticalAreaSourceLayer, externalSetHoverInfo = null) => {
  const [internalHoverInfo, setInternalHoverInfo] = useState(null);
  const [highlightedBuilding, setHighlightedBuilding] = useState(null);

  // Use external setHoverInfo or internal one
  const setHoverInfo = externalSetHoverInfo || setInternalHoverInfo;
  const hoverInfo = externalSetHoverInfo ? undefined : internalHoverInfo;

  // Function to find matching custom data for a hovered building
  const findMatchingCustomData = useCallback((feature, lngLat) => {
    if (!customBuildingData || !customBuildingData.size) return null;

    let closestData = null;
    let minDistance = Infinity;

    customBuildingData.forEach((data, key) => {
      if (data.longitude && data.latitude) {
        const distance = Math.sqrt(
          Math.pow(data.longitude - lngLat.lng, 2) +
          Math.pow(data.latitude - lngLat.lat, 2)
        );

        if (distance < minDistance && distance < 0.0001) {
          minDistance = distance;
          closestData = data;
        }
      }
    });

    return closestData;
  }, [customBuildingData]);

  // Setup enhanced building interactions with highlight effects
  const setupBuildingInteractions = useCallback((map) => {

    let hoveredFeatureId = null;
    let hoveredSourceLayer = null;
    let hoveredStatisticalAreaId = null;

    setTimeout(() => {
      const style = map.getStyle();
      const layers = style.layers || [];

      const allLayers = layers.map(l => ({ id: l.id, type: l.type, source: l.source }));

      // Mouse move handler for hover effects and highlighting
      const onMouseMove = (e) => {
        // 地圖尚未載入完成或正在移動時，不進行昂貴的查詢，避免在動畫/樣式更新期間觸發渲染重算
        if (!map.isStyleLoaded || !map.isStyleLoaded() || (map.isMoving && map.isMoving())) {
          return;
        }

        const features = map.queryRenderedFeatures(e.point);

        // First check if there are buildings
        const buildingFeatures = features.filter(f =>
          f.layer?.id === 'custom-3d-buildings' ||
          (f.properties &&
           (f.properties.height || f.properties.floor || f.properties.area || f.properties.levels || f.properties.building))
        );

        // If there are buildings, prioritize showing building information
        if (buildingFeatures.length > 0) {
          const feature = buildingFeatures[0];

          // Clear statistical area hover state
          if (hoveredStatisticalAreaId !== null) {
            map.setFeatureState(
              { source: 'statistical-areas', sourceLayer: statisticalAreaSourceLayer, id: hoveredStatisticalAreaId },
              { hover: false }
            );
            hoveredStatisticalAreaId = null;
          }

          // Handle building hover
          const customData = findMatchingCustomData(feature, e.lngLat);

          // Clear previous building hover state
          if (hoveredFeatureId !== null && hoveredSourceLayer !== null) {
            map.setFeatureState(
              { source: 'buildings', sourceLayer: hoveredSourceLayer, id: hoveredFeatureId },
              { hover: false }
            );
          }

          // Set new building hover state
          if (feature.layer?.id === 'custom-3d-buildings' && feature.id !== undefined) {
            hoveredFeatureId = feature.id;
            hoveredSourceLayer = feature.sourceLayer;

            map.setFeatureState(
              { source: 'buildings', sourceLayer: feature.sourceLayer, id: feature.id },
              { hover: true }
            );
          } else {
            // If not our 3D building layer, use 2D highlight as fallback
            if (feature.geometry && feature.geometry.coordinates) {
              const highlightFeature = {
                type: 'Feature',
                geometry: feature.geometry,
                properties: {
                  ...feature.properties,
                  isHighlighted: true
                }
              };

              setHighlightedBuilding({
                type: 'FeatureCollection',
                features: [highlightFeature]
              });
            }
          }

          // Display building information
          setHoverInfo({
            longitude: e.lngLat.lng,
            latitude: e.lngLat.lat,
            properties: customData || feature.properties || {},
            isCustomData: !!customData,
            layerInfo: {
              id: feature.layer?.id,
              type: feature.layer?.type,
              source: feature.source,
              sourceLayer: feature.sourceLayer
            }
          });

          map.getCanvas().style.cursor = 'pointer';
        } else {
          // No buildings, check for statistical areas
          const statisticalAreaFeatures = features.filter(f =>
            f.source === 'statistical-areas'
          );

          if (statisticalAreaFeatures.length > 0) {
            const feature = statisticalAreaFeatures[0];

            // Clear previous building hover state
            if (hoveredFeatureId !== null && hoveredSourceLayer !== null) {
              map.setFeatureState(
                { source: 'buildings', sourceLayer: hoveredSourceLayer, id: hoveredFeatureId },
                { hover: false }
              );
              hoveredFeatureId = null;
              hoveredSourceLayer = null;
            }

            // Clear previous statistical area hover state
            if (hoveredStatisticalAreaId !== null) {
              map.setFeatureState(
                { source: 'statistical-areas', sourceLayer: statisticalAreaSourceLayer, id: hoveredStatisticalAreaId },
                { hover: false }
              );
            }

            // Set new statistical area hover state
            if (feature.id !== undefined) {
              hoveredStatisticalAreaId = feature.id;
              map.setFeatureState(
                { source: 'statistical-areas', sourceLayer: feature.sourceLayer, id: feature.id },
                { hover: true }
              );
            }

            // Display statistical area information
            const props = feature.properties || {};
            setHoverInfo({
              longitude: e.lngLat.lng,
              latitude: e.lngLat.lat,
              feature: {
                type: 'district',
                properties: {
                  'District': props.TOWN || 'N/A',
                  'Statistical Area Code': props.CODEBASE || 'N/A',
                  'Population': props.population ? props.population.toLocaleString() : 'N/A',
                  'Households': props.household ? props.household.toLocaleString() : 'N/A',
                  'Avg Building Age': props.avg_building_age ? `${Math.round(props.avg_building_age)} years` : 'N/A',
                  'Elderly Ratio': props.pop_elderly_percentage ? `${props.pop_elderly_percentage.toFixed(1)}%` : 'N/A',
                  'Elderly Living Alone Ratio': props.elderly_alone_percentage ? `${props.elderly_alone_percentage.toFixed(1)}%` : 'N/A',
                  'Low Income Ratio': props.low_income_percentage ? `${props.low_income_percentage.toFixed(1)}%` : 'N/A'
                }
              }
            });

            map.getCanvas().style.cursor = 'pointer';
          } else {
            // Neither buildings nor statistical areas, clear all hover effects
            if (hoveredFeatureId !== null && hoveredSourceLayer !== null) {
              map.setFeatureState(
                { source: 'buildings', sourceLayer: hoveredSourceLayer, id: hoveredFeatureId },
                { hover: false }
              );
              hoveredFeatureId = null;
              hoveredSourceLayer = null;
            }

            if (hoveredStatisticalAreaId !== null) {
              map.setFeatureState(
                { source: 'statistical-areas', sourceLayer: statisticalAreaSourceLayer, id: hoveredStatisticalAreaId },
                { hover: false }
              );
              hoveredStatisticalAreaId = null;
            }

            setHighlightedBuilding(null);
            setHoverInfo(null);
            map.getCanvas().style.cursor = '';
          }
        }
      };

      // Mouse leave handler
      const onMouseLeave = () => {
        if (hoveredFeatureId !== null && hoveredSourceLayer !== null) {
          map.setFeatureState(
            { source: 'buildings', sourceLayer: hoveredSourceLayer, id: hoveredFeatureId },
            { hover: false }
          );
          hoveredFeatureId = null;
          hoveredSourceLayer = null;
        }

        if (hoveredStatisticalAreaId !== null) {
          map.setFeatureState(
            { source: 'statistical-areas', sourceLayer: statisticalAreaSourceLayer, id: hoveredStatisticalAreaId },
            { hover: false }
          );
          hoveredStatisticalAreaId = null;
        }

        setHighlightedBuilding(null);
        setHoverInfo(null);
        map.getCanvas().style.cursor = '';
      };

      // Remove existing listeners to avoid duplicates
      map.off('mousemove', onMouseMove);
      map.off('mouseleave', onMouseLeave);

      // Add new listeners
      map.on('mousemove', onMouseMove);
      map.on('mouseleave', onMouseLeave);

    }, 1000);
  }, [customBuildingData, findMatchingCustomData, statisticalAreaSourceLayer, setHoverInfo]);

  // Auto-setup interactions when map and data are ready
  useEffect(() => {
    if (mapInstance && customBuildingData !== null) {
      setupBuildingInteractions(mapInstance);
    }
  }, [mapInstance, customBuildingData, setupBuildingInteractions]);

  return {
    hoverInfo,
    highlightedBuilding
  };
};
