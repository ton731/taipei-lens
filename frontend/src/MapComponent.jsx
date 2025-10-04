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
import OpeningAnimation from './components/map/OpeningAnimation';

// Hooks
import { useMapInitialization } from './hooks/useMapInitialization';
import { useBuildingData } from './hooks/useBuildingData';
import { useDistrictData } from './hooks/useDistrictData';
import { useStatisticalAreaData } from './hooks/useStatisticalAreaData';
import { useMapInteractions } from './hooks/useMapInteractions';

// Config
import { LAYER_CONFIGS, generateLegendGradient } from './config/layerConfig';

// 視角配置常數
const BUILDING_VIEW_ZOOM = 16.5; // 結構脆弱度圖層的視角高度 (數值越大越接近地面，範圍通常是 0-22)
const ZOOM_ANIMATION_DURATION = 1500; // 視角變化動畫持續時間（毫秒）

const MapComponent = ({ hoverInfo: externalHoverInfo, setHoverInfo: externalSetHoverInfo, llmHighlightAreas, clearLlmHighlight }) => {
  // Opening animation state
  const [isOpeningAnimationComplete, setIsOpeningAnimationComplete] = useState(false);
  const [maxBounds, setMaxBounds] = useState(undefined);

  // Layer selection state
  const [selectedDataLayer, setSelectedDataLayer] = useState(null);
  const [activeLegends, setActiveLegends] = useState([]);
  
  // 結構脆弱度圖層的地震強度狀態 - 使用離散值
  const [earthquakeIntensity, setEarthquakeIntensity] = useState('6弱');

  // General analysis results state - stores analysis results from all modules
  const [analysisResults, setAnalysisResults] = useState({
    test: null,
    roadGreening: null,
    seismicStrengthening: null,
    parkSiting: null,
    urbanRenewal: null
  });

  // Module configuration state - stores weights and threshold configurations for all modules
  const [moduleConfigs, setModuleConfigs] = useState({
    test: {
      weights: { building_age: 0.7, pop_density: 0.3 },
      threshold: 0.4
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

  // Use custom hooks
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
  } = useMapInteractions(
    mapInstance,
    customBuildingData,
    statisticalAreaSourceLayer,
    externalSetHoverInfo || null,
    isOpeningAnimationComplete // 互動只在動畫完成後啟用
  );

  // Use external hoverInfo if provided, otherwise use internal
  const actualHoverInfo = externalHoverInfo !== undefined ? externalHoverInfo : hoverInfo;

  // Handle layer changes from DataLayersModule
  const handleDataLayerChange = useCallback((layerId) => {
    console.log('MapComponent: 接收到圖層變化', { 
      newLayerId: layerId, 
      currentLayer: selectedDataLayer 
    });
    setSelectedDataLayer(layerId);

    // Clear AI highlight when opening layer
    if (layerId && clearLlmHighlight) {
      clearLlmHighlight();
    }
    
    if (layerId === 'structural_vulnerability') {
      console.log('MapComponent: 選擇了結構脆弱度圖層，當前地震強度:', earthquakeIntensity);
      
      // 自動調整地圖視角到較低的高度以顯示建築物細節
      if (mapInstance) {
        const currentCenter = mapInstance.getCenter();
        const currentBearing = mapInstance.getBearing();
        const currentPitch = mapInstance.getPitch();
        
        mapInstance.flyTo({
          center: currentCenter,
          zoom: BUILDING_VIEW_ZOOM,
          bearing: currentBearing,
          pitch: currentPitch,
          duration: ZOOM_ANIMATION_DURATION,
          essential: true
        });
      }
    }
  }, [clearLlmHighlight, selectedDataLayer, earthquakeIntensity, mapInstance]);

  // 處理地震強度變化
  const handleEarthquakeIntensityChange = useCallback((intensity) => {
    console.log('地震強度變化:', intensity);
    setEarthquakeIntensity(intensity);
  }, []);

  // General analysis execution callback - shared by all modules
  const handleAnalysisExecute = useCallback((moduleId, highlightedCodes) => {
    console.log(`[${moduleId}] Analysis executed. Highlighted districts:`, highlightedCodes.length);
    setAnalysisResults(prev => ({
      ...prev,
      [moduleId]: highlightedCodes
    }));

    // Clear AI highlight when executing analysis
    if (clearLlmHighlight) {
      clearLlmHighlight();
    }
  }, [clearLlmHighlight]);

  // General analysis clear callback - shared by all modules
  const handleAnalysisClear = useCallback((moduleId) => {
    setAnalysisResults(prev => ({
      ...prev,
      [moduleId]: null
    }));
  }, []);

  // Clear raw data layer selection - called when executing analysis
  const handleClearDataLayer = useCallback(() => {
    setSelectedDataLayer(null);
  }, []);

  // Update module configuration - shared by all modules
  const handleModuleConfigChange = useCallback((moduleId, config) => {
    setModuleConfigs(prev => ({
      ...prev,
      [moduleId]: { ...prev[moduleId], ...config }
    }));
  }, []);

  // Handle animation completion
  const handleAnimationComplete = useCallback(() => {
    // 停止可能尚未完成的相機動畫
    if (mapInstance && mapInstance.stop) {
      try { mapInstance.stop(); } catch (_) {}
    }

    setIsOpeningAnimationComplete(true);

    // 暫不設定 maxBounds，以排除遞迴來源可能性
    // 如需再加回，請在確認穩定後逐步恢復
  }, [mapInstance]);

  // Handle LLM highlight areas
  useEffect(() => {
    if (llmHighlightAreas) {
      console.log('LLM highlight areas received:', llmHighlightAreas);

      // When AI highlight appears, clear all Toolbox layers and analysis results
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
      // Clear LLM highlight
      setAnalysisResults(prev => ({
        ...prev,
        llm: null
      }));
    }
  }, [llmHighlightAreas]);

  // Handle layer selection changes and update legend
  useEffect(() => {
    if (!selectedDataLayer) {
      setActiveLegends([]);
      return;
    }

    const config = LAYER_CONFIGS[selectedDataLayer];
    if (config) {
      let title = config.title;
      let minLabel = `${config.minValue}${config.unit}`;
      let maxLabel = `${config.maxValue.toLocaleString()}${config.unit}`;
      
      // 如果是結構脆弱度圖層，添加地震強度信息
      if (selectedDataLayer === 'structural_vulnerability') {
        title = `${config.title} (地震強度: ${earthquakeIntensity})`;
        minLabel = `0% (無風險)`;
        maxLabel = `100% (極高風險)`;
      }
      
      // 如果是 LST 圖層，顯示原始溫度值範圍
      if (selectedDataLayer === 'lst') {
        // 保持原始邏輯，因為 config.minValue 和 config.maxValue 已經設置為原始溫度值
        minLabel = `${config.minValue}${config.unit}`;
        maxLabel = `${config.maxValue}${config.unit}`;
      }
      
      setActiveLegends([{
        title: title,
        type: 'gradient',
        gradient: generateLegendGradient(config),
        minLabel: minLabel,
        maxLabel: maxLabel
      }]);
    }
  }, [selectedDataLayer, earthquakeIntensity]);

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
        Please set VITE_MAPBOX_ACCESS_PUBLIC_TOKEN in the .env file
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
        projection='globe'
        maxBounds={maxBounds}
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
        {/* Opening animation */}
        {isStyleLoaded && !isOpeningAnimationComplete && (
          <OpeningAnimation
            mapInstance={mapInstance}
            onAnimationComplete={handleAnimationComplete}
          />
        )}

        {/* Map layers：動畫完成後再渲染，降低動畫期間的計算負擔 */}
        {isStyleLoaded && isOpeningAnimationComplete && (
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
            earthquakeIntensity={earthquakeIntensity}
          />
        )}

        {/* Map title - only show after animation */}
        {isOpeningAnimationComplete && <MapTitle />}

        {/* Toolbox panel - only show after animation */}
        {isOpeningAnimationComplete && <ToolboxPanel
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
          earthquakeIntensity={earthquakeIntensity}
          onEarthquakeIntensityChange={handleEarthquakeIntensityChange}
        />}

        {/* Hover Popup - only show after animation */}
        {isOpeningAnimationComplete && actualHoverInfo && (
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
