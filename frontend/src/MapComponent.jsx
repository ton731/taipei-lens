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
import ContactInfo from './components/ContactInfo';
import TeamMarker from './components/map/TeamMarker';

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

// 團隊位置座標
const TEAM_LOCATION = {
  longitude: 121.54712993973214,
  latitude: 25.01387196243084
};

const MapComponent = ({ hoverInfo: externalHoverInfo, setHoverInfo: externalSetHoverInfo, llmHighlightAreas, clearLlmHighlight }) => {
  // Opening animation state
  const [isOpeningAnimationComplete, setIsOpeningAnimationComplete] = useState(false);
  const [maxBounds, setMaxBounds] = useState(undefined);
  
  // Team marker state
  const [showTeamMarker, setShowTeamMarker] = useState(false);

  // Layer selection state
  const [selectedDataLayer, setSelectedDataLayer] = useState(null);
  const [activeLegends, setActiveLegends] = useState([]);
  
  // 結構脆弱度圖層的地震強度狀態 - 使用離散值
  const [earthquakeIntensity, setEarthquakeIntensity] = useState('6弱');

  // General analysis results state - stores analysis results from all modules
  const [analysisResults, setAnalysisResults] = useState({
    roadGreening: null,
    seismicStrengthening: null,
    parkSiting: null,
    urbanRenewal: null
  });

  // Module configuration state - stores weights and threshold configurations for all modules
  const [moduleConfigs, setModuleConfigs] = useState({
    roadGreening: {
      // Environmental Protection Bureau (first scenario)
      weights: { thermal_stress: 0.50, greening_potential: 0.30, population_benefit: 0.20 },
      threshold: 0.8
    },
    seismicStrengthening: {
      // Public Works Bureau (first scenario)
      weights: { building_vulnerability: 0.50, site_amplification: 0.30, population_exposure: 0.20 },
      threshold: 0.75
    },
    parkSiting: {
      // Public Works Bureau (first scenario)
      weights: { green_space_service_gap: 0.50, population_demand: 0.25, environmental_stress: 0.15, social_equity: 0.10 },
      threshold: 0.8
    },
    urbanRenewal: {
      // Disaster Prevention (first scenario)
      weights: { building_vulnerability: 0.50, environmental_quality: 0.20, population_exposure: 0.30 },
      threshold: 0.5
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
    setSelectedDataLayer(layerId);

    // Clear AI highlight when opening layer
    if (layerId && clearLlmHighlight) {
      clearLlmHighlight();
    }
    
    if (layerId === 'structural_vulnerability') {
      
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
    setEarthquakeIntensity(intensity);
  }, []);

  // General analysis execution callback - shared by all modules
  const handleAnalysisExecute = useCallback((moduleId, highlightedCodes) => {
    
    // Clear all other module results first, then set the new result
    setAnalysisResults(prev => {
      const clearedResults = Object.keys(prev).reduce((acc, key) => {
        acc[key] = null;
        return acc;
      }, {});
      
      return {
        ...clearedResults,
        [moduleId]: highlightedCodes
      };
    });

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
  
  // Handle team icon click
  const handleTeamIconClick = useCallback(() => {
    // Toggle team marker
    if (showTeamMarker) {
      // 如果已經顯示，就關閉它
      setShowTeamMarker(false);
    } else {
      // 如果未顯示，飛到位置並顯示
      if (mapInstance) {
        // 飛到團隊位置，往北偏移視角中心點，讓popup顯示在畫面下方1/3處
        mapInstance.flyTo({
          center: [TEAM_LOCATION.longitude+0.001, TEAM_LOCATION.latitude + 0.0018], // 往北偏移，讓標記點在畫面下方
          zoom: 17.2,
          bearing: 45,
          pitch:75,  // 接近最大傾斜角度，從很低的視線高度往上看
          duration: 2000,
          essential: true
        });
        
        // 顯示團隊標記
        setShowTeamMarker(true);
      }
    }
  }, [mapInstance, showTeamMarker]);

  // Handle LLM highlight areas
  useEffect(() => {
    if (llmHighlightAreas) {

      // When AI highlight appears, clear all Toolbox layers and analysis results
      setSelectedDataLayer(null);
      setAnalysisResults({
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
      
      // If structural vulnerability layer, add earthquake intensity info
      if (selectedDataLayer === 'structural_vulnerability') {
        title = `${config.title} (Earthquake Intensity: ${earthquakeIntensity})`;
        minLabel = `0% (No Risk)`;
        maxLabel = `100% (Extreme Risk)`;
      }
      
      // If LST layer, display original temperature value range
      if (selectedDataLayer === 'lst') {
        // Keep original logic, as config.minValue and config.maxValue are already set to original temperature values
        minLabel = `${config.minValue}${config.unit}`;
        maxLabel = `${config.maxValue}${config.unit}`;
      }
      
      // If UTFVI layer, display comfort labels
      if (selectedDataLayer === 'utfvi' && config.comfortLabels) {
        minLabel = config.comfortLabels.min;
        maxLabel = config.comfortLabels.max;
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

        {/* Team marker - only show after animation and when toggled */}
        {isOpeningAnimationComplete && (
          <TeamMarker
            longitude={TEAM_LOCATION.longitude}
            latitude={TEAM_LOCATION.latitude}
            showPopup={showTeamMarker}
            onClose={() => setShowTeamMarker(false)}
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

        {/* Click Popup - only show after animation */}
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

      {/* Contact Info - only show after animation */}
      {isOpeningAnimationComplete && <ContactInfo onIconClick={handleTeamIconClick} />}
    </div>
  );
};

export default MapComponent;
