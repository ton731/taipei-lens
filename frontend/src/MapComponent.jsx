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

const MapComponent = ({ hoverInfo: externalHoverInfo, setHoverInfo: externalSetHoverInfo, llmHighlightAreas, clearLlmHighlight }) => {
  // Opening animation state
  const [isOpeningAnimationComplete, setIsOpeningAnimationComplete] = useState(false);
  const [maxBounds, setMaxBounds] = useState(undefined);

  // Layer selection state
  const [selectedDataLayer, setSelectedDataLayer] = useState(null);
  const [activeLegends, setActiveLegends] = useState([]);

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
  } = useMapInteractions(mapInstance, customBuildingData, statisticalAreaSourceLayer, externalSetHoverInfo || null);

  // Use external hoverInfo if provided, otherwise use internal
  const actualHoverInfo = externalHoverInfo !== undefined ? externalHoverInfo : hoverInfo;

  // Handle layer changes from DataLayersModule
  const handleDataLayerChange = useCallback((layerId) => {
    setSelectedDataLayer(layerId);

    // Clear AI highlight when opening layer
    if (layerId && clearLlmHighlight) {
      clearLlmHighlight();
    }
  }, [clearLlmHighlight]);

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
    // 停止可能尚未完成的相機動畫，避免與後續 bounds 設定產生競態
    if (mapInstance && mapInstance.stop) {
      try { mapInstance.stop(); } catch (_) {}
    }

    setIsOpeningAnimationComplete(true);

    // 延後設定 bounds，確保地圖已 idle，避免觸發矩陣重算遞迴
    setTimeout(() => {
      setMaxBounds([
        [121.46, 24.95],  // 西南角 [經度, 緯度]
        [121.67, 25.20]   // 東北角 [經度, 緯度]
      ]);
    }, 300);
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
        projection='mercator'
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

        {/* Map layers */}
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
