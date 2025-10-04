import React, { useState, useCallback, useEffect } from 'react';
import { Map as MapboxMap, Popup } from 'react-map-gl/mapbox';
import 'mapbox-gl/dist/mapbox-gl.css';

// Components
import LoadingOverlay from './components/LoadingOverlay';
import ToolboxPanel from './components/toolbox/ToolboxPanel';
import MapTitle from './components/map/MapTitle';
import MapLayers from './components/map/MapLayers';
import BuildingPopup from './components/map/BuildingPopup';
import DistrictPopup from './components/map/DistrictPopup';

// Hooks
import { useMapInitialization } from './hooks/useMapInitialization';
import { useBuildingData } from './hooks/useBuildingData';
import { useDistrictData } from './hooks/useDistrictData';
import { useStatisticalAreaData } from './hooks/useStatisticalAreaData';
import { useMapInteractions } from './hooks/useMapInteractions';

// Config
import { LAYER_CONFIGS, generateLegendGradient } from './config/layerConfig';

const MapComponent = ({ hoverInfo: externalHoverInfo, setHoverInfo: externalSetHoverInfo, llmHighlightAreas, clearLlmHighlight }) => {
  // 圖層選擇狀態
  const [selectedDataLayer, setSelectedDataLayer] = useState(null);
  const [activeLegends, setActiveLegends] = useState([]);

  // 通用分析結果狀態 - 儲存所有模組的分析結果
  const [analysisResults, setAnalysisResults] = useState({
    test: null,
    roadGreening: null,
    seismicStrengthening: null,
    parkSiting: null,
    urbanRenewal: null
  });

  // 模組配置狀態 - 儲存所有模組的權重和閥值配置
  const [moduleConfigs, setModuleConfigs] = useState({
    test: {
      weights: { building_age: 0.5, pop_density: 0.5 },
      threshold: 0.7
    },
    roadGreening: {
      weights: { surface_temp: 0.4, inverse_green_cover: 0.3, pop_density: 0.3 },
      threshold: 0.8
    },
    seismicStrengthening: {
      weights: { building_age: 0.5, structural_vulnerability: 0.3, liquefaction: 0.2 },
      threshold: 0.75
    },
    parkSiting: {
      weights: { inverse_green_service: 0.5, pop_density: 0.3, social_vulnerability: 0.2 },
      threshold: 0.8
    },
    urbanRenewal: {
      weights: { seismic_risk: 0.4, heat_island: 0.3, inverse_land_efficiency: 0.3 },
      threshold: 0.85
    }
  });

  // 使用 custom hooks
  const {
    mapInstance,
    isStyleLoaded,
    setIsStyleLoaded,
    initialViewState,
    mapboxPublicToken,
    styleUrl,
    onMapLoad
  } = useMapInitialization();

  const { districtSourceLayer, districtMapboxUrl } = useDistrictData(mapInstance, isStyleLoaded);

  const { statisticalAreaSourceLayer, statisticalAreaMapboxUrl } = useStatisticalAreaData(mapInstance, isStyleLoaded);

  const {
    buildingData,
    sourceLayerName,
    customBuildingData
  } = useBuildingData(mapInstance, isStyleLoaded);

  const {
    hoverInfo,
    highlightedBuilding
  } = useMapInteractions(mapInstance, customBuildingData, statisticalAreaSourceLayer, externalSetHoverInfo || null);

  // 使用外部 hoverInfo 如果提供了，否則使用內部的
  const actualHoverInfo = externalHoverInfo !== undefined ? externalHoverInfo : hoverInfo;

  // 處理來自 DataLayersModule 的圖層變化
  const handleDataLayerChange = useCallback((layerId) => {
    setSelectedDataLayer(layerId);

    // 當開啟圖層時，清除 AI highlight
    if (layerId && clearLlmHighlight) {
      clearLlmHighlight();
    }
  }, [clearLlmHighlight]);

  // 通用分析執行回調 - 所有模組共用
  const handleAnalysisExecute = useCallback((moduleId, highlightedCodes) => {
    console.log(`[${moduleId}] Analysis executed. Highlighted districts:`, highlightedCodes.length);
    setAnalysisResults(prev => ({
      ...prev,
      [moduleId]: highlightedCodes
    }));

    // 當執行分析時，清除 AI highlight
    if (clearLlmHighlight) {
      clearLlmHighlight();
    }
  }, [clearLlmHighlight]);

  // 通用分析清除回調 - 所有模組共用
  const handleAnalysisClear = useCallback((moduleId) => {
    setAnalysisResults(prev => ({
      ...prev,
      [moduleId]: null
    }));
  }, []);

  // 清除原始數據圖層選擇 - 當執行分析時調用
  const handleClearDataLayer = useCallback(() => {
    setSelectedDataLayer(null);
  }, []);

  // 更新模組配置 - 所有模組共用
  const handleModuleConfigChange = useCallback((moduleId, config) => {
    setModuleConfigs(prev => ({
      ...prev,
      [moduleId]: { ...prev[moduleId], ...config }
    }));
  }, []);

  // 處理 LLM highlight areas
  useEffect(() => {
    if (llmHighlightAreas) {
      console.log('LLM highlight areas received:', llmHighlightAreas);

      // 當 AI highlight 出現時，清除所有 Toolbox 的圖層和分析結果
      setSelectedDataLayer(null);
      setAnalysisResults({
        test: null,
        roadGreening: null,
        seismicStrengthening: null,
        parkSiting: null,
        urbanRenewal: null,
        llm: llmHighlightAreas
      });

    } else {
      // 清除 LLM highlight
      setAnalysisResults(prev => ({
        ...prev,
        llm: null
      }));
    }
  }, [llmHighlightAreas]);

  // 處理圖層選擇變化並更新圖例
  useEffect(() => {
    if (!selectedDataLayer) {
      setActiveLegends([]);
      return;
    }

    const config = LAYER_CONFIGS[selectedDataLayer];
    if (config) {
      setActiveLegends([{
        title: config.title,
        type: 'gradient',
        gradient: generateLegendGradient(config),
        minLabel: `${config.minValue}${config.unit}`,
        maxLabel: `${config.maxValue.toLocaleString()}${config.unit}`
      }]);
    }
  }, [selectedDataLayer]);

  if (!mapboxPublicToken) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '18px',
        color: '#666'
      }}>
        請在 .env 檔案中設定 VITE_MAPBOX_ACCESS_PUBLIC_TOKEN
      </div>
    );
  }

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <LoadingOverlay isLoading={!isStyleLoaded} />

      <MapboxMap
        mapboxAccessToken={mapboxPublicToken}
        initialViewState={initialViewState}
        style={{ width: '100%', height: '100%' }}
        mapStyle={styleUrl}
        maxBounds={[
          [121.46, 24.95],  // 西南角 [經度, 緯度]
          [121.67, 25.20]   // 東北角 [經度, 緯度]
        ]}
        mapConfig={{
          basemap: {
            show3dObjects: true,
            lightPreset: 'day'
          }
        }}
        onError={(error) => {
          // console.error('Mapbox detailed error:', {
          //   message: error.message,
          //   stack: error.stack,
          //   source: error.source,
          //   layer: error.layer
          // });
        }}
        onLoad={onMapLoad}
        onStyleLoad={(event) => {
          setIsStyleLoaded(true);
        }}
        onStyleData={(event) => {
          if (event && event.dataType === 'style') {
            setTimeout(() => {
              if (mapInstance && mapInstance.isStyleLoaded && mapInstance.isStyleLoaded()) {
                setIsStyleLoaded(true);
              }
            }, 100);
          }
        }}
        onSourceData={(e) => {
          if (e.sourceId === 'buildings') {
          }
        }}
      >
        {/* 地圖圖層 */}
        {isStyleLoaded && (
          <MapLayers
            buildingData={buildingData}
            sourceLayerName={sourceLayerName}
            districtSourceLayer={districtSourceLayer}
            districtMapboxUrl={districtMapboxUrl}
            statisticalAreaSourceLayer={statisticalAreaSourceLayer}
            statisticalAreaMapboxUrl={statisticalAreaMapboxUrl}
            selectedDataLayer={selectedDataLayer}
            highlightedBuilding={highlightedBuilding}
            analysisResults={analysisResults}
          />
        )}

        {/* 地圖標題 */}
        <MapTitle />

        {/* 工具箱面板 */}
        <ToolboxPanel
          onMouseEnter={() => externalSetHoverInfo(null)}
          onDataLayerChange={handleDataLayerChange}
          activeLegends={activeLegends}
          selectedDataLayer={selectedDataLayer}
          mapInstance={mapInstance}
          districtSourceLayer={districtSourceLayer}
          statisticalAreaSourceLayer={statisticalAreaSourceLayer}
          onAnalysisExecute={handleAnalysisExecute}
          onAnalysisClear={handleAnalysisClear}
          onClearDataLayer={handleClearDataLayer}
          moduleConfigs={moduleConfigs}
          onModuleConfigChange={handleModuleConfigChange}
          analysisResults={analysisResults}
        />

        {/* Hover Popup */}
        {actualHoverInfo && (
          <Popup
            longitude={actualHoverInfo.longitude}
            latitude={actualHoverInfo.latitude}
            closeButton={false}
            closeOnClick={false}
            anchor="bottom"
            offset={[0, -15]}
            style={{ zIndex: 1000 }}
          >
            {actualHoverInfo.feature?.type === 'district' ? (
              <DistrictPopup data={actualHoverInfo} />
            ) : (
              <BuildingPopup data={actualHoverInfo} />
            )}
          </Popup>
        )}
      </MapboxMap>
    </div>
  );
};

export default MapComponent;
