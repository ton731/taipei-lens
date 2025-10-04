import { useState, useCallback, useEffect } from 'react';

/**
 * 地圖互動 Hook - 處理滑鼠事件和 hover 效果
 * @param {Object} mapInstance - 地圖實例
 * @param {Map} customBuildingData - 自訂建築物資料
 * @param {string} statisticalAreaSourceLayer - 統計區域 source layer 名稱
 * @param {Function} externalSetHoverInfo - 外部的 setHoverInfo 函數（可選）
 * @returns {Object} hover 資訊、高亮建築物、設定互動函數
 */
export const useMapInteractions = (mapInstance, customBuildingData, statisticalAreaSourceLayer, externalSetHoverInfo = null) => {
  const [internalHoverInfo, setInternalHoverInfo] = useState(null);
  const [highlightedBuilding, setHighlightedBuilding] = useState(null);

  // 使用外部 setHoverInfo 或內部的
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
        const features = map.queryRenderedFeatures(e.point);

        // 先檢測是否有建築物
        const buildingFeatures = features.filter(f =>
          f.layer?.id === 'custom-3d-buildings' ||
          (f.properties &&
           (f.properties.height || f.properties.floor || f.properties.area || f.properties.levels || f.properties.building))
        );

        // 如果有建築物，優先顯示建築物資訊
        if (buildingFeatures.length > 0) {
          const feature = buildingFeatures[0];

          // 清除統計區域 hover state
          if (hoveredStatisticalAreaId !== null) {
            map.setFeatureState(
              { source: 'statistical-areas', sourceLayer: statisticalAreaSourceLayer, id: hoveredStatisticalAreaId },
              { hover: false }
            );
            hoveredStatisticalAreaId = null;
          }

          // 處理建築物 hover
          const customData = findMatchingCustomData(feature, e.lngLat);

          // 清除之前的建築物 hover state
          if (hoveredFeatureId !== null && hoveredSourceLayer !== null) {
            map.setFeatureState(
              { source: 'buildings', sourceLayer: hoveredSourceLayer, id: hoveredFeatureId },
              { hover: false }
            );
          }

          // 設定新的建築物 hover state
          if (feature.layer?.id === 'custom-3d-buildings' && feature.id !== undefined) {
            hoveredFeatureId = feature.id;
            hoveredSourceLayer = feature.sourceLayer;

            map.setFeatureState(
              { source: 'buildings', sourceLayer: feature.sourceLayer, id: feature.id },
              { hover: true }
            );
          } else {
            // 如果不是我們的 3D 建築物圖層，使用 2D highlight 作為備用
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

          // 處理 properties，解析 fragility_curve JSON 字符串
          const finalProperties = customData || feature.properties || {};
          
          // 如果 fragility_curve 是字符串，解析成物件
          if (finalProperties.fragility_curve && typeof finalProperties.fragility_curve === 'string') {
            try {
              finalProperties.fragility_curve = JSON.parse(finalProperties.fragility_curve);
              console.log('成功解析 fragility_curve:', finalProperties.fragility_curve);
            } catch (error) {
              console.error('解析 fragility_curve 失敗:', error);
            }
          }

          // 顯示建築物資訊
          setHoverInfo({
            longitude: e.lngLat.lng,
            latitude: e.lngLat.lat,
            properties: finalProperties,
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
          // 沒有建築物，檢測統計區域
          const statisticalAreaFeatures = features.filter(f =>
            f.source === 'statistical-areas'
          );

          if (statisticalAreaFeatures.length > 0) {
            const feature = statisticalAreaFeatures[0];

            // 清除之前的建築物 hover state
            if (hoveredFeatureId !== null && hoveredSourceLayer !== null) {
              map.setFeatureState(
                { source: 'buildings', sourceLayer: hoveredSourceLayer, id: hoveredFeatureId },
                { hover: false }
              );
              hoveredFeatureId = null;
              hoveredSourceLayer = null;
            }

            // 清除之前的統計區域 hover state
            if (hoveredStatisticalAreaId !== null) {
              map.setFeatureState(
                { source: 'statistical-areas', sourceLayer: statisticalAreaSourceLayer, id: hoveredStatisticalAreaId },
                { hover: false }
              );
            }

            // 設定新的統計區域 hover state
            if (feature.id !== undefined) {
              hoveredStatisticalAreaId = feature.id;
              map.setFeatureState(
                { source: 'statistical-areas', sourceLayer: feature.sourceLayer, id: feature.id },
                { hover: true }
              );
            }

            // 顯示統計區域資訊
            const props = feature.properties || {};
            setHoverInfo({
              longitude: e.lngLat.lng,
              latitude: e.lngLat.lat,
              feature: {
                type: 'district',
                properties: {
                  '行政區': props.TOWN || 'N/A',
                  '統計區代碼': props.CODEBASE || 'N/A',
                  '人口數': props.population ? props.population.toLocaleString() : 'N/A',
                  '戶數': props.household ? props.household.toLocaleString() : 'N/A',
                  '平均建築屋齡': props.avg_building_age ? `${Math.round(props.avg_building_age)} 年` : 'N/A',
                  '高齡人口比例': props.pop_elderly_percentage ? `${props.pop_elderly_percentage.toFixed(1)}%` : 'N/A',
                  '高齡中獨居比例': props.elderly_alone_percentage ? `${props.elderly_alone_percentage.toFixed(1)}%` : 'N/A',
                  '低收入比例': props.low_income_percentage ? `${props.low_income_percentage.toFixed(1)}%` : 'N/A'
                }
              }
            });

            map.getCanvas().style.cursor = 'pointer';
          } else {
            // 既沒有建築物也沒有統計區，清除所有 hover 效果
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
