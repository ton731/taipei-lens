import React from 'react';
import { Source, Layer } from 'react-map-gl/mapbox';
import { LAYER_CONFIGS, generateFillColorExpression } from '../../config/layerConfig';
import { ANALYSIS_MODULES } from '../../config/analysisModuleConfig';

/**
 * Map Layers Component - Contains building, district, and statistical area layers
 * @param {Object} props.buildingData - Building data source
 * @param {string} props.sourceLayerName - Building source layer name
 * @param {string} props.districtSourceLayer - District source layer name
 * @param {string} props.districtMapboxUrl - District Mapbox URL
 * @param {string} props.statisticalAreaSourceLayer - Statistical area source layer name
 * @param {string} props.statisticalAreaMapboxUrl - Statistical area Mapbox URL
 * @param {string} props.selectedDataLayer - Currently selected data layer
 * @param {Object} props.highlightedBuilding - Highlighted building GeoJSON
 * @param {Object} props.analysisResults - Analysis results from all modules
 */
const MapLayers = ({
  buildingData,
  sourceLayerName,
  districtSourceLayer,
  districtMapboxUrl,
  statisticalAreaSourceLayer,
  statisticalAreaMapboxUrl,
  selectedDataLayer,
  highlightedBuilding,
  analysisResults
}) => {
  // Custom 3D buildings layer configuration
  const customBuildingsLayer = {
    id: 'custom-3d-buildings',
    source: 'buildings',
    'source-layer': sourceLayerName,
    type: 'fill-extrusion',
    minzoom: 10,
    paint: {
      'fill-extrusion-color': [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        '#FF6B35',
        '#F5F5F0'
      ],
      'fill-extrusion-height': [
        'case',
        ['has', 'height'],
        ['get', 'height'],
        ['has', 'levels'],
        ['*', ['get', 'levels'], 3.5],
        10
      ],
      'fill-extrusion-base': 0,
      'fill-extrusion-opacity': 0.85
    }
  };

  // Universal outline paint configuration
  const getOutlinePaint = (outlineColor) => ({
    'line-color': outlineColor,
    'line-width': [
      'case',
      ['boolean', ['feature-state', 'hover'], false],
      3,
      0
    ],
    'line-opacity': [
      'case',
      ['boolean', ['feature-state', 'hover'], false],
      1,
      0
    ]
  });

  // Render base statistical area layer (transparent fill + border, making the entire area interactive)
  const renderBaseStatisticalAreaLayer = () => {
    return (
      <>
        {/* Transparent fill layer - makes the entire statistical area clickable */}
        <Layer
          id="statistical-area-base-fill"
          source="statistical-areas"
          source-layer={statisticalAreaSourceLayer}
          type="fill"
          minzoom={0}
          maxzoom={24}
          paint={{
            'fill-color': '#FF6B35',
            'fill-opacity': [
              'case',
              ['boolean', ['feature-state', 'hover'], false],
              0.1,    // Slightly visible on hover
              0       // Completely transparent normally
            ]
          }}
          beforeId="custom-3d-buildings"
        />
        {/* Border layer - displays statistical area boundaries */}
        <Layer
          id="statistical-area-base-outline"
          source="statistical-areas"
          source-layer={statisticalAreaSourceLayer}
          type="line"
          minzoom={0}
          maxzoom={24}
          paint={{
            'line-color': '#FF6B35',
            'line-width': [
              'case',
              ['boolean', ['feature-state', 'hover'], false],
              3,      // Thick border on hover
              0.5     // Thin border normally (lets users know it's interactive)
            ],
            'line-opacity': [
              'case',
              ['boolean', ['feature-state', 'hover'], false],
              1,      // Fully opaque on hover
              0.3     // Semi-transparent normally
            ]
          }}
          beforeId="custom-3d-buildings"
        />
      </>
    );
  };

  // Dynamically render data layer (with color fill) - using statistical area data
  const renderDataLayer = (layerKey) => {
    const config = LAYER_CONFIGS[layerKey];
    if (!config) return null;

    return (
      <React.Fragment key={layerKey}>
        <Layer
          id={`district-${layerKey}`}
          source="statistical-areas"
          source-layer={statisticalAreaSourceLayer}
          type="fill"
          minzoom={0}
          maxzoom={24}
          paint={{
            'fill-color': generateFillColorExpression(config),
            'fill-opacity': 0.65
          }}
          beforeId="custom-3d-buildings"
        />
        <Layer
          id={`district-${layerKey}-outline`}
          source="statistical-areas"
          source-layer={statisticalAreaSourceLayer}
          type="line"
          minzoom={0}
          maxzoom={24}
          paint={getOutlinePaint(config.outlineColor)}
          beforeId="custom-3d-buildings"
        />
      </React.Fragment>
    );
  };

  // Render analysis result highlight layers (universal for all modules)
  const renderAnalysisHighlightLayers = () => {
    if (!analysisResults) return null;

    return Object.entries(analysisResults).map(([moduleId, highlightData]) => {
      // Skip if this module has no analysis results
      if (!highlightData) return null;

      const moduleConfig = ANALYSIS_MODULES[moduleId];
      if (!moduleConfig) return null;

      // Handle LLM highlight (with type and ids)
      if (moduleId === 'llm' && highlightData.type && highlightData.ids) {
        const { type, ids, statistical_details, min_value, max_value } = highlightData;

        // If statistical area details exist, render with gradient colors
        if (statistical_details && statistical_details.length > 0 && min_value !== undefined && max_value !== undefined) {
          // Use percentile approach to assign colors, avoiding impact from extreme values
          // 1. Sort statistical areas by value
          const sortedDetails = [...statistical_details].sort((a, b) => a.value - b.value);

          // 2. Create CODEBASE to percentile mapping
          const percentileMap = {};
          sortedDetails.forEach((detail, index) => {
            // Calculate percentile: rank position / total count
            const percentile = sortedDetails.length > 1
              ? index / (sortedDetails.length - 1)
              : 0.5;
            percentileMap[detail.CODEBASE] = percentile;
          });

          const codebaseList = statistical_details.map(d => d.CODEBASE);

          // 3. Determine color based on percentile (based on rank rather than value)
          const colorExpression = [
            'case',
            ...statistical_details.flatMap(detail => {
              const percentile = percentileMap[detail.CODEBASE];

              // Choose color based on percentile
              // First 33.33% (lowest value) → Light orange
              // Middle 33.33% → Medium orange
              // Last 33.33% (highest value) → Dark orange
              let color;
              if (percentile < 0.3333) {
                color = moduleConfig.gradientColors.light;
              } else if (percentile < 0.6667) {
                color = moduleConfig.gradientColors.medium;
              } else {
                color = moduleConfig.gradientColors.dark;
              }

              return [
                ['==', ['get', 'CODEBASE'], detail.CODEBASE],
                color
              ];
            }),
            moduleConfig.highlightColor  // Default color (fallback)
          ];

          return (
            <React.Fragment key={`analysis-${moduleId}`}>
              {/* Fill layer - using gradient colors */}
              <Layer
                id={`analysis-highlight-${moduleId}`}
                source="statistical-areas"
                source-layer={statisticalAreaSourceLayer}
                type="fill"
                minzoom={0}
                maxzoom={24}
                paint={{
                  'fill-color': colorExpression,
                  'fill-opacity': moduleConfig.fillOpacity
                }}
                filter={['in', ['get', 'CODEBASE'], ['literal', codebaseList]]}
                beforeId="custom-3d-buildings"
              />
              {/* Border layer */}
              <Layer
                id={`analysis-highlight-${moduleId}-outline`}
                source="statistical-areas"
                source-layer={statisticalAreaSourceLayer}
                type="line"
                minzoom={0}
                maxzoom={24}
                paint={{
                  'line-color': moduleConfig.outlineColor,
                  'line-width': 1.5,
                  'line-opacity': 0.8
                }}
                filter={['in', ['get', 'CODEBASE'], ['literal', codebaseList]]}
                beforeId="custom-3d-buildings"
              />
            </React.Fragment>
          );
        }

        // If no statistical area details, use original method (single color)
        const sourceId = type === 'district' ? 'districts' : 'statistical-areas';
        const sourceLayer = type === 'district' ? districtSourceLayer : statisticalAreaSourceLayer;
        const fieldName = type === 'district' ? 'district' : 'CODEBASE';

        return (
          <React.Fragment key={`analysis-${moduleId}`}>
            {/* Fill layer */}
            <Layer
              id={`analysis-highlight-${moduleId}`}
              source={sourceId}
              source-layer={sourceLayer}
              type="fill"
              minzoom={0}
              maxzoom={24}
              paint={{
                'fill-color': moduleConfig.highlightColor,
                'fill-opacity': moduleConfig.fillOpacity
              }}
              filter={['in', ['get', fieldName], ['literal', ids]]}
              beforeId="custom-3d-buildings"
            />
            {/* Border layer */}
            <Layer
              id={`analysis-highlight-${moduleId}-outline`}
              source={sourceId}
              source-layer={sourceLayer}
              type="line"
              minzoom={0}
              maxzoom={24}
              paint={{
                'line-color': moduleConfig.outlineColor,
                'line-width': moduleConfig.outlineWidth,
                'line-opacity': 1
              }}
              filter={['in', ['get', fieldName], ['literal', ids]]}
              beforeId="custom-3d-buildings"
            />
          </React.Fragment>
        );
      }

      // Handle other analysis modules (only ids array)
      const highlightedCodes = Array.isArray(highlightData) ? highlightData : [];
      if (highlightedCodes.length === 0) return null;

      return (
        <React.Fragment key={`analysis-${moduleId}`}>
          {/* Fill layer */}
          <Layer
            id={`analysis-highlight-${moduleId}`}
            source="statistical-areas"
            source-layer={statisticalAreaSourceLayer}
            type="fill"
            minzoom={0}
            maxzoom={24}
            paint={{
              'fill-color': moduleConfig.highlightColor,
              'fill-opacity': moduleConfig.fillOpacity
            }}
            filter={['in', ['get', 'CODEBASE'], ['literal', highlightedCodes]]}
            beforeId="custom-3d-buildings"
          />
          {/* Border layer */}
          <Layer
            id={`analysis-highlight-${moduleId}-outline`}
            source="statistical-areas"
            source-layer={statisticalAreaSourceLayer}
            type="line"
            minzoom={0}
            maxzoom={24}
            paint={{
              'line-color': moduleConfig.outlineColor,
              'line-width': moduleConfig.outlineWidth,
              'line-opacity': 1
            }}
            filter={['in', ['get', 'CODEBASE'], ['literal', highlightedCodes]]}
            beforeId="custom-3d-buildings"
          />
        </React.Fragment>
      );
    });
  };

  return (
    <>
      {/* Building 3D Layer */}
      {sourceLayerName && buildingData && (
        <Source id="buildings" {...buildingData}>
          <Layer {...customBuildingsLayer} />
        </Source>
      )}

      {/* District Layer - Reserved but unused (may be needed in the future) */}
      {districtSourceLayer && districtMapboxUrl && (
        <Source
          id="districts"
          type="vector"
          url={districtMapboxUrl}
        >
          {/* Districts currently do not display any layers */}
        </Source>
      )}

      {/* Statistical Area Layer */}
      {statisticalAreaSourceLayer && statisticalAreaMapboxUrl && (
        <Source
          id="statistical-areas"
          type="vector"
          url={statisticalAreaMapboxUrl}
        >
          {/* Base layer: displayed when no data layer is selected, only has hover border */}
          {!selectedDataLayer && renderBaseStatisticalAreaLayer()}

          {/* Data layer: displayed when data layer is selected, includes color fill */}
          {selectedDataLayer && renderDataLayer(selectedDataLayer)}

          {/* Analysis result highlight layer: displays analysis results from all modules */}
          {renderAnalysisHighlightLayers()}
        </Source>
      )}

      {/* Building Highlight Layer */}
      {highlightedBuilding && (
        <Source id="building-highlight" type="geojson" data={highlightedBuilding}>
          <Layer
            id="building-highlight-outline"
            type="line"
            paint={{
              'line-color': '#ff6600',
              'line-width': 3,
              'line-opacity': 0.9
            }}
          />
        </Source>
      )}
    </>
  );
};

export default MapLayers;
