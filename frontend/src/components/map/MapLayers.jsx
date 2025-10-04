import React, { useEffect, useRef } from 'react';
import { Source, Layer } from 'react-map-gl/mapbox';
import { LAYER_CONFIGS, generateFillColorExpression, interpolateFragilityCurve } from '../../config/layerConfig';
import { ANALYSIS_MODULES } from '../../config/analysisModuleConfig';

/**
 * 地圖圖層組件 - 包含建築物、行政區和統計區圖層
 * @param {Object} props.buildingData - 建築物資料來源
 * @param {string} props.sourceLayerName - 建築物 source layer 名稱
 * @param {string} props.districtSourceLayer - 行政區 source layer 名稱
 * @param {string} props.districtMapboxUrl - 行政區 Mapbox URL
 * @param {string} props.statisticalAreaSourceLayer - 統計區域 source layer 名稱
 * @param {string} props.statisticalAreaMapboxUrl - 統計區域 Mapbox URL
 * @param {string} props.selectedDataLayer - 當前選擇的資料圖層
 * @param {Object} props.highlightedBuilding - 高亮的建築物 GeoJSON
 * @param {Object} props.analysisResults - 所有模組的分析結果
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
  analysisResults,
  earthquakeIntensity
}) => {
  // 生成建築物顏色表達式 - 支援結構脆弱度圖層
  const getBuildingColorExpression = () => {
    if (selectedDataLayer === 'structural_vulnerability') {
      console.log('MapLayers: 結構脆弱度圖層被選中，地震強度:', earthquakeIntensity);
      const config = LAYER_CONFIGS.structural_vulnerability;
      
      // 暫時使用簡化的方案：根據建築物年齡來估計脆弱度
      // 年齡越大，在高地震強度下越脆弱
      return [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        '#FF6B35', // hover 顏色
        [
          'case',
          ['has', 'age'],
          [
            'interpolate',
            ['linear'],
            // 使用建築物年齡作為代理指標
            // 並根據地震強度調整顏色深淺
            ['*', 
              ['get', 'age'],
              // 地震強度越大，乘數越大
              ['case',
                ['==', earthquakeIntensity, '3'], 0.01,
                ['==', earthquakeIntensity, '5弱'], 0.015,
                ['==', earthquakeIntensity, '5強'], 0.02,
                ['==', earthquakeIntensity, '6弱'], 0.025,
                ['==', earthquakeIntensity, '6強'], 0.03,
                ['==', earthquakeIntensity, '7'], 0.035,
                0.02
              ]
            ],
            0, '#fff7e6',      // 與建築屋齡相同的配色
            0.2, '#fdd49e',
            0.4, '#fdae6b',
            0.6, '#fd8d3c',
            0.8, '#e6550d',
            1, '#8c3a00'
          ],
          '#f5f5f5' // 沒有 age 資料的建築物用淺灰色而非純白色
        ]
      ];
    } else {
      return [
        'case',
        ['boolean', ['feature-state', 'hover'], false],
        '#FF6B35',
        '#f8f8f8' // 預設使用淺灰色而非純白色，避免與可能的黑色背景產生對比問題
      ];
    }
  };

  // Custom 3D buildings layer configuration
  const customBuildingsLayer = {
    id: 'custom-3d-buildings',
    source: 'buildings',
    'source-layer': sourceLayerName,
    type: 'fill-extrusion',
    minzoom: 10,
    paint: {
      'fill-extrusion-color': getBuildingColorExpression(),
      'fill-extrusion-height': [
        'case',
        ['has', 'height'],
        ['get', 'height'],
        ['has', 'levels'],
        ['*', ['get', 'levels'], 3.5],
        10
      ],
      'fill-extrusion-base': 0,
      'fill-extrusion-opacity': selectedDataLayer === 'structural_vulnerability' ? 0.9 : 0.85
    }
  };

  // 通用的 outline paint 配置
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

  // 渲染統計區基礎圖層（透明填充 + 邊框，使整個區域都可互動）
  const renderBaseStatisticalAreaLayer = () => {
    return (
      <>
        {/* 透明填充層 - 使整個統計區可點擊 */}
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
              0.1,    // hover 時略微可見
              0       // 平常時完全透明
            ]
          }}
          beforeId="custom-3d-buildings"
        />
        {/* 邊框層 - 顯示統計區邊界 */}
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
              3,      // hover 時粗邊框
              0.5     // 平常時細邊框（讓用戶知道可以互動）
            ],
            'line-opacity': [
              'case',
              ['boolean', ['feature-state', 'hover'], false],
              1,      // hover 時完全不透明
              0.3     // 平常時半透明
            ]
          }}
          beforeId="custom-3d-buildings"
        />
      </>
    );
  };

  // 動態渲染資料圖層（帶顏色填充）- 使用統計區域資料
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

  // 渲染分析結果的 highlight 圖層（通用於所有模組）
  const renderAnalysisHighlightLayers = () => {
    if (!analysisResults) return null;

    return Object.entries(analysisResults).map(([moduleId, highlightData]) => {
      // 如果該模組沒有分析結果，跳過
      if (!highlightData) return null;

      const moduleConfig = ANALYSIS_MODULES[moduleId];
      if (!moduleConfig) return null;

      // 處理 LLM highlight（有 type 和 ids）
      if (moduleId === 'llm' && highlightData.type && highlightData.ids) {
        const { type, ids, statistical_details, min_value, max_value } = highlightData;

        // 如果有統計區詳細資料，使用漸變色渲染
        if (statistical_details && statistical_details.length > 0 && min_value !== undefined && max_value !== undefined) {
          // 使用百分位數（percentile）方式來分配顏色，避免極端值影響
          // 1. 先將統計區按照 value 排序
          const sortedDetails = [...statistical_details].sort((a, b) => a.value - b.value);

          // 2. 建立 CODEBASE 到百分位數的映射
          const percentileMap = {};
          sortedDetails.forEach((detail, index) => {
            // 計算百分位數：排名位置 / 總數量
            const percentile = sortedDetails.length > 1
              ? index / (sortedDetails.length - 1)
              : 0.5;
            percentileMap[detail.CODEBASE] = percentile;
          });

          const codebaseList = statistical_details.map(d => d.CODEBASE);

          // 3. 根據百分位數來決定顏色（基於排名而非數值）
          const colorExpression = [
            'case',
            ...statistical_details.flatMap(detail => {
              const percentile = percentileMap[detail.CODEBASE];

              // 根據百分位數來選擇顏色
              // 前 33.33% (最低值) → 淺橘色
              // 中間 33.33% → 中橘色
              // 後 33.33% (最高值) → 深橘色
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
            moduleConfig.highlightColor  // 預設顏色（fallback）
          ];

          return (
            <React.Fragment key={`analysis-${moduleId}`}>
              {/* 填充圖層 - 使用漸變色 */}
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
              {/* 邊框圖層 */}
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

        // 如果沒有統計區詳細資料，使用原來的方式（單一顏色）
        const sourceId = type === 'district' ? 'districts' : 'statistical-areas';
        const sourceLayer = type === 'district' ? districtSourceLayer : statisticalAreaSourceLayer;
        const fieldName = type === 'district' ? 'district' : 'CODEBASE';

        return (
          <React.Fragment key={`analysis-${moduleId}`}>
            {/* 填充圖層 */}
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
            {/* 邊框圖層 */}
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

      // 處理其他分析模組（只有 ids 陣列）
      const highlightedCodes = Array.isArray(highlightData) ? highlightData : [];
      if (highlightedCodes.length === 0) return null;

      return (
        <React.Fragment key={`analysis-${moduleId}`}>
          {/* 填充圖層 */}
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
          {/* 邊框圖層 */}
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
      {/* 建築物 3D 圖層 */}
      {sourceLayerName && buildingData && (
        <Source id="buildings" {...buildingData}>
          <Layer {...customBuildingsLayer} />
        </Source>
      )}

      {/* 行政區圖層 - 保留但不使用（未來可能需要） */}
      {districtSourceLayer && districtMapboxUrl && (
        <Source
          id="districts"
          type="vector"
          url={districtMapboxUrl}
        >
          {/* 行政區目前不顯示任何圖層 */}
        </Source>
      )}

      {/* 統計區域圖層 */}
      {statisticalAreaSourceLayer && statisticalAreaMapboxUrl && (
        <Source
          id="statistical-areas"
          type="vector"
          url={statisticalAreaMapboxUrl}
        >
          {/* 基礎圖層：沒有選擇資料圖層時顯示，或選擇結構脆弱度時也顯示（因為結構脆弱度是在建築物上著色） */}
          {(!selectedDataLayer || selectedDataLayer === 'structural_vulnerability') && renderBaseStatisticalAreaLayer()}

          {/* 資料圖層：選擇資料圖層時顯示，包含顏色填充（但排除結構脆弱度，因為它是在建築物上著色） */}
          {selectedDataLayer && selectedDataLayer !== 'structural_vulnerability' && renderDataLayer(selectedDataLayer)}

          {/* 分析結果 highlight 圖層：顯示所有模組的分析結果 */}
          {renderAnalysisHighlightLayers()}
        </Source>
      )}

      {/* 建築物高亮圖層 */}
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
